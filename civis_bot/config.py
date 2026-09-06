#!/usr/bin/env python3
"""
Configuration module for Civis bot.
Loads environment variables and sets up proxy.
"""

import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN not found in .env file!")

# Admin chat ID for support messages
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
if not ADMIN_CHAT_ID:
    logger.warning("ADMIN_CHAT_ID not set in .env. Support messages will be logged only.")
else:
    logger.info(f"Admin chat ID: {ADMIN_CHAT_ID}")

def get_proxy_url():
    """Get proxy URL from .env or environment variables"""
    proxy_url = os.getenv("PROXY_URL")
    if proxy_url:
        logger.info(f"Using proxy from .env: {proxy_url}")
        return proxy_url
    
    http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
    https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
    
    if https_proxy:
        logger.info(f"Using proxy from HTTPS_PROXY: {https_proxy}")
        return https_proxy
    elif http_proxy:
        logger.info(f"Using proxy from HTTP_PROXY: {http_proxy}")
        return http_proxy
    
    logger.info("No proxy configured, using direct connection")
    return None
