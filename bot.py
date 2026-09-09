#!/usr/bin/env python3
"""Main entry point for Civis Telegram bot.

Supports:
- Original Civis functionality (people matching)
- Coach Bot module (goal-setting and personal development)
"""

import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Import modules
from modules.coach_bot.handler import CoachBotHandler

class CivisBot:
    """Main bot class."""
    
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set in environment")
        
        self.coach_handler = CoachBotHandler()
        self.application = None
    
    def setup(self):
        """Set up the application with handlers."""
        self.application = Application.builder().token(self.token).build()
        
        # === Coach Bot handlers ===
        # Commands
        self.application.add_handler(CommandHandler("start", self.coach_handler.handle_message))
        self.application.add_handler(CommandHandler("help", self.coach_handler.handle_message))
        self.application.add_handler(CommandHandler("model", self.coach_handler.handle_message))
        self.application.add_handler(CommandHandler("setkey", self.coach_handler.handle_message))
        self.application.add_handler(CommandHandler("checkin", self.coach_handler.handle_message))
        self.application.add_handler(CommandHandler("status", self.coach_handler.handle_message))
        
        # Message handler — catch all text messages
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.coach_handler.handle_message)
        )
        
        # Callback queries (inline keyboards)
        self.application.add_handler(
            CallbackQueryHandler(self.coach_handler.handle_callback)
        )
        
        # === TODO: Add original Civis handlers here ===
        # self.application.add_handler(CommandHandler("profile", ...))
        # self.application.add_handler(CommandHandler("search", ...))
        # self.application.add_handler(CommandHandler("match", ...))
        
        logger.info("Bot handlers configured")
    
    def run(self):
        """Run the bot."""
        if not self.application:
            self.setup()
        
        logger.info("Starting bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Main entry point."""
    try:
        bot = CivisBot()
        bot.setup()
        bot.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
