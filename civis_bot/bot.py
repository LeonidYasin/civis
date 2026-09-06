#!/usr/bin/env python3
"""
Civis Bot - Entry point
"""

import logging
import sys
import signal

import requests
from telebot import TeleBot
from telebot.types import BotCommand

from config import TOKEN, get_proxy_url
from database import init_db
from handlers import register_handlers, set_bot

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

# --- SET BOT FOR HANDLERS ---
set_bot(bot)

# --- SET COMMANDS MENU (left sidebar) ---
def set_commands_menu():
    """Set the bot commands menu (visible when typing /)"""
    commands = [
        BotCommand("start", "Create or view your profile"),
        BotCommand("menu", "Show main menu"),
        BotCommand("profile", "View your profile"),
        BotCommand("embedding", "View your AI embedding profile"),
        BotCommand("citizens", "List all citizens"),
        BotCommand("search", "Search citizens"),
        BotCommand("offer", "Publish an offer"),
        BotCommand("request", "Publish a request"),
        BotCommand("my_offers", "View your offers"),
        BotCommand("my_requests", "View your requests"),
        BotCommand("delete_offer", "Delete your offer by ID"),
        BotCommand("delete_request", "Delete your request by ID"),
        BotCommand("marketplace", "View marketplace"),
        BotCommand("subscribe", "View subscription plans"),
        BotCommand("match", "AI-powered matching"),
        BotCommand("setkey", "Set OpenAI API key"),
        BotCommand("language", "Change language"),
        BotCommand("support", "Contact developer support"),
        BotCommand("upload_dialog", "Upload dialog history file"),
        BotCommand("my_dialogs", "List uploaded dialog files"),
        BotCommand("process_dialogs", "Process uploaded dialogs"),
        BotCommand("status", "Bot status"),
        BotCommand("help", "Help"),
        BotCommand("cancel", "Cancel current operation"),
        BotCommand("done", "Finish value selection"),
    ]
    bot.set_my_commands(commands)
    logger.info("Commands menu set")

# --- REGISTER HANDLERS ---
register_handlers()

# --- MAIN ---
if __name__ == "__main__":
    try:
        init_db()
        set_commands_menu()
        
        logger.info("Checking connection to Telegram API...")
        me = bot.get_me()
        logger.info(f"Connected: @{me.username} ({me.full_name})")
        
        logger.info("Starting polling... (Press Ctrl+C to stop)")
        bot.infinity_polling()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"Critical error: {e}")
        sys.exit(1)
