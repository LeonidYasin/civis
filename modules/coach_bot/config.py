"""
Coach Bot Configuration
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class CoachConfig:
    """Configuration for coach bot"""
    
    # Model settings
    default_model: str = "deepseek"  # deepseek | openai | claude
    deepseek_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    # Default DeepSeek key (free tier)
    default_deepseek_key: str = os.environ.get("DEEPSEEK_API_KEY", "")
    
    # Payment settings
    yookassa_shop_id: Optional[str] = None
    yookassa_secret_key: Optional[str] = None
    stripe_secret_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    
    # Pricing
    subscription_price_rub: int = 999
    subscription_price_usd: int = 15
    trial_days: int = 3
    
    # Free tier limits
    free_messages_per_day: int = 5
    
    @classmethod
    def from_env(cls) -> "CoachConfig":
        """Create config from environment variables"""
        return cls(
            default_model=os.environ.get("COACH_DEFAULT_MODEL", "deepseek"),
            deepseek_api_key=os.environ.get("DEEPSEEK_API_KEY"),
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
            yookassa_shop_id=os.environ.get("YOOKASSA_SHOP_ID"),
            yookassa_secret_key=os.environ.get("YOOKASSA_SECRET_KEY"),
            stripe_secret_key=os.environ.get("STRIPE_SECRET_KEY"),
            stripe_webhook_secret=os.environ.get("STRIPE_WEBHOOK_SECRET"),
            subscription_price_rub=int(os.environ.get("COACH_PRICE_RUB", 999)),
            subscription_price_usd=int(os.environ.get("COACH_PRICE_USD", 15)),
            trial_days=int(os.environ.get("COACH_TRIAL_DAYS", 3)),
            free_messages_per_day=int(os.environ.get("COACH_FREE_MESSAGES", 5)),
        )


# Global config instance
config = CoachConfig.from_env()
