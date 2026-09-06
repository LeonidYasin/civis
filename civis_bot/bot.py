#!/usr/bin/env python3
"""
Main Civis bot with proxy support from .env
"""

import asyncio
import logging
import sqlite3
import os
import sys
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from dotenv import load_dotenv

# Proxy support
import aiohttp
from aiogram.client.session.aiohttp import AiohttpSession

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
    logger.error("Create .env file with: BOT_TOKEN=your_token")
    sys.exit(1)

# --- PROXY SETUP ---
def get_proxy_url():
    """Get proxy URL from .env or environment"""
    proxy_url = os.getenv("PROXY_URL")
    if proxy_url:
        logger.info(f"Proxy from .env: {proxy_url}")
        return proxy_url
    
    http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
    https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
    
    if https_proxy:
        logger.info(f"Proxy from HTTPS_PROXY: {https_proxy}")
        return https_proxy
    elif http_proxy:
        logger.info(f"Proxy from HTTP_PROXY: {http_proxy}")
        return http_proxy
    
    logger.info("No proxy configured, using direct connection")
    return None

# --- DATABASE ---
DB_PATH = Path(__file__).parent / "civis_data.db"

def init_db():
    """Initialize database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_user_id TEXT,
                tg_username TEXT,
                text TEXT,
                selected_values TEXT,
                role TEXT,
                format TEXT,
                created_at TEXT
            )
        """)
        conn.commit()
        conn.close()
        logger.info("Database initialized")
        return True
    except Exception as e:
        logger.error(f"Database init error: {e}")
        return False

def save_profile(tg_user_id, tg_username, text, values, role, format):
    """Save profile to database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO profiles (tg_user_id, tg_username, text, selected_values, role, format, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (tg_user_id, tg_username, text, values, role, format, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Profile save error: {e}")
        return False

# --- INIT ---
if not init_db():
    logger.error("Failed to initialize database. Bot will not start.")
    sys.exit(1)

# --- FORM STATES ---
class Form(StatesGroup):
    text = State()
    values = State()
    role = State()
    format = State()

# --- KEYBOARDS ---
values_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Honesty"), KeyboardButton(text="Expertise")],
        [KeyboardButton(text="Initiative"), KeyboardButton(text="Reliability")],
        [KeyboardButton(text="Speed"), KeyboardButton(text="Empathy")],
        [KeyboardButton(text="Systematic"), KeyboardButton(text="Creativity")],
        [KeyboardButton(text="Openness"), KeyboardButton(text="Ambition")]
    ],
    resize_keyboard=True
)

role_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Executor")],
        [KeyboardButton(text="Customer")],
        [KeyboardButton(text="Coordinator")],
        [KeyboardButton(text="Investor")]
    ],
    resize_keyboard=True
)

format_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Text"), KeyboardButton(text="Voice")],
        [KeyboardButton(text="Video"), KeyboardButton(text="Any")]
    ],
    resize_keyboard=True
)

# --- CREATE BOT INSIDE MAIN ---
async def create_bot_with_proxy():
    """Create bot with proxy if configured"""
    proxy_url = get_proxy_url()
    
    if proxy_url:
        from aiohttp_socks import ProxyConnector
        connector = ProxyConnector.from_url(proxy_url)
        aiohttp_session = aiohttp.ClientSession(connector=connector)
        aiogram_session = AiohttpSession(session=aiohttp_session)
        return Bot(token=TOKEN, session=aiogram_session)
    else:
        return Bot(token=TOKEN)

# --- MAIN ---
async def main():
    """Main function"""
    logger.info("Starting Civis main bot...")
    logger.info(f"Token: {TOKEN[:10]}...{TOKEN[-5:]}")
    
    # Create bot inside event loop
    bot = await create_bot_with_proxy()
    dp = Dispatcher()
    
    # Register handlers
    dp.message.register(start, Command("start"))
    dp.message.register(process_text, Form.text)
    dp.message.register(process_values, Form.values)
    dp.message.register(process_role, Form.role)
    dp.message.register(process_format, Form.format)
    
    try:
        # Check connection
        logger.info("Checking connection to Telegram API...")
        me = await bot.me()
        logger.info(f"Connected: @{me.username} ({me.full_name})")
        
        # Start polling
        logger.info("Starting polling...")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Critical error: {e}")
        
        # Diagnostics
        logger.error("Diagnostics:")
        logger.error(f"  - Python: {sys.version}")
        logger.error(f"  - Token: {TOKEN[:10]}...{TOKEN[-5:]}")
        
        # DNS check
        try:
            import socket
            socket.gethostbyname("api.telegram.org")
            logger.error("  DNS: api.telegram.org resolves")
        except Exception as dns_err:
            logger.error(f"  DNS error: {dns_err}")
        
        # Proxy check
        proxy_url = get_proxy_url()
        if proxy_url:
            logger.error(f"  Proxy configured: {proxy_url}")
        else:
            logger.error("  Proxy not configured")
        
        sys.exit(1)

# --- HANDLERS ---
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    """Handler for /start command"""
    logger.info(f"/start from {message.from_user.id}")
    await state.set_state(Form.text)
    await message.answer(
        "Hello! You are joining Civis - the republic of professionals.\n\n"
        "Tell about yourself and your professional goals.\n"
        "Minimum 300 characters. This will help us understand your profile.",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(Form.text)
async def process_text(message: types.Message, state: FSMContext):
    """Process text from form"""
    logger.info(f"Text received from {message.from_user.id}, length: {len(message.text)}")
    if len(message.text) < 300:
        await message.answer("Please write at least 300 characters. This is important for analysis.")
        return
    await state.update_data(text=message.text)
    await state.set_state(Form.values)
    await message.answer(
        "Select 3 key values that you share in your work:",
        reply_markup=values_keyboard
    )

@dp.message(Form.values)
async def process_values(message: types.Message, state: FSMContext):
    """Process values selection"""
    logger.info(f"Values from {message.from_user.id}: {message.text}")
    await state.update_data(values=message.text)
    await state.set_state(Form.role)
    await message.answer(
        "What is your main role?",
        reply_markup=role_keyboard
    )

@dp.message(Form.role)
async def process_role(message: types.Message, state: FSMContext):
    """Process role selection"""
    logger.info(f"Role from {message.from_user.id}: {message.text}")
    await state.update_data(role=message.text)
    await state.set_state(Form.format)
    await message.answer(
        "Which communication format is convenient for you?",
        reply_markup=format_keyboard
    )

@dp.message(Form.format)
async def process_format(message: types.Message, state: FSMContext):
    """Process format selection"""
    logger.info(f"Format from {message.from_user.id}: {message.text}")
    await state.update_data(format=message.text)
    data = await state.get_data()

    # Save to database
    success = save_profile(
        tg_user_id=str(message.from_user.id),
        tg_username=message.from_user.username or "unknown",
        text=data.get('text', ''),
        values=data.get('values', ''),
        role=data.get('role', ''),
        format=data.get('format', '')
    )

    if success:
        await message.answer(
            "You are in Civis!\n\n"
            "Your profile is saved. Soon we will start matching you with projects and teams.\n"
            "Stay tuned.",
            reply_markup=ReplyKeyboardRemove()
        )
        logger.info(f"Profile saved for {message.from_user.id}")
    else:
        await message.answer(
            "Profile save error. Try again later or use /start.",
            reply_markup=ReplyKeyboardRemove()
        )
        logger.error(f"Profile save failed for {message.from_user.id}")

    await state.clear()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        sys.exit(1)
