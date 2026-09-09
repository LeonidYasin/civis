"""
Coach Bot Module — AI-коуч для постановки целей и саморазвития.

Основные функции:
- Бесплатный вход (3 дня) для знакомства
- Подписка для полного доступа
- BYOK (Bring Your Own Key) — пользователь может вставить свой API ключ
- Выбор модели: DeepSeek, OpenAI, Claude
- Ежедневные чекины, трекинг целей, рефлексия
"""

from .handler import CoachBotHandler
from .stages import StageRouter
from .db import CoachDB
from .model_router import ModelRouter
from .payments import PaymentProcessor

__all__ = [
    "CoachBotHandler",
    "StageRouter", 
    "CoachDB",
    "ModelRouter",
    "PaymentProcessor",
]
