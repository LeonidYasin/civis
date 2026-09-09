"""
Model Router for Coach Bot
Supports multiple AI models: DeepSeek, OpenAI, Claude
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import requests

logger = logging.getLogger(__name__)


@dataclass
class ModelResponse:
    """Standardized model response"""
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None


class ModelRouter:
    """Route requests to different AI models"""
    
    def __init__(self, default_model: str = "deepseek"):
        self.default_model = default_model
        self._load_api_keys()
    
    def _load_api_keys(self):
        """Load API keys from environment"""
        self.deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
        self.openai_key = os.environ.get("OPENAI_API_KEY", "")
        self.anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    
    def call(
        self,
        messages: List[Dict[str, str]],
        model: str = "deepseek",
        user_api_key: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> ModelResponse:
        """
        Call the specified model with messages
        
        Args:
            messages: List of {role, content} messages
            model: deepseek | openai | claude
            user_api_key: User's own API key (BYOK)
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
        
        Returns:
            ModelResponse with content and metadata
        """
        model = model.lower()
        
        if model == "deepseek":
            return self._call_deepseek(messages, user_api_key, temperature, max_tokens)
        elif model == "openai":
            return self._call_openai(messages, user_api_key, temperature, max_tokens)
        elif model == "claude":
            return self._call_claude(messages, user_api_key, temperature, max_tokens)
        else:
            logger.warning(f"Unknown model {model}, falling back to deepseek")
            return self._call_deepseek(messages, user_api_key, temperature, max_tokens)
    
    def _call_deepseek(
        self,
        messages: List[Dict[str, str]],
        user_api_key: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> ModelResponse:
        """Call DeepSeek API"""
        api_key = user_api_key or self.deepseek_key
        
        if not api_key:
            raise ValueError("DeepSeek API key required")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        # DeepSeek uses OpenAI-compatible API
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        try:
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            
            return ModelResponse(
                content=content,
                model="deepseek",
                usage=usage,
            )
        except Exception as e:
            logger.error(f"DeepSeek API error: {e}")
            raise
    
    def _call_openai(
        self,
        messages: List[Dict[str, str]],
        user_api_key: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> ModelResponse:
        """Call OpenAI API"""
        api_key = user_api_key or self.openai_key
        
        if not api_key:
            raise ValueError("OpenAI API key required")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": "gpt-4o-mini",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            
            return ModelResponse(
                content=content,
                model="openai",
                usage=usage,
            )
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    def _call_claude(
        self,
        messages: List[Dict[str, str]],
        user_api_key: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> ModelResponse:
        """Call Claude API"""
        api_key = user_api_key or self.anthropic_key
        
        if not api_key:
            raise ValueError("Claude API key required")
        
        # Convert OpenAI-style messages to Claude format
        system_messages = [m for m in messages if m["role"] == "system"]
        user_messages = [m for m in messages if m["role"] in ("user", "assistant")]
        
        system_prompt = system_messages[0]["content"] if system_messages else ""
        
        # Claude uses a different format
        payload = {
            "model": "claude-3-haiku-20240307",
            "system": system_prompt,
            "messages": user_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        
        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            
            content = data["content"][0]["text"]
            usage = data.get("usage", {})
            
            return ModelResponse(
                content=content,
                model="claude",
                usage=usage,
            )
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise
    
    def validate_api_key(self, model: str, api_key: str) -> bool:
        """Validate an API key for the given model"""
        try:
            test_messages = [{"role": "user", "content": "Say hello"}]
            response = self.call(
                messages=test_messages,
                model=model,
                user_api_key=api_key,
                max_tokens=5,
            )
            return bool(response.content)
        except Exception:
            return False
    
    def get_available_models(self) -> List[str]:
        """Get list of available models with keys"""
        available = []
        
        if self.deepseek_key:
            available.append("deepseek")
        if self.openai_key:
            available.append("openai")
        if self.anthropic_key:
            available.append("claude")
        
        return available
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get info about available models"""
        available = self.get_available_models()
        
        info = {
            "default": self.default_model,
            "available": available,
            "can_use_default": self.default_model in available,
            "models": {
                "deepseek": {
                    "name": "DeepSeek",
                    "available": "deepseek" in available,
                    "free": True,
                    "best_for": "Balance of quality and cost",
                },
                "openai": {
                    "name": "OpenAI GPT-4",
                    "available": "openai" in available,
                    "free": False,
                    "best_for": "Creativity and structure",
                },
                "claude": {
                    "name": "Claude",
                    "available": "claude" in available,
                    "free": False,
                    "best_for": "Empathy and deep reflection",
                },
            }
        }
        
        return info
