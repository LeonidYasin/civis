"""
Test suite for Phase 2.1: Marketplace Catalog (/marketplace),
Categories, Pagination, Detail Card, Privacy, Truncation, and FSM Policies.
"""

import html
import pytest
from telebot.types import Update, CallbackQuery, Message

import database
import handlers
from keyboards import CLICK_TRACKER

try:
    from handlers.marketplace import (
        render_marketplace_catalog,
        normalize_username,
        extract_title,
        _safe_cat,
        _safe_page,
    )
except ImportError:
    render_marketplace_catalog = getattr(handlers.marketplace, "render_marketplace_catalog", None)
    normalize_username = getattr(handlers.marketplace, "normalize_username", None)
    extract_title = getattr(handlers.marketplace, "extract_title", None)
    _safe_cat = getattr(handlers.marketplace, "_safe_cat", None)
    _safe_page = getattr(handlers.marketplace, "_safe_page", None)


def seed_user(tg_id: int, username: str = None, name: str = "Test User"):
    database.save_user(tg_id, username, name=name, status="completed")


def get_answered_callbacks(recorder):
    return [
        {
            "text": r.text,
            "show_alert": r.kwargs.get("show_alert"),
            "id": r.kwargs.get("callback_query_id"),
        }
        for r in recorder.records
        if r.method == "answer_callback_query"
    ]


# ---------------------------------------------------------------------------
# Test 1: Default page 1 shows 5 active offers
# ---------------------------------------------------------------------------
def test_marketplace_catalog_default_page_1_shows_5_active_offers(bot_session):
    """Default /marketplace view shows up to 5 newest active offers on page 1."""
    driver, recorder, _, _ = bot_session
    tg_id = 777101
    seed_user(tg_id, username="tester1")

    # Seed 7 offers
    for i in range(1, 8):
        database.save_offer(tg_id, f"Offer #{i}\nDescription details for item {i}", category="services")

    recorder.clear()
    driver.send_text(tg_id, "/marketplace")

    last_text = recorder.last_text or ""
    # Should display newest offers #7, #6, #5, #4, #3
    assert "Offer #7" in last_text
    assert "Offer #3" in last_text
    # Offers #2 and #1 should be on page 2
    assert "Offer #2" not in last_text
    assert "Offer #1" not in last_text

    # Check pagination: 1 / 2
    assert "1 / 2" in last_text or any("1 / 2" in str(b.text) for row in recorder.records[-1].reply_markup.keyboard for b in row)
    
    # Check item buttons [ 1 ] .. [ 5 ]
    callbacks = [b.callback_data for row in recorder.records[-1].reply_markup.keyboard for b in row if getattr(b, "callback_data", None)]
    card_callbacks = [c for c in callbacks if c.startswith("mkt:v:")]
    assert len(card_callbacks) == 5


# ---------------------------------------------------------------------------
# Test 1b: Opens catalog from IDLE state via callback
# ---------------------------------------------------------------------------
def test_marketplace_opens_from_idle_state(bot_session):
    """mkt:cat:all:1 in IDLE state triggers catalog render with offers."""
    driver, recorder, _, _ = bot_session
    tg_id = 777150
    seed_user(tg_id)
    for i in range(1, 4):
        database.save_offer(tg_id, f"Idle Offer {i}\nDetails", category="services")
    database.set_session(tg_id, None, {})

    recorder.clear()
    CLICK_TRACKER.clear()
    update_json = {
        "update_id": 990150,
        "callback_query": {
            "id": "cb_idle_open",
            "from": {"id": tg_id, "is_bot": False, "first_name": "Test"},
            "message": {
                "message_id": 6001,
                "date": 100000,
                "chat": {"id": tg_id, "type": "private"},
                "text": "Initial text"
            },
            "chat_instance": f"ci_{tg_id}",
            "data": "mkt:cat:all:1"
        }
    }
    driver.bot.process_new_updates([Update.de_json(update_json)])

    assert any(r.method == "edit_message_text" for r in recorder.records)
    last_text = recorder.last_text or ""
    assert "маркетплейс" in last_text.lower() or "marketplace" in last_text.lower()
    callbacks = [b.callback_data for row in recorder.records[-1].reply_markup.keyboard for b in row if getattr(b, "callback_data", None)]
    assert any(c.startswith("mkt:v:") for c in callbacks)


# ---------------------------------------------------------------------------
# Test 2: Pagination next and prev
# ---------------------------------------------------------------------------
def test_marketplace_catalog_pagination_next_prev(bot_session):
    """Browsing pages forward and backward updates catalog page without errors."""
    driver, recorder, _, _ = bot_session
    tg_id = 777102
    seed_user(tg_id)

    for i in range(1, 7):
        database.save_offer(tg_id, f"Item {i}\nDesc", category="services")

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "mkt:cat:all:1")

    # On page 1: prev button is noop, next button is mkt:cat:all:2
    callbacks = [b.callback_data for row in recorder.records[-1].reply_markup.keyboard for b in row if getattr(b, "callback_data", None)]
    assert "mkt:cat:all:2" in callbacks

    # Go to page 2
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "mkt:cat:all:2")
    last_text = recorder.last_text or ""
    assert "Item 1" in last_text
    assert "Item 6" not in last_text

    # Back to page 1
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "mkt:cat:all:1")
    last_text = recorder.last_text or ""
    assert "Item 6" in last_text


# ---------------------------------------------------------------------------
# Test 3: Category filtering
# ---------------------------------------------------------------------------
def test_marketplace_catalog_category_filtering(bot_session):
    """Selecting a specific category filters out offers from other categories."""
    driver, recorder, _, _ = bot_session
    tg_id = 777103
    seed_user(tg_id)

    database.save_offer(tg_id, "Plumber Service\nPipe repair", category="services")
    database.save_offer(tg_id, "Electrician Service\nWiring", category="services")
    database.save_offer(tg_id, "Coffee Shop Business\nInvestment", category="business")

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "mkt:cat:business:1")

    last_text = recorder.last_text or ""
    assert "Coffee Shop Business" in last_text
    assert "Plumber Service" not in last_text
    assert "Electrician Service" not in last_text


# ---------------------------------------------------------------------------
# Test 4: Category synonyms mapping
# ---------------------------------------------------------------------------
def test_marketplace_catalog_category_synonyms_mapping(bot_session):
    """Filter by slug finds synonyms such as Russian names or legacy tags."""
    driver, recorder, _, _ = bot_session
    tg_id = 777104
    seed_user(tg_id)

    database.save_offer(tg_id, "English Service\nDesc", category="services")
    database.save_offer(tg_id, "Russian Service\nDesc", category="Услуги")
    database.save_offer(tg_id, "Other item\nDesc", category="other")

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "mkt:cat:services:1")

    last_text = recorder.last_text or ""
    assert "English Service" in last_text
    assert "Russian Service" in last_text
    assert "Other item" not in last_text


# ---------------------------------------------------------------------------
# Test 5: Categories menu screen
# ---------------------------------------------------------------------------
def test_marketplace_categories_menu(bot_session):
    """mkt:cats opens a menu with 11 category choices (10 slugs + All)."""
    driver, recorder, _, _ = bot_session
    tg_id = 777105
    seed_user(tg_id)

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "mkt:cats")

    callbacks = [b.callback_data for row in recorder.records[-1].reply_markup.keyboard for b in row if getattr(b, "callback_data", None)]
    assert "mkt:cat:all:1" in callbacks
    assert "mkt:cat:services:1" in callbacks
    assert "mkt:cat:business:1" in callbacks
    assert "mkt:cat:jobs:1" in callbacks
    assert "mkt:cat:real_estate:1" in callbacks
    assert "mkt:cat:things:1" in callbacks
    assert "mkt:cat:rides:1" in callbacks
    assert "mkt:cat:delivery:1" in callbacks
    assert "mkt:cat:communities:1" in callbacks
    assert "mkt:cat:dating:1" in callbacks
    assert "mkt:cat:other:1" in callbacks

    # Single source of truth check: menu matches KNOWN_CATS - {'all'}
    slugs = {c.split(":")[2] for c in callbacks if c.startswith("mkt:cat:") and c != "mkt:cat:all:1"}
    known = getattr(handlers.marketplace, "KNOWN_CATS", None)
    if known:
        assert slugs == set(known) - {"all"}


# ---------------------------------------------------------------------------
# Test 6: Empty filtered result
# ---------------------------------------------------------------------------
def test_marketplace_empty_filtered_result(bot_session):
    """Empty category display shows friendly message and category reset buttons."""
    driver, recorder, _, _ = bot_session
    tg_id = 777106
    seed_user(tg_id)

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "mkt:cat:dating:1")

    last_text = (recorder.last_text or "").lower()
    assert "пусто" in last_text or "нет объявлений" in last_text or "empty" in last_text
    callbacks = [b.callback_data for row in recorder.records[-1].reply_markup.keyboard for b in row if getattr(b, "callback_data", None)]
    assert "mkt:cat:all:1" in callbacks
    assert "hub:mkt" in callbacks


# ---------------------------------------------------------------------------
# Test 7: Catalog excludes deleted and pending offers
# ---------------------------------------------------------------------------
def test_marketplace_catalog_excludes_deleted_and_pending_offers(bot_session):
    """Only status='active' offers are displayed in public catalog."""
    driver, recorder, _, _ = bot_session
    tg_id = 777107
    seed_user(tg_id)

    id_active = database.save_offer(tg_id, "Active Visible Offer", category="services")
    id_deleted = database.save_offer(tg_id, "Deleted Invisible Offer", category="services")
    id_pending = database.save_offer(tg_id, "Pending Deleted Offer", category="services")

    conn = database.sqlite3.connect(database.DB_PATH)
    conn.execute("UPDATE offers SET status = 'deleted' WHERE id = ?", (id_deleted,))
    conn.execute("UPDATE offers SET status = 'deleted_pending' WHERE id = ?", (id_pending,))
    conn.commit()
    conn.close()

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "mkt:cat:all:1")

    last_text = recorder.last_text or ""
    assert "Active Visible Offer" in last_text
    assert "Deleted Invisible Offer" not in last_text
    assert "Pending Deleted Offer" not in last_text


# ---------------------------------------------------------------------------
# Test 8: Detail card view renders correctly
# ---------------------------------------------------------------------------
def test_marketplace_card_detail_view_renders_correctly(bot_session):
    """mkt:v:<id>:<cat>:<page> opens full card with title, description, price, and author link."""
    driver, recorder, _, _ = bot_session
    author_id = 888108
    viewer_id = 777108
    seed_user(author_id, username="pro_seller", name="Pro Seller")
    seed_user(viewer_id)

    offer_id = database.save_offer(
        author_id,
        "Super Gaming Laptop\nRTX 4090, 64GB RAM, Mint condition.\nContact for tests.",
        category="things",
        price=250000
    )

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(viewer_id, f"mkt:v:{offer_id}:things:1")

    last_text = recorder.last_text or ""
    assert "Super Gaming Laptop" in last_text
    assert "RTX 4090" in last_text
    assert "250000" in last_text

    # Author URL button
    urls = [b.url for row in recorder.records[-1].reply_markup.keyboard for b in row if getattr(b, "url", None)]
    assert "https://t.me/pro_seller" in urls


# ---------------------------------------------------------------------------
# Test 9: Card for deleted or missing listing
# ---------------------------------------------------------------------------
def test_marketplace_card_for_deleted_or_missing_listing(bot_session):
    """Clicking a card for a deleted or missing offer shows alert and returns to list."""
    driver, recorder, _, _ = bot_session
    tg_id = 777109
    seed_user(tg_id)

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "mkt:v:999999:all:1")

    # Toast / Alert check
    answered = get_answered_callbacks(recorder)
    assert any(a.get("show_alert") is True and "недоступно" in (a.get("text") or "").lower() for a in answered)


# ---------------------------------------------------------------------------
# Test 10: Card contact button with username
# ---------------------------------------------------------------------------
def test_marketplace_card_contact_button_with_username(bot_session):
    """If author has username, a direct Telegram contact link is rendered."""
    driver, recorder, _, _ = bot_session
    author_id = 888110
    viewer_id = 777110
    seed_user(author_id, username="art_master")
    seed_user(viewer_id)

    offer_id = database.save_offer(author_id, "Custom Painting\nOil on canvas", category="services")

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(viewer_id, f"mkt:v:{offer_id}:services:1")

    urls = [b.url for row in recorder.records[-1].reply_markup.keyboard for b in row if getattr(b, "url", None)]
    assert "https://t.me/art_master" in urls


# ---------------------------------------------------------------------------
# Test 11: Card contact button anonymous author
# ---------------------------------------------------------------------------
def test_marketplace_card_contact_button_anonymous_author(bot_session):
    """If author has no username, contact button is hidden and note is shown."""
    driver, recorder, _, _ = bot_session
    author_id = 888111
    viewer_id = 777111
    seed_user(author_id, username=None)
    seed_user(viewer_id)

    offer_id = database.save_offer(author_id, "Anonymous Advice\nAsk me anything", category="other")

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(viewer_id, f"mkt:v:{offer_id}:other:1")

    last_text = recorder.last_text or ""
    assert "Автор не указал публичный контакт" in last_text
    assert str(author_id) not in last_text  # Privacy: never leak raw tg_id

    urls = [b.url for row in recorder.records[-1].reply_markup.keyboard for b in row if getattr(b, "url", None)]
    assert len(urls) == 0


# ---------------------------------------------------------------------------
# Test 12: Back button restores category and page
# ---------------------------------------------------------------------------
def test_marketplace_back_button_restores_category_and_page(bot_session):
    """Back button in card generates mkt:cat:<cat>:<page> to return to exact position."""
    driver, recorder, _, _ = bot_session
    author_id = 888112
    viewer_id = 777112
    seed_user(author_id, username="dev_back")
    seed_user(viewer_id)

    offer_id = database.save_offer(author_id, "Special Offer Item\nInfo", category="services")

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(viewer_id, f"mkt:v:{offer_id}:services:3")

    callbacks = [b.callback_data for row in recorder.records[-1].reply_markup.keyboard for b in row if getattr(b, "callback_data", None)]
    assert "mkt:cat:services:3" in callbacks


# ---------------------------------------------------------------------------
# Test 13: Back preserves original filter, not offer's category
# ---------------------------------------------------------------------------
def test_marketplace_back_preserves_original_filter_not_offer_category(bot_session):
    """Viewing a 'services' offer from 'all' page 2 sets back button to 'all:2'."""
    driver, recorder, _, _ = bot_session
    author_id = 888113
    viewer_id = 777113
    seed_user(author_id, username="dev_all")
    seed_user(viewer_id)

    offer_id = database.save_offer(author_id, "Services item viewed in All filter\nInfo", category="services")

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(viewer_id, f"mkt:v:{offer_id}:all:2")

    callbacks = [b.callback_data for row in recorder.records[-1].reply_markup.keyboard for b in row if getattr(b, "callback_data", None)]
    assert "mkt:cat:all:2" in callbacks
    assert "mkt:cat:services:1" not in callbacks


# ---------------------------------------------------------------------------
# Test 14: Dispatcher routing (parametrized across all marketplace callbacks & states)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("cb_template,setup_state", [
    ("mkt:cat:all:1", None),
    ("mkt:v:{id}:all:1", None),
    ("mkt:cats", None),
    ("hub:mkt:confirm", "offer"),   # FSM: clear session + render
    ("hub:mkt", None),              # IDLE: direct render without confirmation
])
def test_marketplace_dispatcher_routing(bot_session, cb_template, setup_state):
    """Callback updates are routed directly to handlers without catch-all interception."""
    driver, recorder, _, _ = bot_session
    tg_id = 777114
    seed_user(tg_id)
    offer_id = database.save_offer(tg_id, "Dispatcher Route Item\nDetails", category="services")
    cb_data = cb_template.format(id=offer_id)

    if setup_state:
        database.set_session(tg_id, setup_state, {"draft": "in_progress"})
    else:
        database.set_session(tg_id, None, {})

    recorder.clear()
    CLICK_TRACKER.clear()
    update_json = {
        "update_id": 990114,
        "callback_query": {
            "id": "cb_route_114",
            "from": {"id": tg_id, "is_bot": False, "first_name": "Test"},
            "message": {
                "message_id": 5001,
                "date": 100000,
                "chat": {"id": tg_id, "type": "private"},
                "text": "Initial text"
            },
            "chat_instance": f"ci_{tg_id}",
            "data": cb_data
        }
    }
    driver.bot.process_new_updates([Update.de_json(update_json)])

    # Must NOT be intercepted by legacy catch-all toast
    answered = get_answered_callbacks(recorder)
    assert not any("unknown action" in (a.get("text") or "").lower() for a in answered)
    assert any(r.method == "edit_message_text" for r in recorder.records)

    # In confirm cases, session must end up cleared to IDLE
    if cb_template == "hub:mkt:confirm":
        state, _ = database.get_session(tg_id)
        assert state is None or state == "IDLE"


# ---------------------------------------------------------------------------
# Test 15: Self listings visible
# ---------------------------------------------------------------------------
def test_marketplace_self_listings_visible(bot_session):
    """The viewer's own offers are visible in the public marketplace catalog."""
    driver, recorder, _, _ = bot_session
    tg_id = 777115
    seed_user(tg_id, username="my_own_user")

    database.save_offer(tg_id, "My Own Public Offer\nSelf item visible", category="services")

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "mkt:cat:all:1")

    last_text = recorder.last_text or ""
    assert "My Own Public Offer" in last_text


# ---------------------------------------------------------------------------
# Test 16: HTML escaping in foreign description
# ---------------------------------------------------------------------------
def test_marketplace_html_escape_in_foreign_description(bot_session):
    """HTML injection in foreign offer text is safely escaped without parse error."""
    driver, recorder, _, _ = bot_session
    author_id = 888116
    viewer_id = 777116
    seed_user(author_id, username="hacker")
    seed_user(viewer_id)

    xss_payload = '<script>alert(1)</script> & <b>bold</b> <unknown_tag>'
    offer_id = database.save_offer(author_id, xss_payload, category="other")

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(viewer_id, f"mkt:v:{offer_id}:all:1")

    last_text = recorder.last_text or ""
    assert "<script>" not in last_text
    assert "&lt;script&gt;" in last_text
    assert "&lt;unknown_tag&gt;" in last_text


# ---------------------------------------------------------------------------
# Test 17: Marketplace callback rejected in active FSM (parametrized)
# Note: Phase 1 regression check - currently caught by catch-all in RED,
# will be caught explicitly by marketplace callback handler in GREEN.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("cb", ["mkt:cat:all:1", "mkt:v:1:all:1", "mkt:cats"])
def test_marketplace_callback_rejected_in_active_fsm(bot_session, cb):
    """Clicking mkt:* while in active FSM is blocked with warning toast."""
    driver, recorder, _, _ = bot_session
    tg_id = 777117
    seed_user(tg_id)

    database.set_session(tg_id, "offer", {"text": "Draft in progress"})

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, cb)

    answered = get_answered_callbacks(recorder)
    assert any("завершите" in (a.get("text") or "").lower() and a.get("show_alert") is True for a in answered)

    state, data = database.get_session(tg_id)
    assert state == "offer"
    assert data.get("text") == "Draft in progress"

    # Must NOT render catalog content over draft form
    assert not any("каталог" in (r.text or "").lower() for r in recorder.records if r.method == "edit_message_text")


# ---------------------------------------------------------------------------
# Test 18: Author without users row
# ---------------------------------------------------------------------------
def test_marketplace_author_without_users_row(bot_session):
    """Offer by an author missing from users table renders safely via LEFT JOIN."""
    driver, recorder, _, _ = bot_session
    orphan_author_id = 999118
    viewer_id = 777118
    seed_user(viewer_id)

    # Save offer directly without seeding users row
    offer_id = database.save_offer(orphan_author_id, "Orphan Offer\nNo user row in DB", category="other")

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(viewer_id, f"mkt:v:{offer_id}:all:1")

    last_text = recorder.last_text or ""
    assert "Orphan Offer" in last_text
    assert "Автор не указал публичный контакт" in last_text
    assert str(orphan_author_id) not in last_text


# ---------------------------------------------------------------------------
# Test 19: Username normalization
# ---------------------------------------------------------------------------
def test_marketplace_username_normalization():
    """Validates Telegram username normalization against strict rules."""
    if normalize_username is None:
        pytest.fail("normalize_username function not implemented in handlers.marketplace")

    test_cases = [
        (None, None),
        ("", None),
        ("@foo", None),              # < 5 chars
        ("foo", None),               # < 5 chars
        ("@my_bot", "my_bot"),       # valid 6 chars
        ("my_bot", "my_bot"),        # valid 6 chars
        ("foo_bar", "foo_bar"),      # valid 7 chars
        ("foo.bar", None),           # dot forbidden in TG username
        ("Маша", None),              # non-latin forbidden
        ("a", None),                 # < 5 chars
        ("a" * 40, None),            # > 32 chars
    ]
    for raw, expected in test_cases:
        assert normalize_username(raw) == expected


# ---------------------------------------------------------------------------
# Test 20: Hub mkt FSM confirmation and cancel
# ---------------------------------------------------------------------------
def test_hub_mkt_fsm_confirmation_and_cancel(bot_session):
    """hub:mkt during active FSM requests confirmation; cancel keeps draft, confirm clears."""
    driver, recorder, _, _ = bot_session
    tg_id = 777120
    seed_user(tg_id)

    database.set_session(tg_id, "offer", {"draft": "Important content"})

    # Step 1: Click hub:mkt
    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "hub:mkt")

    # Verify callback is answered (no spinning button in UI)
    answered_1 = get_answered_callbacks(recorder)
    assert len(answered_1) >= 1

    # Should ask confirmation
    last_text = (recorder.last_text or "").lower()
    assert "несохран" in last_text or "прервать" in last_text or "черновик" in last_text
    callbacks = [b.callback_data for row in recorder.records[-1].reply_markup.keyboard for b in row if getattr(b, "callback_data", None)]
    assert "hub:mkt:confirm" in callbacks
    assert "noop" in callbacks

    # Step 2: Click cancel (noop) -> stays in FSM
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "noop")
    state, data = database.get_session(tg_id)
    assert state == "offer"
    assert data.get("draft") == "Important content"

    # Step 3: Click confirm -> clears FSM and enters marketplace
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "hub:mkt:confirm")
    state, _ = database.get_session(tg_id)
    assert state is None or state == "IDLE"

    # Verify confirm callback is answered
    answered_3 = get_answered_callbacks(recorder)
    assert len(answered_3) >= 2


# ---------------------------------------------------------------------------
# Test 21: Title truncation
# ---------------------------------------------------------------------------
def test_marketplace_title_truncation():
    """Extracts first line as raw title and truncates to max 50 chars."""
    if extract_title is None:
        pytest.fail("extract_title function not implemented in handlers.marketplace")

    # > 50 chars -> 47 + '...'
    long_text = ("a" * 100) + "\nSecond line"
    assert extract_title(long_text) == ("a" * 47) + "..."

    # Short line -> untouched
    short_text = "Short Title\nDetails"
    assert extract_title(short_text) == "Short Title"

    # Empty text -> default fallback
    assert extract_title("") == "Объявление Civis"
    assert extract_title(None) == "Объявление Civis"

    # Raw title keeps content without premature escaping; presentation layer handles escaping
    html_text = ("<b>bold</b>" * 20) + "\nDesc"
    title_res = extract_title(html_text)
    assert len(title_res) <= 50
    assert title_res.endswith("...")


# ---------------------------------------------------------------------------
# Test 22: Card text overflow truncation (parametrized by has_username)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("has_username,expected_note", [
    (True, "свяжитесь с автором"),
    (False, "Текст сокращен"),
])
def test_marketplace_card_text_overflow_truncation(bot_session, has_username, expected_note):
    """Descriptions exceeding 800 chars are truncated to safe bounds."""
    driver, recorder, _, _ = bot_session
    author_id = 888122 if has_username else 888123
    viewer_id = 777122
    uname = "big_author" if has_username else None
    seed_user(author_id, username=uname)
    seed_user(viewer_id)

    giant_text = "Paragraph One Header\n" + ("B" * 2000)
    offer_id = database.save_offer(author_id, giant_text, category="other")

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(viewer_id, f"mkt:v:{offer_id}:all:1")

    last_text = recorder.last_text or ""
    # Raw 2000 B's must not be present
    assert ("B" * 1000) not in last_text
    assert expected_note in last_text
    if not has_username:
        assert "свяжитесь с автором" not in last_text


# ---------------------------------------------------------------------------
# Test 23: Card malformed back parameters
# ---------------------------------------------------------------------------
def test_marketplace_card_malformed_back_params(bot_session):
    """Malformed category and page in mkt:v render card and fallback safely to mkt:cat:all:1."""
    driver, recorder, _, _ = bot_session
    author_id = 888124
    viewer_id = 777124
    seed_user(author_id, username="normal_user")
    seed_user(viewer_id)

    offer_id = database.save_offer(author_id, "Malformed Params Test\nDetails here", category="services")

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(viewer_id, f"mkt:v:{offer_id}:invalid_category:xyz")

    # (a) Card renders properly (not rejected on bad category parameter)
    last_text = recorder.last_text or ""
    assert "Malformed Params Test" in last_text

    # (b) Safe back callback must default to all:1
    callbacks = [b.callback_data for row in recorder.records[-1].reply_markup.keyboard for b in row if getattr(b, "callback_data", None)]
    assert "mkt:cat:all:1" in callbacks
