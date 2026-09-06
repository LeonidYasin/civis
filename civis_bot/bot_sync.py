#!/usr/bin/env python3
"""
Civis MVP Bot - Full version with survey, database, and navigation logic.
Synchronous version using telebot + requests with HTTP proxy support.
"""

import logging
import os
import sys
import sqlite3
import json
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
from telebot import TeleBot
from telebot.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

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
    """Get proxy URL from .env or environment"""
    proxy_url = os.getenv("PROXY_URL")
    if proxy_url:
        logger.info(f"Using proxy: {proxy_url}")
        return proxy_url
    
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

# --- DATABASE SETUP ---
DB_PATH = Path(__file__).parent / "civis_data.db"

def init_db():
    """Initialize database"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Users table - renamed 'values' to 'user_values' to avoid SQL keyword
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            tg_id INTEGER PRIMARY KEY,
            username TEXT,
            name TEXT,
            telegram_contact TEXT,
            about_text TEXT,
            user_values TEXT,
            role TEXT,
            format TEXT,
            status TEXT DEFAULT 'registered',
            created_at TEXT,
            updated_at TEXT
        )
    """)
    
    # Sessions table (for FSM)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            tg_id INTEGER PRIMARY KEY,
            state TEXT,
            data TEXT,
            updated_at TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    logger.info("Database initialized")

def get_user(tg_id):
    """Get user data"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        columns = ['tg_id', 'username', 'name', 'telegram_contact', 'about_text', 'user_values', 'role', 'format', 'status', 'created_at', 'updated_at']
        return dict(zip(columns, row))
    return None

def save_user(tg_id, username, **kwargs):
    """Save or update user"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Check if exists
    cur.execute("SELECT tg_id FROM users WHERE tg_id = ?", (tg_id,))
    exists = cur.fetchone()
    
    if exists:
        # Update
        fields = []
        values = []
        for key, val in kwargs.items():
            if key != 'tg_id':
                fields.append(f"{key} = ?")
                values.append(val)
        values.append(datetime.now().isoformat())
        values.append(tg_id)
        cur.execute(f"UPDATE users SET {', '.join(fields)}, updated_at = ? WHERE tg_id = ?", values)
    else:
        # Insert
        fields = ['tg_id', 'username', 'created_at', 'updated_at']
        values = [tg_id, username, datetime.now().isoformat(), datetime.now().isoformat()]
        for key, val in kwargs.items():
            if key not in ['tg_id', 'username']:
                fields.append(key)
                values.append(val)
        placeholders = ', '.join(['?'] * len(values))
        cur.execute(f"INSERT INTO users ({', '.join(fields)}) VALUES ({placeholders})", values)
    
    conn.commit()
    conn.close()

def get_session(tg_id):
    """Get session state"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT state, data FROM sessions WHERE tg_id = ?", (tg_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return row[0], json.loads(row[1]) if row[1] else {}
    return None, {}

def set_session(tg_id, state, data=None):
    """Set session state"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    data_json = json.dumps(data or {})
    cur.execute("""
        INSERT OR REPLACE INTO sessions (tg_id, state, data, updated_at)
        VALUES (?, ?, ?, ?)
    """, (tg_id, state, data_json, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def clear_session(tg_id):
    """Clear session"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM sessions WHERE tg_id = ?", (tg_id,))
    conn.commit()
    conn.close()

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

# --- KEYBOARDS ---
def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("/start"),
        KeyboardButton("/profile"),
        KeyboardButton("/help")
    )
    return keyboard

def get_values_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    values = ["Honesty", "Expertise", "Initiative", "Reliability", "Speed", "Empathy", "Systematic", "Creativity", "Openness", "Ambition"]
    buttons = [KeyboardButton(v) for v in values]
    keyboard.add(*buttons)
    keyboard.add(KeyboardButton("/cancel"))
    return keyboard

def get_roles_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    roles = ["Executor", "Customer", "Coordinator", "Investor"]
    buttons = [KeyboardButton(r) for r in roles]
    keyboard.add(*buttons)
    keyboard.add(KeyboardButton("/cancel"))
    return keyboard

def get_formats_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    formats = ["Text", "Voice", "Video", "Any"]
    buttons = [KeyboardButton(f) for f in formats]
    keyboard.add(*buttons)
    keyboard.add(KeyboardButton("/cancel"))
    return keyboard

# --- COMMAND HANDLERS ---
@bot.message_handler(commands=['start'])
def cmd_start(message: Message):
    """Start command - begins the survey"""
    tg_id = message.from_user.id
    username = message.from_user.username or "unknown"
    logger.info(f"Received /start from {tg_id}")
    
    user = get_user(tg_id)
    if user and user.get('status') == 'completed':
        bot.reply_to(
            message,
            f"Welcome back, {user.get('name', 'friend')}! 🎉\n\n"
            "Your profile is already complete.\n"
            "Use /profile to view or /survey to update."
        )
        return
    
    # Start survey
    set_session(tg_id, 'survey_name', {})
    bot.reply_to(
        message,
        "Welcome to Civis! 🏛️\n"
        "The Republic of Professionals.\n\n"
        "Let's create your profile. You'll answer 4 questions.\n"
        "Type /cancel anytime to exit.\n\n"
        "1️⃣ What is your name?",
        reply_markup=ReplyKeyboardRemove()
    )

@bot.message_handler(commands=['profile'])
def cmd_profile(message: Message):
    """View profile"""
    tg_id = message.from_user.id
    logger.info(f"Received /profile from {tg_id}")
    
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(
            message,
            "You don't have a profile yet.\n"
            "Use /start to create one!"
        )
        return
    
    profile_text = (
        f"👤 Profile:\n\n"
        f"Name: {user.get('name', 'N/A')}\n"
        f"Telegram: @{user.get('username', 'N/A')}\n"
        f"Role: {user.get('role', 'N/A')}\n"
        f"Values: {user.get('user_values', 'N/A')}\n"
        f"Format: {user.get('format', 'N/A')}\n\n"
        f"About:\n{user.get('about_text', 'N/A')}"
    )
    bot.reply_to(message, profile_text)

@bot.message_handler(commands=['help'])
def cmd_help(message: Message):
    """Help command"""
    bot.reply_to(
        message,
        "📚 Civis Bot Commands:\n\n"
        "/start - Create your profile\n"
        "/profile - View your profile\n"
        "/survey - Update your profile\n"
        "/status - Check bot status\n"
        "/cancel - Cancel current operation\n"
        "/help - Show this message\n\n"
        "💡 You can also use the buttons!"
    )

@bot.message_handler(commands=['survey'])
def cmd_survey(message: Message):
    """Start or restart survey"""
    tg_id = message.from_user.id
    logger.info(f"Received /survey from {tg_id}")
    
    set_session(tg_id, 'survey_name', {})
    bot.reply_to(
        message,
        "📝 Let's update your profile.\n\n"
        "1️⃣ What is your name?",
        reply_markup=ReplyKeyboardRemove()
    )

@bot.message_handler(commands=['status'])
def cmd_status(message: Message):
    """Check bot status"""
    tg_id = message.from_user.id
    logger.info(f"Received /status from {tg_id}")
    
    try:
        me = bot.get_me()
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users WHERE status = 'completed'")
        count = cur.fetchone()[0]
        conn.close()
        
        bot.reply_to(
            message,
            f"🤖 Civis Bot Status\n\n"
            f"Bot: @{me.username}\n"
            f"Total profiles: {count}\n"
            f"Proxy: {proxy_url or 'None'}\n"
            f"DB: {DB_PATH}"
        )
    except Exception as e:
        logger.error(f"Status error: {e}")
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['cancel'])
def cmd_cancel(message: Message):
    """Cancel current operation"""
    tg_id = message.from_user.id
    logger.info(f"Received /cancel from {tg_id}")
    
    clear_session(tg_id)
    bot.reply_to(
        message,
        "✅ Operation cancelled.\n"
        "Use /start to begin again.",
        reply_markup=get_main_keyboard()
    )

# --- SURVEY STATE HANDLERS ---
@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_survey(message: Message):
    """Handle survey states"""
    tg_id = message.from_user.id
    text = message.text.strip()
    
    # Ignore commands
    if text.startswith('/'):
        return
    
    state, data = get_session(tg_id)
    if not state:
        # Not in survey, show help
        bot.reply_to(
            message,
            "Use /start to create your profile or /help for commands.",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Survey flow
    if state == 'survey_name':
        if len(text) < 2:
            bot.reply_to(message, "Please enter a valid name (at least 2 characters).")
            return
        data['name'] = text
        set_session(tg_id, 'survey_about', data)
        bot.reply_to(
            message,
            f"Nice to meet you, {text}! 👋\n\n"
            "2️⃣ Tell me about yourself and your professional goals.\n"
            "Minimum 300 characters. Take your time."
        )
    
    elif state == 'survey_about':
        if len(text) < 300:
            bot.reply_to(
                message,
                f"Please write at least 300 characters. You wrote {len(text)}.\n"
                "Take your time and tell me about yourself."
            )
            return
        data['about_text'] = text
        set_session(tg_id, 'survey_values', data)
        bot.reply_to(
            message,
            "Great! 📝\n\n"
            "3️⃣ Select 3 key values that you share in your work.\n"
            "Choose from the buttons below:",
            reply_markup=get_values_keyboard()
        )
    
    elif state == 'survey_values':
        # Check if valid value
        valid_values = ["Honesty", "Expertise", "Initiative", "Reliability", "Speed", "Empathy", "Systematic", "Creativity", "Openness", "Ambition"]
        selected = [v.strip() for v in text.split(',')]
        selected = [v for v in selected if v in valid_values]
        
        if len(selected) != 3:
            bot.reply_to(
                message,
                "Please select exactly 3 values from the buttons.\n"
                "You can type them separated by commas, or click the buttons."
            )
            return
        
        data['user_values'] = ', '.join(selected)
        set_session(tg_id, 'survey_role', data)
        bot.reply_to(
            message,
            "Excellent! 🎯\n\n"
            "4️⃣ What is your main role?",
            reply_markup=get_roles_keyboard()
        )
    
    elif state == 'survey_role':
        valid_roles = ["Executor", "Customer", "Coordinator", "Investor"]
        if text not in valid_roles:
            bot.reply_to(
                message,
                f"Please select a role from the buttons: {', '.join(valid_roles)}"
            )
            return
        
        data['role'] = text
        set_session(tg_id, 'survey_format', data)
        bot.reply_to(
            message,
            "Almost done! 📱\n\n"
            "5️⃣ Which communication format is convenient for you?",
            reply_markup=get_formats_keyboard()
        )
    
    elif state == 'survey_format':
        valid_formats = ["Text", "Voice", "Video", "Any"]
        if text not in valid_formats:
            bot.reply_to(
                message,
                f"Please select a format from the buttons: {', '.join(valid_formats)}"
            )
            return
        
        data['format'] = text
        
        # Complete survey
        tg_id = message.from_user.id
        username = message.from_user.username or "unknown"
        
        # Save to database
        try:
            save_user(
                tg_id=tg_id,
                username=username,
                name=data.get('name', ''),
                telegram_contact=f"@{username}",
                about_text=data.get('about_text', ''),
                user_values=data.get('user_values', ''),
                role=data.get('role', ''),
                format=data.get('format', ''),
                status='completed'
            )
            
            clear_session(tg_id)
            
            bot.reply_to(
                message,
                f"🎉 Congratulations, {data['name']}!\n\n"
                "Your profile is complete and saved.\n"
                "You are now a citizen of Civis! 🏛️\n\n"
                f"Your profile:\n"
                f"Role: {data['role']}\n"
                f"Values: {data['user_values']}\n"
                f"Format: {data['format']}\n\n"
                "We'll match you with projects and teams soon.\n"
                "Use /profile to view or /survey to update.",
                reply_markup=get_main_keyboard()
            )
            
            logger.info(f"Profile completed for {tg_id}: {data['name']}")
            
        except Exception as e:
            logger.error(f"Error saving profile: {e}")
            bot.reply_to(
                message,
                "❌ Error saving your profile. Please try again or contact support."
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
        
        logger.info("Starting polling...")
        bot.infinity_polling()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Critical error: {e}")
        sys.exit(1)
