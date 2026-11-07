#!/usr/bin/env python3
"""
Navigation Menu Hubs for Civis Bot (Phase 2.2).
Provides stateless navigation hubs:
- hub:main (Dashboard)
- hub:prf (Citizen Profile)
- hub:mkt (Marketplace Catalog)
- hub:mtc (AI Matching)
- hub:set (Account Settings)
- hub:sub (Subscription Leaf View)
- hub:lang (Inline Language Picker)
Includes FSM gate with confirmation dialogs, BYOK security, and match concurrency lock.
"""

import concurrent.futures
import html
import logging
import threading
from typing import Optional

from telebot.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import database
from config import ADMIN_CHAT_ID
from keyboards import CLICK_TRACKER
from utils import find_matches, generate_match_explanation

from .helpers import bot, safe_edit_message
from .marketplace import render_marketplace_catalog

logger = logging.getLogger(__name__)

# Concurrency lock and thread pool for AI matching
_MATCH_LOCK = threading.Lock()
_MATCH_IN_PROGRESS: set = set()
_match_pool = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="match_worker")

COOLDOWN_BY_PREFIX = {
    "hub:": 0.20,
    "set:lang:": 0.30,
    "act:": 0.30,
}


def _check_cooldown(call: CallbackQuery) -> bool:
    """Checks whether the callback action is within cooldown window."""
    tg_id = call.from_user.id
    data = call.data or ""
    action_key = data
    cooldown = 0.20
    for prefix, window in COOLDOWN_BY_PREFIX.items():
        if data.startswith(prefix):
            action_key = prefix
            cooldown = window
            break
    return not CLICK_TRACKER.is_throttled(tg_id, action_key, custom_window=cooldown)


# ---------------------------------------------------------------------------
# 1. Hub Main (Citizen Dashboard)
# ---------------------------------------------------------------------------
def render_hub_main(chat_id: int, tg_id: int, message_id: Optional[int] = None):
    """Renders citizen dashboard with name, role, balances, and 4 navigation hubs."""
    user = database.get_user(tg_id) or {}
    name = html.escape(user.get("name") or "Гражданин")
    username = f"@{html.escape(user['username'])}" if user.get("username") else "N/A"
    role = html.escape(user.get("role") or "Не указана")

    tier = html.escape(database.get_user_tier(tg_id))
    matches_left = database.get_matches_left(tg_id)
    matches_str = "∞" if matches_left == float("inf") else str(matches_left)
    active_offers_count = database.get_active_offers_count(tg_id)

    text = (
        "🏛 <b>Civis — Республика Профессионалов</b>\n\n"
        f"👤 <b>{name}</b> ({username})\n"
        f"🎖 Роль: <b>{role}</b>\n\n"
        f"🎯 Матчинг: <b>{tier}</b> (осталось токенов: {matches_str})\n"
        f"📦 Активных объявлений: <b>{active_offers_count}</b>"
    )

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🏬 Маркетплейс", callback_data="hub:mkt"),
        InlineKeyboardButton("🎯 Матчинг", callback_data="hub:mtc")
    )
    markup.row(
        InlineKeyboardButton("👤 Профиль", callback_data="hub:prf"),
        InlineKeyboardButton("⚙️ Настройки", callback_data="hub:set")
    )
    markup.row(
        InlineKeyboardButton("➕ Создать объявление", callback_data="act:offer")
    )

    if message_id:
        safe_edit_message(bot, chat_id, message_id, text, reply_markup=markup, parse_mode='HTML')
    else:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')


# ---------------------------------------------------------------------------
# 2. Hub Profile (Citizen Questionnaire View)
# ---------------------------------------------------------------------------
def render_hub_profile(chat_id: int, tg_id: int, message_id: Optional[int] = None):
    """Renders citizen profile card or onboarding prompt if incomplete."""
    user = database.get_user(tg_id)
    if not user or user.get("status") != "completed":
        text = (
            "👤 <b>Профиль гражданина</b>\n\n"
            "У вас пока нет заполненного профиля в Республике Civis.\n"
            "Пройдите короткую анкету, чтобы открыть доступ к матчингу и сообществу."
        )
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("📝 Заполнить анкету", callback_data="act:survey"))
        markup.row(InlineKeyboardButton("🔙 В главное меню", callback_data="hub:main"))
    else:
        text = (
            "👤 <b>Профиль гражданина</b>\n\n"
            f"<b>Имя:</b> {html.escape(user.get('name') or 'N/A')}\n"
            f"<b>Telegram:</b> @{html.escape(user.get('username') or 'N/A')}\n"
            f"<b>Роль:</b> {html.escape(user.get('role') or 'N/A')}\n"
            f"<b>Ценности:</b> {html.escape(user.get('user_values') or 'N/A')}\n"
            f"<b>Формат:</b> {html.escape(user.get('format') or 'N/A')}\n\n"
            f"<b>О себе:</b>\n{html.escape(user.get('about_text') or 'N/A')}"
        )
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("✏️ Заполнить заново", callback_data="act:survey"))
        markup.row(
            InlineKeyboardButton("📦 Мои объявления", callback_data="pg:o:1"),
            InlineKeyboardButton("📋 Мои запросы", callback_data="pg:r:1")
        )
        markup.row(InlineKeyboardButton("🔙 В главное меню", callback_data="hub:main"))

    if message_id:
        safe_edit_message(bot, chat_id, message_id, text, reply_markup=markup, parse_mode='HTML')
    else:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')


# ---------------------------------------------------------------------------
# 3. Hub Matching (AI Search View)
# ---------------------------------------------------------------------------
def render_hub_match(chat_id: int, tg_id: int, message_id: Optional[int] = None):
    """Renders AI matching dashboard with tokens count and execution trigger."""
    tier = html.escape(database.get_user_tier(tg_id))
    matches_left = database.get_matches_left(tg_id)
    matches_str = "∞" if matches_left == float("inf") else str(matches_left)

    text = (
        "🎯 <b>AI-Матчинг профессионалов</b>\n\n"
        "Умный поиск партнёров, клиентов и исполнителей на основе ваших ценностей и интересов.\n\n"
        f"<b>Ваш тариф:</b> {tier}\n"
        f"<b>Доступно матчей:</b> {matches_str}"
    )

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🔍 Запустить матчинг", callback_data="act:match:run"))
    markup.row(InlineKeyboardButton("💳 Подписка", callback_data="hub:sub"))
    markup.row(InlineKeyboardButton("🔙 В главное меню", callback_data="hub:main"))

    if message_id:
        safe_edit_message(bot, chat_id, message_id, text, reply_markup=markup, parse_mode='HTML')
    else:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')


# ---------------------------------------------------------------------------
# 4. Hub Settings (Language, BYOK Key, Support)
# ---------------------------------------------------------------------------
def render_hub_settings(chat_id: int, tg_id: int, message_id: Optional[int] = None):
    """Renders account settings with language, key status (bool only), and support."""
    user = database.get_user(tg_id) or {}
    lang = user.get("language", "ru")
    lang_title = "Русский 🇷🇺" if lang == "ru" else "English 🇬🇧"
    has_key = bool(database.get_openai_key(tg_id))

    markup = InlineKeyboardMarkup()
    if lang == "en":
        key_status = "Connected ✅" if has_key else "Not set ⚠️"
        key_btn = "✅ Key set" if has_key else "🔑 OpenAI Key"
        text = (
            "⚙️ <b>Account Settings</b>\n\n"
            f"<b>Interface Language:</b> {lang_title}\n"
            f"<b>OpenAI API Key (BYOK):</b> {key_status}"
        )
        markup.row(InlineKeyboardButton("🌐 Change language", callback_data="hub:lang"))
        markup.row(InlineKeyboardButton(key_btn, callback_data="hub:setkey"))
        markup.row(
            InlineKeyboardButton("📩 Support", callback_data="hub:support"),
            InlineKeyboardButton("💳 Subscription", callback_data="hub:sub")
        )
        markup.row(InlineKeyboardButton("🔙 Main menu", callback_data="hub:main"))
    else:
        key_status = "Подключён ✅" if has_key else "Не установлен ⚠️"
        key_btn = "✅ Key установлен" if has_key else "🔑 OpenAI Key"
        text = (
            "⚙️ <b>Настройки аккаунта</b>\n\n"
            f"<b>Язык интерфейса:</b> {lang_title}\n"
            f"<b>OpenAI API Key (BYOK):</b> {key_status}"
        )
        markup.row(InlineKeyboardButton("🌐 Сменить язык", callback_data="hub:lang"))
        markup.row(InlineKeyboardButton(key_btn, callback_data="hub:setkey"))
        markup.row(
            InlineKeyboardButton("📩 Поддержка", callback_data="hub:support"),
            InlineKeyboardButton("💳 Подписка", callback_data="hub:sub")
        )
        markup.row(InlineKeyboardButton("🔙 В главное меню", callback_data="hub:main"))

    if message_id:
        safe_edit_message(bot, chat_id, message_id, text, reply_markup=markup, parse_mode='HTML')
    else:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')


# ---------------------------------------------------------------------------
# 5. Hub Sub (Subscription Leaf-View)
# ---------------------------------------------------------------------------
def render_hub_sub(chat_id: int, tg_id: int, message_id: Optional[int] = None):
    """Renders subscription tiers view with home return button."""
    tier = html.escape(database.get_user_tier(tg_id))
    matches_left = database.get_matches_left(tg_id)
    matches_str = "∞" if matches_left == float("inf") else str(matches_left)

    text = (
        "💳 <b>Тарифы и подписка Civis</b>\n\n"
        f"<b>Текущий тариф:</b> {tier}\n"
        f"<b>Осталось матчей:</b> {matches_str}\n\n"
        "<b>Доступные планы:</b>\n"
        "• <b>Free:</b> 3 AI-матчинга в месяц (базовый поиск)\n"
        "• <b>Premium:</b> Безлимитный AI-матчинг, приоритет в выдаче ($9.99/мес)\n"
        "• <b>Lifetime:</b> Пожизненный статус гражданина Республики ($99)"
    )

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🔙 В главное меню", callback_data="hub:main"))

    if message_id:
        safe_edit_message(bot, chat_id, message_id, text, reply_markup=markup, parse_mode='HTML')
    else:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')


# ---------------------------------------------------------------------------
# 6. Inline Language Picker
# ---------------------------------------------------------------------------
def render_hub_lang_picker(chat_id: int, tg_id: int, message_id: Optional[int] = None):
    """Renders inline language selector buttons without entering FSM."""
    text = "🌐 <b>Выберите язык интерфейса / Choose language:</b>"
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🇷🇺 Русский", callback_data="set:lang:ru"),
        InlineKeyboardButton("🇬🇧 English", callback_data="set:lang:en")
    )
    markup.row(InlineKeyboardButton("🔙 Назад", callback_data="hub:set"))

    if message_id:
        safe_edit_message(bot, chat_id, message_id, text, reply_markup=markup, parse_mode='HTML')
    else:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')


# ---------------------------------------------------------------------------
# Helpers for Hub Routing
# ---------------------------------------------------------------------------
def _render_dest_hub(chat_id: int, tg_id: int, dest_hub: str, message_id: Optional[int] = None):
    """Routes destination hub string to its respective renderer."""
    if dest_hub == "hub:main":
        render_hub_main(chat_id, tg_id, message_id=message_id)
    elif dest_hub == "hub:prf":
        render_hub_profile(chat_id, tg_id, message_id=message_id)
    elif dest_hub == "hub:mkt":
        render_marketplace_catalog(chat_id, tg_id, cat="all", requested_page=1, message_id=message_id)
    elif dest_hub == "hub:mtc":
        render_hub_match(chat_id, tg_id, message_id=message_id)
    elif dest_hub == "hub:set":
        render_hub_settings(chat_id, tg_id, message_id=message_id)
    elif dest_hub == "hub:sub":
        render_hub_sub(chat_id, tg_id, message_id=message_id)


# ---------------------------------------------------------------------------
# Async Matching Execution
# ---------------------------------------------------------------------------
def _execute_match_search(tg_id: int, chat_id: int, message_id: int):
    """Background worker task executing match calculation with error handling."""
    try:
        user = database.get_user(tg_id) or {}
        key = database.get_openai_key(tg_id)

        matches = find_matches(tg_id, key, limit=5)
        if matches is None:
            text = (
                "❌ <b>Сервис матчинга временно недоступен.</b>\n\n"
                "Не удалось рассчитать эмбеддинги профиля. Попробуйте позже."
            )
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("🔄 Попробовать снова", callback_data="act:match:run"),
                InlineKeyboardButton("🔙 В меню", callback_data="hub:mtc")
            )
            safe_edit_message(bot, chat_id, message_id, text, reply_markup=markup, parse_mode='HTML')
            return

        if not matches:
            text = (
                "🔍 <b>Подходящих совпадений пока не найдено.</b>\n\n"
                "Попробуйте дополнить описание профиля или повторите поиск позже."
            )
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("🔄 Попробовать снова", callback_data="act:match:run"),
                InlineKeyboardButton("🔙 В меню", callback_data="hub:mtc")
            )
            safe_edit_message(bot, chat_id, message_id, text, reply_markup=markup, parse_mode='HTML')
            return

        database.increment_matches_used(tg_id)

        text_lines = ["🤝 <b>Ваши лучшие совпадения:</b>\n"]
        for i, match in enumerate(matches, 1):
            explanation = generate_match_explanation(user, match)
            m_username = f"@{html.escape(match.get('username') or 'N/A')}"
            m_name = html.escape(match.get('name') or 'N/A')
            m_role = html.escape(match.get('role') or 'N/A')
            m_values = html.escape(match.get('values') or 'N/A')
            score = match.get('score', 0)
            text_lines.append(
                f"{i}. <b>{m_name}</b> ({m_username})\n"
                f"   Роль: {m_role}\n"
                f"   Ценности: {m_values}\n"
                f"   Совпадение: <b>{score}%</b>\n"
                f"   <i>{html.escape(explanation)}</i>\n"
            )

        rem = database.get_matches_left(tg_id)
        rem_str = "∞" if rem == float("inf") else str(rem)
        text_lines.append(f"<i>Осталось матчей: {rem_str}</i>")

        text = "\n".join(text_lines)
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("🔄 Обновить", callback_data="act:match:run"),
            InlineKeyboardButton("🔙 В меню", callback_data="hub:mtc")
        )
        safe_edit_message(bot, chat_id, message_id, text, reply_markup=markup, parse_mode='HTML')
    except Exception as e:
        logger.exception(f"match run failed for tg_id={tg_id}: {e}")
        text = (
            "❌ <b>Сервис матчинга временно недоступен.</b>\n\n"
            "Произошла непредвиденная ошибка. Попробуйте позже."
        )
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("🔄 Попробовать снова", callback_data="act:match:run"),
            InlineKeyboardButton("🔙 В меню", callback_data="hub:mtc")
        )
        safe_edit_message(bot, chat_id, message_id, text, reply_markup=markup, parse_mode='HTML')
    finally:
        with _MATCH_LOCK:
            _MATCH_IN_PROGRESS.discard(tg_id)


def _start_match_run(call: CallbackQuery):
    """Initiates matching run, validating preconditions and holding concurrency lock."""
    tg_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    # 1. Check API key precondition
    key = database.get_openai_key(tg_id)
    if not key:
        try:
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.warning(f"answer_callback_query failed: {e}")
        text = (
            "🔑 <b>Для AI-матчинга требуется OpenAI API Key (BYOK).</b>\n\n"
            "Пожалуйста, укажите ваш персональный API-ключ в настройках."
        )
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("🔑 Указать API Key", callback_data="hub:setkey"),
            InlineKeyboardButton("🔙 В меню", callback_data="hub:mtc")
        )
        safe_edit_message(bot, chat_id, message_id, text, reply_markup=markup, parse_mode='HTML')
        return

    # 2. Check tokens limit precondition
    if not database.can_use_match(tg_id):
        try:
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.warning(f"answer_callback_query failed: {e}")
        text = (
            "💳 <b>Лимит бесплатных матчей исчерпан (0 осталось).</b>\n\n"
            "Оформите подписку для безлимитного AI-матчинга."
        )
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("💳 Перейти к тарифам", callback_data="hub:sub"),
            InlineKeyboardButton("🔙 В меню", callback_data="hub:mtc")
        )
        safe_edit_message(bot, chat_id, message_id, text, reply_markup=markup, parse_mode='HTML')
        return

    # 3. Check and acquire concurrency lock
    with _MATCH_LOCK:
        if tg_id in _MATCH_IN_PROGRESS:
            try:
                bot.answer_callback_query(call.id, text="Уже идёт поиск совпадений…", show_alert=False)
            except Exception as e:
                logger.warning(f"answer_callback_query failed: {e}")
            return
        _MATCH_IN_PROGRESS.add(tg_id)

    # 4. Silent feedback and launch background task
    try:
        bot.answer_callback_query(call.id)
    except Exception as e:
        logger.warning(f"answer_callback_query failed: {e}")

    safe_edit_message(bot, chat_id, message_id, "⏳ <b>Ищу совпадения… это займёт 5–10 секунд</b>", parse_mode='HTML')
    _match_pool.submit(_execute_match_search, tg_id, chat_id, message_id)


# ---------------------------------------------------------------------------
# Text Input Handler for Settings States
# ---------------------------------------------------------------------------
def handle_settings_input(message: Message, state: str, data: dict):
    """Handles text message input for settings_setkey and settings_support states."""
    tg_id = message.from_user.id
    chat_id = message.chat.id
    raw_text = (message.text or "").strip()

    if state == "settings_setkey":
        if not (raw_text.startswith("sk-") and len(raw_text) >= 20):
            bot.reply_to(
                message,
                "❌ Ключ не похож на OpenAI (формат: sk-…, ≥20 символов). Попробуйте ещё раз или отправьте /cancel."
            )
            return

        # Attempt to delete secret message from chat history
        try:
            bot.delete_message(chat_id, message.message_id)
        except Exception as e:
            logger.warning(f"failed to delete key message: {e}")

        # Always save key even if delete failed
        database.save_openai_key(tg_id, raw_text)
        database.clear_session(tg_id)
        bot.send_message(chat_id, "✅ OpenAI API Key успешно сохранён!")
        render_hub_settings(chat_id=chat_id, tg_id=tg_id)

    elif state in ("settings_support", "support"):
        if not raw_text:
            bot.reply_to(message, "Пожалуйста, опишите ваш вопрос.")
            return

        admin_target = ADMIN_CHAT_ID
        if admin_target:
            try:
                bot.send_message(
                    admin_target,
                    f"📩 Support message from user {tg_id} (@{message.from_user.username or 'unknown'}):\n\n{raw_text}"
                )
            except Exception as e:
                logger.error(f"Support forward error: {e}")

        database.clear_session(tg_id)
        bot.send_message(chat_id, "✅ Ваше сообщение отправлено в службу поддержки.")
        render_hub_settings(chat_id=chat_id, tg_id=tg_id)


# ---------------------------------------------------------------------------
# Main Hubs Callback Query Dispatcher
# ---------------------------------------------------------------------------
def handle_hub_callbacks(call: CallbackQuery):
    """Central callback query dispatcher for all navigation hubs and FSM gates."""
    tg_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    data = call.data or ""

    state, session_data = database.get_session(tg_id)
    is_fsm_active = (state is not None and state != "IDLE")

    # 1. FSM Gate
    if is_fsm_active:
        if data == "noop":
            try:
                bot.answer_callback_query(call.id)
            except Exception as e:
                logger.warning(f"answer_callback_query failed: {e}")
            safe_edit_message(
                bot, chat_id, message_id,
                "Действие отменено. Вы можете продолжить заполнение формы или отправить /cancel.",
                parse_mode='HTML'
            )
            return
        elif data.startswith("hub:") and data.endswith(":confirm"):
            database.clear_session(tg_id)
            try:
                bot.answer_callback_query(call.id)
            except Exception as e:
                logger.warning(f"answer_callback_query failed: {e}")
            dest_hub = data[:-len(":confirm")]
            _render_dest_hub(chat_id, tg_id, dest_hub, message_id=message_id)
            return
        elif data in ("hub:main", "hub:prf", "hub:mkt", "hub:mtc", "hub:set"):
            try:
                bot.answer_callback_query(call.id)
            except Exception as e:
                logger.warning(f"answer_callback_query failed: {e}")
            text = (
                "⚠️ <b>У вас есть несохранённый черновик!</b>\n\n"
                "Вы находитесь в процессе заполнения формы. "
                "Если перейти в меню, введённые данные будут сброшены.\n\n"
                "Прервать заполнение и выйти?"
            )
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("Да, перейти", callback_data=f"{data}:confirm"),
                InlineKeyboardButton("Отмена", callback_data="noop")
            )
            safe_edit_message(bot, chat_id, message_id, text, reply_markup=markup, parse_mode='HTML')
            return
        else:
            try:
                bot.answer_callback_query(call.id, text="Пожалуйста, сначала завершите текущее действие.", show_alert=True)
            except Exception as e:
                logger.warning(f"answer_callback_query failed: {e}")
            return

    # 2. Cooldown Gate
    if not _check_cooldown(call):
        try:
            bot.answer_callback_query(call.id, text="Слишком частые клики, подождите...", show_alert=False)
        except Exception as e:
            logger.warning(f"answer_callback_query failed: {e}")
        return

    # 3. Silent answer for all non-async triggers
    if data != "act:match:run":
        try:
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.warning(f"answer_callback_query failed: {e}")

    # 4. Dispatch actions in IDLE
    if data == "noop":
        return
    elif data == "hub:main":
        render_hub_main(chat_id, tg_id, message_id=message_id)
    elif data == "hub:prf":
        render_hub_profile(chat_id, tg_id, message_id=message_id)
    elif data == "hub:mkt":
        render_marketplace_catalog(chat_id, tg_id, cat="all", requested_page=1, message_id=message_id)
    elif data == "hub:mtc":
        render_hub_match(chat_id, tg_id, message_id=message_id)
    elif data == "hub:set":
        render_hub_settings(chat_id, tg_id, message_id=message_id)
    elif data == "hub:sub":
        render_hub_sub(chat_id, tg_id, message_id=message_id)
    elif data == "hub:lang":
        render_hub_lang_picker(chat_id, tg_id, message_id=message_id)
    elif data.startswith("set:lang:"):
        parts = data.split(":")
        lang = parts[2] if len(parts) >= 3 else "ru"
        database.set_user_language(tg_id, lang)
        render_hub_settings(chat_id, tg_id, message_id=message_id)
    elif data == "hub:setkey":
        database.set_session(tg_id, "settings_setkey", {})
        text = (
            "🔑 <b>Настройка OpenAI API Key</b>\n\n"
            "Отправьте ваш ключ в сообщении (формат: <code>sk-...</code>, не менее 20 символов).\n\n"
            "<i>Для отмены отправьте /cancel или нажмите кнопку ниже.</i>"
        )
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("❌ Отмена", callback_data="hub:set"))
        safe_edit_message(bot, chat_id, message_id, text, reply_markup=markup, parse_mode='HTML')
    elif data == "hub:support":
        database.set_session(tg_id, "settings_support", {})
        text = (
            "📩 <b>Служба поддержки Civis</b>\n\n"
            "Опишите ваш вопрос или проблему в ответном сообщении.\n\n"
            "<i>Для отмены отправьте /cancel или нажмите кнопку ниже.</i>"
        )
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("❌ Отмена", callback_data="hub:set"))
        safe_edit_message(bot, chat_id, message_id, text, reply_markup=markup, parse_mode='HTML')
    elif data == "act:survey":
        text = (
            "⚠️ <b>Внимание: сброс анкеты</b>\n\n"
            "Вы собираетесь заполнить профиль заново. Все текущие данные анкеты "
            "(имя, о себе, ценности, роль, формат) будут сброшены.\n\n"
            "Начать заново?"
        )
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("Да, начать заново", callback_data="act:survey:confirm"),
            InlineKeyboardButton("Отмена", callback_data="noop")
        )
        safe_edit_message(bot, chat_id, message_id, text, reply_markup=markup, parse_mode='HTML')
    elif data == "act:survey:confirm":
        database.reset_user_profile(tg_id)
        user = database.get_user(tg_id) or {}
        lang = user.get("language", "ru")
        database.set_session(tg_id, "survey_name", {"language": lang})
        bot.send_message(chat_id, "Как вас зовут? / What is your name?")
    elif data == "act:match:run":
        _start_match_run(call)
    elif data.startswith("hub:") and data.endswith(":confirm"):
        dest_hub = data[:-len(":confirm")]
        _render_dest_hub(chat_id, tg_id, dest_hub, message_id=message_id)
    else:
        logger.warning(f"Unhandled hub callback: {data}")
