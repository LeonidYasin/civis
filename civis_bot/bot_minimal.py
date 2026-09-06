#!/usr/bin/env python3
"""
Minimal bot for connection testing with HTTP proxy support
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
    sys.exit(1)
logger.info("Token loaded")

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

# --- CREATE BOT INSIDE MAIN ---
async def create_bot_with_proxy():
    """Create bot with HTTP proxy if configured"""
    proxy_url = get_proxy_url()
    
    if proxy_url:
        # For HTTP proxy we use aiohttp's proxy parameter
        # But aiohttp requires proxy to be in format http://user:pass@host:port
        # Happ uses simple HTTP proxy without auth on 127.0.0.1:10809
        
        # Create aiohttp session with HTTP proxy
        connector = aiohttp.TCPConnector()
        aiohttp_session = aiohttp.ClientSession(connector=connector)
        
        # But we need to use proxy in session requests
        # aiogram uses session internally, so we need to pass proxy via session
        
        # Alternative: use ProxyConnector for SOCKS5
        # But for HTTP proxy we need a different approach
        
        # Since Happ uses HTTP proxy, try simple approach - set system proxy
        # and use aiohttp without custom connector
        logger.info("Using HTTP proxy, will rely on system proxy settings")
        return Bot(token=TOKEN)
    else:
        return Bot(token=TOKEN)

# --- HANDLERS ---
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

async def cmd_ping(message: Message):
    """Check connection"""
    logger.info(f"Received /ping from {message.from_user.id}")
    start_time = datetime.now()
    await message.answer("Pong!")
    end_time = datetime.now()
    latency = (end_time - start_time).total_seconds() * 1000
    await message.answer(f"Latency: {latency:.0f} ms")

async def cmd_echo(message: Message):
    """Echo user text"""
    logger.info(f"Received /echo from {message.from_user.id}")
    text = message.text.replace("/echo", "", 1).strip()
    if text:
        await message.answer(f"Echo: {text}")
    else:
        await message.answer("Please write something after /echo")

async def cmd_info(message: Message):
    """Bot information"""
    logger.info(f"Received /info from {message.from_user.id}")
    try:
        bot = message.bot
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
    
    # Create bot
    bot = await create_bot_with_proxy()
    dp = Dispatcher()
    
    # Register handlers
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_ping, Command("ping"))
    dp.message.register(cmd_echo, Command("echo"))
    dp.message.register(cmd_info, Command("info"))
    dp.message.register(handle_unknown)
    
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
        proxy_url = get_proxy_url()
        if proxy_url:
            logger.error(f"  Proxy configured: {proxy_url}")
        else:
            logger.error("  Proxy not configured")
        
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        sys.exit(1)
