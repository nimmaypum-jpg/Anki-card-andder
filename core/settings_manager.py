# -*- coding: utf-8 -*-
"""
Модуль управления настройками приложения.
Загрузка и сохранение настроек в файл.
"""
import os
import sys
import json
from typing import Dict, Any

# Константы по умолчанию
DEFAULT_DECK_NAME = "Местоиминия"
DEFAULT_OLLAMA_MODEL = "gemma3:1b"

DEFAULT_TRANSLATE_PROMPT = (
    'Переведи следующий немецкий текст на русский язык качественно:\n\n'
    '"{phrase}"\n\n'
    'Ответь только переводом на русском языке. '
    'Не используй в ответе кавычки, маркдаун или любой дополнительный текст.'
)

DEFAULT_CONTEXT_PROMPT = (
    'Проанализируй следующее немецкое предложение:\n\n'
    '"{phrase}"\n\n'
    'Ответь строго в следующем формате (не добавляй ничего лишнего, не используй маркдаун):\n\n'
    'ПЕРЕВОД: [краткий перевод на русский одной или несколькими фразами]\n'
    'КОНТЕКСТ: [кратко разъясни значение важных слов, грамматику, род и падежи, '
    'приведи 1–3 похожих примера. Избегай списков и таблиц.]'
)


def get_user_dir() -> str:
    """Возвращает директорию для хранения пользовательских файлов (рядом с EXE)"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(__file__))


def get_resource_path(relative_path: str) -> str:
    """Возвращает путь к ресурсу внутри EXE или в папке проекта"""
    if getattr(sys, 'frozen', False):
        # PyInstaller создает временную папку и хранит путь в _MEIPASS
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)


def get_data_dir() -> str:
    """Возвращает директорию data для внешних конфигов"""
    return os.path.join(get_user_dir(), "data")


def get_settings_path() -> str:
    """Возвращает путь к файлу настроек"""
    return os.path.join(get_user_dir(), "anki_settings.txt")


def get_default_settings() -> Dict[str, Any]:
    """Возвращает настройки по умолчанию"""
    return {
        "LAST_DECK": DEFAULT_DECK_NAME,
        "CONTEXT_ENABLED": False,
        "OLLAMA_MODEL": DEFAULT_OLLAMA_MODEL,
        "TRANSLATE_PROMPT": DEFAULT_TRANSLATE_PROMPT,
        "CONTEXT_PROMPT": DEFAULT_CONTEXT_PROMPT,
        "TTS_SPEED_LEVEL": 0,
        "TTS_TLD": "de",
        "TTS_LANG": "de",
        "AUTO_GENERATE_ON_COPY": True,
        "PAUSE_CLIPBOARD_MONITORING": False,
        "SOUND_SOURCE": "original",
        "FONT_SIZE": 14,
        "FONT_FAMILY": "Roboto",
        "LAST_PROMPT": "",
        "AUDIO_ENABLED": True,
        "AUTO_ADD_TO_ANKI": False,
        # AI Settings
        "AI_PROVIDER": "ollama",
        "OLLAMA_URL": "http://localhost:11434",
        "OPENROUTER_API_KEY": "",
        "OPENROUTER_MODEL": "openai/gpt-4o-mini",
        "GOOGLE_API_KEY": "",
        "LAST_SETTINGS_TAB": "Озвучка",
        "AI_PRESETS": []
    }


def load_settings(update_app_state: bool = True) -> Dict[str, Any]:
    """
    Загружает настройки из файла.
    
    Args:
        update_app_state: Если True, обновляет глобальное состояние приложения
        
    Returns:
        Dict с настройками
    """
    settings = get_default_settings()
    path = get_settings_path()
    
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                core, _, prompts = f.read().partition("---\nPROMPTS---\n")
                
                # Парсим основные настройки
                for line in core.splitlines():
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        # Разрешаем загрузку любых ключей, даже если их нет в дефолтных (для совместимости)
                        # Но приводим типы для известных
                        if k in settings and isinstance(settings[k], bool):
                             settings[k] = v.lower() == "true"
                        elif k in settings and isinstance(settings[k], int):
                             settings[k] = int(v) if v.isdigit() else settings[k]
                        elif k == "AI_PRESETS":
                             try:
                                 settings[k] = json.loads(v)
                             except:
                                 settings[k] = []
                        else:
                             settings[k] = v
                
                # Парсим промпты
                if prompts:
                    tr, _, ctx = prompts.partition("---\nCONTEXT---\n")
                    if tr.strip():
                        settings["TRANSLATE_PROMPT"] = tr.strip()
                    if ctx.strip():
                        settings["CONTEXT_PROMPT"] = ctx.strip()
        except Exception as e:
            print(f"⚠️ Ошибка загрузки настроек: {e}")
    
    # Обновляем глобальное состояние
    if update_app_state:
        from core.app_state import app_state
        app_state.ollama_model = settings["OLLAMA_MODEL"]
        app_state.translate_prompt = settings["TRANSLATE_PROMPT"]
        app_state.context_prompt = settings["CONTEXT_PROMPT"]
        app_state.tts.speed_level = settings["TTS_SPEED_LEVEL"]
        app_state.tts.tld = settings["TTS_TLD"]
        app_state.tts.lang = settings["TTS_LANG"]
        app_state.auto_generate_on_copy = settings["AUTO_GENERATE_ON_COPY"]
        app_state.pause_clipboard_monitoring = settings["PAUSE_CLIPBOARD_MONITORING"]
        
        # AI настройки
        app_state.ai_provider = settings.get("AI_PROVIDER", "ollama")
        app_state.openrouter_api_key = settings.get("OPENROUTER_API_KEY", "")
        app_state.openrouter_model = settings.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
        app_state.google_api_key = settings.get("GOOGLE_API_KEY", "")
    
    return settings


def save_settings(settings: Dict[str, Any]) -> bool:
    """
    Сохраняет настройки в файл.
    
    Args:
        settings: Dict с настройками
        
    Returns:
        True при успехе, False при ошибке
    """
    try:
        with open(get_settings_path(), "w", encoding="utf-8") as f:
            # Записываем основные настройки
            for k, v in settings.items():
                if k not in ["TRANSLATE_PROMPT", "CONTEXT_PROMPT"]:
                    value = v
                    if isinstance(v, bool):
                        value = str(v).lower()
                    elif k == "AI_PRESETS":
                        value = json.dumps(v, ensure_ascii=False)
                    
                    f.write(f"{k}={value}\n")
            
            # Записываем промпты
            translate_prompt = settings.get('TRANSLATE_PROMPT', DEFAULT_TRANSLATE_PROMPT)
            context_prompt = settings.get('CONTEXT_PROMPT', DEFAULT_CONTEXT_PROMPT)
            f.write(f"---\nPROMPTS---\n{translate_prompt}\n---\nCONTEXT---\n{context_prompt}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения настроек: {e}")
        return False
