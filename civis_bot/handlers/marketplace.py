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
    DB_PATH
)
from locales import TEXTS
from keyboards import (
    get_main_keyboard, get_category_keyboard,
    CLICK_TRACKER, get_empty_items_keyboard, get_item_card_keyboard, get_delete_confirm_keyboard
)
from utils import get_text
import mcp_client

from .helpers import log_message, bot, safe_edit_message

logger = logging.getLogger(__name__)

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


def handle_marketplace_callbacks(call: CallbackQuery):
    """Unified callback query handler for marketplace pagination, deletion and navigation."""
    tg_id = call.from_user.id
    data = call.data or ""
    chat_id = call.message.chat.id if call.message and call.message.chat else tg_id
    message_id = call.message.message_id if call.message else None

    # 1. Anti-flood click throttle check
    action_key = data.split(":")[0] if ":" in data else data
    if CLICK_TRACKER.is_throttled(tg_id, action_key):
        try:
            bot.answer_callback_query(call.id, text="Слишком частые клики, подождите...")
        except Exception:
            pass
        return

    # 2. FSM Policy check
    state, session_data = get_session(tg_id)
    is_fsm_active = (state is not None and state != "IDLE")

    if is_fsm_active:
        if data == "noop":
            try:
                bot.answer_callback_query(call.id)
            except Exception:
                pass
            return
        elif data.startswith("cxl_del:"):
            pass  # Allowed without clearing session
        elif data == "hub:mkt" or data.startswith("hub:"):
            # Escape hatch: clear session to IDLE and proceed
            clear_session(tg_id)
        elif data in ["act:offer", "act:request"] and state in ["offer_category", "request_category"]:
            # Allowed to switch category selection
            pass
        else:
            try:
                bot.answer_callback_query(call.id, text="Пожалуйста, сначала завершите текущее действие.", show_alert=True)
            except Exception:
                pass
            return

    # 3. Handle data
    if data == "noop":
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        return

    if data.startswith("pg:"):
        parts = data.split(":")
        if len(parts) >= 3:
            entity_type = "offer" if parts[1] == "o" else "request"
            page = int(parts[2])
            try:
                bot.answer_callback_query(call.id)
            except Exception:
                pass
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
            except Exception:
                pass
            render_delete_confirm_screen(chat_id, message_id, entity_type, item_id, page)
        return

    if data.startswith("cxl_del:"):
        parts = data.split(":")
        if len(parts) >= 4:
            entity_type = "offer" if parts[1] == "o" else "request"
            page = int(parts[3])
            try:
                bot.answer_callback_query(call.id)
            except Exception:
                pass
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
        except Exception:
            pass
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
        except Exception:
            pass
        bot.send_message(
            chat_id,
            "Select the category for your request:\n\nChoose from the buttons below:",
            reply_markup=get_category_keyboard('ru')
        )
        return

    if data == "hub:mkt":
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        render_marketplace_hub(chat_id, message_id)
        return


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
    offers = get_all_offers()
    requests = get_all_requests()
    
    text = "🛒 Marketplace:\n\n"
    text += "📦 Offers:\n"
    if offers:
        for row in offers[:5]:
            if len(row) >= 5:
                id, tg_id, category, offer_text, _ = row[:5]
            else:
                tg_id, offer_text, _ = row
                id = '?'
                category = 'general'
            user = get_user(tg_id)
            name = user.get('name', 'Unknown') if user else 'Unknown'
            text += f"  - #{id} [{category}] {name}: {offer_text}\n"
    else:
        text += "  (none)\n"
    
    text += "\n📥 Requests:\n"
    if requests:
        for row in requests[:5]:
            if len(row) >= 5:
                id, tg_id, category, req_text, _ = row[:5]
            else:
                tg_id, req_text, _ = row
                id = '?'
                category = 'general'
            user = get_user(tg_id)
            name = user.get('name', 'Unknown') if user else 'Unknown'
            text += f"  - #{id} [{category}] {name}: {req_text}\n"
    else:
        text += "  (none)\n"
    
    bot.reply_to(message, text)

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
