"""
Stage management for Coach Bot
Handles the conversation flow: welcome → reflection → planning → tracking
"""

import logging
from datetime import datetime, date
from typing import Dict, Any, Optional, Tuple

from .db import CoachDB
from .prompts import get_prompt
from .model_router import ModelRouter, ModelResponse

logger = logging.getLogger(__name__)


class StageRouter:
    """Routes user messages to appropriate stage logic"""
    
    def __init__(self):
        self.db = CoachDB()
        self.model_router = ModelRouter()
    
    async def route(
        self,
        user_id: int,
        text: str,
        stage: str,
        status: str,
    ) -> Tuple[str, str]:
        """
        Route a message to the appropriate stage handler.
        Returns (response_text, new_stage)
        """
        # Check if user should be in paywall stage
        if status in ['free', 'trial'] and stage not in ['welcome', 'paywall']:
            # Check if trial is active
            user_status = self.db.get_user_status(user_id)
            if not user_status.get('is_trial_active') and status == 'trial':
                return await self._handle_paywall(user_id, text), 'paywall'
            if user_status.get('today_messages', 0) >= user_status.get('free_limit', 5):
                return await self._handle_paywall(user_id, text), 'paywall'
        
        # Route to appropriate stage
        if stage == 'welcome':
            return await self._handle_welcome(user_id, text)
        elif stage == 'reflection':
            return await self._handle_reflection(user_id, text)
        elif stage == 'planning':
            return await self._handle_planning(user_id, text)
        elif stage == 'tracking':
            return await self._handle_tracking(user_id, text)
        elif stage == 'paywall':
            return await self._handle_paywall(user_id, text), 'paywall'
        else:
            return await self._handle_welcome(user_id, text)
    
    async def _handle_welcome(self, user_id: int, text: str) -> Tuple[str, str]:
        """Welcome stage: initial contact"""
        # Get user context
        recent = self.db.get_recent_messages(user_id, 3)
        
        # Build prompt
        if not recent or len(recent) <= 1:
            # First message
            prompt = """Это первый диалог с пользователем. 
Он только что написал: "{}"

Поприветствуй его, создай безопасную атмосферу, задай простой вопрос о том, что его волнует.
"""
        else:
            prompt = f"""Продолжи диалог с пользователем.
Предыдущие сообщения: {recent}

Пользователь написал: "{text}"

Продолжи разговор. Задай уточняющий вопрос или отрефлексируй то, что он сказал.
"""
        
        system = get_prompt('welcome')
        response = await self.model_router.generate(prompt.format(text), system)
        
        # Determine if we should move to reflection
        # After 3-5 exchanges, suggest moving deeper
        msg_count = len(recent)
        if msg_count > 4:
            new_stage = 'reflection'
            response.text += "\n\n💡 Мне кажется, мы уже достаточно разогрелись. Хочешь копнуть глубже и разобраться, что на самом деле стоит за этим?"
        else:
            new_stage = 'welcome'
        
        return response.text, new_stage
    
    async def _handle_reflection(self, user_id: int, text: str) -> Tuple[str, str]:
        """Reflection stage: deep self-discovery"""
        recent = self.db.get_recent_messages(user_id, 10)
        goals = self.db.get_active_goals(user_id)
        
        prompt = f"""Ты помогаешь пользователю глубже понять себя.

История диалога (последние сообщения): {recent}

Текущие цели пользователя: {goals if goals else 'пока не сформулированы'}

Пользователь написал: "{text}"

Твоя задача:
1. Отрази то, что он сказал, своими словами
2. Заметь паттерн или противоречие, если видишь
3. Задай один глубокий вопрос, который поможет ему увидеть новое
4. Не давай советов — помогай ему найти свой ответ

Будь внимателен, но мягок. Используй то, что он уже рассказывал."""
        
        system = get_prompt('reflection')
        response = await self.model_router.generate(prompt, system)
        
        # Check if we have enough insight to move to planning
        # Simple heuristic: if user has talked about goals or desires
        goal_keywords = ['хочу', 'мечта', 'цель', 'желаю', 'планирую', 'хотел бы']
        if any(kw in text.lower() for kw in goal_keywords) and len(recent) > 6:
            new_stage = 'planning'
            response.text += "\n\n🎯 Я вижу, у тебя уже есть образ желаемого. Хочешь превратить это в конкретный план?"
        else:
            new_stage = 'reflection'
        
        # Save any goals mentioned
        if any(kw in text.lower() for kw in goal_keywords):
            # Try to extract goal from text (simple approach)
            goal_text = text[:200]
            self.db.add_goal(user_id, goal_text)
        
        return response.text, new_stage
    
    async def _handle_planning(self, user_id: int, text: str) -> Tuple[str, str]:
        """Planning stage: turn insights into actionable goals"""
        recent = self.db.get_recent_messages(user_id, 10)
        goals = self.db.get_active_goals(user_id)
        
        prompt = f"""Ты помогаешь пользователю превратить его желания в конкретные, достижимые цели.

История диалога: {recent}

Цели, которые уже сформулированы: {goals if goals else 'пока нет'}

Пользователь написал: "{text}"

Твоя задача:
1. Помоги сформулировать цель чётко и измеримо
2. Разбей её на шаги (если цель уже есть)
3. Предложи сроки и способ трекинга
4. Спроси, что может помешать — и как это преодолеть

Будь практичным и поддерживающим."""
        
        system = get_prompt('planning')
        response = await self.model_router.generate(prompt, system)
        
        # Check if we should move to tracking
        if len(goals) > 0:
            # Check if user seems ready to start
            ready_keywords = ['готов', 'начинаю', 'сделаю', 'план', 'шаги']
            if any(kw in text.lower() for kw in ready_keywords):
                new_stage = 'tracking'
                response.text += "\n\n📅 Отлично! У тебя есть план. Я буду проверять твой прогресс каждый день. Начнём?"
            else:
                new_stage = 'planning'
        else:
            new_stage = 'planning'
        
        return response.text, new_stage
    
    async def _handle_tracking(self, user_id: int, text: str) -> Tuple[str, str]:
        """Tracking stage: daily check-ins and progress monitoring"""
        goals = self.db.get_active_goals(user_id)
        today_checkin = self.db.get_today_checkin(user_id)
        
        # Check if this is a check-in request
        if not today_checkin:
            # First check-in of the day
            prompt = f"""Ты помогаешь пользователю отслеживать прогресс.

Его цели: {goals if goals else 'ещё не сформулированы'}

Это первая проверка за сегодня. Пользователь написал: "{text}"

Проверь:
1. Как прошёл день?
2. Что получилось?
3. Что было сложно?
4. Что в плане на завтра?

Будь поддерживающим, но не дави."""
            system = get_prompt('tracking')
            response = await self.model_router.generate(prompt, system)
            
            # Save check-in
            self.db.save_checkin(user_id, progress=text[:500])
        else:
            # Follow-up check-in
            prompt = f"""Пользователь уже делал сегодня чекин: {today_checkin}
Теперь он пишет: "{text}"

Его цели: {goals if goals else 'не сформулированы'}

Отреагируй на его прогресс. Отметь, что получилось хорошо. Если есть трудности — помоги найти решение.
"""
            system = get_prompt('tracking')
            response = await self.model_router.generate(prompt, system)
        
        # Stay in tracking
        return response.text, 'tracking'
    
    async def _handle_paywall(self, user_id: int, text: str) -> str:
        """Paywall stage: show subscription options"""
        system = get_prompt('paywall')
        
        prompt = f"""Пользователь хочет продолжить, но его бесплатный лимит исчерпан.

Что он может получить:
- Безлимитные диалоги со всеми моделями (DeepSeek, GPT, Claude)
- Ежедневные чекины и напоминания
- Глубокий анализ целей и прогресса
- Приоритетный матчинг и эмбеддинги

Предложи ему выбор:
1. Попробовать 3 дня бесплатно
2. Купить подписку за 999 ₽/мес
3. Ввести свой API ключ (BYOK)

Не дави, предложи уважительно."""
        
        response = await self.model_router.generate(prompt, system)
        return response.text
