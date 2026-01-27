# -*- coding: utf-8 -*-
"""
Модуль состояния приложения.
Заменяет глобальные переменные на централизованный dataclass.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import queue


@dataclass
class TTSSettings:
    """Настройки Text-to-Speech"""
    lang: str = "de"
    tld: str = "de"
    speed_level: int = 0  # 0=normal, 1=slow, 2=very slow


@dataclass
class AppState:
    """
    Централизованное состояние приложения.
    Заменяет множество глобальных переменных.
    """
    # AI настройки
    ai_provider: str = "ollama"  # ollama, openrouter, google
    ollama_model: str = "model"
    openrouter_model: str = "openai/gpt-4o-mini"
    openrouter_api_key: str = ""
    google_api_key: str = ""
    translate_prompt: str = ""
    context_prompt: str = ""
    context_delimiter: str = "КОНТЕКСТ"
    
    # TTS настройки
    tts: TTSSettings = field(default_factory=TTSSettings)
    
    # Флаги состояния
    pause_clipboard_monitoring: bool = True  # По умолчанию перехват выключен
    auto_generate_on_copy: bool = True
    generation_running: bool = False
    clipboard_running: bool = True
    force_replace_flag: bool = False
    
    # Буфер обмена
    last_clipboard: str = ""
    
    # Очереди для межпоточной коммуникации
    clipboard_queue: queue.Queue = field(default_factory=queue.Queue)
    results_queue: queue.Queue = field(default_factory=queue.Queue)
    
    # Компоненты главного окна (ссылки на виджеты и переменные)
    main_window_components: Dict[str, Any] = field(default_factory=dict)
    
    # Мьютекс для single instance
    single_instance_mutex_handle: Optional[Any] = None
    
    def update_tts(self, lang: str = None, speed_level: int = None, tld: str = None):
        """Обновляет настройки TTS"""
        if lang is not None:
            self.tts.lang = lang
        if speed_level is not None:
            self.tts.speed_level = speed_level
        if tld is not None:
            self.tts.tld = tld
    
    def stop_generation(self):
        """Останавливает текущую генерацию"""
        self.generation_running = False
    
    def stop_clipboard_monitoring(self):
        """Останавливает мониторинг буфера обмена"""
        self.clipboard_running = False
    
    def get_checkbox_value(self, var_name: str, default: bool = False) -> bool:
        """Безопасное чтение значения чекбокса из UI компонентов"""
        try:
            if self.main_window_components and "vars" in self.main_window_components:
                var = self.main_window_components["vars"].get(var_name)
                if var is not None:
                    return var.get()
        except Exception as e:
            print(f"⚠️ Ошибка чтения {var_name}: {e}")
        return default


# Глобальный экземпляр состояния приложения (singleton)
app_state = AppState()
