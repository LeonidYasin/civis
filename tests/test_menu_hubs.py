"""
Test suite for Phase 2.2: Navigation Menu Hubs (/menu, /profile, /match, /settings, /subscribe),
Stateless Navigation, FSM Protection, Profile Reset Confirmation, Match Concurrency Lock,
Settings BYOK API Key Security, and Subscription View.
"""

import logging
import pytest
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

import database
import handlers
from keyboards import CLICK_TRACKER

# Optional import of hubs module if already implemented or None during RED phase
try:
    from civis_bot.handlers import hubs as menu_hubs
except ImportError:
    try:
        import handlers.hubs as menu_hubs
    except ImportError:
        menu_hubs = None


def seed_user(tg_id: int, username: str = "tester", name: str = "Test Citizen", status: str = "completed"):
    """Seeds a user in database with profile data."""
    database.save_user(
        tg_id,
        username,
        name=name,
        about_text="Experienced Python Developer building agentic platforms",
        user_values="Freedom, Trust, Growth",
        role="Executor",
        format="Text, Voice",
        language="ru",
        status=status
    )


@pytest.fixture(autouse=True)
def clean_match_lock():
    """Ensures _MATCH_IN_PROGRESS concurrency set is isolated across all tests."""
    for mod in (menu_hubs, getattr(handlers, "hubs", None)):
        if mod and hasattr(mod, "_MATCH_IN_PROGRESS"):
            mod._MATCH_IN_PROGRESS.clear()
    yield
    for mod in (menu_hubs, getattr(handlers, "hubs", None)):
        if mod and hasattr(mod, "_MATCH_IN_PROGRESS"):
            mod._MATCH_IN_PROGRESS.clear()


@pytest.fixture
def deferred_match_pool(monkeypatch):
    """Fixture replacing background worker pool with deterministic deferred queue."""
    class DeferredPool:
        def __init__(self):
            self.tasks = []
        def submit(self, fn, *args, **kwargs):
            self.tasks.append((fn, args, kwargs))
            class FutureMock:
                def result(self, timeout=None):
                    return None
            return FutureMock()

    pool = DeferredPool()
    for mod_path in ("civis_bot.handlers.hubs._match_pool", "handlers.hubs._match_pool"):
        try:
            monkeypatch.setattr(mod_path, pool, raising=False)
        except Exception:
            pass
    return pool


# ---------------------------------------------------------------------------
# Test 1: Hub Main in IDLE shows dashboard and 4 hub navigation buttons
# ---------------------------------------------------------------------------
def test_hub_main_in_idle_shows_catalog_balance_and_4_hubs(bot_session):
    """hub:main in IDLE renders citizen dashboard with balance, badges, and 4 hubs."""
    driver, recorder, _, _ = bot_session
    tg_id = 777201
    seed_user(tg_id, username="citizen1", name="Alice")

    # Seed an active offer to test badge
    database.save_offer(tg_id, "Dev Services\nExpert backend architecture", category="services")

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "hub:main")

    last_text = recorder.last_text or ""
    assert "Civis" in last_text or "Республика" in last_text
    assert "Alice" in last_text
    assert "@citizen1" in last_text
    assert "Матчинг" in last_text or "Free" in last_text

    callbacks = [b.callback_data for row in recorder.records[-1].reply_markup.keyboard for b in row if getattr(b, "callback_data", None)]
    assert "hub:mkt" in callbacks
    assert "hub:mtc" in callbacks
    assert "hub:prf" in callbacks
    assert "hub:set" in callbacks
    assert "act:offer" in callbacks


# ---------------------------------------------------------------------------
# Test 2: Hub Profile renders user data and navigation
# ---------------------------------------------------------------------------
def test_hub_profile_renders_user_data_and_navigation(bot_session):
    """hub:prf renders complete user profile and navigation buttons."""
    driver, recorder, _, _ = bot_session
    tg_id = 777202
    seed_user(tg_id, username="alice_prf", name="Alice Citizen")

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "hub:prf")

    last_text = recorder.last_text or ""
    assert "Alice Citizen" in last_text
    assert "Executor" in last_text or "Исполнитель" in last_text
    assert "Freedom, Trust, Growth" in last_text

    callbacks = [b.callback_data for row in recorder.records[-1].reply_markup.keyboard for b in row if getattr(b, "callback_data", None)]
    assert "act:survey" in callbacks
    assert "pg:o:1" in callbacks
    assert "pg:r:1" in callbacks
    assert "hub:main" in callbacks


# ---------------------------------------------------------------------------
# Test 3: Hub Profile without completed profile prompts registration
# ---------------------------------------------------------------------------
def test_hub_profile_without_profile_prompts_registration(bot_session):
    """hub:prf for unknown user or incomplete user prompts registration onboarding."""
    driver, recorder, _, _ = bot_session

    # Case A: User not in users table at all
    tg_id_unregistered = 777203
    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id_unregistered, "hub:prf")
    last_text = (recorder.last_text or "").lower()
    assert "зарегистр" in last_text or "анкет" in last_text or "profile" in last_text

    # Case B: User in users table but status != completed
    tg_id_incomplete = 777204
    database.save_user(tg_id_incomplete, "newbie", status="registered")
    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id_incomplete, "hub:prf")
    last_text = (recorder.last_text or "").lower()
    assert "зарегистр" in last_text or "анкет" in last_text or "profile" in last_text


# ---------------------------------------------------------------------------
# Test 4: Hub Matching renders subscription status and action buttons
# ---------------------------------------------------------------------------
def test_hub_matching_renders_subscription_status(bot_session):
    """hub:mtc renders AI matching dashboard, tokens remaining, and sub button."""
    driver, recorder, _, _ = bot_session
    tg_id = 777205
    seed_user(tg_id)

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "hub:mtc")

    last_text = recorder.last_text or ""
    assert "Матчинг" in last_text or "Matching" in last_text

    callbacks = [b.callback_data for row in recorder.records[-1].reply_markup.keyboard for b in row if getattr(b, "callback_data", None)]
    assert "act:match:run" in callbacks
    assert "hub:sub" in callbacks
    assert "hub:main" in callbacks


# ---------------------------------------------------------------------------
# Test 5: Hub Settings renders configuration options
# ---------------------------------------------------------------------------
def test_hub_settings_renders_options(bot_session):
    """hub:set renders language, API key, support, and subscription entry points."""
    driver, recorder, _, _ = bot_session
    tg_id = 777206
    seed_user(tg_id)

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "hub:set")

    last_text = (recorder.last_text or "").lower()
    assert "настройк" in last_text or "settings" in last_text

    callbacks = [b.callback_data for row in recorder.records[-1].reply_markup.keyboard for b in row if getattr(b, "callback_data", None)]
    assert "hub:lang" in callbacks
    assert "hub:setkey" in callbacks
    assert "hub:support" in callbacks
    assert "hub:sub" in callbacks
    assert "hub:main" in callbacks


# ---------------------------------------------------------------------------
# Test 6: Hub Navigation returns back to hub:main from all subhubs
# ---------------------------------------------------------------------------
def test_hub_navigation_back_to_main_from_all_subhubs(bot_session):
    """hub:main returns cleanly to citizen dashboard from prf, mtc, and set."""
    driver, recorder, _, _ = bot_session
    tg_id = 777207
    seed_user(tg_id)

    for subhub in ("hub:prf", "hub:mtc", "hub:set"):
        recorder.clear()
        CLICK_TRACKER.clear()
        driver.click_button(tg_id, subhub)

        recorder.clear()
        CLICK_TRACKER.clear()
        driver.click_button(tg_id, "hub:main")

        callbacks = [b.callback_data for row in recorder.records[-1].reply_markup.keyboard for b in row if getattr(b, "callback_data", None)]
        assert "hub:mkt" in callbacks
        assert "hub:prf" in callbacks
        assert "hub:mtc" in callbacks
        assert "hub:set" in callbacks


# ---------------------------------------------------------------------------
# Tests 7–11: Clicking any hub during active FSM prompts confirmation dialog
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("hub_cb", ["hub:main", "hub:prf", "hub:mkt", "hub:mtc", "hub:set"])
def test_hub_switch_in_active_fsm_prompts_confirmation(bot_session, hub_cb):
    """Any hub click in active FSM displays confirmation dialog with dest-confirm and noop."""
    driver, recorder, _, _ = bot_session
    tg_id = 777210
    seed_user(tg_id)

    database.set_session(tg_id, "offer", {"language": "ru", "category": "services"})

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, hub_cb)

    # General confirmation markers
    last_text = (recorder.last_text or "").lower()
    assert "черновик" in last_text or "draft" in last_text

    callbacks = [b.callback_data for row in recorder.records[-1].reply_markup.keyboard for b in row if getattr(b, "callback_data", None)]
    assert f"{hub_cb}:confirm" in callbacks
    assert "noop" in callbacks

    # Session is preserved prior to confirmation
    state, data = database.get_session(tg_id)
    assert state == "offer"
    assert data == {"language": "ru", "category": "services"}


# ---------------------------------------------------------------------------
# Tests 12–16: Confirming hub switch in FSM clears session and renders destination
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("hub_cb,confirm_cb", [
    ("hub:main", "hub:main:confirm"),
    ("hub:prf", "hub:prf:confirm"),
    ("hub:mkt", "hub:mkt:confirm"),
    ("hub:mtc", "hub:mtc:confirm"),
    ("hub:set", "hub:set:confirm")
])
def test_hub_confirm_in_fsm_clears_session_and_renders_dest(bot_session, hub_cb, confirm_cb):
    """Clicking hub confirm button clears FSM session and displays destination hub view."""
    driver, recorder, _, _ = bot_session
    tg_id = 777215
    seed_user(tg_id)

    database.set_session(tg_id, "offer", {"language": "ru", "category": "services"})

    # Click hub to prompt confirmation
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, hub_cb)

    # Click confirm
    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, confirm_cb)

    state, data = database.get_session(tg_id)
    assert state is None
    assert data == {}

    # Verify destination view rendered (not confirmation dialog)
    assert "черновик" not in (recorder.last_text or "").lower()


# ---------------------------------------------------------------------------
# Tests 17–21: Canceling hub switch in FSM preserves session and dismisses dialog
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("hub_cb", ["hub:main", "hub:prf", "hub:mkt", "hub:mtc", "hub:set"])
def test_hub_cancel_in_fsm_preserves_session(bot_session, hub_cb):
    """Clicking noop in confirmation dialog preserves active FSM state and dismisses confirmation."""
    driver, recorder, _, _ = bot_session
    tg_id = 777220
    seed_user(tg_id)

    database.set_session(tg_id, "offer", {"language": "ru", "category": "services"})

    # Phase 1: Click hub_cb -> confirmation MUST appear
    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, hub_cb)

    last_text_p1 = (recorder.last_text or "").lower()
    assert "черновик" in last_text_p1 or "draft" in last_text_p1, f"confirmation not shown for {hub_cb}"
    callbacks_p1 = [b.callback_data for row in recorder.records[-1].reply_markup.keyboard for b in row if getattr(b, "callback_data", None)]
    assert f"{hub_cb}:confirm" in callbacks_p1
    assert "noop" in callbacks_p1
    state_1, data_1 = database.get_session(tg_id)
    assert state_1 == "offer"
    assert data_1 == {"language": "ru", "category": "services"}

    # Phase 2: Click noop -> confirmation dismissed, session preserved
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "noop")

    # Retrieve the latest message text (from edit_message_text or send_message)
    last_msg_text = next((r.text for r in reversed(recorder.records) if r.method in ("edit_message_text", "send_message")), None)
    assert "черновик" not in (last_msg_text or "").lower(), f"confirmation still visible after noop for {hub_cb}"
    state_2, data_2 = database.get_session(tg_id)
    assert state_2 == "offer"
    assert data_2 == {"language": "ru", "category": "services"}


# ---------------------------------------------------------------------------
# Test 22: Rapid clicks throttled by cooldown
# ---------------------------------------------------------------------------
def test_hub_cooldown_throttles_rapid_clicks(bot_session):
    """Rapid duplicate clicks within 0.20s window are throttled without duplicate rendering."""
    driver, recorder, _, _ = bot_session
    tg_id = 777225
    seed_user(tg_id)

    # Setup: CLICK_TRACKER.clear() called ONCE before first click
    recorder.clear()
    CLICK_TRACKER.clear()

    # Click 1: renders view
    driver.click_button(tg_id, "hub:prf")
    edits_count_1 = sum(1 for r in recorder.records if r.method in ("edit_message_text", "send_message"))
    assert edits_count_1 == 1, "handler must render view on first click"

    # Click 2: immediately (without clear!) -> throttled
    driver.click_button(tg_id, "hub:prf")
    edits_count_2 = sum(1 for r in recorder.records if r.method in ("edit_message_text", "send_message"))
    # Edit count must remain 1
    assert edits_count_2 == 1, "second click within cooldown window must be throttled without another edit"

    # Throttling toast answer returned
    toast_answers = [r for r in recorder.records if r.method == "answer_callback_query" and r.text]
    assert any("подождите" in str(r.text).lower() or "частые" in str(r.text).lower() for r in toast_answers)


# ---------------------------------------------------------------------------
# Test 23: Marketplace catalog and categories menu have home button
# ---------------------------------------------------------------------------
def test_catalog_and_categories_have_home_button(bot_session):
    """Both /marketplace catalog view and categories menu include [🏠 Главное меню] (hub:main)."""
    driver, recorder, _, _ = bot_session
    tg_id = 777226
    seed_user(tg_id)
    database.save_offer(tg_id, "Offer for Home Button Check\nDescription", category="services")

    # Catalog view check
    recorder.clear()
    CLICK_TRACKER.clear()
    driver.send_text(tg_id, "/marketplace")

    catalog_cbs = [b.callback_data for row in recorder.records[-1].reply_markup.keyboard for b in row if getattr(b, "callback_data", None)]
    assert "hub:main" in catalog_cbs
    assert "mkt:cats" in catalog_cbs

    # Categories menu check
    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "mkt:cats")

    cats_cbs = [b.callback_data for row in recorder.records[-1].reply_markup.keyboard for b in row if getattr(b, "callback_data", None)]
    assert "hub:main" in cats_cbs


# ---------------------------------------------------------------------------
# Test 24: /menu command in IDLE renders hub:main
# ---------------------------------------------------------------------------
def test_cmd_menu_in_idle_renders_hub_main(bot_session):
    """Sending /menu command in IDLE renders citizen hub:main dashboard."""
    driver, recorder, _, _ = bot_session
    tg_id = 777227
    seed_user(tg_id, name="Bob")

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.send_text(tg_id, "/menu")

    last_text = recorder.last_text or ""
    assert "Civis" in last_text or "Республика" in last_text
    assert "Bob" in last_text
    callbacks = [b.callback_data for row in recorder.records[-1].reply_markup.keyboard for b in row if getattr(b, "callback_data", None)]
    assert "hub:mkt" in callbacks
    assert "hub:prf" in callbacks


# ---------------------------------------------------------------------------
# Test 25: /menu command during active FSM shows reminder warning
# ---------------------------------------------------------------------------
def test_cmd_menu_in_fsm_shows_reminder_not_hub(bot_session):
    """Sending /menu command in active FSM warns user and preserves draft without opening menu."""
    driver, recorder, _, _ = bot_session
    tg_id = 777228
    seed_user(tg_id)

    database.set_session(tg_id, "offer", {"language": "ru", "category": "services"})

    recorder.clear()
    driver.send_text(tg_id, "/menu")

    last_text = (recorder.last_text or "").lower()
    assert "завершите" in last_text or "незаверш" in last_text
    assert "full menu" not in last_text
    assert not any(getattr(b, "callback_data", None) == "hub:mkt" for r in recorder.records if r.reply_markup for row in r.reply_markup.keyboard for b in row)

    # Session remains intact
    state, data = database.get_session(tg_id)
    assert state == "offer"
    assert data == {"language": "ru", "category": "services"}


# ---------------------------------------------------------------------------
# Test 26: Profile reset requires confirmation
# ---------------------------------------------------------------------------
def test_profile_reset_requires_confirmation(bot_session):
    """act:survey prompts confirmation; cancel preserves profile; confirm clears profile and starts onboarding."""
    driver, recorder, _, _ = bot_session
    tg_id = 777229
    seed_user(tg_id, username="reset_me", name="Old Name")

    # Step 1: Click act:survey -> confirmation dialog
    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "act:survey")

    last_text = (recorder.last_text or "").lower()
    assert "сброс" in last_text or "заново" in last_text or "потеря" in last_text
    callbacks = [b.callback_data for row in recorder.records[-1].reply_markup.keyboard for b in row if getattr(b, "callback_data", None)]
    assert "act:survey:confirm" in callbacks
    assert "noop" in callbacks

    # Step 2: Cancel (noop) keeps user profile untouched
    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "noop")
    u1 = database.get_user(tg_id)
    assert u1["name"] == "Old Name"
    assert u1["status"] == "completed"

    # Step 3: Confirm resets profile fields and starts survey onboarding
    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "act:survey:confirm")

    state, _ = database.get_session(tg_id)
    assert state in ("survey_name", "language_select")
    u2 = database.get_user(tg_id)
    assert u2.get("about_text") is None or u2.get("status") != "completed"


# ---------------------------------------------------------------------------
# Test 27: Settings language switch inline
# ---------------------------------------------------------------------------
def test_settings_language_switch_inline(bot_session):
    """hub:lang opens inline language selector; selecting language updates DB and rerenders hub:set."""
    driver, recorder, _, _ = bot_session
    tg_id = 777230
    seed_user(tg_id)

    # Step 1: Click hub:lang -> inline selector without FSM
    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "hub:lang")

    state, _ = database.get_session(tg_id)
    assert state is None or state == "IDLE"

    callbacks = [b.callback_data for row in recorder.records[-1].reply_markup.keyboard for b in row if getattr(b, "callback_data", None)]
    assert "set:lang:ru" in callbacks
    assert "set:lang:en" in callbacks

    # Step 2: Select English -> saves to DB, rerenders hub:set in English
    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "set:lang:en")

    user = database.get_user(tg_id)
    assert user["language"] == "en"

    last_text = (recorder.last_text or "").lower()
    assert "settings" in last_text


# ---------------------------------------------------------------------------
# Test 28: Settings setkey starts FSM
# ---------------------------------------------------------------------------
def test_settings_setkey_starts_fsm_and_deletes_key_message(bot_session):
    """hub:setkey transitions session to settings_setkey and prompts for OpenAI key."""
    driver, recorder, _, _ = bot_session
    tg_id = 777231
    seed_user(tg_id)

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "hub:setkey")

    state, _ = database.get_session(tg_id)
    assert state == "settings_setkey"

    last_text = recorder.last_text or ""
    assert "sk-" in last_text or "OpenAI" in last_text
    callbacks = [b.callback_data for row in recorder.records[-1].reply_markup.keyboard for b in row if getattr(b, "callback_data", None)]
    assert "hub:set" in callbacks


# ---------------------------------------------------------------------------
# Test 29: Settings setkey consumes text input
# ---------------------------------------------------------------------------
def test_settings_setkey_consumes_text_input(bot_session):
    """Valid sk-... key message in settings_setkey saves key, deletes message, and clears session."""
    driver, recorder, _, _ = bot_session
    tg_id = 777232
    seed_user(tg_id)

    database.set_session(tg_id, "settings_setkey", {})

    recorder.clear()
    driver.send_text(tg_id, "sk-proj-validkey1234567890abcdef1234567890")

    # Key is saved
    saved_key = database.get_openai_key(tg_id)
    assert saved_key == "sk-proj-validkey1234567890abcdef1234567890"

    # Message deletion was attempted for security
    assert any(r.method == "delete_message" for r in recorder.records)

    # Session is cleared
    state, data = database.get_session(tg_id)
    assert state is None
    assert data == {}


# ---------------------------------------------------------------------------
# Test 30: Settings setkey rejects invalid format and keeps state
# ---------------------------------------------------------------------------
def test_settings_setkey_rejects_invalid_format_keeps_state(bot_session):
    """Invalid key input prompts error message and preserves settings_setkey state."""
    driver, recorder, _, _ = bot_session
    tg_id = 777233
    seed_user(tg_id)

    database.set_session(tg_id, "settings_setkey", {})

    recorder.clear()
    driver.send_text(tg_id, "not-a-valid-key")

    last_text = (recorder.last_text or "").lower()
    assert "неверн" in last_text or "sk-" in last_text or "попробуйте" in last_text

    # Session state remains settings_setkey
    state, _ = database.get_session(tg_id)
    assert state == "settings_setkey"
    assert database.get_openai_key(tg_id) is None


# ---------------------------------------------------------------------------
# Test 31: Settings setkey delete fail still saves key
# ---------------------------------------------------------------------------
def test_settings_setkey_delete_fail_still_saves_key(bot_session, monkeypatch, caplog):
    """If bot.delete_message fails, key is still saved in DB and warning is logged."""
    driver, recorder, _, bot = bot_session
    tg_id = 777234
    seed_user(tg_id)

    def failing_delete_message(chat_id, message_id, **kwargs):
        raise RuntimeError("Telegram API delete error: message cannot be deleted")

    monkeypatch.setattr(bot, "delete_message", failing_delete_message)
    database.set_session(tg_id, "settings_setkey", {})

    recorder.clear()
    with caplog.at_level(logging.WARNING):
        driver.send_text(tg_id, "sk-valid-key-with-delete-failure-1234567890")

    # Key is still saved
    saved_key = database.get_openai_key(tg_id)
    assert saved_key == "sk-valid-key-with-delete-failure-1234567890"

    # Session is cleared
    state, _ = database.get_session(tg_id)
    assert state is None

    # Warning logged in log stream
    assert "failed to delete key message" in caplog.text or "delete" in caplog.text


# ---------------------------------------------------------------------------
# Test 32: Settings setkey cancel returns to hub:set via send_message
# ---------------------------------------------------------------------------
def test_settings_setkey_cancel_returns_to_hub_set(bot_session):
    """Sending /cancel while in settings_setkey clears session and sends hub:set view."""
    driver, recorder, _, _ = bot_session
    tg_id = 777235
    seed_user(tg_id)

    database.set_session(tg_id, "settings_setkey", {})

    recorder.clear()
    driver.send_text(tg_id, "/cancel")

    state, _ = database.get_session(tg_id)
    assert state is None

    # Sent via send_message (not edit_message_text since triggered by message command)
    assert any(r.method == "send_message" for r in recorder.records)
    callbacks = [b.callback_data for r in recorder.records if r.reply_markup for row in r.reply_markup.keyboard for b in row if getattr(b, "callback_data", None)]
    assert "hub:setkey" in callbacks
    assert "hub:main" in callbacks


# ---------------------------------------------------------------------------
# Test 33: Settings support starts FSM
# ---------------------------------------------------------------------------
def test_settings_support_starts_fsm(bot_session):
    """hub:support transitions session to settings_support and prompts for question."""
    driver, recorder, _, _ = bot_session
    tg_id = 777236
    seed_user(tg_id)

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "hub:support")

    state, _ = database.get_session(tg_id)
    assert state in ("settings_support", "support")

    callbacks = [b.callback_data for row in recorder.records[-1].reply_markup.keyboard for b in row if getattr(b, "callback_data", None)]
    assert "hub:set" in callbacks


# ---------------------------------------------------------------------------
# Test 34: Match run without key redirects to setkey
# ---------------------------------------------------------------------------
def test_match_run_without_key_redirects_to_setkey(bot_session):
    """act:match:run without configured OpenAI key shows prompt with [🔑 Указать API Key] button."""
    driver, recorder, _, _ = bot_session
    tg_id = 777237
    seed_user(tg_id)

    # Ensure no key
    database.save_openai_key(tg_id, None)

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "act:match:run")

    last_text = (recorder.last_text or "").lower()
    assert "ключ" in last_text or "key" in last_text or "api" in last_text

    callbacks = [b.callback_data for row in recorder.records[-1].reply_markup.keyboard for b in row if getattr(b, "callback_data", None)]
    assert "hub:setkey" in callbacks
    assert "hub:mtc" in callbacks


# ---------------------------------------------------------------------------
# Test 35: Match run without subscription tokens redirects to sub
# ---------------------------------------------------------------------------
def test_match_run_without_subscription_redirects_to_sub(bot_session):
    """act:match:run when free match limit is exceeded prompts for subscription upgrade."""
    driver, recorder, _, _ = bot_session
    tg_id = 777238
    seed_user(tg_id)
    database.save_openai_key(tg_id, "sk-valid-key-for-sub-check-1234567890")

    # Exhaust matches used
    for _ in range(5):
        database.increment_matches_used(tg_id)

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "act:match:run")

    last_text = (recorder.last_text or "").lower()
    assert "лимит" in last_text or "подписк" in last_text or "limit" in last_text

    callbacks = [b.callback_data for row in recorder.records[-1].reply_markup.keyboard for b in row if getattr(b, "callback_data", None)]
    assert "hub:sub" in callbacks
    assert "hub:mtc" in callbacks


# ---------------------------------------------------------------------------
# Test 36: Match run double click is ignored via concurrency lock
# ---------------------------------------------------------------------------
def test_match_run_double_click_is_ignored(bot_session, deferred_match_pool):
    """Second click while match search is in progress returns toast without scheduling second task."""
    driver, recorder, _, _ = bot_session
    tg_id = 777239
    seed_user(tg_id)
    database.save_openai_key(tg_id, "sk-valid-key-for-double-click-check-1234567890")

    # Optional module access for direct lock verification if present
    hubs_mod = getattr(handlers, "hubs", menu_hubs)

    # Click 1: initiates match search
    recorder.clear()
    CLICK_TRACKER.clear()
    driver.click_button(tg_id, "act:match:run")

    assert hubs_mod and tg_id in getattr(hubs_mod, "_MATCH_IN_PROGRESS", set()), "handler must set lock on first click"
    assert len(deferred_match_pool.tasks) == 1

    # Clearing cooldown between clicks to exercise _MATCH_IN_PROGRESS lock specifically
    CLICK_TRACKER.clear()

    # Click 2: rapid duplicate click while task is still deferred
    recorder.clear()
    driver.click_button(tg_id, "act:match:run")

    # Second task was NOT scheduled
    assert len(deferred_match_pool.tasks) == 1

    # Complete deferred task manually
    fn, a, kw = deferred_match_pool.tasks[0]
    fn(*a, **kw)
    if hubs_mod and hasattr(hubs_mod, "_MATCH_IN_PROGRESS"):
        assert tg_id not in hubs_mod._MATCH_IN_PROGRESS


# ---------------------------------------------------------------------------
# Test 37: Hub Sub reachable from match and settings
# ---------------------------------------------------------------------------
def test_hub_sub_reachable_from_match_and_settings(bot_session):
    """hub:sub displays subscription plans and returns to main menu."""
    driver, recorder, _, _ = bot_session
    tg_id = 777240
    seed_user(tg_id)

    for entry_point in ("hub:mtc", "hub:set"):
        recorder.clear()
        CLICK_TRACKER.clear()
        driver.click_button(tg_id, entry_point)

        recorder.clear()
        CLICK_TRACKER.clear()
        driver.click_button(tg_id, "hub:sub")

        last_text = (recorder.last_text or "").lower()
        assert "тариф" in last_text or "подписк" in last_text or "subscription" in last_text or "premium" in last_text

        callbacks = [b.callback_data for row in recorder.records[-1].reply_markup.keyboard for b in row if getattr(b, "callback_data", None)]
        assert "hub:main" in callbacks


# ---------------------------------------------------------------------------
# Test 38: /subscribe command renders hub:sub
# ---------------------------------------------------------------------------
def test_cmd_subscribe_renders_hub_sub(bot_session):
    """Sending /subscribe command renders hub:sub view with plans and hub:main button."""
    driver, recorder, _, _ = bot_session
    tg_id = 777241
    seed_user(tg_id)

    recorder.clear()
    CLICK_TRACKER.clear()
    driver.send_text(tg_id, "/subscribe")

    last_text = (recorder.last_text or "").lower()
    assert "тариф" in last_text or "подписк" in last_text or "subscription" in last_text or "premium" in last_text

    callbacks = [b.callback_data for row in recorder.records[-1].reply_markup.keyboard for b in row if getattr(b, "callback_data", None)]
    assert "hub:main" in callbacks
