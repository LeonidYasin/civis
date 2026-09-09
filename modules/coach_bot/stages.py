"""
Coach Bot Stage Logic
Handles different stages: welcome → reflection → planning → tracking
"""

import logging
from typing import Dict, Any, List
from .db import CoachDB
from .prompts import get_prompt_for_stage
from .model_router import ModelRouter, ModelResponse

logger = logging.getLogger(__name__)


class StageRouter:
    """Route messages based on user stage"""
    
    def __init__(self):
        self.db = CoachDB()
        self.model_router = ModelRouter()
    
    async def route(
        self,
        user_id: int,
        message: str,
        stage: str,
        status: str,
        model_preference: str = "deepseek",
        user_api_key: str = None,
    ) -> str:
        """
        Route a message to the appropriate stage handler
        
        Returns:
            Response text to send to user
        """
        logger.info(f"Routing message for user {user_id}, stage: {stage}, status: {status}")
        
        # Check if user has reached message limit on free tier
        if status == "free" and stage != "welcome":
            status_info = self.db.get_user_status(user_id)
            if not status_info.get("can_message", True):
                return self._get_paywall_message()
        
        # Handle stage-specific logic
        if stage == "welcome":
            return await self._handle_welcome(user_id, message)
        elif stage == "reflection":
            return await self._handle_reflection(user_id, message, model_preference, user_api_key)
        elif stage == "planning":
            return await self._handle_planning(user_id, message, model_preference, user_api_key)
        elif stage == "tracking":
            return await self._handle_tracking(user_id, message, model_preference, user_api_key)
        elif stage == "payment":
            return self._get_paywall_message()
        else:
            return self._get_fallback_response()
    
    async def _handle_welcome(self, user_id: int, message: str) -> str:
        """Handle welcome stage - first contact"""
        # Save user message
        self.db.save_message(user_id, "user", message)
        
        # Get recent context
        history = self.db.get_recent_messages(user_id, 10)
        
        # Build messages for model
        messages = [
            {"role": "system", "content": get_prompt_for_stage("welcome")},
        ]
        
        # Add history
        for h in history:
            messages.append({"role": h["role"], "content": h["content"]})
        
        # Add current message if not already in history
        if not history or history[-1]["content"] != message:
            messages.append({"role": "user", "content": message})
        
        # Get response
        response = self.model_router.call(messages, model="deepseek")
        
        # Save response
        self.db.save_message(user_id, "assistant", response.content)
        
        # Check if should move to reflection stage
        # After a few exchanges, move to reflection
        message_count = len([m for m in history if m["role"] == "user"]) + 1
        if message_count >= 3:
            self.db.update_user_stage(user_id, "reflection")
        
        return response.content
    
    async def _handle_reflection(
        self,
        user_id: int,
        message: str,
        model: str,
        user_api_key: str = None,
    ) -> str:
        """Handle reflection stage - deep self-understanding"""
        # Save user message
        self.db.save_message(user_id, "user", message)
        
        # Get recent context
        history = self.db.get_recent_messages(user_id, 30)
        
        # Build messages for model
        messages = [
            {"role": "system", "content": get_prompt_for_stage("reflection")},
        ]
        
        for h in history:
            messages.append({"role": h["role"], "content": h["content"]})
        
        if not history or history[-1]["content"] != message:
            messages.append({"role": "user", "content": message})
        
        # Get response
        response = self.model_router.call(
            messages,
            model=model,
            user_api_key=user_api_key,
            temperature=0.8,
        )
        
        # Save response
        self.db.save_message(user_id, "assistant", response.content)
        
        # Check if should move to planning stage
        # Look for signs of clarity: user mentions "I realize", "I want", "my goal"
        clarity_indicators = ["я понял", "я хочу", "моя цель", "я решил", "теперь я вижу"]
        has_clarity = any(indicator in message.lower() for indicator in clarity_indicators)
        
        message_count = len([m for m in history if m["role"] == "user"]) + 1
        if has_clarity and message_count >= 5:
            self.db.update_user_stage(user_id, "planning")
        
        return response.content
    
    async def _handle_planning(
        self,
        user_id: int,
        message: str,
        model: str,
        user_api_key: str = None,
    ) -> str:
        """Handle planning stage - goal setting and action plan"""
        # Save user message
        self.db.save_message(user_id, "user", message)
        
        # Get recent context
        history = self.db.get_recent_messages(user_id, 30)
        
        # Build messages
        messages = [
            {"role": "system", "content": get_prompt_for_stage("planning")},
        ]
        
        for h in history:
            messages.append({"role": h["role"], "content": h["content"]})
        
        if not history or history[-1]["content"] != message:
            messages.append({"role": "user", "content": message})
        
        # Get response
        response = self.model_router.call(
            messages,
            model=model,
            user_api_key=user_api_key,
            temperature=0.7,
        )
        
        # Save response
        self.db.save_message(user_id, "assistant", response.content)
        
        # Extract goals from messages if possible
        self._extract_goals(user_id, message)
        
        # Check if should move to tracking stage
        # After plan is created, move to tracking
        message_count = len([m for m in history if m["role"] == "user"]) + 1
        if message_count >= 3:
            self.db.update_user_stage(user_id, "tracking")
        
        return response.content
    
    async def _handle_tracking(
        self,
        user_id: int,
        message: str,
        model: str,
        user_api_key: str = None,
    ) -> str:
        """Handle tracking stage - daily check-ins and progress"""
        # Save user message
        self.db.save_message(user_id, "user", message)
        
        # Get recent context
        history = self.db.get_recent_messages(user_id, 30)
        
        # Build messages
        messages = [
            {"role": "system", "content": get_prompt_for_stage("tracking")},
        ]
        
        for h in history:
            messages.append({"role": h["role"], "content": h["content"]})
        
        if not history or history[-1]["content"] != message:
            messages.append({"role": "user", "content": message})
        
        # Get response
        response = self.model_router.call(
            messages,
            model=model,
            user_api_key=user_api_key,
            temperature=0.7,
        )
        
        # Save response
        self.db.save_message(user_id, "assistant", response.content)
        
        return response.content
    
    def _extract_goals(self, user_id: int, message: str):
        """Extract goals from user messages"""
        # Simple extraction for now
        # In production, use LLM to extract goals
        goal_keywords = ["хочу", "моя цель", "цель", "добиться", "достичь"]
        for keyword in goal_keywords:
            if keyword in message.lower():
                # Extract sentence or phrase after keyword
                parts = message.lower().split(keyword, 1)
                if len(parts) > 1:
                    goal_text = parts[1].strip()[:200]
                    if goal_text:
                        self.db.add_goal(user_id, goal_text)
                        logger.info(f"Extracted goal for user {user_id}: {goal_text[:50]}...")
                        break
    
    def _get_paywall_message(self) -> str:
        """Get paywall message"""
        return """🔥 Ты уже прошёл бесплатный этап. Теперь — самое интересное.

Что ты получишь, если продолжишь:
✅ Ежедневные чекины — не дадим сбиться с пути
✅ Глубокий анализ твоих целей и прогресса
✅ Персонализированный план действий
✅ Поддержку 24/7 — я всегда рядом
✅ Доступ ко всем моделям ИИ (DeepSeek, GPT, Claude)

Попробуй 3 дня бесплатно — или оформи подписку сразу.

👇 Нажми кнопку ниже, чтобы начать трансформацию."""
    
    def _get_fallback_response(self) -> str:
        """Get fallback response"""
        return "Извини, я немного запутался. Давай начнём сначала. Расскажи, что тебя беспокоит или что ты хочешь изменить в жизни?"
