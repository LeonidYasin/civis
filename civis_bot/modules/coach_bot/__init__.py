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
from .models import (
    CoachUser, CoachGoal, CoachCheckin,
    CoachMessage, CoachPayment, CoachInsight,
    Base
)
from .stages import StageRouter, StageManager
from .prompts import get_prompt, STAGE_PROMPTS
from .model_router import ModelRouter, DeepSeekProvider, OpenAIProvider, ClaudeProvider

__all__ = [
    "CoachBotHandler",
    "StageRouter",
    "StageManager",
    "get_prompt",
    "STAGE_PROMPTS",
    "ModelRouter",
    "DeepSeekProvider",
    "OpenAIProvider",
    "ClaudeProvider",
    "CoachUser",
    "CoachGoal",
    "CoachCheckin",
    "CoachMessage",
    "CoachPayment",
    "CoachInsight",
    "Base",
]
