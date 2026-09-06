#!/usr/bin/env python3
"""
Civis MVP Bot - Full version with Russian language and marketplace commands.
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

# --- SIGNAL HANDLER ---
def signal_handler(sig, frame):
    logger.info("Stopping bot...")
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

# --- DATABASE ---
DB_PATH = Path(__file__).parent / "civis_data.db"

def init_db():
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
    
    cur.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cur.fetchall()]
    if 'language' not in columns:
        cur.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'en'")
        logger.info("Added 'language' column")
    
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
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT state, data FROM sessions WHERE tg_id = ?", (tg_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return row[0], json.loads(row[1]) if row[1] else {}
    return None, {}

def set_session(tg_id, state, data=None):
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
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM sessions WHERE tg_id = ?", (tg_id,))
    conn.commit()
    conn.close()

# --- TRANSLATIONS ---
TEXTS = {
    'en': {
        'welcome': "Welcome to Civis!\n\nCivis is a Republic of Professionals - a community where people connect based on trust, values, and shared goals.\n\nWe use AI to understand who you are and match you with the right people, projects, and opportunities.\n\nNo resumes. No cold calls. Just real connections.\n\nLet's create your profile!",
        'language_set': "Language set to English.",
        'choose_language': "Choose your language:",
        'name_ask': "What is your name?",
        'about_ask': "Tell me a bit about yourself and your professional goals.\n(Just a few sentences is fine.)",
        'about_short': "That's a bit short. Could you tell me a little more about yourself?",
        'values_intro': "To match you with the right people, we need to understand what matters to you in work.\n\nSelect 3 key values from the list below.\n(Just click the buttons one by one. You'll see your selection below.)",
        'values_ask': "Choose 3 values from the buttons below:",
        'values_selected': "Selected: {values}\n\nChoose {remaining} more or click /done when finished:",
        'values_error': "Please select 3 values total. You have {count}. Choose {remaining} more.",
        'values_complete': "Great! You've selected 3 values.",
        'role_ask': "What is your main role?",
        'role_error': "Please select a role from the buttons.",
        'format_ask': "Which communication format is convenient for you?",
        'format_error': "Please select a format from the buttons.",
        'profile_complete': "Congratulations! You are now a citizen of Civis!",
        'welcome_citizen': "Welcome to Civis, {name}!\n\nYou are now a citizen. You can:\n/offer - Publish an offer (sell something)\n/request - Publish a request (buy something)\n/marketplace - View all offers and requests\n/profile - View your profile\n/survey - Update your profile",
        'cancel': "Cancelled.",
        'unknown': "Use /start to create your profile or /help for commands.",
        'profile': "Profile:",
        'no_profile': "You don't have a profile yet. Use /start to create one!",
        'help': "Civis Bot\n\n/start - Create your profile\n/profile - View your profile\n/survey - Update your profile\n/offer - Publish an offer\n/request - Publish a request\n/marketplace - View marketplace\n/status - Bot status\n/cancel - Cancel current operation\n/help - Show this message",
        'status': "Civis Bot\n\nProfiles: {count}\nProxy: {proxy}",
        'done_button': "/done",
        'marketplace_empty': "Marketplace is empty. Use /offer or /request to publish something.",
        'offer_prompt': "Describe what you are offering (service, product, knowledge, etc.):",
        'request_prompt': "Describe what you are looking for (service, product, etc.):",
        'offer_saved': "Your offer has been published!",
        'request_saved': "Your request has been published!",
    },
    'ru': {
        'welcome': "Welcome to Civis!\n\nCivis is a Republic of Professionals - a community where people connect based on trust, values, and shared goals.\n\nWe use AI to understand who you are and match you with the right people, projects, and opportunities.\n\nNo resumes. No cold calls. Just real connections.\n\nLet's create your profile!",
        'language_set': "Language set to Russian.",
        'choose_language': "Choose your language:",
        'name_ask': "What is your name?",
        'about_ask': "Tell me a bit about yourself and your professional goals.\n(Just a few sentences is fine.)",
        'about_short': "That's a bit short. Could you tell me a little more about yourself?",
        'values_intro': "To match you with the right people, we need to understand what matters to you in work.\n\nSelect 3 key values from the list below.\n(Just click the buttons one by one. You'll see your selection below.)",
        'values_ask': "Choose 3 values from the buttons below:",
        'values_selected': "Selected: {values}\n\nChoose {remaining} more or click /done when finished:",
        'values_error': "Please select 3 values total. You have {count}. Choose {remaining} more.",
        'values_complete': "Great! You've selected 3 values.",
        'role_ask': "What is your main role?",
        'role_error': "Please select a role from the buttons.",
        'format_ask': "Which communication format is convenient for you?",
        'format_error': "Please select a format from the buttons.",
        'profile_complete': "Congratulations! You are now a citizen of Civis!",
        'welcome_citizen': "Welcome to Civis, {name}!\n\nYou are now a citizen. You can:\n/offer - Publish an offer (sell something)\n/request - Publish a request (buy something)\n/marketplace - View all offers and requests\n/profile - View your profile\n/survey - Update your profile",
        'cancel': "Cancelled.",
        'unknown': "Use /start to create your profile or /help for commands.",
        'profile': "Profile:",
        'no_profile': "You don't have a profile yet. Use /start to create one!",
        'help': "Civis Bot\n\n/start - Create your profile\n/profile - View your profile\n/survey - Update your profile\n/offer - Publish an offer\n/request - Publish a request\n/marketplace - View marketplace\n/status - Bot status\n/cancel - Cancel current operation\n/help - Show this message",
        'status': "Civis Bot\n\nProfiles: {count}\nProxy: {proxy}",
        'done_button': "/done",
        'marketplace_empty': "Marketplace is empty. Use /offer or /request to publish something.",
        'offer_prompt': "Describe what you are offering (service, product, knowledge, etc.):",
        'request_prompt': "Describe what you are looking for (service, product, etc.):",
        'offer_saved': "Your offer has been published!",
        'request_saved': "Your request has been published!",
    }
}

# --- VALUE MAPPING ---
VALUE_MAP = {
    'en': {
        'Honesty': 'Honesty',
        'Expertise': 'Expertise',
        'Initiative': 'Initiative',
        'Reliability': 'Reliability',
        'Speed': 'Speed',
        'Empathy': 'Empathy',
        'Systematic': 'Systematic',
        'Creativity': 'Creativity',
        'Openness': 'Openness',
        'Ambition': 'Ambition',
    },
    'ru': {
        'Honesty': 'Honesty',
        'Expertise': 'Expertise',
        'Initiative': 'Initiative',
        'Reliability': 'Reliability',
        'Speed': 'Speed',
        'Empathy': 'Empathy',
        'Systematic': 'Systematic',
        'Creativity': 'Creativity',
        'Openness': 'Openness',
        'Ambition': 'Ambition',
    }
}

def get_text(tg_id, key, **kwargs):
    user = get_user(tg_id)
    lang = user.get('language', 'en') if user else 'en'
    text = TEXTS.get(lang, TEXTS['en']).get(key, TEXTS['en'][key])
    return text.format(**kwargs) if kwargs else text

def get_value_buttons(lang):
    if lang == 'ru':
        return ["Honesty", "Expertise", "Initiative", "Reliability", "Speed", "Empathy", "Systematic", "Creativity", "Openness", "Ambition"]
    return ["Honesty", "Expertise", "Initiative", "Reliability", "Speed", "Empathy", "Systematic", "Creativity", "Openness", "Ambition"]

def get_roles(lang):
    if lang == 'ru':
        return ["Executor", "Customer", "Coordinator", "Investor"]
    return ["Executor", "Customer", "Coordinator", "Investor"]

def get_formats(lang):
    if lang == 'ru':
        return ["Text", "Voice", "Video", "Any"]
    return ["Text", "Voice", "Video", "Any"]

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

# --- SET COMMANDS ---
def set_commands():
    commands = [
        BotCommand("start", "Create your profile"),
        BotCommand("profile", "View your profile"),
        BotCommand("survey", "Update your profile"),
        BotCommand("offer", "Publish an offer"),
        BotCommand("request", "Publish a request"),
        BotCommand("marketplace", "View marketplace"),
        BotCommand("status", "Bot status"),
        BotCommand("help", "Help"),
        BotCommand("cancel", "Cancel current operation"),
        BotCommand("done", "Finish value selection"),
    ]
    bot.set_my_commands(commands)
    logger.info("Commands menu set")

# --- KEYBOARDS ---
def get_language_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(KeyboardButton("English"), KeyboardButton("Russian"))
    return keyboard

def get_main_keyboard(lang='en'):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("/offer"),
        KeyboardButton("/request"),
        KeyboardButton("/marketplace"),
        KeyboardButton("/profile"),
        KeyboardButton("/help"),
    )
    return keyboard

def get_values_keyboard(lang='en'):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    for v in get_value_buttons(lang):
        keyboard.add(KeyboardButton(v))
    keyboard.add(KeyboardButton(TEXTS[lang]['done_button']))
    return keyboard

def get_roles_keyboard(lang='en'):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for r in get_roles(lang):
        keyboard.add(KeyboardButton(r))
    return keyboard

def get_formats_keyboard(lang='en'):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for f in get_formats(lang):
        keyboard.add(KeyboardButton(f))
    return keyboard

# --- COMMAND HANDLERS ---
@bot.message_handler(commands=['start'])
def cmd_start(message: Message):
    tg_id = message.from_user.id
    logger.info(f"Received /start from {tg_id}")
    
    user = get_user(tg_id)
    if user and user.get('status') == 'completed':
        lang = user.get('language', 'en')
        bot.reply_to(
            message,
            get_text(tg_id, 'welcome_citizen', name=user.get('name', 'friend')),
            reply_markup=get_main_keyboard(lang)
        )
        return
    
    set_session(tg_id, 'language_select', {})
    bot.reply_to(
        message,
        "Choose your language:\n\nEnglish / Russian",
        reply_markup=get_language_keyboard()
    )

@bot.message_handler(commands=['profile'])
def cmd_profile(message: Message):
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    lang = user.get('language', 'en')
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
    bot.reply_to(message, get_text(message.from_user.id, 'help'))

@bot.message_handler(commands=['survey'])
def cmd_survey(message: Message):
    tg_id = message.from_user.id
    user = get_user(tg_id)
    lang = user.get('language', 'en') if user else 'en'
    set_session(tg_id, 'survey_name', {'language': lang})
    bot.reply_to(message, get_text(tg_id, 'name_ask'), reply_markup=ReplyKeyboardRemove())

@bot.message_handler(commands=['status'])
def cmd_status(message: Message):
    tg_id = message.from_user.id
    try:
        me = bot.get_me()
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users WHERE status = 'completed'")
        count = cur.fetchone()[0]
        conn.close()
        bot.reply_to(message, get_text(tg_id, 'status', count=count, proxy=proxy_url or 'None'))
    except Exception as e:
        bot.reply_to(message, f"Error: {e}")

@bot.message_handler(commands=['cancel'])
def cmd_cancel(message: Message):
    tg_id = message.from_user.id
    clear_session(tg_id)
    bot.reply_to(message, get_text(tg_id, 'cancel'))

@bot.message_handler(commands=['done'])
def cmd_done(message: Message):
    tg_id = message.from_user.id
    state, data = get_session(tg_id)
    if state != 'survey_values':
        bot.reply_to(message, "You're not in value selection mode.")
        return
    
    selected = data.get('selected_values', [])
    if len(selected) != 3:
        lang = data.get('language', 'en')
        remaining = 3 - len(selected)
        bot.reply_to(message, TEXTS[lang]['values_error'].format(count=len(selected), remaining=remaining))
        return
    
    lang = data.get('language', 'en')
    data['user_values'] = ', '.join(selected)
    set_session(tg_id, 'survey_role', data)
    bot.reply_to(message, TEXTS[lang]['values_complete'] + "\n\n" + TEXTS[lang]['role_ask'], reply_markup=get_roles_keyboard(lang))

@bot.message_handler(commands=['offer'])
def cmd_offer(message: Message):
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    lang = user.get('language', 'en')
    set_session(tg_id, 'offer', {'language': lang})
    bot.reply_to(message, get_text(tg_id, 'offer_prompt'), reply_markup=ReplyKeyboardRemove())

@bot.message_handler(commands=['request'])
def cmd_request(message: Message):
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    lang = user.get('language', 'en')
    set_session(tg_id, 'request', {'language': lang})
    bot.reply_to(message, get_text(tg_id, 'request_prompt'), reply_markup=ReplyKeyboardRemove())

@bot.message_handler(commands=['marketplace'])
def cmd_marketplace(message: Message):
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    lang = user.get('language', 'en')
    bot.reply_to(message, get_text(tg_id, 'marketplace_empty'))

# --- LANGUAGE SELECTION ---
@bot.message_handler(func=lambda message: message.text in ["English", "Russian"])
def handle_language_selection(message: Message):
    tg_id = message.from_user.id
    text = message.text
    
    lang = 'en' if text == "English" else 'ru'
    
    user = get_user(tg_id)
    if user:
        save_user(tg_id, user.get('username', 'unknown'), language=lang)
    else:
        save_user(tg_id, message.from_user.username or "unknown", language=lang)
    
    state, _ = get_session(tg_id)
    if state == 'language_select':
        clear_session(tg_id)
    
    bot.reply_to(
        message,
        TEXTS[lang]['language_set'] + "\n\n" + TEXTS[lang]['welcome'],
        reply_markup=ReplyKeyboardRemove()
    )
    
    set_session(tg_id, 'survey_name', {'language': lang})
    bot.send_message(tg_id, TEXTS[lang]['name_ask'])

# --- SURVEY HANDLERS ---
@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_survey(message: Message):
    tg_id = message.from_user.id
    text = message.text.strip()
    
    if text.startswith('/'):
        return
    
    state, data = get_session(tg_id)
    if not state:
        lang = get_user(tg_id).get('language', 'en') if get_user(tg_id) else 'en'
        bot.reply_to(message, get_text(tg_id, 'unknown'), reply_markup=get_main_keyboard(lang))
        return
    
    lang = data.get('language', 'en')
    
    if state == 'survey_name':
        if len(text) < 2:
            bot.reply_to(message, "Please enter a valid name (at least 2 characters).")
            return
        data['name'] = text
        set_session(tg_id, 'survey_about', data)
        bot.reply_to(message, f"Nice to meet you, {text}!\n\n" + TEXTS[lang]['about_ask'])
    
    elif state == 'survey_about':
        if len(text) < 20:
            bot.reply_to(message, TEXTS[lang]['about_short'])
            return
        data['about_text'] = text
        data['selected_values'] = []
        set_session(tg_id, 'survey_values', data)
        bot.reply_to(
            message,
            TEXTS[lang]['values_intro'] + "\n\n" + TEXTS[lang]['values_ask'],
            reply_markup=get_values_keyboard(lang)
        )
    
    elif state == 'survey_values':
        value_map = VALUE_MAP.get(lang, VALUE_MAP['en'])
        selected = data.get('selected_values', [])
        
        valid_value = None
        if text in value_map:
            valid_value = value_map[text]
        elif text in VALUE_MAP['en']:
            valid_value = text
        elif text in VALUE_MAP['ru']:
            valid_value = VALUE_MAP['ru'][text]
        
        if valid_value and valid_value not in selected:
            selected.append(valid_value)
            data['selected_values'] = selected
            set_session(tg_id, 'survey_values', data)
            
            remaining = 3 - len(selected)
            if remaining > 0:
                bot.reply_to(
                    message,
                    TEXTS[lang]['values_selected'].format(
                        values=', '.join(selected),
                        remaining=remaining
                    ),
                    reply_markup=get_values_keyboard(lang)
                )
            else:
                bot.reply_to(message, TEXTS[lang]['values_complete'], reply_markup=ReplyKeyboardRemove())
                data['user_values'] = ', '.join(selected)
                set_session(tg_id, 'survey_role', data)
                bot.reply_to(message, TEXTS[lang]['role_ask'], reply_markup=get_roles_keyboard(lang))
        else:
            bot.reply_to(message, f"Please choose a value from the buttons.\n\nCurrent selection: {len(selected)}/3")
    
    elif state == 'survey_role':
        roles = get_roles(lang)
        if text not in roles:
            bot.reply_to(message, f"Please select a role from the buttons: {', '.join(roles)}")
            return
        
        data['role'] = text
        set_session(tg_id, 'survey_format', data)
        bot.reply_to(message, TEXTS[lang]['format_ask'], reply_markup=get_formats_keyboard(lang))
    
    elif state == 'survey_format':
        formats = get_formats(lang)
        if text not in formats:
            bot.reply_to(message, f"Please select a format from the buttons: {', '.join(formats)}")
            return
        
        data['format'] = text
        
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
                language=lang,
                status='completed'
            )
            
            clear_session(tg_id)
            
            bot.reply_to(
                message,
                TEXTS[lang]['profile_complete'] + "\n\n" + TEXTS[lang]['welcome_citizen'].format(name=data.get('name', '')),
                reply_markup=get_main_keyboard(lang)
            )
            
            logger.info(f"Profile completed for {tg_id}: {data.get('name')}")
            
        except Exception as e:
            logger.error(f"Error saving profile: {e}")
            bot.reply_to(message, "Error saving your profile. Please try again.")
    
    elif state == 'offer':
        bot.reply_to(
            message,
            get_text(tg_id, 'offer_saved') + "\n\n" + get_text(tg_id, 'welcome_citizen', name=get_user(tg_id).get('name', '')),
            reply_markup=get_main_keyboard(lang)
        )
        clear_session(tg_id)
    
    elif state == 'request':
        bot.reply_to(
            message,
            get_text(tg_id, 'request_saved') + "\n\n" + get_text(tg_id, 'welcome_citizen', name=get_user(tg_id).get('name', '')),
            reply_markup=get_main_keyboard(lang)
        )
        clear_session(tg_id)

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
        logger.info("Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"Critical error: {e}")
        sys.exit(1)
