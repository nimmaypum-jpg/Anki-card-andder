# -*- coding: utf-8 -*-
"""
Anki German Helper - Главная точка входа.
Качественные переводы с Ollama (CustomTkinter)
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import time
import os
import ctypes
import sys
import types
import shutil

# Импорты из модулей
from core.app_state import app_state
from core.settings_manager import load_settings, save_settings, get_user_dir, get_data_dir, get_resource_path, DEFAULT_DECK_NAME
from core.prompts_manager import prompts_manager, update_active_prompts, rename_prompt_preset
from core.workers import ask_ai_worker, get_ollama_models, add_to_anki_worker, load_background_data_worker, clipboard_worker
from core.processing import process_clipboard_queue, process_results_queue
from core.ui_callbacks import update_auto_generate_flag, update_pause_monitoring_flag, update_processing_indicator
from core import audio_utils
from api.anki_api import anki_api
from api.ai.ollama_provider import ollama_provider
from ui.main_window import build_main_window
from ui.settings_window import open_settings_window, apply_font_settings
from core.localization import localization_manager


# =============================================================================
# SINGLE INSTANCE CHECK
# =============================================================================
def check_single_instance():
    """Проверяет, что запущен только один экземпляр приложения"""
    mutex_name = "AnkiGermanHelperMutex"
    app_state.single_instance_mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    if ctypes.windll.kernel32.GetLastError() == 183:
        messagebox.showwarning(localization_manager.get_text("app_title"), "Another instance is already running.")
        sys.exit(0)


# =============================================================================
# DATA SETUP
# =============================================================================
def ensure_data_setup():
    """Создает внешние папки и копирует ресурсы при первом запуске"""
    # 1. Папка для аудио
    user_files_dir = os.path.join(get_user_dir(), "user_files")
    if not os.path.exists(user_files_dir):
        os.makedirs(user_files_dir, exist_ok=True)
        print(f"📁 Создана папка: {user_files_dir}")

    # 2. Папка data
    data_dir = get_data_dir()
    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)
        print(f"📁 Создана папка: {data_dir}")
    
    # 3. Папка документация внутри data
    docs_dir = os.path.join(data_dir, "документация")
    if not os.path.exists(docs_dir):
        os.makedirs(docs_dir, exist_ok=True)
        src_docs = get_resource_path("документация")
        if os.path.exists(src_docs):
            for item in os.listdir(src_docs):
                shutil.copy2(os.path.join(src_docs, item), os.path.join(docs_dir, item))
            print(f"📄 Справка скопирована в: {docs_dir}")

    # 4. Копируем prompts.json если его нет
    prompts_dest = os.path.join(data_dir, "prompts.json")
    if not os.path.exists(prompts_dest):
        prompts_src = get_resource_path("prompts.json")
        if os.path.exists(prompts_src):
            shutil.copy2(prompts_src, prompts_dest)
            print(f"📄 Промпты скопированы в: {prompts_dest}")


# =============================================================================
# MAIN FUNCTION
# =============================================================================
def main():
    check_single_instance()
    
    # Инициализация внешних файлов
    ensure_data_setup()
    
    # Создаем файл промптов по умолчанию если его нет
    prompts_manager.create_defaults_if_missing()
    
    # Инициализация CustomTkinter
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    
    root = ctk.CTk()
    
    # Загрузка настроек
    settings = load_settings()
    
    # Обновляем audio_utils
    audio_utils.update_tts_settings(
        app_state.tts.lang, 
        app_state.tts.speed_level, 
        app_state.tts.tld
    )
    
    # Создание зависимостей
    dependencies = types.SimpleNamespace()
    dependencies.main_window_components = app_state.main_window_components
    dependencies.stop_clipboard_monitoring = app_state.stop_clipboard_monitoring
    dependencies.load_settings = load_settings
    dependencies.save_settings = save_settings
    dependencies.update_auto_generate_flag = update_auto_generate_flag
    dependencies.update_pause_monitoring_flag = update_pause_monitoring_flag
    dependencies.stop_generation = app_state.stop_generation
    dependencies.get_ollama_models = get_ollama_models
    dependencies.get_deck_names = anki_api.get_deck_names
    dependencies.create_deck = anki_api.create_deck
    dependencies.clean_deck_name = anki_api.clean_deck_name
    dependencies.open_settings_window = lambda parent, deps, **kwargs: open_settings_window(parent, deps, settings, **kwargs)
    dependencies.threading = threading
    dependencies.DEFAULT_DECK_NAME = DEFAULT_DECK_NAME
    dependencies.load_background_data_worker = load_background_data_worker
    dependencies.results_queue = app_state.results_queue
    dependencies.update_active_prompts = update_active_prompts
    dependencies.rename_prompt_preset = rename_prompt_preset
    
    # Generate action wrapper
    def generate_action_wrapper():
        phrase = app_state.main_window_components["widgets"]["german_text"].get("1.0", tk.END).strip()
        if not phrase:
            return

        widgets = app_state.main_window_components["widgets"]
        
        # Запуск таймера сразу
        app_state.generation_running = True
        widgets["generate_btn"].configure(text="0s", state="disabled", fg_color="#FFD700", hover_color="#E6C200", text_color="black")
        
        start_time = time.time()
        def update_timer():
            if not app_state.generation_running:
                return
            elapsed = time.time() - start_time
            try:
                widgets["generate_btn"].configure(text=f"{int(elapsed)}s", text_color="black")
                root.after(1000, update_timer)
            except Exception:
                pass
        update_timer()
        
        def _pre_generation_worker():
            app_state.force_replace_flag = False
            existing_ids = anki_api.find_notes(phrase)
            
            def _continue_generation_on_main():
                if existing_ids:
                    audio_utils.play_sound("notify")
                    if messagebox.askyesno("Дубликат", "Такая карточка уже есть в Anki.\nСгенерировать новую версию для замены?", parent=root):
                        app_state.force_replace_flag = True
                    else:
                        app_state.generation_running = False
                        widgets["generate_btn"].configure(text=localization_manager.get_text("generate"), state="normal", fg_color="#2CC985", text_color="white")
                        return

                widgets["stop_btn"].configure(state="normal")
                widgets["add_btn"].configure(fg_color="#FFD700", hover_color="#E6C200", text_color="black")
                
                with_context = app_state.get_checkbox_value("context_var", default=False)
                print(f"🔄 Генерация: phrase={len(phrase)} chars, контекст={'☑ ВКЛ' if with_context else '☐ ВЫКЛ'}")
                
                threading.Thread(target=ask_ai_worker, args=(app_state.results_queue, phrase, with_context), daemon=True).start()

            root.after(0, _continue_generation_on_main)

        threading.Thread(target=_pre_generation_worker, daemon=True).start()
        
    dependencies.generate_action = generate_action_wrapper
    
    # On yes action wrapper
    def on_yes_action_wrapper():
        text = app_state.main_window_components["widgets"]["german_text"].get("1.0", tk.END).strip()
        if not text:
            return
        
        app_state.main_window_components["widgets"]["add_btn"].configure(state="disabled", text="⏳ Озвучка...")
        
        audio_enabled = app_state.main_window_components.get("vars", {}).get("audio_enabled_var", tk.BooleanVar(value=True)).get()
        
        def _async_audio_gen():
            try:
                if audio_enabled:
                    audio_path = audio_utils.generate_audio(
                        text, 
                        app_state.tts.lang, 
                        app_state.tts.speed_level, 
                        app_state.tts.tld
                    )
                else:
                    audio_path = None
                
                app_state.results_queue.put(("audio_ok", audio_path))
            except Exception as e:
                print(f"❌ Critical error in audio generation: {e}")
                app_state.results_queue.put(("audio_error", str(e)))

        threading.Thread(target=_async_audio_gen, daemon=True).start()
        
    dependencies.on_yes_action = on_yes_action_wrapper
    
    # Сохраняем функции для авто-вызова
    app_state.main_window_components["generate_function"] = generate_action_wrapper
    app_state.main_window_components["on_yes_action_func"] = on_yes_action_wrapper
    
    # Строим интерфейс
    build_main_window(dependencies, root, settings)
    
    # Показываем окно
    root.deiconify()
    root.update()
    
    # Применяем шрифт при старте
    def apply_fonts_deferred():
        apply_font_settings(settings.get("FONT_FAMILY", "Roboto"), settings.get("FONT_SIZE", 14))
    
    root.after(50, apply_fonts_deferred)
    
    # Запускаем потоки
    threading.Thread(target=clipboard_worker, args=(app_state.clipboard_queue,), daemon=True).start()
    
    # Запускаем обработку очередей
    root.after(100, process_clipboard_queue, root)
    root.after(100, process_results_queue, root)
    
    root.mainloop()


if __name__ == "__main__":
    main()
