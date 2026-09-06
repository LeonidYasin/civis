#!/usr/bin/env python3
"""
Category-specific handlers for offers and requests.
"""

import logging

from telebot.types import Message, ReplyKeyboardRemove

from database import (
    get_user, get_session, set_session, clear_session,
    get_all_offers, get_all_requests,
    save_offer, save_request,
)
from utils import get_text
from keyboards import get_main_keyboard, get_category_keyboard

logger = logging.getLogger(__name__)

# Global bot reference (set from commands)
bot = None

def set_bot(bot_instance):
    global bot
    bot = bot_instance

# --- COMMAND HANDLERS ---

def cmd_taxi_offer(message: Message):
    """Publish a taxi offer"""
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    lang = user.get('language', 'en')
    set_session(tg_id, 'offer_taxi', {'language': lang})
    bot.reply_to(
        message,
        "🚕 Describe your taxi offer:\n"
        "Where can you take people? (e.g., 'Airport → City center, $20')",
        reply_markup=ReplyKeyboardRemove()
    )

def cmd_taxi_request(message: Message):
    """Publish a taxi request"""
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    lang = user.get('language', 'en')
    set_session(tg_id, 'request_taxi', {'language': lang})
    bot.reply_to(
        message,
        "🚕 Describe what taxi ride you need:\n"
        "Where and when? (e.g., 'Airport → City center, tomorrow 10am')",
        reply_markup=ReplyKeyboardRemove()
    )

def cmd_delivery_offer(message: Message):
    """Publish a delivery offer"""
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    lang = user.get('language', 'en')
    set_session(tg_id, 'offer_delivery', {'language': lang})
    bot.reply_to(
        message,
        "📦 Describe your delivery offer:\n"
        "What can you deliver and where? (e.g., 'Food delivery in downtown, 30min')",
        reply_markup=ReplyKeyboardRemove()
    )

def cmd_delivery_request(message: Message):
    """Publish a delivery request"""
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    lang = user.get('language', 'en')
    set_session(tg_id, 'request_delivery', {'language': lang})
    bot.reply_to(
        message,
        "📦 Describe what delivery you need:\n"
        "What, where, and when? (e.g., 'Package from A to B, today 5pm')",
        reply_markup=ReplyKeyboardRemove()
    )

def cmd_taxi(message: Message):
    """View all taxi offers and requests"""
    tg_id = message.from_user.id
    offers = get_all_offers('taxi')
    requests = get_all_requests('taxi')
    
    text = "🚕 **Taxi Marketplace**\n\n"
    
    text += "🚗 **Offers:**\n"
    if offers:
        for row in offers[:5]:
            if len(row) == 5:
                id, tg_id, category, offer_text, created_at = row
            else:
                tg_id, offer_text, created_at = row
                id = '?'
            user = get_user(tg_id)
            name = user.get('name', 'Unknown') if user else 'Unknown'
            text += f"  #{id} {name}: {offer_text}\n"
    else:
        text += "  (none)\n"
    
    text += "\n📥 **Requests:**\n"
    if requests:
        for row in requests[:5]:
            if len(row) == 5:
                id, tg_id, category, req_text, created_at = row
            else:
                tg_id, req_text, created_at = row
                id = '?'
            user = get_user(tg_id)
            name = user.get('name', 'Unknown') if user else 'Unknown'
            text += f"  #{id} {name}: {req_text}\n"
    else:
        text += "  (none)\n"
    
    text += "\nTo publish:\n"
    text += "  /taxi_offer - Offer a ride\n"
    text += "  /taxi_request - Request a ride"
    
    bot.reply_to(message, text, parse_mode='Markdown')

def cmd_delivery(message: Message):
    """View all delivery offers and requests"""
    tg_id = message.from_user.id
    offers = get_all_offers('delivery')
    requests = get_all_requests('delivery')
    
    text = "📦 **Delivery Marketplace**\n\n"
    
    text += "📦 **Offers:**\n"
    if offers:
        for row in offers[:5]:
            if len(row) == 5:
                id, tg_id, category, offer_text, created_at = row
            else:
                tg_id, offer_text, created_at = row
                id = '?'
            user = get_user(tg_id)
            name = user.get('name', 'Unknown') if user else 'Unknown'
            text += f"  #{id} {name}: {offer_text}\n"
    else:
        text += "  (none)\n"
    
    text += "\n📥 **Requests:**\n"
    if requests:
        for row in requests[:5]:
            if len(row) == 5:
                id, tg_id, category, req_text, created_at = row
            else:
                tg_id, req_text, created_at = row
                id = '?'
            user = get_user(tg_id)
            name = user.get('name', 'Unknown') if user else 'Unknown'
            text += f"  #{id} {name}: {req_text}\n"
    else:
        text += "  (none)\n"
    
    text += "\nTo publish:\n"
    text += "  /delivery_offer - Offer delivery\n"
    text += "  /delivery_request - Request delivery"
    
    bot.reply_to(message, text, parse_mode='Markdown')
