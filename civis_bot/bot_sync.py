#!/usr/bin/env python3
"""
Synchronous Telegram bot with HTTP proxy support.
Uses telebot (pyTelegramBotAPI) with requests session.
"""

import logging
import os
import sys
from datetime import datetime

import requests
from dotenv import load_dotenv
from telebot import TeleBot
from telebot.types import Message

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# --- LOAD ENV ---
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    logger.error("ERROR: BOT_TOKEN not found in .env file!")
    sys.exit(1)
logger.info("Token loaded")

# --- PROXY SETUP ---
def get_proxy_url():
    """Get HTTP proxy URL from .env or environment"""
    # First check .env
    proxy_url = os.getenv("PROXY_URL")
    if proxy_url:
        # Convert socks5 to http if needed
        if proxy_url.startswith("socks5://"):
            # Happ uses HTTP proxy on same port
            port = proxy_url.split(":")[-1]
            http_proxy = f"http://127.0.0.1:{port}"
            logger.info(f"Converted SOCKS5 to HTTP proxy: {http_proxy}")
            return http_proxy
        logger.info(f"Using proxy: {proxy_url}")
        return proxy_url
    
    # Check system env
    http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
    https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
    
    if https_proxy:
        logger.info(f"Using proxy: {https_proxy}")
        return https_proxy
    elif http_proxy:
        logger.info(f"Using proxy: {http_proxy}")
        return http_proxy
    
    logger.info("No proxy configured, using direct connection")
    return None

# --- CREATE BOT ---
proxy_url = get_proxy_url()

if proxy_url:
    # For HTTP proxy with requests
    proxies = {
        'http': proxy_url,
        'https': proxy_url,
    }
    
    # Create session with proxy
    session = requests.Session()
    session.proxies = proxies
    
    # Test proxy connection
    try:
        test_response = session.get("https://api.telegram.org", timeout=10)
        logger.info(f"Proxy test: {test_response.status_code}")
    except Exception as e:
        logger.warning(f"Proxy test failed: {e}")
    
    # Create bot with custom session
    bot = TeleBot(token=TOKEN, threaded=False)
    bot.session = session
    logger.info(f"Bot created with HTTP proxy: {proxy_url}")
else:
    bot = TeleBot(token=TOKEN, threaded=False)
    logger.info("Bot created without proxy")

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def cmd_start(message: Message):
    """Handler for /start command"""
    logger.info(f"Received /start from {message.from_user.id}")
    bot.reply_to(
        message,
        "Hello! I am a sync test bot for Civis.\n"
        "If you see this - connection to Telegram API works!\n\n"
        "Available commands:\n"
        "/ping - check connection\n"
        "/info - bot information"
    )

@bot.message_handler(commands=['ping'])
def cmd_ping(message: Message):
    """Check connection"""
    logger.info(f"Received /ping from {message.from_user.id}")
    start_time = datetime.now()
    bot.reply_to(message, "Pong!")
    end_time = datetime.now()
    latency = (end_time - start_time).total_seconds() * 1000
    bot.send_message(message.chat.id, f"Latency: {latency:.0f} ms")

@bot.message_handler(commands=['info'])
def cmd_info(message: Message):
    """Bot information"""
    logger.info(f"Received /info from {message.from_user.id}")
    try:
        me = bot.get_me()
        bot.reply_to(
            message,
            f"Bot info:\n"
            f"Name: {me.full_name}\n"
            f"Username: @{me.username}\n"
            f"ID: {me.id}\n"
            f"Token: {TOKEN[:10]}...{TOKEN[-5:]}\n"
            f"Proxy: {proxy_url or 'None'}"
        )
    except Exception as e:
        logger.error(f"Error getting bot info: {e}")
        bot.reply_to(message, f"Error: {e}")

@bot.message_handler(func=lambda message: True)
def handle_unknown(message: Message):
    """Unknown message handler"""
    logger.info(f"Unknown message from {message.from_user.id}: {message.text}")
    bot.reply_to(
        message,
        "Unknown command. Use /start for command list."
    )

# --- MAIN ---
if __name__ == "__main__":
    try:
        logger.info("Starting sync bot...")
        
        # Test connection
        logger.info("Checking connection to Telegram API...")
        me = bot.get_me()
        logger.info(f"Connected: @{me.username} ({me.full_name})")
        
        logger.info("Starting polling...")
        bot.infinity_polling()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Critical error: {e}")
        logger.error("Diagnostics:")
        logger.error(f"  - Proxy: {proxy_url}")
        logger.error(f"  - Token: {TOKEN[:10]}...{TOKEN[-5:]}")
        sys.exit(1)
