"""Model router for coach_bot — supports multiple LLM providers with BYOK."""

import os
import json
import requests
from typing import Optional, Dict, Any

class ModelRouter:
    """Router for LLM models with BYOK support."""
    
    def __init__(self):
        self.default_model = os.getenv("COACH_DEFAULT_MODEL", "deepseek")
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
        
    def call(self, prompt: str, user_id: int, user_api_key: Optional[str] = None, model: Optional[str] = None) -> str:
        """Call the appropriate model based on user preference."""
        model = model or self.default_model
        
        # If user has their own key, use it
        if user_api_key:
            return self._call_with_key(prompt, model, user_api_key)
        
        # Otherwise use our keys
        if model == "deepseek":
            return self._call_deepseek(prompt)
        elif model == "openai":
            return self._call_openai(prompt)
        elif model == "claude":
            return self._call_claude(prompt)
        else:
            return self._call_deepseek(prompt)
    
    def _call_deepseek(self, prompt: str) -> str:
        """Call DeepSeek API."""
        if not self.deepseek_api_key:
            return "⚠️ DeepSeek API key not configured. Please add DEEPSEEK_API_KEY to .env"
        
        try:
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.deepseek_api_key}", "Content-Type": "application/json"},
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 2000
                },
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                return f"⚠️ DeepSeek API error: {response.status_code}"
        except Exception as e:
            return f"⚠️ DeepSeek error: {str(e)}"
    
    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API."""
        if not self.openai_api_key:
            return "⚠️ OpenAI API key not configured. Please add OPENAI_API_KEY to .env or use BYOK"
        
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.openai_api_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 2000
                },
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                return f"⚠️ OpenAI API error: {response.status_code}"
        except Exception as e:
            return f"⚠️ OpenAI error: {str(e)}"
    
    def _call_claude(self, prompt: str) -> str:
        """Call Anthropic Claude API."""
        if not self.anthropic_api_key:
            return "⚠️ Anthropic API key not configured. Please add ANTHROPIC_API_KEY to .env or use BYOK"
        
        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "max_tokens": 2000,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                return data["content"][0]["text"]
            else:
                return f"⚠️ Claude API error: {response.status_code}"
        except Exception as e:
            return f"⚠️ Claude error: {str(e)}"
    
    def _call_with_key(self, prompt: str, model: str, api_key: str) -> str:
        """Call API with user's own key."""
        if model in ["openai", "gpt"]:
            try:
                response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7,
                        "max_tokens": 2000
                    },
                    timeout=30
                )
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    return f"⚠️ API error with your key: {response.status_code}"
            except Exception as e:
                return f"⚠️ Error with your key: {str(e)}"
        elif model in ["claude", "anthropic"]:
            try:
                response = requests.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "claude-3-5-haiku-20241022",
                        "max_tokens": 2000,
                        "messages": [{"role": "user", "content": prompt}]
                    },
                    timeout=30
                )
                if response.status_code == 200:
                    data = response.json()
                    return data["content"][0]["text"]
                else:
                    return f"⚠️ API error with your key: {response.status_code}"
            except Exception as e:
                return f"⚠️ Error with your key: {str(e)}"
        else:
            # Fallback to deepseek with user key
            try:
                response = requests.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": "deepseek-chat",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7,
                        "max_tokens": 2000
                    },
                    timeout=30
                )
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    return f"⚠️ API error with your key: {response.status_code}"
            except Exception as e:
                return f"⚠️ Error with your key: {str(e)}"

    def validate_key(self, api_key: str, model: str = "deepseek") -> bool:
        """Validate a user's API key."""
        test_prompt = "Reply with just 'OK' if you can read this."
        result = self._call_with_key(test_prompt, model, api_key)
        return "OK" in result or "ok" in result.lower()
