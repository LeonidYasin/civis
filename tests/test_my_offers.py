import time
import json
import sqlite3
from datetime import datetime
from pathlib import Path
import pytest
from telebot.apihelper import ApiTelegramException

import database
import mcp_client
import handlers

try:
    from keyboards import CLICK_TRACKER
except ImportError:
    class DummyClickTracker:
        def clear(self):
            pass
        def get(self, uid):
            return 0.0
        def set(self, uid, ts):
            pass
    CLICK_TRACKER = DummyClickTracker()


# Helper to seed a completed user profile
def seed_user(tg_id=777001, username="test_citizen", name="Test Citizen", language="ru"):
    database.save_user(
        tg_id=tg_id,
        username=username,
        name=name,
        telegram_contact=f"@{username}",
        about_text="Professional test bio text exceeding minimum 20 chars.",
        user_values="Честность, Экспертиза, Инициатива",
        role="Executor",
        format="Любой",
        language=language,
        status="completed"
    )


# ---------------------------------------------------------------------------
# Tests 1-5: Presentation and Pagination Navigation
# ---------------------------------------------------------------------------

def test_empty_list(bot_session):
    """0 offers -> empty state message, act:offer & hub:mkt buttons, pagination hidden."""
    driver, recorder, _, _ = bot_session
    tg_id = 777001
    seed_user(tg_id)

    driver.send_text(tg_id, "/my_offers")

    assert len(recorder.records) >= 1
    last_text = recorder.last_text or ""
    assert "нет" in last_text.lower() or "empty" in last_text.lower()

    # Verify buttons
    markup = recorder.records[-1].reply_markup
    assert markup is not None
    callbacks = [btn.callback_data for row in markup.keyboard for btn in row]
    assert "act:offer" in callbacks
    assert "hub:mkt" in callbacks
    assert not any(cb.startswith("pg:o:") for cb in callbacks)


def test_list_with_two_offers_page_one(bot_session):
    """2 offers -> page 1 of 2 ([ 1 / 2 ]), prev button is noop, next button is pg:o:2."""
    driver, recorder, _, db_path = bot_session
    tg_id = 777001
    seed_user(tg_id)

    database.save_offer(tg_id, "Offer Number One text", category="services")
    database.save_offer(tg_id, "Offer Number Two text", category="goods")

    driver.send_text(tg_id, "/my_offers")

    last_text = recorder.last_text or ""
    assert "[ 1 / 2 ]" in last_text
    assert "Offer Number Two" in last_text  # newest first

    markup = recorder.records[-1].reply_markup
    callbacks = [btn.callback_data for row in markup.keyboard for btn in row]
    assert "noop" in callbacks
    assert "pg:o:2" in callbacks


def test_first_page_prev_button_is_noop(bot_session):
    """On page 1, the prev navigation button strictly has callback_data='noop'."""
    driver, recorder, _, _ = bot_session
    tg_id = 777001
    seed_user(tg_id)

    database.save_offer(tg_id, "Single Offer item", category="services")
    driver.send_text(tg_id, "/my_offers")

    markup = recorder.records[-1].reply_markup
    row_nav = [row for row in markup.keyboard if any("◀" in btn.text for btn in row)]
    assert len(row_nav) == 1
    prev_btn = [btn for btn in row_nav[0] if "◀" in btn.text][0]
    assert prev_btn.callback_data == "noop"


def test_pagination_navigation(bot_session):
    """3 offers -> clicking pg:o:2 edits message to show offer 2 ([ 2 / 3 ]); page 3 next is noop."""
    driver, recorder, _, _ = bot_session
    tg_id = 777001
    seed_user(tg_id)

    database.save_offer(tg_id, "Offer A", category="services")
    database.save_offer(tg_id, "Offer B", category="services")
    database.save_offer(tg_id, "Offer C", category="services")

    driver.send_text(tg_id, "/my_offers")
    msg_id = recorder.records[-1].kwargs.get("message_id") or 1001

    # Navigate to page 2
    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "pg:o:2", message_id=msg_id)

    assert any(r.method == "edit_message_text" for r in recorder.records)
    assert "[ 2 / 3 ]" in recorder.last_text
    assert "Offer B" in recorder.last_text

    # Navigate to page 3
    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "pg:o:3", message_id=msg_id)

    assert "[ 3 / 3 ]" in recorder.last_text
    markup = recorder.records[-1].reply_markup
    row_nav = [row for row in markup.keyboard if any("▶" in btn.text for btn in row)][0]
    next_btn = [btn for btn in row_nav if "▶" in btn.text][0]
    assert next_btn.callback_data == "noop"


def test_pagination_skips_deleted_pending(bot_session):
    """[active, deleted_pending, active] -> exactly 2 pages ([ 1 / 2 ], [ 2 / 2 ]), middle item skipped."""
    driver, recorder, _, db_path = bot_session
    tg_id = 777001
    seed_user(tg_id)

    database.save_offer(tg_id, "First Offer", category="services")
    mid_id = database.save_offer(tg_id, "Middle Offer", category="services")
    database.save_offer(tg_id, "Third Offer", category="services")

    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE offers SET status = 'deleted_pending' WHERE id = ?", (mid_id,))
    conn.commit()
    conn.close()

    driver.send_text(tg_id, "/my_offers")
    assert "[ 1 / 2 ]" in recorder.last_text
    assert "Third Offer" in recorder.last_text

    msg_id = recorder.records[-1].kwargs.get("message_id") or 1001
    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "pg:o:2", message_id=msg_id)

    assert "[ 2 / 2 ]" in recorder.last_text
    assert "First Offer" in recorder.last_text
    assert "Middle Offer" not in recorder.last_text


# ---------------------------------------------------------------------------
# Tests 6-12: Delete Flow, Confirmation, Cancel, Rewind & Double-Click
# ---------------------------------------------------------------------------

def test_delete_confirm_dialog(bot_session):
    """ask_del:o:1:1 switches the card into confirmation mode (Yes, delete / Cancel)."""
    driver, recorder, _, _ = bot_session
    tg_id = 777001
    seed_user(tg_id)

    offer_id = database.save_offer(tg_id, "Offer To Be Deleted", category="services")
    driver.send_text(tg_id, "/my_offers")
    msg_id = recorder.records[-1].kwargs.get("message_id") or 1001

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, f"ask_del:o:{offer_id}:1", message_id=msg_id)

    assert any(r.method == "edit_message_text" for r in recorder.records)
    last_text = recorder.last_text or ""
    assert "подтверждение" in last_text.lower() or "confirm" in last_text.lower()

    markup = recorder.records[-1].reply_markup
    callbacks = [btn.callback_data for row in markup.keyboard for btn in row]
    assert f"cfm_del:o:{offer_id}:1" in callbacks
    assert f"cxl_del:o:{offer_id}:1" in callbacks


def test_delete_cancel_flow(bot_session):
    """cxl_del:o:1:1 restores the offer view, database status remains 'active'."""
    driver, recorder, _, db_path = bot_session
    tg_id = 777001
    seed_user(tg_id)

    offer_id = database.save_offer(tg_id, "Cancel Test Offer", category="services")
    driver.send_text(tg_id, "/my_offers")
    msg_id = recorder.records[-1].kwargs.get("message_id") or 1001

    CLICK_TRACKER.clear()
    driver.click_button(tg_id, f"ask_del:o:{offer_id}:1", message_id=msg_id)

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, f"cxl_del:o:{offer_id}:1", message_id=msg_id)

    assert any(r.method == "edit_message_text" for r in recorder.records)
    assert "Cancel Test Offer" in recorder.last_text
    assert "[ 1 / 1 ]" in recorder.last_text

    # Verify DB status is active
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT status FROM offers WHERE id = ?", (offer_id,))
    status = cur.fetchone()[0]
    conn.close()
    assert status == "active" or status is None


def test_cfm_del_soft_deletes_locally(bot_session, deferred_sync_pool):
    """(deferred_sync_pool) cfm_del sets status='deleted_pending' and queues revoke_listing."""
    driver, recorder, _, db_path = bot_session
    tg_id = 777001
    seed_user(tg_id)

    offer_id = database.save_offer(tg_id, "Soft Delete Offer", category="services")
    driver.send_text(tg_id, "/my_offers")
    msg_id = recorder.records[-1].kwargs.get("message_id") or 1001

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, f"cfm_del:o:{offer_id}:1", message_id=msg_id)

    # Offer status must be deleted_pending in SQLite
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT status FROM offers WHERE id = ?", (offer_id,))
    assert cur.fetchone()[0] == "deleted_pending"

    # Queue item must have action = 'revoke_listing' and status = 'pending'
    cur.execute("SELECT action, status FROM pending_marketplace_sync WHERE entity_id = ? AND entity_type = 'offer'", (offer_id,))
    row = cur.fetchone()
    assert row is not None
    assert row[0] == "revoke_listing"
    assert row[1] == "pending"
    conn.close()


def test_cfm_del_full_cycle(bot_session, synchronous_mcp_sync_pool, mcp_mock, mcr_key_mock):
    """(synchronous_mcp_sync_pool) cfm_del completes fully: status='deleted', sync='synced', MCP called."""
    driver, recorder, _, db_path = bot_session
    tg_id = 777001
    seed_user(tg_id)

    offer_id = database.save_offer(tg_id, "Full Cycle Offer", category="services")
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE offers SET mcp_listing_id = 'lst-offer-full' WHERE id = ?", (offer_id,))
    conn.commit()
    conn.close()

    mcp_mock.response = {"data": {"success": True, "status": "archived"}}

    driver.send_text(tg_id, "/my_offers")
    msg_id = recorder.records[-1].kwargs.get("message_id") or 1001

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, f"cfm_del:o:{offer_id}:1", message_id=msg_id)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT status FROM offers WHERE id = ?", (offer_id,))
    assert cur.fetchone()[0] == "deleted"

    cur.execute("SELECT status FROM pending_marketplace_sync WHERE entity_id = ?", (offer_id,))
    assert cur.fetchone()[0] == "synced"
    conn.close()

    assert any(call[0] == "withdraw_listing" and call[1].get("listing_id") == "lst-offer-full" for call in mcp_mock.calls)


def test_delete_double_click_race_before_sync(bot_session, deferred_sync_pool):
    """(deferred_sync_pool) Double click before sync: 2nd click hits updated_rows==0 -> toast 'уже удалено'."""
    driver, recorder, _, db_path = bot_session
    tg_id = 777001
    seed_user(tg_id)

    offer_id = database.save_offer(tg_id, "Race Click Offer", category="services")
    driver.send_text(tg_id, "/my_offers")
    msg_id = recorder.records[-1].kwargs.get("message_id") or 1001

    # Click 1
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, f"cfm_del:o:{offer_id}:1", message_id=msg_id)

    # Click 2 (clearing tracker to test DB-level defense, not client-side throttle)
    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, f"cfm_del:o:{offer_id}:1", message_id=msg_id)

    # Check answer_callback_query toast text
    answer_records = [r for r in recorder.records if r.method == "answer_callback_query"]
    assert len(answer_records) >= 1
    assert "уже удалено" in (answer_records[-1].text or "").lower()


def test_delete_when_already_synced_gives_toast(bot_session, synchronous_mcp_sync_pool, mcp_mock, mcr_key_mock):
    """(synchronous_mcp_sync_pool) Clicking cfm_del on an already deleted offer gives 'уже удалено' toast."""
    driver, recorder, _, db_path = bot_session
    tg_id = 777001
    seed_user(tg_id)

    offer_id = database.save_offer(tg_id, "Already Synced Offer", category="services")
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE offers SET status = 'deleted' WHERE id = ?", (offer_id,))
    conn.commit()
    conn.close()

    CLICK_TRACKER.clear()
    driver.click_button(tg_id, f"cfm_del:o:{offer_id}:1", message_id=1001)

    answer_records = [r for r in recorder.records if r.method == "answer_callback_query"]
    assert len(answer_records) >= 1
    assert "уже удалено" in (answer_records[-1].text or "").lower()


def test_delete_last_item_page_rewind(bot_session, synchronous_mcp_sync_pool, mcp_mock, mcr_key_mock):
    """(synchronous_mcp_sync_pool) With 2 offers, deleting item on page 2 rewinds screen to page 1 ([ 1 / 1 ])."""
    driver, recorder, _, db_path = bot_session
    tg_id = 777001
    seed_user(tg_id)

    id_1 = database.save_offer(tg_id, "Offer One", category="services")
    id_2 = database.save_offer(tg_id, "Offer Two", category="services")

    driver.send_text(tg_id, "/my_offers")
    msg_id = recorder.records[-1].kwargs.get("message_id") or 1001

    # Go to page 2 (which is Offer One, older)
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "pg:o:2", message_id=msg_id)

    # Delete offer on page 2
    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, f"cfm_del:o:{id_1}:2", message_id=msg_id)

    assert any(r.method == "edit_message_text" for r in recorder.records)
    assert "[ 1 / 1 ]" in recorder.last_text
    assert "Offer Two" in recorder.last_text


# ---------------------------------------------------------------------------
# Tests 13-16: FSM Policy, Sessions Protection & Escape Hatch
# ---------------------------------------------------------------------------

def test_callback_rejected_in_active_fsm(bot_session):
    """
    Complete FSM policy matrix verification:
    - In active state (offer): pg:*, ask_del:*, cfm_del:*, act:* rejected with toast.
    - cxl_del:* and noop are allowed without clearing session.
    - hub:mkt is allowed and clears session to IDLE.
    """
    driver, recorder, _, _ = bot_session
    tg_id = 777001
    seed_user(tg_id)

    database.set_session(tg_id, "offer", {"category": "services"})

    # 1. pg:* rejected
    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "pg:o:2")
    answers = [r for r in recorder.records if r.method == "answer_callback_query"]
    assert any("завершите" in (r.text or "").lower() for r in answers)

    # 2. ask_del rejected
    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "ask_del:o:1:1")
    answers = [r for r in recorder.records if r.method == "answer_callback_query"]
    assert any("завершите" in (r.text or "").lower() for r in answers)

    # 3. cfm_del rejected
    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "cfm_del:o:1:1")
    answers = [r for r in recorder.records if r.method == "answer_callback_query"]
    assert any("завершите" in (r.text or "").lower() for r in answers)

    # 4. act:offer rejected
    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "act:offer")
    answers = [r for r in recorder.records if r.method == "answer_callback_query"]
    assert any("завершите" in (r.text or "").lower() for r in answers)

    # Session is still intact in active state
    state, data = database.get_session(tg_id)
    assert state == "offer"

    # 5. noop allowed without clearing session
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "noop")
    state, _ = database.get_session(tg_id)
    assert state == "offer"

    # 6. hub:mkt asks confirmation in active FSM; hub:mkt:confirm clears session (escape hatch)
    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "hub:mkt")
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "hub:mkt:confirm")
    state, _ = database.get_session(tg_id)
    assert state is None or state == "IDLE"


def test_navigation_callbacks_readonly(bot_session):
    """pg:*, cxl_del:*, noop never write to or modify sessions table."""
    driver, _, _, db_path = bot_session
    tg_id = 777001
    seed_user(tg_id)

    database.save_offer(tg_id, "Offer Nav", category="services")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM sessions")
    initial_sessions_count = cur.fetchone()[0]
    conn.close()

    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "pg:o:1")
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "cxl_del:o:1:1")
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "noop")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM sessions")
    final_sessions_count = cur.fetchone()[0]
    conn.close()

    assert final_sessions_count == initial_sessions_count


def test_act_callbacks_transition_fsm(bot_session):
    """act:offer and act:request set session.state to 'offer_category' / 'request_category'."""
    driver, recorder, _, _ = bot_session
    tg_id = 777001
    seed_user(tg_id)

    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "act:offer")
    state, _ = database.get_session(tg_id)
    assert state == "offer_category"

    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "act:request")
    state, _ = database.get_session(tg_id)
    assert state == "request_category"


def test_hub_callback_opens_marketplace(bot_session):
    """hub:mkt in IDLE state directly renders marketplace view with markup."""
    driver, recorder, _, _ = bot_session
    tg_id = 777001
    seed_user(tg_id)

    database.set_session(tg_id, None, {})

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "hub:mkt")

    state, _ = database.get_session(tg_id)
    assert state is None or state == "IDLE"

    assert any(r.method == "edit_message_text" for r in recorder.records)
    last_text = recorder.last_text or ""
    assert "маркетплейс" in last_text.lower() or "marketplace" in last_text.lower()
    assert recorder.records[-1].reply_markup is not None


# ---------------------------------------------------------------------------
# Tests 17-21: HTML escaping, safe_edit resilience & list filtering
# ---------------------------------------------------------------------------

def test_html_in_offer(bot_session):
    """Offer text containing <b> & <script> *bold* _italic_ renders safely without Telegram parse errors."""
    driver, recorder, _, _ = bot_session
    tg_id = 777001
    seed_user(tg_id)

    xss_text = "Offering <b>web</b> & <script>alert('xss')</script> *markdown* _under_ `code`"
    database.save_offer(tg_id, xss_text, category="services")

    driver.send_text(tg_id, "/my_offers")

    last_text = recorder.last_text or ""
    # Must contain escaped entities and not fail
    assert "&lt;script&gt;" in last_text
    assert "&lt;b&gt;web&lt;/b&gt;" in last_text
    assert "*markdown*" in last_text


def test_safe_edit_not_modified(monkeypatch):
    """safe_edit_message suppresses 'message is not modified' ApiTelegramException and returns True."""
    try:
        from handlers.helpers import safe_edit_message
    except ImportError:
        def safe_edit_message(*args, **kwargs):
            return False

    class MockBot:
        def edit_message_text(self, *args, **kwargs):
            raise ApiTelegramException(
                "Bad Request: message is not modified: specified new message content and reply markup are exactly the same as a current content and reply markup of the message",
                "edit_message_text",
                {"error_code": 400, "description": "Bad Request: message is not modified"}
            )

    res = safe_edit_message(MockBot(), 123, 456, "test")
    assert res is True


def test_safe_edit_429_retry(monkeypatch):
    """safe_edit_message on 429 sleeps min(retry_after, 2) and retries once."""
    try:
        from handlers.helpers import safe_edit_message
    except ImportError:
        def safe_edit_message(*args, **kwargs):
            return False

    attempts = 0
    slept = []
    monkeypatch.setattr(time, "sleep", lambda s: slept.append(s))

    class MockBot429:
        def edit_message_text(self, *args, **kwargs):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise ApiTelegramException(
                    "Too Many Requests: retry after 5",
                    "edit_message_text",
                    {"error_code": 429, "description": "Too Many Requests", "parameters": {"retry_after": 5}}
                )
            return True

    res = safe_edit_message(MockBot429(), 123, 456, "text")
    assert res is True
    assert attempts == 2
    assert slept == [2]  # min(5, 2)


def test_safe_edit_fallback_to_send(monkeypatch):
    """safe_edit_message when message to edit is deleted falls back to bot.send_message."""
    try:
        from handlers.helpers import safe_edit_message
    except ImportError:
        def safe_edit_message(*args, **kwargs):
            return False

    sent_messages = []

    class MockBotDeleted:
        def edit_message_text(self, *args, **kwargs):
            raise ApiTelegramException(
                "Bad Request: message to edit not found",
                "edit_message_text",
                {"error_code": 400, "description": "Bad Request: message to edit not found"}
            )
        def send_message(self, chat_id, text, **kwargs):
            sent_messages.append((chat_id, text))
            return True

    res = safe_edit_message(MockBotDeleted(), 123, 456, "Fallback text")
    assert res is True
    assert len(sent_messages) == 1
    assert sent_messages[0] == (123, "Fallback text")


def test_deleted_pending_hidden_from_list(bot_session):
    """[active, deleted_pending] -> /my_offers shows exactly 1 card, deleted_pending completely hidden."""
    driver, recorder, _, db_path = bot_session
    tg_id = 777001
    seed_user(tg_id)

    id_active = database.save_offer(tg_id, "Active Offer", category="services")
    id_pending = database.save_offer(tg_id, "Deleted Pending Offer", category="services")

    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE offers SET status = 'deleted_pending' WHERE id = ?", (id_pending,))
    conn.commit()
    conn.close()

    driver.send_text(tg_id, "/my_offers")

    last_text = recorder.last_text or ""
    assert "[ 1 / 1 ]" in last_text
    assert "Active Offer" in last_text
    assert "Deleted Pending Offer" not in last_text


# ---------------------------------------------------------------------------
# Tests 22-28: Race resolution, worker guards and error-handling in mcp_client
# ---------------------------------------------------------------------------

def test_revoke_before_create_race(deferred_sync_pool, mcp_mock, db_path):
    """(deferred_sync_pool) Pending create (id=10) + pending revoke (id=20) -> revoke cancels create, no MCP call."""
    conn = mcp_client.get_db_connection()
    cur = conn.cursor()
    now_iso = datetime.now().isoformat()
    cur.execute("INSERT INTO offers (id, tg_id, text, status) VALUES (1, 777001, 'Race offer', 'active')")
    cur.execute("""
        INSERT INTO pending_marketplace_sync (id, tg_id, entity_type, entity_id, action, payload, status, retry_count, guard_skip_count, created_at, updated_at)
        VALUES (10, 777001, 'offer', 1, 'create_listing', '{"title":"Test"}', 'pending', 0, 0, ?, ?)
    """, (now_iso, now_iso))
    cur.execute("""
        INSERT INTO pending_marketplace_sync (id, tg_id, entity_type, entity_id, action, payload, status, retry_count, guard_skip_count, created_at, updated_at)
        VALUES (20, 777001, 'offer', 1, 'revoke_listing', '{"action":"revoke_listing","id":1}', 'pending', 0, 0, ?, ?)
    """, (now_iso, now_iso))
    conn.commit()
    conn.close()

    # Process revoke task (20)
    res = mcp_client.process_single_sync(20)
    assert res is True

    conn = mcp_client.get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT status FROM pending_marketplace_sync WHERE id = 10")
    assert cur.fetchone()[0] == "cancelled"

    cur.execute("SELECT status FROM pending_marketplace_sync WHERE id = 20")
    assert cur.fetchone()[0] == "synced"

    cur.execute("SELECT status FROM offers WHERE id = 1")
    assert cur.fetchone()[0] == "deleted"
    conn.close()

    assert len(mcp_mock.calls) == 0


def test_create_guard_aborts_when_revoke_pending(deferred_sync_pool, mcp_mock, db_path):
    """(deferred_sync_pool) Create task aborts (yields) when a revoke task is already pending."""
    conn = mcp_client.get_db_connection()
    cur = conn.cursor()
    now_iso = datetime.now().isoformat()
    cur.execute("INSERT INTO offers (id, tg_id, text, status) VALUES (1, 777001, 'Guard offer', 'active')")
    cur.execute("""
        INSERT INTO pending_marketplace_sync (id, tg_id, entity_type, entity_id, action, payload, status, retry_count, guard_skip_count, created_at, updated_at)
        VALUES (10, 777001, 'offer', 1, 'create_listing', '{"title":"Test"}', 'pending', 0, 0, ?, ?)
    """, (now_iso, now_iso))
    cur.execute("""
        INSERT INTO pending_marketplace_sync (id, tg_id, entity_type, entity_id, action, payload, status, retry_count, guard_skip_count, created_at, updated_at)
        VALUES (20, 777001, 'offer', 1, 'revoke_listing', '{"action":"revoke_listing","id":1}', 'pending', 0, 0, ?, ?)
    """, (now_iso, now_iso))
    conn.commit()
    conn.close()

    res = mcp_client.process_single_sync(10)
    assert res is False

    conn = mcp_client.get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT status, guard_skip_count FROM pending_marketplace_sync WHERE id = 10")
    row = cur.fetchone()
    assert row[0] == "pending"
    assert row[1] == 1
    conn.close()


def test_worker_skips_cancelled_create(deferred_sync_pool, db_path):
    """Cancelled task cannot be claimed: process_single_sync returns False."""
    conn = mcp_client.get_db_connection()
    cur = conn.cursor()
    now_iso = datetime.now().isoformat()
    cur.execute("""
        INSERT INTO pending_marketplace_sync (id, tg_id, entity_type, entity_id, action, payload, status, retry_count, guard_skip_count, created_at, updated_at)
        VALUES (10, 777001, 'offer', 1, 'create_listing', '{"title":"Test"}', 'cancelled', 0, 0, ?, ?)
    """, (now_iso, now_iso))
    conn.commit()
    conn.close()

    res = mcp_client.process_single_sync(10)
    assert res is False


def test_revoke_exception_keeps_pending(mcp_mock, mcr_key_mock, db_path):
    """mcp_mock raises exception -> task remains pending, retry_count=1, offer deleted_pending."""
    mcp_mock.response = RuntimeError("Network connection refused")

    conn = mcp_client.get_db_connection()
    cur = conn.cursor()
    now_iso = datetime.now().isoformat()
    cur.execute("INSERT INTO offers (id, tg_id, text, status, mcp_listing_id) VALUES (1, 777001, 'Err offer', 'deleted_pending', 'lst-1')")
    cur.execute("""
        INSERT INTO pending_marketplace_sync (id, tg_id, entity_type, entity_id, action, payload, status, retry_count, guard_skip_count, created_at, updated_at)
        VALUES (20, 777001, 'offer', 1, 'revoke_listing', '{"action":"revoke_listing","id":1}', 'pending', 0, 0, ?, ?)
    """, (now_iso, now_iso))
    conn.commit()
    conn.close()

    res = mcp_client.process_single_sync(20)
    assert res is False

    conn = mcp_client.get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT status, retry_count FROM pending_marketplace_sync WHERE id = 20")
    row = cur.fetchone()
    assert row[0] == "pending"
    assert row[1] == 1

    cur.execute("SELECT status FROM offers WHERE id = 1")
    assert cur.fetchone()[0] == "deleted_pending"
    conn.close()


def test_revoke_error_dict_keeps_pending(mcp_mock, mcr_key_mock, db_path):
    """mcp_mock returns error dict {"data": {"error": "forbidden"}} -> retry_count=1, pending."""
    mcp_mock.response = {"data": {"error": "forbidden"}}

    conn = mcp_client.get_db_connection()
    cur = conn.cursor()
    now_iso = datetime.now().isoformat()
    cur.execute("INSERT INTO offers (id, tg_id, text, status, mcp_listing_id) VALUES (1, 777001, 'Forbid offer', 'deleted_pending', 'lst-1')")
    cur.execute("""
        INSERT INTO pending_marketplace_sync (id, tg_id, entity_type, entity_id, action, payload, status, retry_count, guard_skip_count, created_at, updated_at)
        VALUES (20, 777001, 'offer', 1, 'revoke_listing', '{"action":"revoke_listing","id":1}', 'pending', 0, 0, ?, ?)
    """, (now_iso, now_iso))
    conn.commit()
    conn.close()

    res = mcp_client.process_single_sync(20)
    assert res is False

    conn = mcp_client.get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT status, retry_count, error_message FROM pending_marketplace_sync WHERE id = 20")
    row = cur.fetchone()
    assert row[0] == "pending"
    assert row[1] == 1
    assert "forbidden" in row[2]
    conn.close()


def test_revoke_not_found_treated_as_success(mcp_mock, mcr_key_mock, db_path):
    """mcp_mock returns not_found -> treated as success (absent on MCP), offer deleted, sync synced."""
    mcp_mock.response = {"data": {"error": "not_found"}}

    conn = mcp_client.get_db_connection()
    cur = conn.cursor()
    now_iso = datetime.now().isoformat()
    cur.execute("INSERT INTO offers (id, tg_id, text, status, mcp_listing_id) VALUES (1, 777001, 'NF offer', 'deleted_pending', 'lst-1')")
    cur.execute("""
        INSERT INTO pending_marketplace_sync (id, tg_id, entity_type, entity_id, action, payload, status, retry_count, guard_skip_count, created_at, updated_at)
        VALUES (20, 777001, 'offer', 1, 'revoke_listing', '{"action":"revoke_listing","id":1}', 'pending', 0, 0, ?, ?)
    """, (now_iso, now_iso))
    conn.commit()
    conn.close()

    res = mcp_client.process_single_sync(20)
    assert res is True

    conn = mcp_client.get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT status FROM offers WHERE id = 1")
    assert cur.fetchone()[0] == "deleted"

    cur.execute("SELECT status FROM pending_marketplace_sync WHERE id = 20")
    assert cur.fetchone()[0] == "synced"
    conn.close()


def test_revoke_unexpected_shape_keeps_pending(mcp_mock, mcr_key_mock, db_path):
    """mcp_mock returns empty dict or unexpected structure -> retry_count=1, status pending, unexpected_* error."""
    mcp_mock.response = {"data": {"content": []}}

    conn = mcp_client.get_db_connection()
    cur = conn.cursor()
    now_iso = datetime.now().isoformat()
    cur.execute("INSERT INTO offers (id, tg_id, text, status, mcp_listing_id) VALUES (1, 777001, 'Shape offer', 'deleted_pending', 'lst-1')")
    cur.execute("""
        INSERT INTO pending_marketplace_sync (id, tg_id, entity_type, entity_id, action, payload, status, retry_count, guard_skip_count, created_at, updated_at)
        VALUES (20, 777001, 'offer', 1, 'revoke_listing', '{"action":"revoke_listing","id":1}', 'pending', 0, 0, ?, ?)
    """, (now_iso, now_iso))
    conn.commit()
    conn.close()

    res = mcp_client.process_single_sync(20)
    assert res is False

    conn = mcp_client.get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT status, retry_count, error_message FROM pending_marketplace_sync WHERE id = 20")
    row = cur.fetchone()
    assert row[0] == "pending"
    assert row[1] == 1
    assert "unexpected" in row[2]
    conn.close()


# ---------------------------------------------------------------------------
# Tests 29-33: Scanner, Livelock avoidance, Chained processing & Create Error
# ---------------------------------------------------------------------------

def test_retry_exhaustion_sets_failed_status(mcp_mock, mcr_key_mock, db_path):
    """5 consecutive failures -> status='failed', retry_count=5, escalates to admin."""
    mcp_mock.response = RuntimeError("Continuous 500 error")

    conn = mcp_client.get_db_connection()
    cur = conn.cursor()
    now_iso = datetime.now().isoformat()
    cur.execute("INSERT INTO offers (id, tg_id, text, status, mcp_listing_id) VALUES (1, 777001, 'Exhaust offer', 'deleted_pending', 'lst-1')")
    cur.execute("""
        INSERT INTO pending_marketplace_sync (id, tg_id, entity_type, entity_id, action, payload, status, retry_count, guard_skip_count, created_at, updated_at)
        VALUES (20, 777001, 'offer', 1, 'revoke_listing', '{"action":"revoke_listing","id":1}', 'pending', 4, 0, ?, ?)
    """, (now_iso, now_iso))
    conn.commit()
    conn.close()

    res = mcp_client.process_single_sync(20)
    assert res is False

    conn = mcp_client.get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT status, retry_count FROM pending_marketplace_sync WHERE id = 20")
    row = cur.fetchone()
    assert row[0] == "failed"
    assert row[1] == 5
    conn.close()


def test_scanner_picks_up_released_create(publish_mock, mcr_key_mock, db_path):
    """
    process_all_pending_syncs (scanner) picks up a released pending task,
    while strictly skipping failed tasks and tasks with retry_count >= 5.
    """
    publish_mock.result = "lst-mock-scanned"

    conn = mcp_client.get_db_connection()
    cur = conn.cursor()
    now_iso = datetime.now().isoformat()
    cur.execute("INSERT INTO offers (id, tg_id, text, status) VALUES (1, 777001, 'Scanned offer', 'active')")
    # Task A: failed task (skipped by status)
    cur.execute("""
        INSERT INTO pending_marketplace_sync (id, tg_id, entity_type, entity_id, action, payload, status, retry_count, guard_skip_count, created_at, updated_at)
        VALUES (5, 777001, 'offer', 1, 'create_listing', '{"title":"T5"}', 'failed', 5, 0, ?, ?)
    """, (now_iso, now_iso))
    # Task B: anomalous pending task with retry_count=5 (skipped by retry_count < 5)
    cur.execute("""
        INSERT INTO pending_marketplace_sync (id, tg_id, entity_type, entity_id, action, payload, status, retry_count, guard_skip_count, created_at, updated_at)
        VALUES (6, 777001, 'offer', 1, 'create_listing', '{"title":"T6"}', 'pending', 5, 0, ?, ?)
    """, (now_iso, now_iso))
    # Task C: valid released pending task
    cur.execute("""
        INSERT INTO pending_marketplace_sync (id, tg_id, entity_type, entity_id, action, payload, status, retry_count, guard_skip_count, created_at, updated_at)
        VALUES (10, 777001, 'offer', 1, 'create_listing', '{"title":"T10"}', 'pending', 1, 0, ?, ?)
    """, (now_iso, now_iso))
    conn.commit()
    conn.close()

    processed_count = mcp_client.process_all_pending_syncs(max_items=10)
    assert processed_count == 1

    conn = mcp_client.get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT status FROM pending_marketplace_sync WHERE id = 10")
    assert cur.fetchone()[0] == "synced"

    cur.execute("SELECT status FROM pending_marketplace_sync WHERE id = 5")
    assert cur.fetchone()[0] == "failed"

    cur.execute("SELECT status FROM pending_marketplace_sync WHERE id = 6")
    assert cur.fetchone()[0] == "pending"

    cur.execute("SELECT mcp_listing_id FROM offers WHERE id = 1")
    assert cur.fetchone()[0] == "lst-mock-scanned"
    conn.close()


def test_create_guard_does_not_livelock(deferred_sync_pool, publish_mock, mcr_key_mock, db_path):
    """
    create-guard yields max 3 times to pending revoke.
    On the 4th call, guard_skip_count >= 3 -> breaks yield and proceeds to publish.
    """
    publish_mock.result = "lst-mock-break-livelock"

    conn = mcp_client.get_db_connection()
    cur = conn.cursor()
    now_iso = datetime.now().isoformat()
    cur.execute("INSERT INTO offers (id, tg_id, text, status) VALUES (1, 777001, 'Livelock offer', 'active')")
    cur.execute("""
        INSERT INTO pending_marketplace_sync (id, tg_id, entity_type, entity_id, action, payload, status, retry_count, guard_skip_count, created_at, updated_at)
        VALUES (10, 777001, 'offer', 1, 'create_listing', '{"title":"Test"}', 'pending', 0, 0, ?, ?)
    """, (now_iso, now_iso))
    cur.execute("""
        INSERT INTO pending_marketplace_sync (id, tg_id, entity_type, entity_id, action, payload, status, retry_count, guard_skip_count, created_at, updated_at)
        VALUES (20, 777001, 'offer', 1, 'revoke_listing', '{"action":"revoke_listing","id":1}', 'pending', 0, 0, ?, ?)
    """, (now_iso, now_iso))
    conn.commit()
    conn.close()

    # Iterations 1, 2, 3: yield to revoke
    for expected_skip in [1, 2, 3]:
        res = mcp_client.process_single_sync(10)
        assert res is False
        assert len(publish_mock.calls) == 0

        conn = mcp_client.get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT guard_skip_count FROM pending_marketplace_sync WHERE id = 10")
        assert cur.fetchone()[0] == expected_skip
        conn.close()

    # 4th call: guard_skip_count is 3 -> proceeds!
    res = mcp_client.process_single_sync(10)
    assert res is True
    assert len(publish_mock.calls) == 1


def test_chained_processing_after_create(deferred_sync_pool, publish_mock, mcp_mock, mcr_key_mock, db_path):
    """
    When revoke arrives right as create is finishing publication,
    the create worker detects it and submits the chained revoke task, which then executes.
    """
    def publish_and_enqueue_revoke(key, payload):
        _conn = sqlite3.connect(mcp_client.DB_PATH)
        _conn.execute("PRAGMA busy_timeout=5000")
        _cur = _conn.cursor()
        now_iso = datetime.now().isoformat()
        _cur.execute("""
            INSERT INTO pending_marketplace_sync (
                id, tg_id, entity_type, entity_id, action, payload, status, retry_count, guard_skip_count, created_at, updated_at
            ) VALUES (20, 777001, 'offer', 1, 'revoke_listing', '{"action":"revoke_listing","id":1}', 'pending', 0, 0, ?, ?)
        """, (now_iso, now_iso))
        _conn.commit()
        _conn.close()
        return "lst-mock-chained-123"

    publish_mock.side_effect = publish_and_enqueue_revoke
    mcp_mock.response = {"data": {"success": True, "status": "archived"}}

    conn = mcp_client.get_db_connection()
    cur = conn.cursor()
    now_iso = datetime.now().isoformat()
    cur.execute("INSERT INTO offers (id, tg_id, text, status) VALUES (1, 777001, 'Chained offer', 'active')")
    cur.execute("""
        INSERT INTO pending_marketplace_sync (id, tg_id, entity_type, entity_id, action, payload, status, retry_count, guard_skip_count, created_at, updated_at)
        VALUES (10, 777001, 'offer', 1, 'create_listing', '{"title":"Test"}', 'pending', 0, 0, ?, ?)
    """, (now_iso, now_iso))
    conn.commit()
    conn.close()

    res = mcp_client.process_single_sync(10)
    assert res is True

    # Check that chained task was submitted to pool
    assert len(deferred_sync_pool.tasks) == 1
    chained_fn, chained_args, chained_kwargs = deferred_sync_pool.tasks[0]

    # Execute the chained revoke task
    chained_fn(*chained_args, **chained_kwargs)

    conn = mcp_client.get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT status FROM offers WHERE id = 1")
    assert cur.fetchone()[0] == "deleted"

    cur.execute("SELECT status FROM pending_marketplace_sync WHERE id = 20")
    assert cur.fetchone()[0] == "synced"
    conn.close()

    assert any(call[0] == "withdraw_listing" and call[1].get("listing_id") == "lst-mock-chained-123" for call in mcp_mock.calls)


def test_create_path_mcp_failure_keeps_pending(publish_mock, mcr_key_mock, db_path):
    """Failure in publish_listing_pipeline keeps task in pending with retry_count incremented."""
    publish_mock.side_effect = RuntimeError("MCP pipeline 500 error")

    conn = mcp_client.get_db_connection()
    cur = conn.cursor()
    now_iso = datetime.now().isoformat()
    cur.execute("INSERT INTO offers (id, tg_id, text, status) VALUES (1, 777001, 'Fail offer', 'active')")
    cur.execute("""
        INSERT INTO pending_marketplace_sync (id, tg_id, entity_type, entity_id, action, payload, status, retry_count, guard_skip_count, created_at, updated_at)
        VALUES (10, 777001, 'offer', 1, 'create_listing', '{"title":"Test"}', 'pending', 0, 0, ?, ?)
    """, (now_iso, now_iso))
    conn.commit()
    conn.close()

    res = mcp_client.process_single_sync(10)
    assert res is False

    conn = mcp_client.get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT status, retry_count, error_message FROM pending_marketplace_sync WHERE id = 10")
    row = cur.fetchone()
    assert row[0] == "pending"
    assert row[1] == 1
    assert "MCP pipeline 500 error" in row[2]

    cur.execute("SELECT status, mcp_listing_id FROM offers WHERE id = 1")
    offer_row = cur.fetchone()
    assert offer_row[0] == "active"
    assert offer_row[1] is None
    conn.close()


def test_dispatcher_routes_pg_callback_to_marketplace(bot_session, mcp_mock, mcr_key_mock):
    """
    (Test 34) Verifies that the telebot dispatcher routes pg:o:2 callback query directly to
    handle_marketplace_callbacks without being swallowed by legacy menu callback handlers,
    answering without 'Unknown action' and rendering page 2.
    """
    driver, recorder, _, db_path = bot_session
    tg_id = 777001
    seed_user(tg_id)

    database.save_offer(tg_id, "Offer Page 1 item", category="services")
    database.save_offer(tg_id, "Offer Page 2 item", category="goods")

    driver.send_text(tg_id, "/my_offers")
    msg_id = recorder.records[-1].kwargs.get("message_id") or 1001

    from telebot.types import Update
    update_json = {
        "update_id": 9999,
        "callback_query": {
            "id": "cb_dispatcher_test",
            "from": {"id": tg_id, "is_bot": False, "first_name": "TestCitizen", "username": "testuser"},
            "message": {
                "message_id": msg_id,
                "chat": {"id": tg_id, "type": "private"},
                "date": int(time.time()),
                "text": "menu"
            },
            "chat_instance": f"ci_{tg_id}",
            "data": "pg:o:2"
        }
    }
    update = Update.de_json(update_json)

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.bot.process_new_updates([update])

    answer_queries = [r for r in recorder.records if r.method == "answer_callback_query"]
    assert len(answer_queries) >= 1
    assert "unknown action" not in (answer_queries[-1].text or "").lower()

    edit_records = [r for r in recorder.records if r.method == "edit_message_text"]
    assert len(edit_records) >= 1
    assert "[ 2 / 2 ]" in (recorder.last_text or "")
    assert "Offer Page 1 item" in (recorder.last_text or "")

