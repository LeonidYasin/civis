#!/usr/bin/env python3
"""
Handlers module for Civis bot.
Exports all command handlers and helper functions.
"""

from .helpers import set_bot, log_message, bot
from .core import (
    cmd_start, cmd_profile, cmd_embedding, cmd_citizens,
    cmd_help, cmd_survey, cmd_status, cmd_cancel, cmd_done
)
from .marketplace import (
    cmd_offer, cmd_request, cmd_offers, cmd_requests,
    cmd_my_offers, cmd_my_requests,
    cmd_delete_offer, cmd_delete_request,
    cmd_marketplace
)
from .subscription import cmd_subscribe, cmd_setkey, cmd_match
from .dialogs import (
    cmd_upload_dialog, cmd_my_dialogs, cmd_delete_dialog, cmd_process_dialogs,
    handle_document
)
from .support import cmd_support, cmd_search
from .language import handle_language_selection
from .survey import handle_survey

# Register all handlers into a list for easy import
def register_handlers():
    """Register all command handlers with the bot"""
    if not bot:
        raise RuntimeError("Bot not set. Call set_bot() first.")
    
    # Core commands
    bot.message_handler(commands=['start'])(cmd_start)
    bot.message_handler(commands=['profile'])(cmd_profile)
    bot.message_handler(commands=['embedding'])(cmd_embedding)
    bot.message_handler(commands=['citizens'])(cmd_citizens)
    bot.message_handler(commands=['help'])(cmd_help)
    bot.message_handler(commands=['survey'])(cmd_survey)
    bot.message_handler(commands=['status'])(cmd_status)
    bot.message_handler(commands=['cancel'])(cmd_cancel)
    bot.message_handler(commands=['done'])(cmd_done)
    
    # Marketplace commands
    bot.message_handler(commands=['offer'])(cmd_offer)
    bot.message_handler(commands=['request'])(cmd_request)
    bot.message_handler(commands=['offers'])(cmd_offers)
    bot.message_handler(commands=['requests'])(cmd_requests)
    bot.message_handler(commands=['my_offers'])(cmd_my_offers)
    bot.message_handler(commands=['my_requests'])(cmd_my_requests)
    bot.message_handler(commands=['delete_offer'])(cmd_delete_offer)
    bot.message_handler(commands=['delete_request'])(cmd_delete_request)
    bot.message_handler(commands=['marketplace'])(cmd_marketplace)
    
    # Subscription commands
    bot.message_handler(commands=['subscribe'])(cmd_subscribe)
    bot.message_handler(commands=['setkey'])(cmd_setkey)
    bot.message_handler(commands=['match'])(cmd_match)
    
    # Dialog commands
    bot.message_handler(commands=['upload_dialog'])(cmd_upload_dialog)
    bot.message_handler(commands=['my_dialogs'])(cmd_my_dialogs)
    bot.message_handler(commands=['delete_dialog'])(cmd_delete_dialog)
    bot.message_handler(commands=['process_dialogs'])(cmd_process_dialogs)
    
    # Support and search
    bot.message_handler(commands=['support'])(cmd_support)
    bot.message_handler(commands=['search'])(cmd_search)
    
    # Language selection
    bot.message_handler(func=lambda m: m.text in ["English", "Русский"])(handle_language_selection)
    
    # Document handler
    bot.message_handler(content_types=['document'])(handle_document)
    
    # Survey state handler (catch-all for text messages)
    bot.message_handler(func=lambda m: True, content_types=['text'])(handle_survey)
    
    logger.info("All handlers registered")

# Import logger for register_handlers
import logging
logger = logging.getLogger(__name__)

__all__ = [
    'set_bot', 'register_handlers',
    'cmd_start', 'cmd_profile', 'cmd_embedding', 'cmd_citizens',
    'cmd_help', 'cmd_survey', 'cmd_status', 'cmd_cancel', 'cmd_done',
    'cmd_offer', 'cmd_request', 'cmd_offers', 'cmd_requests',
    'cmd_my_offers', 'cmd_my_requests',
    'cmd_delete_offer', 'cmd_delete_request',
    'cmd_marketplace',
    'cmd_subscribe', 'cmd_setkey', 'cmd_match',
    'cmd_upload_dialog', 'cmd_my_dialogs', 'cmd_delete_dialog', 'cmd_process_dialogs',
    'cmd_support', 'cmd_search',
    'handle_document', 'handle_language_selection', 'handle_survey'
]
