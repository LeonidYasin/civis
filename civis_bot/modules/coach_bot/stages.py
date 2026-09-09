"""Логика этапов coach_bot"""

import logging
from typing import Dict, Any, List, Optional
from .prompts import get_prompt
from .model_router import ModelRouter

logger = logging.getLogger(__name__)

class StageRouter:
    """Маршрутизация по этапам"""
    
    def __init__(self):
        self.model_router = ModelRouter()
    
    async def route(
        self,
        user_id: int,
        text: str,
        stage: str,
        history: List[Dict[str, str]],
        goals: List[Dict[str, Any]],
        model: str = 'deepseek'
    ) -> Dict[str, Any]:
        """
        Маршрутизация сообщения в зависимости от этапа.
        Возвращает: {"content": str, "new_stage": str, "keyboard": list}
        """
        
        # Получаем системный промпт для этапа
        system_prompt = get_prompt(stage)
        
        # Формируем контекст
        context = self._build_context(stage, history, goals)
        
        # Генерируем ответ
        response = await self.model_router.generate(
            system_prompt=system_prompt,
            context=context,
            user_message=text,
            model=model
        )
        
        # Определяем, нужно ли сменить этап
        new_stage = self._detect_stage_transition(stage, text, response)
        
        return {
            "content": response,
            "new_stage": new_stage,
            "keyboard": None  # можно добавить клавиатуру в будущем
        }
    
    def _build_context(self, stage: str, history: List[Dict], goals: List[Dict]) -> str:
        """Построить контекст для модели"""
        context_parts = []
        
        # Добавляем историю диалога (последние 5 сообщений)
        if history:
            recent = history[-5:] if len(history) > 5 else history
            context_parts.append("\n--- Недавние сообщения ---")
            for msg in recent:
                role = "Пользователь" if msg['role'] == 'user' else "Бот"
                context_parts.append(f"{role}: {msg['content'][:500]}")
        
        # Добавляем цели
        if goals:
            context_parts.append("\n--- Текущие цели ---")
            for goal in goals:
                context_parts.append(f"• {goal['text']} (прогресс: {goal['progress']}%)")
        
        return "\n".join(context_parts)
    
    def _detect_stage_transition(self, current_stage: str, user_text: str, response: str) -> Optional[str]:
        """
        Определить, нужно ли перейти на следующий этап.
        Упрощённая логика — в будущем можно улучшить с помощью AI.
        """
        # Если пользователь просит перейти к планированию
        if "план" in user_text.lower() or "цель" in user_text.lower():
            if current_stage == 'reflection':
                return 'planning'
        
        # Если пользователь просит перейти к трекингу
        if "трек" in user_text.lower() or "отслеж" in user_text.lower() or "прогресс" in user_text.lower():
            if current_stage in ['planning', 'reflection']:
                return 'tracking'
        
        # Если пользователь говорит что разобрался
        if "понял" in user_text.lower() and "себя" in user_text.lower():
            if current_stage == 'reflection' and len(user_text) > 20:
                return 'planning'
        
        # Если пользователь говорит, что уже знает чего хочет
        if "хочу" in user_text.lower() and len(user_text) > 30:
            if current_stage == 'welcome':
                return 'reflection'
        
        # Переход в трекинг, если пользователь согласился на ежедневные чекины
        if "согласен" in user_text.lower() and "ежеднев" in user_text.lower():
            if current_stage == 'planning':
                return 'tracking'
        
        return None


class StageManager:
    """Управление этапами пользователя"""
    
    STAGES = ['welcome', 'reflection', 'planning', 'tracking']
    
    @staticmethod
    def get_next_stage(current_stage: str) -> Optional[str]:
        """Получить следующий этап"""
        try:
            idx = StageManager.STAGES.index(current_stage)
            if idx < len(StageManager.STAGES) - 1:
                return StageManager.STAGES[idx + 1]
        except ValueError:
            pass
        return None
    
    @staticmethod
    def get_stage_description(stage: str) -> str:
        """Описание этапа для пользователя"""
        descriptions = {
            'welcome': 'Знакомство и разогрев',
            'reflection': 'Глубокая рефлексия и поиск истинных желаний',
            'planning': 'Постановка целей и планирование',
            'tracking': 'Ежедневный трекинг и поддержка',
        }
        return descriptions.get(stage, 'Неизвестный этап')
