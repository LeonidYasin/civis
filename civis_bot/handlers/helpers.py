#!/usr/bin/env python3
"""
Helper functions for handlers.
"""

import logging

from telebot.types import Message

logger = logging.getLogger(__name__)

# Global bot reference (set in bot.py)
bot = None

def set_bot(bot_instance):
    global bot
    bot = bot_instance

def log_message(message: Message, prefix=""):
    """Helper to log message details"""
    if not message or not message.from_user:
        return
    tg_id = message.from_user.id
    username = message.from_user.username or "unknown"
    chat_type = message.chat.type if message.chat else "unknown"
    chat_id = message.chat.id if message.chat else 0
    text = message.text or ""
    logger.info(f"{prefix} msg from {tg_id} (@{username}) in {chat_type} (chat_id={chat_id}): {text[:50]}")
    if chat_type in ['group', 'supergroup']:
        logger.info(f"[GROUP] chat_id={chat_id}, title={message.chat.title or 'N/A'}")
