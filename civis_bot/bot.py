#!/usr/bin/env python3
"""
Civis MVP Bot - Entry point.
Reorganized into modules for better maintainability.
"""

import logging
import sys
import signal

import requests
from telebot import TeleBot

from config import TOKEN, get_proxy_url
from database import init_db
from handlers import register_handlers

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# --- SIGNAL HANDLER ---
def signal_handler(sig, frame):
    logger.info("Stopping bot...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# --- CREATE BOT ---
def create_bot():
    """Create bot instance with proxy support"""
    proxy_url = get_proxy_url()
    if proxy_url:
        session = requests.Session()
        session.proxies = {'http': proxy_url, 'https': proxy_url}
        bot = TeleBot(token=TOKEN, threaded=False)
        bot.session = session
        logger.info(f"Bot created with proxy: {proxy_url}")
    else:
        bot = TeleBot(token=TOKEN, threaded=False)
        logger.info("Bot created without proxy")
    return bot

# --- MAIN ---
def main():
    """Main function"""
    try:
        # Initialize database
        init_db()
        
        # Create bot
        bot = create_bot()
        
        # Register all handlers
        register_handlers(bot)
        
        # Test connection
        logger.info("Checking connection to Telegram API...")
        me = bot.get_me()
        logger.info(f"Connected: @{me.username} ({me.full_name})")
        
        # Start polling
        logger.info("Starting polling... (Press Ctrl+C to stop)")
        bot.infinity_polling()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"Critical error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
