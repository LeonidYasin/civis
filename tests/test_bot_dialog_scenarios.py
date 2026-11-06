import sqlite3
import json
import time
from pathlib import Path
import pytest

import database
import mcp_client


def test_start_to_offer_publication_scenario(bot_session):
    """
    Scenario:
    1. New citizen arrives: /start -> language -> onboarding profile (name, about, values, role, format).
    2. Citizen creates an offer: /offer -> enters description.
    3. Bot responds with confirmation and main menu.
    4. Dual-write verified:
       - Saved to Civis SQLite database (`offers`).
       - Enqueued to `pending_marketplace_sync` with compliant Marketplace OS payload.
    5. MCP synchronization executes:
       - Calls register-user endpoint to provision mcr_ key.
       - Publishes listing to Marketplace OS catalog.
       - Pending sync status updates to 'synced'.
    """
    driver, recorder, mcp_mock, db_path = bot_session
    tg_id = 777001
    username = "ivan_civis"

    # -------------------------------------------------------------
    # Step 1: /start
    # -------------------------------------------------------------
    driver.send_text(tg_id=tg_id, text="/start", username=username)
    assert len(recorder.records) >= 1
    assert "Choose your language" in recorder.last_text

    # -------------------------------------------------------------
    # Step 2: Select language 'Русский'
    # -------------------------------------------------------------
    recorder.clear()
    driver.send_text(tg_id=tg_id, text="Русский", username=username)
    assert any("Как вас зовут?" in t for t in recorder.all_texts)

    # -------------------------------------------------------------
    # Step 3: Enter Name
    # -------------------------------------------------------------
    recorder.clear()
    driver.send_text(tg_id=tg_id, text="Иван Иванов", username=username)
    assert any("Расскажите немного о себе" in t for t in recorder.all_texts)

    # -------------------------------------------------------------
    # Step 4: Enter About
    # -------------------------------------------------------------
    recorder.clear()
    driver.send_text(tg_id=tg_id, text="Python & AI Архитектор, строю ботов и интеграции", username=username)
    assert any("Выберите 3 ценности" in t for t in recorder.all_texts)

    # -------------------------------------------------------------
    # Step 5: Select 3 valid values -> Auto-transitions to Role
    # -------------------------------------------------------------
    recorder.clear()
    driver.send_text(tg_id=tg_id, text="Честность", username=username)
    driver.send_text(tg_id=tg_id, text="Экспертиза", username=username)
    driver.send_text(tg_id=tg_id, text="Инициатива", username=username)
    assert any("Какова ваша основная роль?" in t or "role" in t.lower() for t in recorder.all_texts)

    # -------------------------------------------------------------
    # Step 6: Select Role 'Исполнитель'
    # -------------------------------------------------------------
    recorder.clear()
    driver.send_text(tg_id=tg_id, text="Исполнитель", username=username)
    assert any("формат" in t.lower() or "format" in t.lower() for t in recorder.all_texts)

    # -------------------------------------------------------------
    # Step 7: Select Format 'Любой' -> Profile Completed
    # -------------------------------------------------------------
    recorder.clear()
    driver.send_text(tg_id=tg_id, text="Любой", username=username)
    assert any("Поздравляем" in t or "гражданин" in t.lower() for t in recorder.all_texts)

    # Verify user state in SQLite DB
    user = database.get_user(tg_id)
    assert user is not None
    assert user["status"] == "completed"
    assert user["name"] == "Иван Иванов"
    assert user["role"] == "Executor"
    assert user["language"] == "ru"

    # -------------------------------------------------------------
    # Step 8: Create Offer (/offer) -> Select Category -> Offer Text
    # -------------------------------------------------------------
    recorder.clear()
    driver.send_text(tg_id=tg_id, text="/offer", username=username)
    assert any("Select the category for your offer" in t or "категорию" in t.lower() for t in recorder.all_texts)

    # Step 8b: Select Category 'Услуги'
    recorder.clear()
    driver.send_text(tg_id=tg_id, text="Услуги", username=username)
    assert any("Category selected: Услуги" in t or "Опишите ваше предложение" in t for t in recorder.all_texts)

    # -------------------------------------------------------------
    # Step 9: Send Offer Content -> Publication
    # -------------------------------------------------------------
    recorder.clear()
    offer_text = "Разработка Telegram ботов на Python и интеграция с Marketplace OS"
    driver.send_text(tg_id=tg_id, text=offer_text, username=username)

    # Check bot response
    assert any("опубликовано" in t.lower() or "offer" in t.lower() for t in recorder.all_texts)

    # -------------------------------------------------------------
    # Step 10: Verify Local Database Persistence (Dual-Write Local)
    # -------------------------------------------------------------
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, tg_id, text FROM offers WHERE tg_id = ?", (tg_id,))
    saved_offers = cur.fetchall()
    assert len(saved_offers) == 1
    offer_id, db_tg_id, db_text = saved_offers[0]
    assert db_tg_id == tg_id
    assert db_text == offer_text

    # Verify pending queue insertion
    cur.execute("""
        SELECT id, entity_type, entity_id, payload, status 
        FROM pending_marketplace_sync 
        WHERE tg_id = ?
    """, (tg_id,))
    sync_rows = cur.fetchall()
    conn.close()

    assert len(sync_rows) == 1
    sync_id, entity_type, entity_id, raw_payload, status = sync_rows[0]
    assert entity_type == "offer"
    assert entity_id == offer_id
    payload = json.loads(raw_payload)

    # Check schema mapping
    assert payload["kind"] == "offer"
    assert "Telegram ботов" in payload["title"]
    assert payload["category"] in mcp_client.VALID_MCP_CATEGORIES

    # -------------------------------------------------------------
    # Step 11: Execute / Verify MCP Synchronization
    # -------------------------------------------------------------
    # Give background thread a split-second or flush pending items
    time.sleep(0.2)
    mcp_client.process_all_pending_syncs(max_items=10)

    # Verify that MCP Mock received expected API calls
    register_calls = [c for c in mcp_mock.calls if "register-user" in c["url"]]
    assert len(register_calls) == 1
    assert register_calls[0]["payload"]["tg_id"] == tg_id

    rpc_calls = [c for c in mcp_mock.calls if "/mcp" in c["url"]]
    methods_called = [c["payload"].get("params", {}).get("name") for c in rpc_calls]
    assert "create_listing" in methods_called
    assert "preview_listing" in methods_called
    assert "publish_listing" in methods_called

    # Verify pending queue status changed to 'synced'
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT status, mcp_listing_id FROM pending_marketplace_sync WHERE id = ?", (sync_id,))
    final_status, mcp_listing_id = cur.fetchone()
    conn.close()

    assert final_status == "synced"
    assert mcp_listing_id is not None
    assert mcp_listing_id.startswith("lst_mock_")


def test_request_publication_scenario(bot_session):
    """
    Scenario for an existing citizen publishing a request:
    1. Seed an existing citizen with completed profile.
    2. Citizen sends /request.
    3. Citizen selects category 'Такси'.
    4. Citizen enters request description.
    5. Bot confirms publication and dual-write synchronizes to Marketplace OS.
    """
    driver, recorder, mcp_mock, db_path = bot_session
    tg_id = 888002
    username = "elena_civis"

    # Seed existing citizen
    database.save_user(
        tg_id=tg_id,
        username=username,
        name="Елена Смирнова",
        telegram_contact=f"@{username}",
        about_text="Product Manager",
        user_values="Honesty, Expertise, Openness",
        role="Customer",
        format="Any",
        language="ru",
        status="completed"
    )

    # 1. /request
    recorder.clear()
    driver.send_text(tg_id=tg_id, text="/request", username=username)
    assert any("Select the category for your request" in t or "категорию" in t.lower() for t in recorder.all_texts)

    # 2. Select Category 'Такси'
    recorder.clear()
    driver.send_text(tg_id=tg_id, text="Такси", username=username)
    assert any("Category selected: Такси" in t or "Опишите ваш запрос" in t for t in recorder.all_texts)

    # 3. Enter request text
    recorder.clear()
    req_text = "Нужно такси в аэропорт завтра к 08:00 утра с детским креслом"
    driver.send_text(tg_id=tg_id, text=req_text, username=username)

    # Verify confirmation message
    assert any("опубликован" in t.lower() or "request" in t.lower() for t in recorder.all_texts)

    # 4. Verify local database persistence
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, text, category FROM requests WHERE tg_id = ?", (tg_id,))
    req_rows = cur.fetchall()
    assert len(req_rows) == 1
    req_id, db_text, db_cat = req_rows[0]
    assert db_text == req_text
    assert db_cat == "taxi"

    # Verify sync queue
    cur.execute("SELECT entity_type, payload, status FROM pending_marketplace_sync WHERE tg_id = ?", (tg_id,))
    sync_rows = cur.fetchall()
    conn.close()

    assert len(sync_rows) == 1
    entity_type, raw_payload, status = sync_rows[0]
    assert entity_type == "request"
    payload = json.loads(raw_payload)
    assert payload["kind"] == "request"
    assert payload["category"] in ("rides", "delivery", "other")

    # 5. Process sync
    time.sleep(0.2)
    mcp_client.process_all_pending_syncs(max_items=10)

    # Verify sync succeeded in DB
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT status, mcp_listing_id FROM pending_marketplace_sync WHERE tg_id = ?", (tg_id,))
    final_status, mcp_listing_id = cur.fetchone()
    conn.close()

    assert final_status == "synced"
    assert mcp_listing_id is not None
