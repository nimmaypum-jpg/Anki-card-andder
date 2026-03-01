# -*- coding: utf-8 -*-
import time
import os
from core.app_state import app_state
from api.anki_api import anki_api

def batch_processing_worker(q, phrase_list, deck_name, audio_enabled, context_enabled, get_current_ai_provider_func, audio_utils_module):
    """
    Чистая логика пакетной обработки.
    Не зависит от UI напрямую, общается через очередь q.
    """
    app_state.batch_running = True
    total = len(phrase_list)
    
    q.put(("batch_log", f"🚀 Начало обработки {total} фраз..."))
    
    for i, phrase in enumerate(phrase_list):
        if not app_state.batch_running:
            q.put(("batch_log", "🛑 Обработка прервана."))
            break
        
        # Проверка паузы
        if app_state.batch_paused:
            q.put(("batch_log", f"⏸ Пауза перед фразой: {phrase[:30]}..."))
            while app_state.batch_paused:
                time.sleep(0.2)
                if not app_state.batch_running:
                    break
            if app_state.batch_running:
                q.put(("batch_log", "▶ Продолжение работы..."))
        
        if not app_state.batch_running:
            q.put(("batch_log", "🛑 Обработка прервана."))
            break
            
        phrase = phrase.strip()
        if not phrase:
            continue
            
        q.put(("batch_progress", (i + 1, total, phrase)))
        
        # Начало логирования фразы (одна строка на фразу)
        short_phrase = (phrase[:40] + '...') if len(phrase) > 40 else phrase
        q.put(("batch_log", f"{short_phrase}:"))
        
        try:
            # 1. Проверка дубликата
            if app_state.check_duplicates:
                existing = anki_api.find_notes(phrase)
                if existing:
                    q.put(("batch_log_append", "⚠️ Дубликат (пропущено)"))
                    continue
            
            # 2. Генерация через AI
            q.put(("batch_log_append", "🤖"))
            provider = get_current_ai_provider_func()
            
            # Определяем модель в зависимости от провайдера
            if provider.name == "Ollama":
                model = app_state.ollama_model
            elif provider.name == "OpenRouter":
                model = app_state.openrouter_model
            else:
                model = None  # Провайдер сам определит модель
            
            if context_enabled:
                translation, context = provider.translate_with_context(
                    phrase, app_state.context_prompt, model,
                    delimiter=app_state.context_delimiter
                )
            else:
                translation, context = provider.translate(
                    phrase, app_state.translate_prompt, model
                )
            
            # 3. Озвучка
            audio_path = None
            if audio_enabled:
                q.put(("batch_log_append", "🔊"))
                audio_path = audio_utils_module.generate_audio(
                    phrase, 
                    app_state.tts.lang, 
                    app_state.tts.speed_level, 
                    app_state.tts.tld
                )
            
            # 4. Добавление в Anki
            q.put(("batch_log_append", "📇"))
            anki_api.add_note(phrase, translation, context, deck_name, audio_path, allow_duplicate=not app_state.check_duplicates)
            
            # Очистка аудио
            if audio_path and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                except OSError:
                    pass
                
            q.put(("batch_log_append", "✅ Готово"))
            
        except Exception as e:
            q.put(("batch_log_append", f"❌ Ошибка: {str(e)}"))
            
        # Пауза 3 секунды между фразами
        if i < total - 1 and app_state.batch_running:
            # q.put(("batch_log", "⏳ Ожидание 3 сек..."))
            for _ in range(30): 
                if not app_state.batch_running: break
                # Если во время ожидания нажали паузу - заходим в цикл ожидания паузы
                if app_state.batch_paused:
                    while app_state.batch_paused:
                        time.sleep(0.2)
                        if not app_state.batch_running: break
                time.sleep(0.1)
                
    app_state.batch_running = False
    app_state.batch_paused = False
    q.put(("batch_done", True))
