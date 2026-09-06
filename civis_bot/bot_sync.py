#!/usr/bin/env python3
"""
Civis MVP Bot - Natural conversation flow with language selection.
"""

import logging
import os
import sys
import sqlite3
import json
import signal
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
from telebot import TeleBot
from telebot.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, BotCommand

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# --- SIGNAL HANDLER FOR CLEAN EXIT ---
def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    logger.info("\n⏹️ Received interrupt signal. Stopping bot...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

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
            language TEXT DEFAULT 'en',
            status TEXT DEFAULT 'registered',
            created_at TEXT,
            updated_at TEXT
        )
    """)
    
    # Check if language column exists, if not add it
    cur.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cur.fetchall()]
    if 'language' not in columns:
        cur.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'en'")
        logger.info("Added 'language' column to users table")
    
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
        columns = ['tg_id', 'username', 'name', 'telegram_contact', 'about_text', 'user_values', 'role', 'format', 'language', 'status', 'created_at', 'updated_at']
        return dict(zip(columns, row))
    return None

def save_user(tg_id, username, **kwargs):
    """Save or update user"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("SELECT tg_id FROM users WHERE tg_id = ?", (tg_id,))
    exists = cur.fetchone()
    
    if exists:
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

# --- TRANSLATIONS ---
TEXTS = {
    'en': {
        'welcome': """🏛️ Welcome to Civis!

Civis is a Republic of Professionals — a community where people connect based on trust, values, and shared goals.

We use AI to understand who you are and match you with the right people, projects, and opportunities.

No resumes. No cold calls. Just real connections.

Let's create your profile!""",
        'language_set': "🌍 Language set to English.",
        'choose_language': "🌍 Choose your language:",
        'name_ask': "What is your name?",
        'about_ask': "Tell me a bit about yourself and your professional goals.\n(Just a few sentences is fine.)",
        'about_short': "That's a bit short. Could you tell me a little more about yourself?",
        'values_ask': "Select 3 key values that you share in your work:",
        'values_error': "Please select exactly 3 values from the buttons.",
        'role_ask': "What is your main role?",
        'role_error': "Please select a role from the buttons.",
        'format_ask': "Which communication format is convenient for you?",
        'format_error': "Please select a format from the buttons.",
        'profile_complete': "🎉 Congratulations! Your profile is complete.\nYou are now a citizen of Civis!",
        'cancel': "✅ Cancelled.",
        'unknown': "Use /start to create your profile or /help for commands.",
        'profile': "👤 Profile:",
        'no_profile': "You don't have a profile yet. Use /start to create one!",
        'help': "📚 Civis Bot\n\n/start - Create your profile\n/profile - View your profile\n/survey - Update your profile\n/status - Bot status\n/cancel - Cancel current operation\n/help - Show this message",
        'status': "🤖 Civis Bot\n\nProfiles: {count}\nProxy: {proxy}",
    },
    'ru': {
        'welcome': """🏛️ Добро пожаловать в Civis!

Civis — это Республика Профессионалов — сообщество, где люди соединяются на основе доверия, ценностей и общих целей.

Мы используем ИИ, чтобы понять, кто вы, и подобрать вам подходящих людей, проекты и возможности.

Без резюме. Без холодных звонков. Только настоящие связи.

Давайте создадим ваш профиль!""",
        'language_set': "🌍 Язык установлен: Русский.",
        'choose_language': "🌍 Выберите язык:",
        'name_ask': "Как вас зовут?",
        'about_ask': "Расскажите немного о себе и своих профессиональных целях.\n(Достаточно пары предложений.)",
        'about_short': "Это коротковато. Не могли бы вы рассказать о себе чуть больше?",
        'values_ask': "Выберите 3 ключевые ценности, которые вы разделяете в работе:",
        'values_error': "Пожалуйста, выберите ровно 3 ценности из кнопок.",
        'role_ask': "Какова ваша основная роль?",
        'role_error': "Пожалуйста, выберите роль из кнопок.",
        'format_ask': "Какой формат общения вам удобен?",
        'format_error': "Пожалуйста, выберите формат из кнопок.",
        'profile_complete': "🎉 Поздравляем! Ваш профиль заполнен.\nТеперь вы гражданин Civis!",
        'cancel': "✅ Отменено.",
        'unknown': "Используйте /start для создания профиля или /help для помощи.",
        'profile': "👤 Профиль:",
        'no_profile': "У вас ещё нет профиля. Используйте /start, чтобы создать его!",
        'help': "📚 Civis Бот\n\n/start - Создать профиль\n/profile - Мой профиль\n/survey - Обновить профиль\n/status - Статус бота\n/cancel - Отменить текущую операцию\n/help - Помощь",
        'status': "🤖 Civis Бот\n\nПрофилей: {count}\nПрокси: {proxy}",
    }
}

def get_text(tg_id, key, **kwargs):
    """Get localized text for user"""
    user = get_user(tg_id)
    lang = user.get('language', 'en') if user else 'en'
    text = TEXTS.get(lang, TEXTS['en']).get(key, TEXTS['en'][key])
    return text.format(**kwargs) if kwargs else text

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

# --- SET COMMANDS MENU ---
def set_commands():
    """Set bot commands menu"""
    commands = [
        BotCommand("start", "Create or view your profile"),
        BotCommand("profile", "View your profile"),
        BotCommand("survey", "Update your profile"),
        BotCommand("status", "Bot status"),
        BotCommand("help", "Help"),
        BotCommand("cancel", "Cancel current operation"),
    ]
    bot.set_my_commands(commands)
    logger.info("Commands menu set")

# --- KEYBOARDS ---
def get_language_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("🇬🇧 English"),
        KeyboardButton("🇷🇺 Русский")
    )
    return keyboard

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
    """Start command - show welcome and language selection"""
    tg_id = message.from_user.id
    username = message.from_user.username or "unknown"
    logger.info(f"Received /start from {tg_id}")
    
    user = get_user(tg_id)
    if user and user.get('status') == 'completed':
        lang = user.get('language', 'en')
        bot.reply_to(
            message,
            f"Welcome back, {user.get('name', 'friend')}! 🎉\n\n"
            "Your profile is complete.\n"
            "Use /profile to view or /survey to update."
        )
        return
    
    set_session(tg_id, 'language_select', {})
    bot.reply_to(
        message,
        TEXTS['en']['choose_language'] + "\n\n" + TEXTS['ru']['choose_language'],
        reply_markup=get_language_keyboard()
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
            get_text(tg_id, 'no_profile')
        )
        return
    
    profile_text = (
        f"{get_text(tg_id, 'profile')}\n\n"
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
    tg_id = message.from_user.id
    bot.reply_to(message, get_text(tg_id, 'help'))

@bot.message_handler(commands=['survey'])
def cmd_survey(message: Message):
    """Start or restart survey"""
    tg_id = message.from_user.id
    logger.info(f"Received /survey from {tg_id}")
    
    user = get_user(tg_id)
    lang = user.get('language', 'en') if user else 'en'
    set_session(tg_id, 'survey_name', {'language': lang})
    bot.reply_to(
        message,
        get_text(tg_id, 'name_ask'),
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
            get_text(tg_id, 'status', count=count, proxy=proxy_url or 'None')
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
        get_text(tg_id, 'cancel'),
        reply_markup=get_main_keyboard()
    )

# --- LANGUAGE SELECTION ---
@bot.message_handler(func=lambda message: message.text in ["🇬🇧 English", "🇷🇺 Русский"])
def handle_language_selection(message: Message):
    """Handle language selection"""
    tg_id = message.from_user.id
    text = message.text
    
    if "English" in text:
        lang = 'en'
    else:
        lang = 'ru'
    
    # Save language to user
    user = get_user(tg_id)
    if user:
        save_user(tg_id, user.get('username', 'unknown'), language=lang)
    else:
        save_user(tg_id, message.from_user.username or "unknown", language=lang)
    
    # Clear language selection session if exists
    state, _ = get_session(tg_id)
    if state == 'language_select':
        clear_session(tg_id)
    
    # Show welcome message in selected language
    bot.reply_to(
        message,
        TEXTS[lang]['language_set'] + "\n\n" + TEXTS[lang]['welcome'],
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Start survey
    set_session(tg_id, 'survey_name', {'language': lang})
    bot.send_message(
        tg_id,
        TEXTS[lang]['name_ask']
    )

# --- SURVEY STATE HANDLERS ---
@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_survey(message: Message):
    """Handle survey states - natural conversation"""
    tg_id = message.from_user.id
    text = message.text.strip()
    
    if text.startswith('/'):
        return
    
    state, data = get_session(tg_id)
    if not state or state == 'language_select':
        bot.reply_to(
            message,
            get_text(tg_id, 'unknown'),
            reply_markup=get_main_keyboard()
        )
        return
    
    lang = data.get('language', 'en')
    
    if state == 'survey_name':
        if len(text) < 2:
            bot.reply_to(message, "Please enter a valid name (at least 2 characters).")
            return
        data['name'] = text
        set_session(tg_id, 'survey_about', data)
        bot.reply_to(
            message,
            f"Nice to meet you, {text}! 👋\n\n" + TEXTS[lang]['about_ask']
        )
    
    elif state == 'survey_about':
        if len(text) < 20:
            bot.reply_to(message, TEXTS[lang]['about_short'])
            return
        data['about_text'] = text
        set_session(tg_id, 'survey_values', data)
        bot.reply_to(
            message,
            TEXTS[lang]['values_ask'],
            reply_markup=get_values_keyboard()
        )
    
    elif state == 'survey_values':
        valid_values = ["Honesty", "Expertise", "Initiative", "Reliability", "Speed", "Empathy", "Systematic", "Creativity", "Openness", "Ambition"]
        selected = [v.strip() for v in text.split(',')]
        selected = [v for v in selected if v in valid_values]
        
        if len(selected) != 3:
            bot.reply_to(message, TEXTS[lang]['values_error'])
            return
        
        data['user_values'] = ', '.join(selected)
        set_session(tg_id, 'survey_role', data)
        bot.reply_to(
            message,
            TEXTS[lang]['role_ask'],
            reply_markup=get_roles_keyboard()
        )
    
    elif state == 'survey_role':
        valid_roles = ["Executor", "Customer", "Coordinator", "Investor"]
        if text not in valid_roles:
            bot.reply_to(message, TEXTS[lang]['role_error'])
            return
        
        data['role'] = text
        set_session(tg_id, 'survey_format', data)
        bot.reply_to(
            message,
            TEXTS[lang]['format_ask'],
            reply_markup=get_formats_keyboard()
        )
    
    elif state == 'survey_format':
        valid_formats = ["Text", "Voice", "Video", "Any"]
        if text not in valid_formats:
            bot.reply_to(message, TEXTS[lang]['format_error'])
            return
        
        data['format'] = text
        
        tg_id = message.from_user.id
        username = message.from_user.username or "unknown"
        
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
                language=data.get('language', 'en'),
                status='completed'
            )
            
            clear_session(tg_id)
            
            bot.reply_to(
                message,
                f"🎉 {data['name']}!\n\n" + TEXTS[lang]['profile_complete'] + "\n\n"
                f"Role: {data['role']}\n"
                f"Values: {data['user_values']}\n"
                f"Format: {data['format']}\n\n"
                "Use /profile to view or /survey to update.",
                reply_markup=get_main_keyboard()
            )
            
            logger.info(f"Profile completed for {tg_id}: {data['name']}")
            
        except Exception as e:
            logger.error(f"Error saving profile: {e}")
            bot.reply_to(message, "❌ Error saving your profile. Please try again.")

# --- MAIN ---
if __name__ == "__main__":
    try:
        init_db()
        set_commands()
        
        logger.info("Checking connection to Telegram API...")
        me = bot.get_me()
        logger.info(f"Connected: @{me.username} ({me.full_name})")
        
        logger.info("Starting polling... (Press Ctrl+C to stop)")
        bot.infinity_polling()
        
    except KeyboardInterrupt:
        logger.info("⏹️ Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"Critical error: {e}")
        sys.exit(1)
