# -*- coding: utf-8 -*-
"""
Воркеры для фоновых операций.
AI генерация, Anki операции, мониторинг буфера обмена.
"""
import threading
import time
import os
import re

from core.app_state import app_state
from api.anki_api import anki_api
from api.ai.ollama_provider import ollama_provider
from api.ai.openrouter_provider import OpenRouterProvider


# =============================================================================
# AI PROVIDER CACHE
# =============================================================================
_cached_provider = None
_cached_settings_hash = None


def get_current_ai_provider():
    """Возвращает настроенный инстанс AI провайдера (с кэшированием)"""
    global _cached_provider, _cached_settings_hash
    
    provider_type = app_state.ai_provider
    
    current_settings = {
        "type": provider_type,
        "key": app_state.openrouter_api_key if provider_type == "openrouter" else app_state.google_api_key,
        "model": app_state.openrouter_model if provider_type == "openrouter" else None
    }
    
    settings_hash = str(current_settings)
    
    if _cached_provider and _cached_settings_hash == settings_hash:
        return _cached_provider
    
    new_provider = None
    if provider_type == "openrouter":
        new_provider = OpenRouterProvider(
            api_key=app_state.openrouter_api_key,
            model=app_state.openrouter_model
        )
    elif provider_type == "google":
        new_provider = ollama_provider  # Placeholder
    else:
        new_provider = ollama_provider
        
    _cached_provider = new_provider
    _cached_settings_hash = settings_hash
    return new_provider


# =============================================================================
# AI WORKER
# =============================================================================
def ask_ai_worker(q, phrase, with_context):
    """Воркер для генерации перевода через выбранный AI"""
    try:
        provider = get_current_ai_provider()
        
        model = None
        if provider.name == "Ollama":
            if app_state.main_window_components and "vars" in app_state.main_window_components:
                try:
                    model = app_state.main_window_components["vars"].get("ollama_var").get()
                except:
                    model = app_state.ollama_model
            if not model:
                model = app_state.ollama_model

        if with_context:
            translation, context = provider.translate_with_context(
                phrase, app_state.context_prompt, model,
                delimiter=app_state.context_delimiter
            )
        else:
            translation, context = provider.translate(
                phrase, app_state.translate_prompt, model
            )
        
        q.put(("ollama_ok", (translation, context)))
    except Exception as e:
        q.put(("ollama_error", e))


def get_ollama_models():
    """Получает список моделей Ollama"""
    models = ollama_provider.get_models()
    if not models and not ollama_provider.is_available():
        return "OLLAMA_CONNECT_ERROR"
    return models


# =============================================================================
# ANKI WORKER
# =============================================================================
def add_to_anki_worker(q, phrase, translation, context, deck_name, audio_path, 
                       confirm_delete=False, force_replace=False):
    """Воркер для добавления в Anki"""
    try:
        if force_replace:
            existing_ids = anki_api.find_notes(phrase)
            if existing_ids:
                print(f"🔄 Force replace: удаление {len(existing_ids)} старых заметок.")
                anki_api.delete_notes(existing_ids)
        
        anki_api.add_note(phrase, translation, context, deck_name, audio_path)
        
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except OSError:
                pass
        
        q.put(("anki_ok", True))
    except Exception as e:
        err_msg = str(e).lower()
        if "duplicate" in err_msg and not confirm_delete and not force_replace:
            existing_ids = anki_api.find_notes(phrase)
            if existing_ids:
                q.put(("anki_duplicate", (phrase, translation, context, deck_name, audio_path, existing_ids)))
                return
        
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except OSError:
                pass
        q.put(("anki_error", e))


def load_background_data_worker(q):
    """Загружает данные в фоне (модели и колоды)"""
    anki_api.setup_model()
    
    try:
        models = get_ollama_models()
        if models == "OLLAMA_CONNECT_ERROR":
            q.put(("models_error", models))
        else:
            q.put(("models_ok", models))
    except Exception as e:
        q.put(("models_error", e))
    
    try:
        decks = anki_api.get_deck_names()
        if decks == "ANKI_CONNECT_ERROR":
            q.put(("decks_error", decks))
        else:
            q.put(("decks_ok", decks))
    except Exception as e:
        q.put(("decks_error", e))


# =============================================================================
# CLIPBOARD WORKER
# =============================================================================
def format_clipboard_text(text):
    """Форматирует текст из буфера обмена"""
    return re.sub(r'(?<![.!?,;:])\s*[\r\n]+\s*', ' ', text)


def clipboard_worker(q):
    """Воркер для мониторинга буфера обмена"""
    import pyperclip
    
    print("🚀 Clipboard worker запущен!")
    last_heartbeat = time.time()
    
    while app_state.clipboard_running:
        try:
            current_time = time.time()
            if current_time - last_heartbeat > 20:
                last_heartbeat = current_time
            
            if not app_state.clipboard_running:
                break
            
            pause_from_ui = True
            try:
                if app_state.main_window_components and "vars" in app_state.main_window_components:
                    var = app_state.main_window_components["vars"].get("pause_monitoring_var")
                    if var is not None:
                        pause_from_ui = not var.get()
            except Exception:
                pass
            
            if pause_from_ui:
                time.sleep(0.5)
                continue
            
            try:
                current = pyperclip.paste()
            except Exception as e:
                print(f"⚠️ Ошибка чтения буфера: {type(e).__name__}: {e}")
                time.sleep(1.0)
                continue
            
            if current != app_state.last_clipboard and current.strip():
                word_count = len(current.split())
                has_letters = any(c.isalpha() for c in current)
                
                print(f"📋 Буфер изменился: слов={word_count}, текст: {current[:50]}...")
                
                if word_count <= 100 and has_letters:
                    print(f"✅ Текст перехвачен, помещаем в очередь")
                    q.put(current)
                    app_state.last_clipboard = current
                else:
                    app_state.last_clipboard = current
            
        except Exception as e:
            print(f"❌ Ошибка в clipboard_worker: {type(e).__name__}: {e}")
            time.sleep(1.0)
        
        time.sleep(0.5)
    
    print("🛑 Clipboard worker остановлен")
