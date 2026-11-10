#!/usr/bin/env python3
"""
Marketplace command handlers for Civis bot.
Contains: offer, request, my_offers, my_requests, delete_offer, delete_request, marketplace, offers, requests
"""

import logging
import sqlite3
import html
from typing import Optional

from telebot.types import Message, ReplyKeyboardRemove, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database import (
    get_user, get_session, set_session, clear_session,
    get_all_offers, get_all_requests,
    get_my_offers, get_my_requests,
    save_offer, save_request, delete_offer, delete_request,
    soft_delete_offer, soft_delete_request,
    get_catalog_page, get_catalog_count, get_offer_with_author,
    DB_PATH
)
from locales import TEXTS
from keyboards import (
    get_main_keyboard, get_category_keyboard,
    CLICK_TRACKER, get_empty_items_keyboard, get_item_card_keyboard, get_delete_confirm_keyboard
)
from utils import get_text
import mcp_client

from .helpers import (
    log_message, bot, safe_edit_message,
    normalize_username, extract_title
)

logger = logging.getLogger(__name__)

# --- CATEGORY CONSTANTS & SYNONYMS ---

CATEGORY_SYNONYMS = {
    'business': ['business', 'Бизнес', 'бизнес'],
    'jobs': ['jobs', 'job', 'work', 'Работа', 'работа', 'Вакансии', 'вакансии'],
    'services': ['services', 'service', 'Услуги', 'услуги'],
    'real_estate': ['real_estate', 'realty', 'Недвижимость', 'недвижимость'],
    'things': ['things', 'goods', 'Товары', 'товары', 'Вещи', 'вещи'],
    'rides': ['rides', 'taxi', 'Такси', 'такси', 'Поездки', 'поездки'],
    'delivery': ['delivery', 'Доставка', 'доставка'],
    'communities': ['communities', 'community', 'Сообщества', 'сообщества'],
    'dating': ['dating', 'Знакомства', 'знакомства', 'Дейтинг', 'дейтинг'],
    'other': ['other', 'general', 'Другое', 'другое', 'Общее', 'общее'],
}

KNOWN_CATS = set(CATEGORY_SYNONYMS.keys()) | {'all'}

CATEGORY_LABELS = {
    'all': '🌐 Все категории',
    'services': '🛠 Услуги',
    'business': '💼 Бизнес',
    'jobs': '💻 Работа',
    'real_estate': '🏠 Недвижимость',
    'things': '📦 Товары / Вещи',
    'rides': '🚕 Поездки',
    'delivery': '🚚 Доставка',
    'communities': '👥 Сообщества',
    'dating': '❤️ Знакомства',
    'other': '📁 Другое',
}

COOLDOWN_BY_PREFIX = {
    "mkt:cat": 0.08,
    "mkt:v": 0.15,
    "mkt:cats": 0.30,
}


def _safe_cat(cat) -> str:
    if isinstance(cat, str) and (cat in KNOWN_CATS):
        return cat
    return "all"


def _safe_page(p) -> int:
    try:
        val = int(p)
        return max(1, val)
    except (ValueError, TypeError):
        return 1


# --- COMMAND HANDLERS ---

def cmd_offer(message: Message):
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    lang = user.get('language', 'en')
    set_session(tg_id, 'offer_category', {'language': lang})
    bot.reply_to(
        message,
        "Select the category for your offer:\n\nChoose from the buttons below:",
        reply_markup=get_category_keyboard(lang)
    )

def cmd_offer_real_estate(message: Message):
    """Quick offer in real estate category"""
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    lang = user.get('language', 'en')
    set_session(tg_id, 'offer', {'language': lang, 'category': 'real_estate'})
    bot.reply_to(
        message,
        "🏠 **Real Estate Offer**\n\n"
        "Describe your property (price, location, type, area, rooms, etc.):\n\n"
        "Example: \"1-room apartment, 45 sq m, city center, $200,000\"",
        parse_mode='Markdown'
    )

def cmd_offer_taxi(message: Message):
    """Quick offer in taxi category"""
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    lang = user.get('language', 'en')
    set_session(tg_id, 'offer', {'language': lang, 'category': 'taxi'})
    bot.reply_to(
        message,
        "🚕 **Taxi Service Offer**\n\n"
        "Describe your taxi service (car type, price per km, availability, etc.):\n\n"
        "Example: \"Comfort sedan, $2/km, 24/7 available in the city\"",
        parse_mode='Markdown'
    )

def cmd_offer_delivery(message: Message):
    """Quick offer in delivery category"""
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    lang = user.get('language', 'en')
    set_session(tg_id, 'offer', {'language': lang, 'category': 'delivery'})
    bot.reply_to(
        message,
        "📦 **Delivery Service Offer**\n\n"
        "Describe your delivery service (items, price, delivery area, etc.):\n\n"
        "Example: \"Food delivery, $5 per order, within 5 km radius\"",
        parse_mode='Markdown'
    )

def cmd_request(message: Message):
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    lang = user.get('language', 'en')
    set_session(tg_id, 'request_category', {'language': lang})
    bot.reply_to(
        message,
        "Select the category for your request:\n\nChoose from the buttons below:",
        reply_markup=get_category_keyboard(lang)
    )

def render_my_items_screen(chat_id: int, tg_id: int, entity_type: str = "offer", requested_page: int = 1, message_id: Optional[int] = None, user_lang: str = "ru"):
    """
    Renders/edits paginated single-item screen for my_offers or my_requests.
    """
    is_offer = (entity_type == "offer")
    prefix = "o" if is_offer else "r"
    items = get_my_offers(tg_id) if is_offer else get_my_requests(tg_id)
    total_items = len(items)

    if total_items == 0:
        if is_offer:
            text = "У вас пока нет активных предложений (empty)."
        else:
            text = "У вас пока нет активных запросов (empty)."
        markup = get_empty_items_keyboard(prefix, user_lang)
        if message_id:
            safe_edit_message(bot, chat_id, message_id, text, reply_markup=markup, parse_mode='HTML')
        else:
            bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')
        return

    total_pages = total_items
    current_page = max(1, min(requested_page, total_pages))
    item = items[current_page - 1]

    item_id = item[0]
    category = item[1] or "general"
    item_text = item[2] or ""
    created_at = item[8] if len(item) > 8 and item[8] else ""
    created_str = str(created_at)[:10] if created_at else ""

    escaped_text = html.escape(item_text)
    escaped_cat = html.escape(category)

    if is_offer:
        header = f"📦 <b>Ваше предложение [ {current_page} / {total_pages} ]</b>"
    else:
        header = f"📥 <b>Ваш запрос [ {current_page} / {total_pages} ]</b>"

    text = (
        f"{header}\n\n"
        f"<b>Категория:</b> {escaped_cat}\n"
        f"{escaped_text}\n\n"
        f"<i>ID: {item_id} | Создано: {created_str}</i>"
    )

    markup = get_item_card_keyboard(prefix, item_id, current_page, total_pages, user_lang)
    if message_id:
        safe_edit_message(bot, chat_id, message_id, text, reply_markup=markup, parse_mode='HTML')
    else:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')


def render_delete_confirm_screen(chat_id: int, message_id: int, entity_type: str, item_id: int, page: int, user_lang: str = "ru"):
    """Renders confirmation card for delete action."""
    prefix = "o" if entity_type == "offer" else "r"
    name = "предложение" if entity_type == "offer" else "запрос"
    text = (
        f"⚠️ <b>Подтверждение удаления</b>\n\n"
        f"Вы действительно хотите отозвать и удалить это {name} (ID #{item_id})?"
    )
    markup = get_delete_confirm_keyboard(prefix, item_id, page, user_lang)
    safe_edit_message(bot, chat_id, message_id, text, reply_markup=markup, parse_mode='HTML')


def handle_confirm_delete(chat_id: int, message_id: int, tg_id: int, entity_type: str, item_id: int, page: int, callback_query_id: str, user_lang: str = "ru"):
    """Processes confirmed deletion: marks deleted_pending locally and queues MCP revocation."""
    is_offer = (entity_type == "offer")
    deleted = soft_delete_offer(item_id, tg_id) if is_offer else soft_delete_request(item_id, tg_id)
    if not deleted:
        try:
            bot.answer_callback_query(callback_query_id, text="Это объявление уже удалено.", show_alert=False)
        except Exception:
            pass
        render_my_items_screen(chat_id, tg_id, entity_type=entity_type, requested_page=page, message_id=message_id, user_lang=user_lang)
        return

    payload = {"action": "revoke_listing", "id": item_id}
    mcp_client.trigger_background_sync(tg_id, entity_type, item_id, payload, action="revoke_listing")

    try:
        bot.answer_callback_query(callback_query_id, text="Объявление удалено.")
    except Exception:
        pass

    render_my_items_screen(chat_id, tg_id, entity_type=entity_type, requested_page=page, message_id=message_id, user_lang=user_lang)


def render_marketplace_hub(chat_id: int, message_id: Optional[int] = None):
    """Renders marketplace hub escape hatch view."""
    text = (
        "🛒 <b>Маркетплейс Civis</b>\n\n"
        "Здесь вы можете управлять своими предложениями и запросами, а также находить совпадения через Marketplace OS."
    )
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("📦 Мои предложения", callback_data="pg:o:1"),
        InlineKeyboardButton("📥 Мои запросы", callback_data="pg:r:1")
    )
    markup.row(
        InlineKeyboardButton("➕ Создать оффер", callback_data="act:offer"),
        InlineKeyboardButton("➕ Создать запрос", callback_data="act:request")
    )
    if message_id:
        safe_edit_message(bot, chat_id, message_id, text, reply_markup=markup, parse_mode='HTML')
    else:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')


def render_marketplace_catalog(
    chat_id: int,
    tg_id: int,
    cat: str = "all",
    requested_page: int = 1,
    message_id: Optional[int] = None
):
    """
    Renders 5-item paginated public catalog screen with category filter.
    """
    safe_cat = _safe_cat(cat)
    page = _safe_page(requested_page)

    category_slugs = None if safe_cat == "all" else CATEGORY_SYNONYMS.get(safe_cat, [safe_cat])
    total_count = get_catalog_count(category_slugs)

    if total_count == 0:
        cat_label = CATEGORY_LABELS.get(safe_cat, safe_cat)
        text = (
            f"🛒 <b>Маркетплейс Civis</b>\n"
            f"Категория: <b>{html.escape(cat_label)}</b>\n\n"
            f"В этой категории пока нет объявлений (пусто)."
        )
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("📂 Все категории", callback_data="mkt:cat:all:1"))
        markup.row(InlineKeyboardButton("🔙 В меню", callback_data="hub:mkt"))
        if message_id:
            safe_edit_message(bot, chat_id, message_id, text, reply_markup=markup, parse_mode='HTML')
        else:
            bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')
        return

    limit = 5
    total_pages = (total_count + limit - 1) // limit
    if page > total_pages:
        page = total_pages
    if page < 1:
        page = 1

    offset = (page - 1) * limit
    items = get_catalog_page(category_slugs, limit=limit, offset=offset)

    cat_label = CATEGORY_LABELS.get(safe_cat, safe_cat)
    text_lines = [
        f"🛒 <b>Маркетплейс Civis</b> [ {page} / {total_pages} ]",
        f"Категория: <b>{html.escape(cat_label)}</b> (всего: {total_count})\n",
    ]

    item_buttons = []
    for i, item in enumerate(items, 1):
        title = extract_title(item["text"])
        escaped_title = html.escape(title)
        price_val = item["price"]
        price_str = f" — <i>{price_val} ₽</i>" if price_val is not None else ""
        text_lines.append(f"{i}. <b>{escaped_title}</b>{price_str}")
        item_buttons.append(
            InlineKeyboardButton(
                text=f"[ {i} ]",
                callback_data=f"mkt:v:{item['id']}:{safe_cat}:{page}"
            )
        )

    text = "\n".join(text_lines)

    markup = InlineKeyboardMarkup()
    if item_buttons:
        markup.row(*item_buttons)

    prev_cb = "noop" if page <= 1 else f"mkt:cat:{safe_cat}:{page - 1}"
    next_cb = f"mkt:cat:{safe_cat}:{page + 1}" if page < total_pages else "noop"
    markup.row(
        InlineKeyboardButton("◀", callback_data=prev_cb),
        InlineKeyboardButton(f"{page} / {total_pages}", callback_data="noop"),
        InlineKeyboardButton("▶", callback_data=next_cb)
    )

    markup.row(
        InlineKeyboardButton("📂 Категории", callback_data="mkt:cats"),
        InlineKeyboardButton("🏠 Главное меню", callback_data="hub:main")
    )

    if message_id:
        safe_edit_message(bot, chat_id, message_id, text, reply_markup=markup, parse_mode='HTML')
    else:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')


def render_categories_menu(chat_id: int, message_id: Optional[int] = None):
    """
    Renders 11-button category selector menu (All + 10 slugs in 2 columns).
    """
    text = "📂 <b>Выберите категорию каталога:</b>"
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🌐 Все категории", callback_data="mkt:cat:all:1"))

    slugs = ['services', 'business', 'jobs', 'real_estate', 'things', 'rides', 'delivery', 'communities', 'dating', 'other']
    for i in range(0, len(slugs), 2):
        row_btns = []
        s1 = slugs[i]
        row_btns.append(InlineKeyboardButton(CATEGORY_LABELS.get(s1, s1), callback_data=f"mkt:cat:{s1}:1"))
        if i + 1 < len(slugs):
            s2 = slugs[i + 1]
            row_btns.append(InlineKeyboardButton(CATEGORY_LABELS.get(s2, s2), callback_data=f"mkt:cat:{s2}:1"))
        markup.row(*row_btns)

    if message_id:
        safe_edit_message(bot, chat_id, message_id, text, reply_markup=markup, parse_mode='HTML')
    else:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')


def render_marketplace_card(
    chat_id: int,
    tg_id: int,
    offer_id: int,
    cat: str = "all",
    page: int = 1,
    message_id: Optional[int] = None,
    call_id: Optional[str] = None
):
    """
    Renders detail card for a single offer with author username URL or anonymous note.
    """
    safe_cat = _safe_cat(cat)
    safe_p = _safe_page(page)

    offer = get_offer_with_author(offer_id)
    if not offer:
        if call_id:
            try:
                bot.answer_callback_query(call_id, text="Объявление больше недоступно.", show_alert=True)
            except Exception as e:
                logger.warning(f"answer_callback_query failed for {call_id}: {e}")
        render_marketplace_catalog(chat_id, tg_id, cat=safe_cat, requested_page=safe_p, message_id=message_id)
        return

    raw_text = offer["text"] or ""
    title = extract_title(raw_text)
    escaped_title = html.escape(title)

    author_username = normalize_username(offer["username"])
    has_username = bool(author_username)

    if len(raw_text) > 800:
        truncated_text = raw_text[:800] + "..."
        if has_username:
            overflow_note = "\n\n<i>(Текст сокращен, свяжитесь с автором)</i>"
        else:
            overflow_note = "\n\n<i>(Текст сокращен)</i>"
    else:
        truncated_text = raw_text
        overflow_note = ""

    escaped_desc = html.escape(truncated_text)

    category_slug = offer["category"] or "other"
    category_label = CATEGORY_LABELS.get(category_slug, category_slug)
    price_val = offer["price"]
    price_text = f"<b>Цена:</b> {price_val} ₽\n" if price_val is not None else ""
    created_at = str(offer["created_at"])[:10] if offer["created_at"] else ""

    contact_note = ""
    if not has_username:
        contact_note = "\n<i>(Автор не указал публичный контакт)</i>\n"

    card_text = (
        f"<b>Категория:</b> {html.escape(category_label)}\n"
        f"{price_text}\n"
        f"{escaped_desc}{overflow_note}\n"
        f"{contact_note}\n"
        f"<i>Создано: {created_at}</i>"
    )

    markup = InlineKeyboardMarkup()
    if has_username:
        markup.row(InlineKeyboardButton("💬 Написать автору", url=f"https://t.me/{author_username}"))
    markup.row(InlineKeyboardButton("⬅ К списку", callback_data=f"mkt:cat:{safe_cat}:{safe_p}"))

    if message_id:
        safe_edit_message(bot, chat_id, message_id, card_text, reply_markup=markup, parse_mode='HTML')
    else:
        bot.send_message(chat_id, card_text, reply_markup=markup, parse_mode='HTML')


def handle_marketplace_callbacks(call: CallbackQuery):
    """Unified callback query handler for marketplace pagination, deletion and navigation."""
    tg_id = call.from_user.id
    data = call.data or ""
    chat_id = call.message.chat.id if call.message and call.message.chat else tg_id
    message_id = call.message.message_id if call.message else None

    # 1. Anti-flood click throttle check
    action_key = data.split(":")[0] if ":" in data else data
    if data.startswith("mkt:cat"):
        action_key = "mkt:cat"
    elif data.startswith("mkt:v"):
        action_key = "mkt:v"
    elif data.startswith("mkt:cats"):
        action_key = "mkt:cats"

    cooldown = COOLDOWN_BY_PREFIX.get(action_key, 1.0)
    if CLICK_TRACKER.is_throttled(tg_id, action_key, custom_window=cooldown):
        try:
            bot.answer_callback_query(call.id, text="Слишком частые клики, подождите...")
        except Exception as e:
            logger.warning(f"answer_callback_query failed for {call.id}: {e}")
        return

    # 2. FSM Policy check
    state, session_data = get_session(tg_id)
    is_fsm_active = (state is not None and state != "IDLE")

    if is_fsm_active:
        if data == "noop":
            try:
                bot.answer_callback_query(call.id)
            except Exception as e:
                logger.warning(f"answer_callback_query failed for {call.id}: {e}")
            return
        elif data.startswith("cxl_del:"):
            pass  # Allowed without clearing session
        elif data == "hub:mkt":
            # Confirmation dialog in active FSM
            try:
                bot.answer_callback_query(call.id)
            except Exception as e:
                logger.warning(f"answer_callback_query failed for {call.id}: {e}")
            text = (
                "⚠️ <b>У вас есть несохранённый черновик!</b>\n\n"
                "Вы находитесь в процессе заполнения формы. "
                "Если перейти в маркетплейс, введённые данные будут сброшены.\n\n"
                "Прервать заполнение и перейти в каталог?"
            )
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("Да, перейти", callback_data="hub:mkt:confirm"),
                InlineKeyboardButton("Отмена", callback_data="noop")
            )
            if message_id:
                safe_edit_message(bot, chat_id, message_id, text, reply_markup=markup, parse_mode='HTML')
            else:
                bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')
            return
        elif data == "hub:mkt:confirm":
            clear_session(tg_id)
            try:
                bot.answer_callback_query(call.id)
            except Exception as e:
                logger.warning(f"answer_callback_query failed for {call.id}: {e}")
            render_marketplace_catalog(chat_id, tg_id, cat="all", requested_page=1, message_id=message_id)
            return
        elif data.startswith("mkt:"):
            try:
                bot.answer_callback_query(call.id, text="Пожалуйста, сначала завершите текущее действие.", show_alert=True)
            except Exception as e:
                logger.warning(f"answer_callback_query failed for {call.id}: {e}")
            return
        elif data in ["act:offer", "act:request"] and state in ["offer_category", "request_category"]:
            pass
        else:
            try:
                bot.answer_callback_query(call.id, text="Пожалуйста, сначала завершите текущее действие.", show_alert=True)
            except Exception as e:
                logger.warning(f"answer_callback_query failed for {call.id}: {e}")
            return

    # 3. Handle data in IDLE state
    if data == "noop":
        try:
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.warning(f"answer_callback_query failed for {call.id}: {e}")
        return

    if data == "hub:mkt:confirm":
        clear_session(tg_id)
        try:
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.warning(f"answer_callback_query failed for {call.id}: {e}")
        render_marketplace_catalog(chat_id, tg_id, cat="all", requested_page=1, message_id=message_id)
        return

    if data == "hub:mkt":
        try:
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.warning(f"answer_callback_query failed for {call.id}: {e}")
        render_marketplace_catalog(chat_id, tg_id, cat="all", requested_page=1, message_id=message_id)
        return

    if data == "mkt:cats":
        try:
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.warning(f"answer_callback_query failed for {call.id}: {e}")
        render_categories_menu(chat_id, message_id=message_id)
        return

    if data.startswith("mkt:cat:"):
        parts = data.split(":")
        cat = parts[2] if len(parts) >= 3 else "all"
        page = int(parts[3]) if len(parts) >= 4 and parts[3].isdigit() else 1
        try:
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.warning(f"answer_callback_query failed for {call.id}: {e}")
        render_marketplace_catalog(chat_id, tg_id, cat=cat, requested_page=page, message_id=message_id)
        return

    if data.startswith("mkt:v:"):
        parts = data.split(":")
        if len(parts) >= 5:
            try:
                offer_id = int(parts[2])
            except ValueError:
                offer_id = 0
            cat = parts[3]
            page = parts[4]
            try:
                bot.answer_callback_query(call.id)
            except Exception as e:
                logger.warning(f"answer_callback_query failed for {call.id}: {e}")
            render_marketplace_card(chat_id, tg_id, offer_id=offer_id, cat=cat, page=page, message_id=message_id, call_id=call.id)
            return

    if data.startswith("pg:"):
        parts = data.split(":")
        if len(parts) >= 3:
            entity_type = "offer" if parts[1] == "o" else "request"
            page = int(parts[2])
            try:
                bot.answer_callback_query(call.id)
            except Exception as e:
                logger.warning(f"answer_callback_query failed for {call.id}: {e}")
            render_my_items_screen(chat_id, tg_id, entity_type=entity_type, requested_page=page, message_id=message_id)
        return

    if data.startswith("ask_del:"):
        parts = data.split(":")
        if len(parts) >= 4:
            entity_type = "offer" if parts[1] == "o" else "request"
            item_id = int(parts[2])
            page = int(parts[3])
            try:
                bot.answer_callback_query(call.id)
            except Exception as e:
                logger.warning(f"answer_callback_query failed for {call.id}: {e}")
            render_delete_confirm_screen(chat_id, message_id, entity_type, item_id, page)
        return

    if data.startswith("cxl_del:"):
        parts = data.split(":")
        if len(parts) >= 4:
            entity_type = "offer" if parts[1] == "o" else "request"
            page = int(parts[3])
            try:
                bot.answer_callback_query(call.id)
            except Exception as e:
                logger.warning(f"answer_callback_query failed for {call.id}: {e}")
            render_my_items_screen(chat_id, tg_id, entity_type=entity_type, requested_page=page, message_id=message_id)
        return

    if data.startswith("cfm_del:"):
        parts = data.split(":")
        if len(parts) >= 4:
            entity_type = "offer" if parts[1] == "o" else "request"
            item_id = int(parts[2])
            page = int(parts[3])
            handle_confirm_delete(chat_id, message_id, tg_id, entity_type, item_id, page, call.id)
        return

    if data == "act:offer":
        set_session(tg_id, 'offer_category', {'language': 'ru'})
        try:
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.warning(f"answer_callback_query failed for {call.id}: {e}")
        bot.send_message(
            chat_id,
            "Select the category for your offer:\n\nChoose from the buttons below:",
            reply_markup=get_category_keyboard('ru')
        )
        return

    if data == "act:request":
        set_session(tg_id, 'request_category', {'language': 'ru'})
        try:
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.warning(f"answer_callback_query failed for {call.id}: {e}")
        bot.send_message(
            chat_id,
            "Select the category for your request:\n\nChoose from the buttons below:",
            reply_markup=get_category_keyboard('ru')
        )
        return

    # Fallback logging and silent answer for unhandled callback data
    logger.warning(f"Unhandled callback_data received: '{data}' from tg_id={tg_id}")
    try:
        bot.answer_callback_query(call.id)
    except Exception as e:
        logger.warning(f"answer_callback_query failed for {call.id}: {e}")



def cmd_my_offers(message: Message):
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    render_my_items_screen(message.chat.id, tg_id, entity_type="offer", requested_page=1, message_id=None)


def cmd_my_requests(message: Message):
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    render_my_items_screen(message.chat.id, tg_id, entity_type="request", requested_page=1, message_id=None)


def cmd_delete_offer(message: Message):
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /delete_offer <id>\n\nUse /my_offers to see your offers with IDs.")
        return
    
    try:
        offer_id = int(parts[1])
    except ValueError:
        bot.reply_to(message, "Invalid ID. Please provide a number.")
        return
    
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    if delete_offer(offer_id, tg_id):
        bot.reply_to(message, f"✅ Offer #{offer_id} deleted successfully.")
    else:
        bot.reply_to(message, f"❌ Offer #{offer_id} not found or you don't have permission to delete it.")

def cmd_delete_request(message: Message):
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /delete_request <id>\n\nUse /my_requests to see your requests with IDs.")
        return
    
    try:
        req_id = int(parts[1])
    except ValueError:
        bot.reply_to(message, "Invalid ID. Please provide a number.")
        return
    
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    if delete_request(req_id, tg_id):
        bot.reply_to(message, f"✅ Request #{req_id} deleted successfully.")
    else:
        bot.reply_to(message, f"❌ Request #{req_id} not found or you don't have permission to delete it.")

def cmd_marketplace(message: Message):
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    render_marketplace_catalog(chat_id=message.chat.id, tg_id=tg_id, cat="all", requested_page=1, message_id=None)


def cmd_offers(message: Message):
    log_message(message, "[CMD]")
    rows = get_all_offers()
    if not rows:
        bot.reply_to(message, "No offers yet. Use /offer to publish one!")
        return
    
    text = "📦 All Offers:\n\n"
    for row in rows:
        if len(row) >= 5:
            id, tg_id, category, offer_text, created_at = row[:5]
        else:
            tg_id, offer_text, created_at = row
            id = '?'
            category = 'general'
        user = get_user(tg_id)
        name = user.get('name', 'Unknown') if user else 'Unknown'
        text += f"ID {id} [{category}] - @{name}: {offer_text}\n\n"
    bot.reply_to(message, text)

def cmd_requests(message: Message):
    log_message(message, "[CMD]")
    rows = get_all_requests()
    if not rows:
        bot.reply_to(message, "No requests yet. Use /request to publish one!")
        return
    
    text = "📥 All Requests:\n\n"
    for row in rows:
        if len(row) >= 5:
            id, tg_id, category, req_text, created_at = row[:5]
        else:
            tg_id, req_text, created_at = row
            id = '?'
            category = 'general'
        user = get_user(tg_id)
        name = user.get('name', 'Unknown') if user else 'Unknown'
        text += f"ID {id} [{category}] - @{name}: {req_text}\n\n"
    bot.reply_to(message, text)
