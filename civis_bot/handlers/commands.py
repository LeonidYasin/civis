#!/usr/bin/env python3
"""
Command handlers for Civis bot.
"""

import logging
import sqlite3

from telebot.types import Message, ReplyKeyboardRemove

from database import (
    get_user, save_user, get_session, set_session, clear_session,
    get_all_citizens, get_my_offers, get_my_requests,
    get_all_offers, get_all_requests,
    save_offer, save_request, delete_offer, delete_request,
    get_subscription, create_subscription,
    can_use_match, get_matches_remaining, increment_matches_used,
    get_openai_key, save_openai_key, search_citizens, DB_PATH
)
from locales import TEXTS
from keyboards import (
    get_main_keyboard, get_language_keyboard,
    get_values_keyboard, get_roles_keyboard, get_formats_keyboard
)
from utils import get_text, get_embedding_profile
from config import get_proxy_url, ADMIN_CHAT_ID

from .survey import handle_survey, set_bot as set_survey_bot
from .language import handle_language_selection, set_bot as set_language_bot

logger = logging.getLogger(__name__)

# Global bot reference (set in bot.py)
bot = None

def set_bot(bot_instance):
    global bot
    bot = bot_instance
    set_survey_bot(bot_instance)
    set_language_bot(bot_instance)

# --- REGISTRATION ---

def register_handlers():
    """Register all command handlers with the bot"""
    if not bot:
        raise RuntimeError("Bot not set. Call set_bot() first.")
    
    # Log all messages (for debugging groups)
    @bot.message_handler(func=lambda m: True)
    def log_all_messages(message: Message):
        tg_id = message.from_user.id
        username = message.from_user.username or "unknown"
        chat_type = message.chat.type
        chat_id = message.chat.id
        text = message.text or ""
        
        logger.info(f"[ALL] msg from {tg_id} (@{username}) in {chat_type} (chat_id={chat_id}): {text[:50]}")
        
        # If this is a group and we have ADMIN_CHAT_ID, log group ID
        if chat_type in ['group', 'supergroup'] and ADMIN_CHAT_ID:
            logger.info(f"[GROUP] chat_id={chat_id}, chat_title={message.chat.title or 'N/A'}")
    
    # Command handlers
    bot.message_handler(commands=['start'])(cmd_start)
    bot.message_handler(commands=['profile'])(cmd_profile)
    bot.message_handler(commands=['embedding'])(cmd_embedding)
    bot.message_handler(commands=['citizens'])(cmd_citizens)
    bot.message_handler(commands=['offers'])(cmd_offers)
    bot.message_handler(commands=['requests'])(cmd_requests)
    bot.message_handler(commands=['my_offers'])(cmd_my_offers)
    bot.message_handler(commands=['my_requests'])(cmd_my_requests)
    bot.message_handler(commands=['marketplace'])(cmd_marketplace)
    bot.message_handler(commands=['help'])(cmd_help)
    bot.message_handler(commands=['survey'])(cmd_survey)
    bot.message_handler(commands=['status'])(cmd_status)
    bot.message_handler(commands=['cancel'])(cmd_cancel)
    bot.message_handler(commands=['done'])(cmd_done)
    bot.message_handler(commands=['offer'])(cmd_offer)
    bot.message_handler(commands=['request'])(cmd_request)
    bot.message_handler(commands=['language'])(cmd_language)
    bot.message_handler(commands=['subscribe'])(cmd_subscribe)
    bot.message_handler(commands=['setkey'])(cmd_setkey)
    bot.message_handler(commands=['match'])(cmd_match)
    bot.message_handler(commands=['search'])(cmd_search)
    bot.message_handler(commands=['delete_offer'])(cmd_delete_offer)
    bot.message_handler(commands=['delete_request'])(cmd_delete_request)
    bot.message_handler(commands=['support'])(cmd_support)
    
    # Language selection handler
    bot.message_handler(func=lambda m: m.text in ["English", "Русский"])(handle_language_selection)
    
    # Survey state handler
    bot.message_handler(func=lambda m: True, content_types=['text'])(handle_survey)
    
    logger.info("All handlers registered")

# --- COMMAND HANDLERS ---

def cmd_start(message: Message):
    tg_id = message.from_user.id
    username = message.from_user.username or "unknown"
    logger.info(f"Received /start from {tg_id} (chat: {message.chat.id})")
    
    user = get_user(tg_id)
    if user and user.get('status') == 'completed':
        lang = user.get('language', 'en')
        bot.reply_to(
            message,
            get_text(tg_id, 'welcome_citizen', name=user.get('name', 'friend')),
            reply_markup=get_main_keyboard(lang)
        )
        return
    
    set_session(tg_id, 'language_select', {})
    bot.reply_to(
        message,
        "Choose your language:\n\nEnglish / Русский",
        reply_markup=get_language_keyboard()
    )

# ... (остальные команды без изменений) ...

def cmd_support(message: Message):
    """Support command - forward message to admin"""
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    set_session(tg_id, 'support', {'language': user.get('language', 'en')})
    bot.reply_to(message, get_text(tg_id, 'support_prompt'))

# ... (остальные команды без изменений) ...
