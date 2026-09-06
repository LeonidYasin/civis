#!/usr/bin/env python3
"""
Minimal bot for connection testing.
Uses standard Bot without custom session - proxy via env vars.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv

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

# --- PROXY CHECK (from env vars) ---
http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
if http_proxy or https_proxy:
    logger.info(f"Proxy from env: {https_proxy or http_proxy}")
else:
    logger.info("No proxy configured, using direct connection")

# --- BOT INIT (standard, no custom session) ---
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- HANDLERS ---
async def cmd_start(message: Message):
    logger.info(f"Received /start from {message.from_user.id}")
    await message.answer(
        "Hello! I am a minimal test bot for Civis.\n"
        "If you see this - connection to Telegram API works!\n\n"
        "Commands: /ping, /echo <text>, /info"
    )

async def cmd_ping(message: Message):
    logger.info(f"Received /ping from {message.from_user.id}")
    start_time = datetime.now()
    await message.answer("Pong!")
    end_time = datetime.now()
    latency = (end_time - start_time).total_seconds() * 1000
    await message.answer(f"Latency: {latency:.0f} ms")

async def cmd_echo(message: Message):
    logger.info(f"Received /echo from {message.from_user.id}")
    text = message.text.replace("/echo", "", 1).strip()
    if text:
        await message.answer(f"Echo: {text}")
    else:
        await message.answer("Please write something after /echo")

async def cmd_info(message: Message):
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
        logger.error(f"Error: {e}")
        await message.answer(f"Error: {e}")

async def handle_unknown(message: Message):
    logger.info(f"Unknown message from {message.from_user.id}")
    await message.answer("Unknown command. Use /start for commands.")

# --- MAIN ---
async def main():
    logger.info("Starting minimal bot...")
    
    # Register handlers
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_ping, Command("ping"))
    dp.message.register(cmd_echo, Command("echo"))
    dp.message.register(cmd_info, Command("info"))
    dp.message.register(handle_unknown)
    
    try:
        logger.info("Checking connection to Telegram API...")
        me = await bot.me()
        logger.info(f"Connected! Bot: @{me.username} ({me.full_name}), ID: {me.id}")
        
        logger.info("Starting polling...")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Critical error: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        
        # Diagnostics
        logger.error("Diagnostics:")
        logger.error(f"  - Python: {sys.version}")
        logger.error(f"  - Token: {TOKEN[:10]}...{TOKEN[-5:]}")
        
        # DNS
        try:
            import socket
            socket.gethostbyname("api.telegram.org")
            logger.info("  DNS resolves: api.telegram.org")
        except Exception as dns_err:
            logger.error(f"  DNS error: {dns_err}")
        
        # Proxy
        http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
        if http_proxy:
            logger.error(f"  Proxy from env: {http_proxy}")
        else:
            logger.error("  Proxy not configured in env")
        
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        sys.exit(1)
