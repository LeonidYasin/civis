#!/usr/bin/env python3
"""
Civis Bot - Entry point
"""

import logging
import sys
import signal
import time
import os
import threading

import requests
from telebot import TeleBot
from telebot.types import BotCommand, CallbackQuery

from config import TOKEN, get_proxy_url
from database import init_db
from handlers import register_handlers, set_bot

# --- LOGGING ---
# Force UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Global flag for shutdown
shutting_down = False

# --- SIGNAL HANDLER ---
def signal_handler(sig, frame):
    global shutting_down
    if shutting_down:
        logger.info("Force exit...")
        os._exit(0)
    
    shutting_down = True
    print("\n" + "="*50)
    print("Shutting down bot...")
    print("Press Ctrl+C again to force exit immediately.")
    print("="*50)
    logger.info("="*50)
    logger.info("Shutting down bot...")
    logger.info("Press Ctrl+C again to force exit immediately.")
    logger.info("="*50)

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

# --- CALLBACK QUERY HANDLER (for inline keyboard) ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call: CallbackQuery):
    """Handle inline keyboard button clicks — execute command immediately"""
    data = call.data
    
    # Map callback data to commands
    command_map = {
        'offer': '/offer',
        'request': '/request',
        'my_offers': '/my_offers',
        'my_requests': '/my_requests',
        'delete_offer': '/delete_offer',
        'delete_request': '/delete_request',
        'marketplace': '/marketplace',
        'profile': '/profile',
        'embedding': '/embedding',
        'citizens': '/citizens',
        'subscribe': '/subscribe',
        'match': '/match',
        'search': '/search',
        'help': '/help',
        'support': '/support',
        'language': '/language',
        'start': '/start',
        'menu': '/menu',
        'offer_real_estate': '/offer_real_estate',
        'offer_taxi': '/offer_taxi',
        'offer_delivery': '/offer_delivery',
    }
    
    if data not in command_map:
        bot.answer_callback_query(call.id, "Unknown action")
        return
    
    # Answer callback to remove loading state
    bot.answer_callback_query(call.id)
    
    # Get the command
    cmd = command_map[data]
    
    # Create a fake message to simulate command
    class FakeMessage:
        def __init__(self, text, from_user, chat):
            self.text = text
            self.from_user = from_user
            self.chat = chat
            self.content_type = 'text'
    
    fake_msg = FakeMessage(
        text=cmd,
        from_user=call.from_user,
        chat=call.message.chat
    )
    
    # Process the command using bot's message handler
    try:
        bot.process_new_messages([fake_msg])
    except Exception as e:
        logger.error(f"Error processing callback command {cmd}: {e}")
        bot.send_message(call.message.chat.id, f"Error: {e}")

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
        BotCommand("offer_real_estate", "Quick real estate offer"),
        BotCommand("offer_taxi", "Quick taxi offer"),
        BotCommand("offer_delivery", "Quick delivery offer"),
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
        BotCommand("reload", "Reload bot (admin only)"),
    ]
    bot.set_my_commands(commands)
    logger.info("Commands menu set")

# --- REGISTER HANDLERS ---
register_handlers()

# --- MAIN ---
if __name__ == "__main__":
    try:
        logger.info("Starting Civis Bot...")
        
        init_db()
        logger.info("Database initialized")
        
        set_commands_menu()
        
        logger.info("Checking connection to Telegram API...")
        me = bot.get_me()
        logger.info(f"Connected: @{me.username} ({me.full_name})")
        
        logger.info("Starting polling... (Press Ctrl+C to stop)")
        logger.info("-" * 50)
        
        def polling_thread():
            try:
                bot.infinity_polling(interval=0.5)
            except Exception as e:
                if not shutting_down:
                    logger.error(f"Polling error: {e}")
        
        thread = threading.Thread(target=polling_thread, daemon=True)
        thread.start()
        
        while not shutting_down:
            time.sleep(0.1)
        
        logger.info("Stopping polling...")
        try:
            bot.stop_polling()
        except:
            pass
        
        logger.info("Bot stopped.")
        sys.exit(0)
        
    except KeyboardInterrupt:
        logger.info("\nBot stopped by user (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Critical error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
