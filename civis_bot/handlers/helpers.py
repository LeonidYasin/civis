#!/usr/bin/env python3
"""
Helper functions for handlers.
"""

import logging
from telebot.types import Message

logger = logging.getLogger(__name__)

# Global bot instance
_bot = None

def set_bot(bot_instance):
    """Set the global bot instance"""
    global _bot
    _bot = bot_instance
    logger.info("Bot instance set in helpers")

def get_bot():
    """Get the global bot instance"""
    return _bot

# For backward compatibility - use as a property
class BotProxy:
    """Proxy for bot instance that can be used as a module-level variable"""
    def __getattr__(self, name):
        if _bot is None:
            raise RuntimeError("Bot not set. Call set_bot() first.")
        return getattr(_bot, name)

# This is the actual bot object that will be used
# It proxies all calls to the real bot instance
bot = BotProxy()

def log_message(message: Message, prefix=""):
    """Helper to log message details"""
    tg_id = message.from_user.id
    username = message.from_user.username or "unknown"
    chat_type = message.chat.type
    chat_id = message.chat.id
    text = message.text or ""
    logger.info(f"{prefix} msg from {tg_id} (@{username}) in {chat_type} (chat_id={chat_id}): {text[:50]}")
    if chat_type in ['group', 'supergroup']:
        logger.info(f"[GROUP] chat_id={chat_id}, title={message.chat.title or 'N/A'}")
