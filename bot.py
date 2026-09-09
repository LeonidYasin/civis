"""
Main bot entry point for Civis
Supports multiple modules: matcher, coach_bot, and more
"""

import logging
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from modules.coach_bot.handler import CoachBotHandler

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize handlers
coach_handler = CoachBotHandler()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        "Я — твой личный AI-коуч. Помогаю разобраться в себе, ставить цели и достигать их.\n\n"
        "Просто расскажи, что тебя волнует, и мы начнём."
    )
    
    # Initialize user in database
    user_id = update.effective_user.id
    coach_handler.db.get_or_create_user(user_id)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    await update.message.reply_text(
        "📖 **Доступные команды**\n\n"
        "/start — Начать работу с ботом\n"
        "/help — Показать справку\n"
        "/model — Выбрать модель ИИ\n"
        "/key — Ввести свой API ключ\n"
        "/subscribe — Управление подпиской\n"
        "/status — Проверить статус\n\n"
        "Просто напиши мне сообщение, и я помогу тебе разобраться в твоих желаниях и целях."
    )


def main():
    """Start the bot"""
    # Get token from environment
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set in environment")
        return
    
    # Create application
    application = Application.builder().token(token).build()
    
    # Add command handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('model', coach_handler._handle_model_command))
    application.add_handler(CommandHandler('key', coach_handler._handle_key_command))
    application.add_handler(CommandHandler('subscribe', coach_handler._handle_subscribe_command))
    application.add_handler(CommandHandler('status', coach_handler._handle_status_command))
    
    # Add message handler
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        coach_handler.handle_message
    ))
    
    # Add callback query handler for inline buttons
    application.add_handler(CallbackQueryHandler(coach_handler.handle_message))
    
    # Start the bot
    logger.info("Starting bot...")
    
    # Use webhook or polling
    webhook_url = os.getenv('WEBHOOK_URL')
    if webhook_url:
        # Webhook mode
        port = int(os.getenv('PORT', '8443'))
        application.run_webhook(
            listen='0.0.0.0',
            port=port,
            url_path=token,
            webhook_url=f'{webhook_url}/{token}'
        )
    else:
        # Polling mode (for development)
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
