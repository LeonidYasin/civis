"""
Configuration for Coach Bot module
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class CoachConfig:
    """Configuration class for Coach Bot"""
    
    # Database
    database_url: str = os.getenv('COACH_DATABASE_URL', 'sqlite:///coach_bot.db')
    
    # Models
    default_model: str = os.getenv('COACH_DEFAULT_MODEL', 'deepseek')
    
    # DeepSeek
    deepseek_api_key: Optional[str] = os.getenv('DEEPSEEK_API_KEY')
    deepseek_model: str = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
    
    # OpenAI
    openai_api_key: Optional[str] = os.getenv('OPENAI_API_KEY')
    openai_model: str = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
    
    # Claude
    claude_api_key: Optional[str] = os.getenv('CLAUDE_API_KEY')
    claude_model: str = os.getenv('CLAUDE_MODEL', 'claude-3-haiku-20240307')
    
    # Payments
    yookassa_shop_id: Optional[str] = os.getenv('YOOKASSA_SHOP_ID')
    yookassa_secret_key: Optional[str] = os.getenv('YOOKASSA_SECRET_KEY')
    stripe_api_key: Optional[str] = os.getenv('STRIPE_API_KEY')
    
    # Subscription prices (in RUB)
    subscription_price: int = int(os.getenv('SUBSCRIPTION_PRICE', '999'))
    premium_price: int = int(os.getenv('PREMIUM_PRICE', '2999'))
    
    # Free tier limits
    free_messages_per_day: int = int(os.getenv('FREE_MESSAGES_PER_DAY', '5'))
    trial_days: int = int(os.getenv('TRIAL_DAYS', '3'))
    
    # Telegram
    telegram_token: Optional[str] = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # Logging
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')
    
    # Deployment
    webhook_url: Optional[str] = os.getenv('WEBHOOK_URL')
    webhook_port: int = int(os.getenv('PORT', '8443'))


# Singleton instance
config = CoachConfig()
