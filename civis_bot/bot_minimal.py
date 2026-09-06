#!/usr/bin/env python3
"""
Minimal bot for connection testing with proxy support from .env
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv

# Proxy support
import aiohttp
from aiogram.client.session.aiohttp import AiohttpSession
from aiohttp_socks import ProxyConnector

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
def get_proxy_connector():
    """Create proxy connector from .env or environment variables"""
    # First check .env
    proxy_url = os.getenv("PROXY_URL")
    if proxy_url:
        logger.info(f"Proxy from .env: {proxy_url}")
        return ProxyConnector.from_url(proxy_url)
    
    # Then check system env
    http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
    https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
    
    if https_proxy:
        logger.info(f"Proxy from HTTPS_PROXY: {https_proxy}")
        return ProxyConnector.from_url(https_proxy)
    elif http_proxy:
        logger.info(f"Proxy from HTTP_PROXY: {http_proxy}")
        return ProxyConnector.from_url(http_proxy)
    
    logger.info("No proxy configured, using direct connection")
    return None

# --- CREATE SESSION ---
def create_bot_session():
    """Create bot with proxy support if configured"""
    connector = get_proxy_connector()
    if connector:
        # Create aiohttp session with proxy
        aiohttp_session = aiohttp.ClientSession(connector=connector)
        aiogram_session = AiohttpSession(session=aiohttp_session)
        return aiogram_session
    else:
        # Use default session
        return None

# --- BOT INIT ---
session = create_bot_session()
if session:
    bot = Bot(token=TOKEN, session=session)
else:
    bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- HANDLERS ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Handler for /start command"""
    logger.info(f"Received /start from {message.from_user.id}")
    await message.answer(
        "Hello! I am a minimal test bot for Civis.\n"
        "If you see this - connection to Telegram API works!\n\n"
        "Available commands:\n"
        "/ping - check connection\n"
        "/echo <text> - echo your message\n"
        "/info - bot information"
    )

@dp.message(Command("ping"))
async def cmd_ping(message: Message):
    """Check connection"""
    logger.info(f"Received /ping from {message.from_user.id}")
    start_time = datetime.now()
    await message.answer("Pong!")
    end_time = datetime.now()
    latency = (end_time - start_time).total_seconds() * 1000
    await message.answer(f"Latency: {latency:.0f} ms")

@dp.message(Command("echo"))
async def cmd_echo(message: Message):
    """Echo user text"""
    logger.info(f"Received /echo from {message.from_user.id}")
    text = message.text.replace("/echo", "", 1).strip()
    if text:
        await message.answer(f"Echo: {text}")
    else:
        await message.answer("Please write something after /echo")

@dp.message(Command("info"))
async def cmd_info(message: Message):
    """Bot information"""
    logger.info(f"Received /info from {message.from_user.id}")
    try:
        me = await bot.me()
        await message.answer(
            f"Bot info:\n"
            f"Name: {me.full_name}\n"
            f"Username: @{me.username}\n"
            f"ID: {me.id}\n"
            f"Token: {TOKEN[:10]}...{TOKEN[-5:]}"
        )
    except Exception as e:
        logger.error(f"Error getting bot info: {e}")
        await message.answer(f"Error: {e}")

@dp.message()
async def handle_unknown(message: Message):
    """Unknown message handler"""
    logger.info(f"Unknown message from {message.from_user.id}: {message.text}")
    await message.answer(
        "Unknown command. Use /start for command list."
    )

# --- MAIN ---
async def main():
    """Main function"""
    logger.info("Starting minimal bot...")
    
    try:
        # Check connection to Telegram
        logger.info("Checking connection to Telegram API...")
        me = await bot.me()
        logger.info(f"Connected to Telegram API!")
        logger.info(f"Bot name: {me.full_name}")
        logger.info(f"Username: @{me.username}")
        logger.info(f"ID: {me.id}")
        
        # Start polling
        logger.info("Starting polling...")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Critical error: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        
        # Diagnostics
        logger.error("Diagnostics:")
        logger.error(f"  - Python version: {sys.version}")
        logger.error(f"  - Token: {TOKEN[:10]}...{TOKEN[-5:]}")
        
        # DNS check
        try:
            import socket
            socket.gethostbyname("api.telegram.org")
            logger.info("  DNS resolves: api.telegram.org")
        except Exception as dns_err:
            logger.error(f"  DNS error: {dns_err}")
        
        # Proxy check
        proxy_url = os.getenv("PROXY_URL")
        if proxy_url:
            logger.error(f"  Proxy configured in .env: {proxy_url}")
        else:
            logger.error("  Proxy not configured in .env")
        
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        sys.exit(1)
