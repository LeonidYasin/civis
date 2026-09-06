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

logger = logging.getLogger(__name__)

# Global bot reference (set from commands)
bot = None

def set_bot(bot_instance):
    global bot
    bot = bot_instance

# --- LANGUAGE SELECTION ---

def handle_language_selection(message: Message):
    """Handle language selection"""
    if bot is None:
        logger.error("Bot not set in language.py!")
        return
    
    tg_id = message.from_user.id
    text = message.text
    
    lang = 'en' if text == "English" else 'ru'
    
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
