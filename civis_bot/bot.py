#!/usr/bin/env python3
"""
Civis Bot - Main entry point.
Full MVP with AI matching, subscriptions, and marketplace.
"""

import logging
import sys
import signal

import requests
from telebot import TeleBot
from dotenv import load_dotenv

from config import TOKEN, get_proxy_url
from database import init_db
from handlers import (
    cmd_start, cmd_profile, cmd_embedding, cmd_citizens,
    cmd_offers, cmd_requests, cmd_my_offers, cmd_my_requests,
    cmd_marketplace, cmd_help, cmd_survey, cmd_status,
    cmd_cancel, cmd_done, cmd_offer, cmd_request,
    cmd_subscribe, cmd_setkey, cmd_match,
    handle_survey, handle_language_selection
)
from keyboards import get_main_keyboard

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

# --- REGISTER HANDLERS ---

# Language selection
@bot.message_handler(func=lambda message: message.text in ["English", "Русский"])
def language_selection(message):
    handle_language_selection(message, bot)

# Commands
@bot.message_handler(commands=['start'])
def start(message):
    cmd_start(message, bot)

@bot.message_handler(commands=['profile'])
def profile(message):
    cmd_profile(message, bot)

@bot.message_handler(commands=['embedding'])
def embedding(message):
    cmd_embedding(message, bot)

@bot.message_handler(commands=['citizens'])
def citizens(message):
    cmd_citizens(message, bot)

@bot.message_handler(commands=['offers'])
def offers(message):
    cmd_offers(message, bot)

@bot.message_handler(commands=['requests'])
def requests_cmd(message):
    cmd_requests(message, bot)

@bot.message_handler(commands=['my_offers'])
def my_offers(message):
    cmd_my_offers(message, bot)

@bot.message_handler(commands=['my_requests'])
def my_requests(message):
    cmd_my_requests(message, bot)

@bot.message_handler(commands=['marketplace'])
def marketplace(message):
    cmd_marketplace(message, bot)

@bot.message_handler(commands=['help'])
def help_cmd(message):
    cmd_help(message, bot)

@bot.message_handler(commands=['survey'])
def survey(message):
    cmd_survey(message, bot)

@bot.message_handler(commands=['status'])
def status_cmd(message):
    cmd_status(message, bot)

@bot.message_handler(commands=['cancel'])
def cancel(message):
    cmd_cancel(message, bot)

@bot.message_handler(commands=['done'])
def done(message):
    cmd_done(message, bot)

@bot.message_handler(commands=['offer'])
def offer(message):
    cmd_offer(message, bot)

@bot.message_handler(commands=['request'])
def request_cmd(message):
    cmd_request(message, bot)

# Subscription and AI
@bot.message_handler(commands=['subscribe'])
def subscribe(message):
    cmd_subscribe(message, bot)

@bot.message_handler(commands=['setkey'])
def setkey(message):
    cmd_setkey(message, bot)

@bot.message_handler(commands=['match'])
def match_cmd(message):
    cmd_match(message, bot)

# Survey state handler (catch-all for text messages)
@bot.message_handler(func=lambda message: True, content_types=['text'])
def survey_handler(message):
    handle_survey(message, bot)

# --- CALLBACK QUERY HANDLER ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    tg_id = call.from_user.id
    data = call.data
    
    if data == "subscribe_premium":
        bot.answer_callback_query(call.id, "🔗 Payment link coming soon!")
        bot.send_message(
            tg_id,
            "💳 Premium Subscription\n\n"
            "To subscribe, send $9.99 via PayPal to: **your-paypal@email.com**\n\n"
            "After payment, send /confirm to activate your subscription."
        )
    elif data == "subscribe_lifetime":
        bot.answer_callback_query(call.id, "🔗 Payment link coming soon!")
        bot.send_message(
            tg_id,
            "🌟 Lifetime Subscription\n\n"
            "To subscribe, send $99 via PayPal to: **your-paypal@email.com**\n\n"
            "After payment, send /confirm to activate your subscription."
        )
    elif data == "setkey":
        bot.answer_callback_query(call.id, "Use /setkey command")
        bot.send_message(
            tg_id,
            "🔑 Set your OpenAI API key:\n\n"
            "Use: /setkey sk-...\n\n"
            "You can get a key from: https://platform.openai.com/api-keys"
        )

# --- MAIN ---
if __name__ == "__main__":
    try:
        # Initialize database
        init_db()
        
        # Test connection
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
