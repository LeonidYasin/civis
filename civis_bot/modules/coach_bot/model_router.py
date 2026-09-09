"""Маршрутизация моделей для coach_bot"""

import os
import logging
from typing import Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseModelProvider(ABC):
    """Базовый класс для провайдеров моделей"""
    
    @abstractmethod
    async def generate(self, system_prompt: str, context: str, user_message: str) -> str:
        pass
    
    @abstractmethod
    def validate_key(self, api_key: str) -> bool:
        pass


class DeepSeekProvider(BaseModelProvider):
    """Провайдер DeepSeek (по умолчанию, самый дешёвый)"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('DEEPSEEK_API_KEY')
    
    async def generate(self, system_prompt: str, context: str, user_message: str) -> str:
        # В реальном проекте здесь будет вызов DeepSeek API
        # Пока возвращаем заглушку
        return f"[DeepSeek] Это ответ на: {user_message[:50]}...\n\nПопробуй написать что-то более конкретное, и я смогу дать глубокий ответ."
    
    def validate_key(self, api_key: str) -> bool:
        return api_key.startswith('ds-') or len(api_key) > 20


class OpenAIProvider(BaseModelProvider):
    """Провайдер OpenAI"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
    
    async def generate(self, system_prompt: str, context: str, user_message: str) -> str:
        # В реальном проекте здесь будет вызов OpenAI API
        return f"[OpenAI] Ответ на: {user_message[:50]}...\n\nРасскажи подробнее, что ты имеешь в виду."
    
    def validate_key(self, api_key: str) -> bool:
        return api_key.startswith('sk-') and len(api_key) > 20


class ClaudeProvider(BaseModelProvider):
    """Провайдер Claude (Anthropic)"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
    
    async def generate(self, system_prompt: str, context: str, user_message: str) -> str:
        # В реальном проекте здесь будет вызов Claude API
        return f"[Claude] На твой запрос: {user_message[:50]}...\n\nДавай разберём это вместе."
    
    def validate_key(self, api_key: str) -> bool:
        return api_key.startswith('claude-') or api_key.startswith('sk-ant-')


class ModelRouter:
    """Маршрутизация запросов к разным моделям"""
    
    PROVIDERS = {
        'deepseek': DeepSeekProvider,
        'openai': OpenAIProvider,
        'claude': ClaudeProvider,
        'custom': None,  # определяется динамически
    }
    
    def __init__(self):
        self._providers_cache = {}
    
    def get_provider(self, model: str, api_key: Optional[str] = None) -> Optional[BaseModelProvider]:
        """Получить провайдера для модели"""
        
        # Если модель custom — используем провайдера по ключу
        if model == 'custom':
            if not api_key:
                return None
            # Определяем провайдера по формату ключа
            if api_key.startswith('sk-'):
                return OpenAIProvider(api_key)
            elif api_key.startswith('claude-') or api_key.startswith('sk-ant-'):
                return ClaudeProvider(api_key)
            else:
                return DeepSeekProvider(api_key)
        
        # Стандартные провайдеры
        provider_class = self.PROVIDERS.get(model)
        if not provider_class:
            return None
        
        return provider_class(api_key)
    
    async def generate(
        self,
        system_prompt: str,
        context: str,
        user_message: str,
        model: str = 'deepseek',
        api_key: Optional[str] = None
    ) -> str:
        """
        Генерация ответа с использованием указанной модели
        """
        provider = self.get_provider(model, api_key)
        if not provider:
            logger.warning(f"Провайдер для модели {model} не найден, использую DeepSeek")
            provider = DeepSeekProvider()
        
        try:
            # Полный промпт
            full_prompt = f"{system_prompt}\n\n{context}\n\nПользователь: {user_message}\n\nБот:"
            response = await provider.generate(system_prompt, context, user_message)
            return response
        except Exception as e:
            logger.error(f"Ошибка при генерации через {model}: {e}")
            return f"Извини, произошла ошибка при обращении к модели {model}. Попробуй ещё раз или выбери другую модель."
    
    async def generate_with_insights(
        self,
        system_prompt: str,
        context: str,
        user_message: str,
        model: str = 'deepseek',
        api_key: Optional[str] = None
    ) -> dict:
        """
        Генерация ответа с извлечением инсайтов
        """
        response = await self.generate(system_prompt, context, user_message, model, api_key)
        
        # Простое извлечение инсайтов (в будущем можно улучшить)
        insights = []
        if "понял" in response.lower() or "осознал" in response.lower():
            insights.append(response[:200])
        
        return {
            "content": response,
            "insights": insights,
            "model_used": model
        }
    
    def get_available_models(self) -> list:
        """Список доступных моделей"""
        return ['deepseek', 'openai', 'claude', 'custom']
    
    def get_model_price(self, model: str) -> dict:
        """Цена за 1K токенов для модели"""
        prices = {
            'deepseek': {'input': 0.00014, 'output': 0.00028},  # $/1K токенов
            'openai': {'input': 0.003, 'output': 0.006},
            'claude': {'input': 0.003, 'output': 0.015},
            'custom': {'input': 0, 'output': 0},
        }
        return prices.get(model, {'input': 0, 'output': 0})
