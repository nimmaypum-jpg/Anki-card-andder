# AI Providers module
from api.ai.base_provider import BaseAIProvider
from api.ai.ollama_provider import OllamaProvider

def get_ai_provider(provider_name: str = "ollama") -> BaseAIProvider:
    """Фабрика для получения AI провайдера по имени"""
    providers = {
        "ollama": OllamaProvider,
        # Будущие провайдеры:
        # "openrouter": OpenRouterProvider,
        # "google": GoogleProvider,
    }
    provider_class = providers.get(provider_name.lower())
    if not provider_class:
        raise ValueError(f"Неизвестный AI провайдер: {provider_name}")
    return provider_class()

__all__ = ['BaseAIProvider', 'OllamaProvider', 'get_ai_provider']
