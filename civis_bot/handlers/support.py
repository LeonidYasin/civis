#!/usr/bin/env python3
"""
Support and search handlers for Civis bot.
Contains: support, search
"""

import logging

from telebot.types import Message

from database import get_user, set_session, search_citizens
from utils import get_text
from .helpers import log_message, bot

logger = logging.getLogger(__name__)

# --- SUPPORT ---

def cmd_support(message: Message):
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    set_session(tg_id, 'support', {'language': user.get('language', 'en')})
    bot.reply_to(message, get_text(tg_id, 'support_prompt'))

# --- SEARCH ---

def cmd_search(message: Message):
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /search <text>\n\nSearch for citizens by name, role, or values.")
        return
    
    query = ' '.join(parts[1:])
    results = search_citizens(query)
    
    if not results:
        bot.reply_to(message, f"No citizens found matching '{query}'.")
        return
    
    text = f"Search results for '{query}':\n\n"
    for username, name, role, values, about in results[:20]:
        text += f"@{username or 'unknown'} - {name}\n"
        text += f"Role: {role}\nValues: {values}\n"
        if about:
            text += f"About: {about[:100]}...\n"
        text += "\n"
    
    if len(results) > 20:
        text += f"... and {len(results) - 20} more results."
    
    bot.reply_to(message, text)
