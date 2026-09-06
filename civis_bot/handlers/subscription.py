#!/usr/bin/env python3
"""
Subscription and AI matching handlers.
Contains: subscribe, setkey, match
"""

import logging

from telebot.types import Message

from database import (
    get_user, get_session, set_session, clear_session,
    get_subscription, create_subscription,
    can_use_match, get_matches_remaining, increment_matches_used,
    get_openai_key, save_openai_key
)
from utils import get_text, find_matches, generate_match_explanation

from .helpers import log_message, bot

logger = logging.getLogger(__name__)

# --- SUBSCRIPTION ---

def cmd_subscribe(message: Message):
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    
    user = get_user(tg_id)
    if not user:
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    if user.get('status') != 'completed':
        bot.reply_to(message, "Your profile is not complete. Use /start to complete it!")
        return
    
    lang = user.get('language', 'en')
    sub = get_subscription(tg_id)
    if not sub:
        create_subscription(tg_id)
        sub = get_subscription(tg_id)
    
    remaining = get_matches_remaining(tg_id)
    remaining_text = str(remaining) if remaining != float('inf') else '∞'
    
    text = f"""{get_text(tg_id, 'subscribe_title')}

{get_text(tg_id, 'subscribe_current', plan=sub['plan'].upper())}
{get_text(tg_id, 'subscribe_remaining', remaining=remaining_text)}

{get_text(tg_id, 'subscribe_free')}

{get_text(tg_id, 'subscribe_premium')}

{get_text(tg_id, 'subscribe_lifetime')}

{get_text(tg_id, 'subscribe_upgrade')}"""
    bot.reply_to(message, text)

def cmd_setkey(message: Message):
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, get_text(tg_id, 'setkey_prompt'))
        return
    
    key = parts[1]
    if not key.startswith('sk-') or len(key) < 20:
        bot.reply_to(message, get_text(tg_id, 'setkey_invalid'))
        return
    
    save_openai_key(tg_id, key)
    bot.reply_to(message, get_text(tg_id, 'setkey_saved'))

def cmd_match(message: Message):
    """AI-powered matching with fallback to local model"""
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    openai_key = get_openai_key(tg_id)
    
    if openai_key and not can_use_match(tg_id):
        remaining = get_matches_remaining(tg_id)
        bot.reply_to(
            message,
            get_text(tg_id, 'match_limit_exceeded', remaining=remaining)
        )
        return
    
    if openai_key:
        increment_matches_used(tg_id)
    
    status_msg = bot.reply_to(message, "🔍 Finding matches... This may take a moment.")
    
    matches = find_matches(tg_id, openai_key, limit=5)
    
    if matches is None:
        bot.edit_message_text(
            "❌ Error generating your profile embedding. Please make sure you have a complete profile and try again.",
            chat_id=message.chat.id,
            message_id=status_msg.message_id
        )
        return
    
    if not matches:
        bot.edit_message_text(
            "No matches found yet. Try updating your profile with more details, or come back later when more people join!",
            chat_id=message.chat.id,
            message_id=status_msg.message_id
        )
        return
    
    lang = user.get('language', 'en')
    text = f"🤝 **Your Top Matches**\n\n"
    
    for i, match in enumerate(matches, 1):
        explanation = generate_match_explanation(user, match)
        text += f"{i}. **@{match['username']}** - {match['name']}\n"
        text += f"   Role: {match['role']}\n"
        text += f"   Values: {match['values']}\n"
        text += f"   Match score: {match['score']}%\n"
        text += f"   Why: {explanation}\n\n"
    
    if openai_key:
        remaining = get_matches_remaining(tg_id)
        text += f"\n---\nMatches remaining: {remaining if remaining != float('inf') else 'unlimited'}"
    else:
        text += "\n---\nUsing local embedding model (no API key needed).\nSet /setkey for better quality matches."
    
    bot.edit_message_text(
        text,
        chat_id=message.chat.id,
        message_id=status_msg.message_id,
        parse_mode='Markdown'
    )
