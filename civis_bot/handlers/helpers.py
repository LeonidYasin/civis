#!/usr/bin/env python3
"""
Helper functions for handlers.
"""

import time
import re
import logging
from typing import Optional
from telebot.types import Message
from telebot.apihelper import ApiTelegramException

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


def safe_edit_message(bot_inst, chat_id, message_id, text, reply_markup=None, parse_mode='HTML') -> bool:
    """
    Safely edits an existing message with:
    1. 'message is not modified' suppression -> returns True.
    2. 429 rate limit retry with sleep(min(retry_after, 2)).
    3. Fallback to send_message if message was deleted/not found.
    """
    attempts = 0
    while attempts < 2:
        attempts += 1
        try:
            bot_inst.edit_message_text(
                text=text,
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
            return True
        except ApiTelegramException as e:
            desc = (e.description or "").lower()
            if "message is not modified" in desc:
                return True
            if e.error_code == 429:
                retry_after = 1
                if hasattr(e, "result_json") and isinstance(e.result_json, dict):
                    retry_after = e.result_json.get("parameters", {}).get("retry_after", 1)
                time.sleep(min(float(retry_after), 2.0))
                continue
            if "message to edit not found" in desc or "message can't be edited" in desc or "message not found" in desc:
                try:
                    bot_inst.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
                    return True
                except Exception as send_err:
                    logger.warning(f"Fallback send_message failed: {send_err}")
                    return False
            logger.warning(f"safe_edit_message error: {e}")
            return False
        except Exception as e:
            logger.warning(f"Unexpected error in safe_edit_message: {e}")
            return False
    return False


# --- USERNAME AND TITLE UTILITIES ---

_TG_USERNAME_RE = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]{4,31}$')


def normalize_username(raw: Optional[str]) -> Optional[str]:
    """
    Validates and normalizes Telegram username:
    - Strips leading '@' and whitespace.
    - Strict regex: 5..32 chars, starts with latin letter, latin+digits+underscore.
    - Returns cleaned string or None.
    """
    if not raw or not isinstance(raw, str):
        return None
    cleaned = raw.strip().lstrip('@')
    if _TG_USERNAME_RE.match(cleaned):
        return cleaned
    return None


def extract_title(text: Optional[str]) -> str:
    """
    Extracts first non-empty line as raw title, truncated to max 50 chars (47 + '...').
    Does NOT HTML-escape; presentation layer escapes at render time.
    Fallback: 'Объявление Civis' if empty or None.
    """
    if not text or not isinstance(text, str) or not text.strip():
        return "Объявление Civis"
    first_line = text.strip().split("\n")[0].strip()
    if not first_line:
        return "Объявление Civis"
    if len(first_line) > 50:
        return first_line[:47] + "..."
    return first_line


