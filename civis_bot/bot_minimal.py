#!/usr/bin/env python3
"""
Minimal bot version for connection testing.
Redirects all output to file to avoid Windows console encoding issues.
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

# --- LOGGING TO FILE (bypass Windows console) ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_minimal.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# --- LOAD ENV ---
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    print("ERROR: BOT_TOKEN not found in .env file!")
    sys.exit(1)
print("Token loaded")

# --- BOT INIT ---
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- HANDLERS ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    print(f"[INFO] Received /start from {message.from_user.id}")
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
    print(f"[INFO] Received /ping from {message.from_user.id}")
    start_time = datetime.now()
    await message.answer("Pong!")
    end_time = datetime.now()
    latency = (end_time - start_time).total_seconds() * 1000
    await message.answer(f"Latency: {latency:.0f} ms")

@dp.message(Command("echo"))
async def cmd_echo(message: Message):
    print(f"[INFO] Received /echo from {message.from_user.id}")
    text = message.text.replace("/echo", "", 1).strip()
    if text:
        await message.answer(f"Echo: {text}")
    else:
        await message.answer("Please write something after /echo")

@dp.message(Command("info"))
async def cmd_info(message: Message):
    print(f"[INFO] Received /info from {message.from_user.id}")
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
        print(f"[ERROR] Error getting bot info: {e}")
        await message.answer(f"Error: {e}")

@dp.message()
async def handle_unknown(message: Message):
    print(f"[INFO] Unknown message from {message.from_user.id}: {message.text}")
    await message.answer(
        "Unknown command. Use /start for command list."
    )

# --- MAIN ---
async def main():
    print("[INFO] Starting minimal bot...")
    
    try:
        print("[INFO] Checking connection to Telegram API...")
        me = await bot.me()
        print(f"[INFO] Connected to Telegram API!")
        print(f"[INFO] Bot name: {me.full_name}")
        print(f"[INFO] Username: @{me.username}")
        print(f"[INFO] ID: {me.id}")
        
        print("[INFO] Starting polling...")
        await dp.start_polling(bot)
        
    except Exception as e:
        print(f"[ERROR] Critical error: {e}")
        print(f"[ERROR] Error type: {type(e).__name__}")
        
        print("[INFO] Diagnostics:")
        print(f"  - Python version: {sys.version}")
        print(f"  - Token: {TOKEN[:10]}...{TOKEN[-5:]}")
        
        print("  - Checking network...")
        try:
            import socket
            socket.gethostbyname("api.telegram.org")
            print("  DNS resolves: api.telegram.org")
        except Exception as dns_err:
            print(f"  DNS error: {dns_err}")
        
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[INFO] Bot stopped by user")
    except Exception as e:
        print(f"[ERROR] Unhandled error: {e}")
        sys.exit(1)
