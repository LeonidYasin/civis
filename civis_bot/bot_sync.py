#!/usr/bin/env python3
"""
Синхронный бот для тестирования через HTTP-прокси
Использует telebot + requests
"""

import os
import sys
import logging
from datetime import datetime

from dotenv import load_dotenv
import requests
import telebot
from telebot import types

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
PROXY_URL = os.getenv("PROXY_URL")

# Создаём сессию requests с прокси
session = requests.Session()

if PROXY_URL:
    logger.info(f"Using proxy: {PROXY_URL}")
    # Для HTTP-прокси
    if PROXY_URL.startswith("http"):
        session.proxies = {
            'http': PROXY_URL,
            'https': PROXY_URL,
        }
    # Для SOCKS5
    elif PROXY_URL.startswith("socks5"):
        try:
            import socks
            from requests_socks import SocksSession
            session = SocksSession(proxy_url=PROXY_URL)
        except ImportError:
            logger.error("Install: pip install requests-socks")
            sys.exit(1)
else:
    logger.info("No proxy configured, using direct connection")

# --- BOT INIT ---
bot = telebot.TeleBot(token=TOKEN, threaded=False)
# Заменяем сессию
bot.session = session

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def cmd_start(message):
    """Handler for /start command"""
    logger.info(f"Received /start from {message.from_user.id}")
    bot.reply_to(
        message,
        "Hello! I am a synchronous test bot for Civis.\n"
        "If you see this - connection to Telegram API works!\n\n"
        "Available commands:\n"
        "/ping - check connection\n"
        "/echo <text> - echo your message\n"
        "/info - bot information"
    )

@bot.message_handler(commands=['ping'])
def cmd_ping(message):
    """Check connection"""
    logger.info(f"Received /ping from {message.from_user.id}")
    start_time = datetime.now()
    bot.reply_to(message, "Pong!")
    end_time = datetime.now()
    latency = (end_time - start_time).total_seconds() * 1000
    bot.send_message(message.chat.id, f"Latency: {latency:.0f} ms")

@bot.message_handler(commands=['echo'])
def cmd_echo(message):
    """Echo user text"""
    logger.info(f"Received /echo from {message.from_user.id}")
    text = message.text.replace("/echo", "", 1).strip()
    if text:
        bot.reply_to(message, f"Echo: {text}")
    else:
        bot.reply_to(message, "Please write something after /echo")

@bot.message_handler(commands=['info'])
def cmd_info(message):
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
            f"Proxy: {PROXY_URL or 'None'}"
        )
    except Exception as e:
        logger.error(f"Error getting bot info: {e}")
        bot.reply_to(message, f"Error: {e}")

@bot.message_handler(func=lambda m: True)
def handle_unknown(message):
    """Unknown message handler"""
    logger.info(f"Unknown message from {message.from_user.id}: {message.text}")
    bot.reply_to(message, "Unknown command. Use /start for command list.")

# --- MAIN ---
if __name__ == "__main__":
    logger.info("Starting synchronous bot...")
    try:
        # Проверка соединения
        me = bot.get_me()
        logger.info(f"Connected to Telegram API!")
        logger.info(f"Bot name: {me.full_name}")
        logger.info(f"Username: @{me.username}")
        logger.info(f"ID: {me.id}")
        
        # Запуск бота
        logger.info("Starting polling...")
        bot.infinity_polling()
    except Exception as e:
        logger.error(f"Critical error: {e}")
        sys.exit(1)
