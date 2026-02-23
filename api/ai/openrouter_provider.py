# -*- coding: utf-8 -*-
"""
OpenRouter AI провайдер.
Доступ к моделям через OpenRouter API (openai-compatible).
"""
import requests
import json
from typing import List, Tuple

from api.ai.base_provider import BaseAIProvider


class OpenRouterProvider(BaseAIProvider):
    """Провайдер для OpenRouter (OpenAI-compatible)"""
    
    API_URL = "https://openrouter.ai/api/v1"
    
    def __init__(self, api_key: str, model: str = "openai/gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/your-repo/anki-german-helper", # Required by OpenRouter
            "X-Title": "Anki German Helper",
            "Content-Type": "application/json"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    @property
    def name(self) -> str:
        return "OpenRouter"
    
    @property
    def is_local(self) -> bool:
        return False
    
    def is_available(self) -> bool:
        """Проверяет доступность (наличие ключа)"""
        return bool(self.api_key)
    
    def get_models(self) -> List[str]:
        """Возвращает список моделей (требует запрос к API)"""
        try:
            response = requests.get(f"{self.API_URL}/models", timeout=5)
            if response.status_code == 200:
                data = response.json().get("data", [])
                return sorted([m["id"] for m in data])
            return []
        except Exception:
            return []
    
    def generate(self, prompt: str, model: str = None, timeout: float = 60) -> str:
        """
        Генерирует ответ через OpenRouter.
        """
        if not self.api_key:
            raise Exception("API ключ OpenRouter не задан")
            
        model_to_use = model or self.model
        
        payload = {
            "model": model_to_use,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }
        
        try:
            # Используем сессию для переиспользования соединения
            response = self.session.post(
                f"{self.API_URL}/chat/completions",
                data=json.dumps(payload),
                timeout=timeout
            )
            
            if response.status_code != 200:
                error_msg = response.text
                try:
                    error_json = response.json()
                    if "error" in error_json:
                        error_msg = error_json["error"].get("message", error_msg)
                except Exception:
                    pass
                raise Exception(f"OpenRouter Error {response.status_code}: {error_msg}")
            
            result = response.json()
            choices = result.get("choices", [])
            if not choices:
                raise Exception("OpenRouter вернул пустой ответ")
                
            content = choices[0].get("message", {}).get("content", "").strip()
            return content
            
        except requests.exceptions.Timeout:
            raise Exception(f"OpenRouter: превышено время ожидания ({timeout}с)")
        except requests.exceptions.ConnectionError:
            raise Exception("Ошибка подключения к OpenRouter")
        except Exception as e:
            raise Exception(f"Ошибка генерации OpenRouter: {e}")
