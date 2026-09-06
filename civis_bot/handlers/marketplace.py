#!/usr/bin/env python3
"""
Marketplace command handlers for Civis bot.
Contains: offer, request, my_offers, my_requests, delete_offer, delete_request, marketplace, offers, requests
"""

import logging
import sqlite3

from telebot.types import Message, ReplyKeyboardRemove

from database import (
    get_user, get_session, set_session, clear_session,
    get_all_offers, get_all_requests,
    get_my_offers, get_my_requests,
    save_offer, save_request, delete_offer, delete_request,
    DB_PATH
)
from locales import TEXTS
from keyboards import (
    get_main_keyboard, get_category_keyboard
)
from utils import get_text

from .helpers import log_message, bot

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

def cmd_my_offers(message: Message):
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    rows = get_my_offers(tg_id)
    if not rows:
        bot.reply_to(message, "You have no offers yet.")
        return
    
    text = "📦 Your Offers:\n\n"
    for row in rows:
        if len(row) >= 4:
            id, category, offer_text, created_at = row[:4]
        else:
            id, offer_text, created_at = row
            category = 'general'
        text += f"ID {id} [{category}]: {offer_text}\n"
        text += f"To delete: /delete_offer {id}\n\n"
    bot.reply_to(message, text)

def cmd_my_requests(message: Message):
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    rows = get_my_requests(tg_id)
    if not rows:
        bot.reply_to(message, "You have no requests yet.")
        return
    
    text = "📥 Your Requests:\n\n"
    for row in rows:
        if len(row) >= 4:
            id, category, req_text, created_at = row[:4]
        else:
            id, req_text, created_at = row
            category = 'general'
        text += f"ID {id} [{category}]: {req_text}\n"
        text += f"To delete: /delete_request {id}\n\n"
    bot.reply_to(message, text)

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
