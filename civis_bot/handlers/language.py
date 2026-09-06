#!/usr/bin/env python3
"""
Language selection handlers for Civis bot.
"""

import logging

from telebot.types import Message, ReplyKeyboardRemove

from database import get_user, save_user, get_session, set_session, clear_session
from locales import TEXTS
from keyboards import get_main_keyboard, get_language_keyboard
from utils import get_text

from .helpers import get_bot

logger = logging.getLogger(__name__)

def get_bot_safe():
    """Get bot instance safely"""
    bot = get_bot()
    if bot is None:
        logger.error("Bot not set in language.py!")
        raise RuntimeError("Bot not set")
    return bot

# --- LANGUAGE SELECTION ---

def handle_language_selection(message: Message):
    """Handle language selection"""
    try:
        bot = get_bot_safe()
    except RuntimeError:
        return
    
    tg_id = message.from_user.id
    text = message.text.strip()
    
    # Check if text is exactly "English" or "Русский" (case-insensitive, trimmed)
    if text.lower() == "english":
        lang = 'en'
    elif text.lower() == "русский" or text == "Русский":
        lang = 'ru'
    else:
        # Not a language selection message
        return
    
    logger.info(f"Language selected: {lang} for user {tg_id}")
    
    user = get_user(tg_id)
    if user:
        save_user(tg_id, user.get('username', 'unknown'), language=lang)
    else:
        save_user(tg_id, message.from_user.username or "unknown", language=lang)
    
    state, _ = get_session(tg_id)
    if state == 'language_select':
        clear_session(tg_id)
    
    user = get_user(tg_id)
    if user and user.get('status') == 'completed':
        bot.reply_to(
            message,
            TEXTS[lang]['language_changed'] + "\n\n" + TEXTS[lang]['welcome_citizen'].format(name=user.get('name', '')),
            reply_markup=get_main_keyboard(lang)
        )
    else:
        bot.reply_to(
            message,
            TEXTS[lang]['language_set'] + "\n\n" + TEXTS[lang]['welcome'],
            reply_markup=ReplyKeyboardRemove()
        )
        
        set_session(tg_id, 'survey_name', {'language': lang})
        bot.send_message(tg_id, TEXTS[lang]['name_ask'])
