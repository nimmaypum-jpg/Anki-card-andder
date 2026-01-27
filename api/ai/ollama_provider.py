# -*- coding: utf-8 -*-
"""
Ollama AI провайдер.
Локальный AI через Ollama API.
"""
import requests
from typing import List, Tuple

from api.ai.base_provider import BaseAIProvider


class OllamaProvider(BaseAIProvider):
    """Провайдер для локального Ollama"""
    
    DEFAULT_MODEL = "gemma3:1b"
    API_URL = "http://localhost:11434"
    
    def __init__(self, api_url: str = None):
        self.api_url = api_url or self.API_URL
        self.default_model = self.DEFAULT_MODEL
    
    @property
    def name(self) -> str:
        return "Ollama"
    
    @property
    def is_local(self) -> bool:
        return True
    
    def is_available(self) -> bool:
        """Проверяет доступность Ollama"""
        try:
            response = requests.get(f"{self.api_url}/api/tags", timeout=2.0)
            return response.status_code == 200
        except Exception:
            return False
    
    def get_models(self) -> List[str]:
        """
        Возвращает список доступных моделей Ollama.
        
        Returns:
            Отсортированный список имен моделей или пустой список
        """
        try:
            response = requests.get(f"{self.api_url}/api/tags", timeout=2.0)
            if response.status_code == 200:
                models = response.json().get("models", [])
                return sorted([model["name"] for model in models]) if models else []
            return []
        except requests.exceptions.ConnectionError:
            return []
        except Exception:
            return []
    
    def generate(self, prompt: str, model: str = None, 
                 timeout: float = 45) -> str:
        """
        Генерирует ответ через Ollama.
        
        Args:
            prompt: Текст промпта
            model: Имя модели (если None, используется default)
            timeout: Таймаут в секундах
            
        Returns:
            Сгенерированный текст
        """
        model_to_use = model or self.default_model
        
        payload = {
            "model": model_to_use,
            "prompt": prompt,
            "stream": False
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/api/generate",
                json=payload,
                timeout=timeout
            )
            
            if response.status_code != 200:
                error = response.json().get('error', response.text)
                raise Exception(f"Ollama Error: {error}")
            
            result = response.json().get("response", "").strip()
            if not result:
                raise Exception("Ollama вернул пустой ответ")
            
            return result
            
        except requests.exceptions.Timeout:
            raise Exception(f"Ollama: превышено время ожидания ({timeout}с)")
        except requests.exceptions.ConnectionError:
            raise Exception("OLLAMA_CONNECT_ERROR")
        except Exception as e:
            if "canceled" in str(e).lower():
                raise Exception("Генерация прервана")
            raise


# Синглтон для удобства
ollama_provider = OllamaProvider()
