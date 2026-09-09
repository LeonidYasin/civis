"""
Model router for Coach Bot
Supports multiple LLM providers with BYOK (Bring Your Own Key)
"""

import os
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass
import httpx

from .config import config


@dataclass
class ModelResponse:
    """Standardized model response"""
    text: str
    model: str
    provider: str
    usage: Optional[Dict[str, int]] = None


class ModelRouter:
    """Router for LLM models with BYOK support"""
    
    def __init__(self):
        self.client = httpx.Client(timeout=60.0)
    
    def get_available_models(self, user_api_key: Optional[str] = None) -> Dict[str, bool]:
        """Get available models for a user"""
        return {
            'deepseek': True,  # Always available (our key)
            'openai': bool(config.openai_api_key or user_api_key),
            'claude': bool(config.claude_api_key or user_api_key),
        }
    
    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        model: str = 'deepseek',
        user_api_key: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> ModelResponse:
        """Generate a response using the specified model"""
        
        if model == 'deepseek':
            return await self._call_deepseek(prompt, system_prompt, temperature, max_tokens)
        elif model == 'openai':
            return await self._call_openai(prompt, system_prompt, user_api_key, temperature, max_tokens)
        elif model == 'claude':
            return await self._call_claude(prompt, system_prompt, user_api_key, temperature, max_tokens)
        else:
            raise ValueError(f"Unknown model: {model}")
    
    async def _call_deepseek(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> ModelResponse:
        """Call DeepSeek API"""
        if not config.deepseek_api_key:
            raise ValueError("DeepSeek API key not configured")
        
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {config.deepseek_api_key}",
            "Content-Type": "application/json",
        }
        data = {
            "model": config.deepseek_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        response = await self.client.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        
        return ModelResponse(
            text=result['choices'][0]['message']['content'],
            model=config.deepseek_model,
            provider='deepseek',
            usage=result.get('usage'),
        )
    
    async def _call_openai(
        self,
        prompt: str,
        system_prompt: str,
        user_api_key: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> ModelResponse:
        """Call OpenAI API"""
        api_key = user_api_key or config.openai_api_key
        if not api_key:
            raise ValueError("OpenAI API key not provided")
        
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        data = {
            "model": config.openai_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        response = await self.client.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        
        return ModelResponse(
            text=result['choices'][0]['message']['content'],
            model=config.openai_model,
            provider='openai',
            usage=result.get('usage'),
        )
    
    async def _call_claude(
        self,
        prompt: str,
        system_prompt: str,
        user_api_key: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> ModelResponse:
        """Call Claude API"""
        api_key = user_api_key or config.claude_api_key
        if not api_key:
            raise ValueError("Claude API key not provided")
        
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        data = {
            "model": config.claude_model,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        response = await self.client.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        
        return ModelResponse(
            text=result['content'][0]['text'],
            model=config.claude_model,
            provider='claude',
            usage=result.get('usage'),
        )
    
    def validate_api_key(self, provider: str, api_key: str) -> bool:
        """Validate an API key by making a test call"""
        # Simple validation: check format
        if provider == 'openai':
            return api_key.startswith('sk-') and len(api_key) > 20
        elif provider == 'claude':
            return api_key.startswith('sk-ant-') and len(api_key) > 20
        elif provider == 'deepseek':
            return len(api_key) > 10
        return False
