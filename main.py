# -*- coding: utf-8 -*-
"""
Anki German Helper - Главная точка входа.
Качественные переводы с Ollama (CustomTkinter)
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import queue
import time
import re
import os
import ctypes
import sys
import types

# Импорты из модулей
from core.app_state import app_state
from core.settings_manager import load_settings, save_settings, get_user_dir, DEFAULT_DECK_NAME
from core.prompts_manager import prompts_manager, update_active_prompts, rename_prompt_preset
from api.anki_api import AnkiAPI, anki_api
from api.ai.ollama_provider import OllamaProvider, ollama_provider
from ui.main_window import build_main_window
from ui.settings_window import open_settings_window, apply_font_settings
import audio_utils


# =====================================================================================
# SINGLE INSTANCE CHECK
# =====================================================================================
def check_single_instance():
    """Проверяет, что запущен только один экземпляр приложения"""
    mutex_name = "AnkiGermanHelperMutex"
    app_state.single_instance_mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    if ctypes.windll.kernel32.GetLastError() == 183:
        messagebox.showwarning("Anki German Helper", "Another instance is already running.")
        sys.exit(0)


# =====================================================================================
# FLAG UPDATE CALLBACKS
# =====================================================================================
def update_auto_generate_flag(*args):
    """Обновляет флаг автогенерации из UI"""
    try:
        if app_state.main_window_components and "vars" in app_state.main_window_components:
            var = app_state.main_window_components["vars"].get("auto_generate_var")
            if var is not None:
                app_state.auto_generate_on_copy = var.get()
                print(f"🔄 Автогенерация: {'☑ ВКЛ' if app_state.auto_generate_on_copy else '☐ ВЫКЛ'}")
    except Exception as e:
        print(f"⚠️ Ошибка обновления auto_generate: {e}")


def update_pause_monitoring_flag(*args):
    """Обновляет флаг паузы мониторинга из UI"""
    try:
        if app_state.main_window_components and "vars" in app_state.main_window_components:
            var = app_state.main_window_components["vars"].get("pause_monitoring_var")
            if var is not None:
                checkbox_checked = var.get()
                app_state.pause_clipboard_monitoring = not checkbox_checked
                
                print(f"🔄 Перехват буфера: {'☑ ВКЛ' if checkbox_checked else '☐ ВЫКЛ'}")
                
                if "root" in app_state.main_window_components:
                    root = app_state.main_window_components["root"]
                    if app_state.pause_clipboard_monitoring:
                        root._animation_running = False
                        if hasattr(root, '_animation_job'):
                            try:
                                root.after_cancel(root._animation_job)
                            except Exception:
                                pass
                        if hasattr(root, 'animation_label'):
                            root.animation_label.configure(text="")
                    else:
                        root._animation_running = True
                        if hasattr(root, 'start_animation'):
                            root.start_animation()
    except Exception as e:
        print(f"⚠️ Ошибка обновления pause_monitoring: {e}")
        import traceback
        traceback.print_exc()


# =====================================================================================
# PROCESSING INDICATOR
# =====================================================================================
def update_processing_indicator(text="", animate=False):
    """Обновляет индикатор обработки над полем немецкого текста"""
    if app_state.main_window_components and "widgets" in app_state.main_window_components:
        try:
            indicator = app_state.main_window_components["widgets"].get("processing_indicator")
            if indicator:
                indicator.configure(text=text)
                if animate and "root" in app_state.main_window_components:
                    root = app_state.main_window_components["root"]
                    _start_processing_animation(root, indicator)
                elif not animate and "root" in app_state.main_window_components:
                    root = app_state.main_window_components["root"]
                    _stop_processing_animation(root)
        except Exception:
            pass


def _start_processing_animation(root, indicator):
    """Запускает анимацию точек для индикатора обработки"""
    if not hasattr(root, '_processing_animation_running'):
        root._processing_animation_running = False
    
    if root._processing_animation_running:
        return
    
    root._processing_animation_running = True
    dots = ["", ".", "..", "..."]
    index = [0]
    
    def animate():
        if not root._processing_animation_running:
            return
        indicator.configure(text=f"⏳ Обработка{dots[index[0]]}")
        index[0] = (index[0] + 1) % len(dots)
        root._processing_animation_job = root.after(400, animate)
    
    animate()


def _stop_processing_animation(root):
    """Останавливает анимацию обработки"""
    if hasattr(root, '_processing_animation_running'):
        root._processing_animation_running = False
    if hasattr(root, '_processing_animation_job'):
        root.after_cancel(root._processing_animation_job)


# =====================================================================================
# AI GENERATION
# =====================================================================================
from api.ai.openrouter_provider import OpenRouterProvider

# =====================================================================================
# AI GENERATION
# =====================================================================================
# Глобальный кеш провайдера
_cached_provider = None
_cached_settings_hash = None

def get_current_ai_provider():
    """Возвращает настроенный инстанс AI провайдера (с кэшированием)"""
    global _cached_provider, _cached_settings_hash
    
    provider_type = app_state.ai_provider
    
    # Собираем текущие настройки для проверки изменений
    current_settings = {
        "type": provider_type,
        "key": app_state.openrouter_api_key if provider_type == "openrouter" else app_state.google_api_key,
        "model": app_state.openrouter_model if provider_type == "openrouter" else None
    }
    
    # Формируем хеш настроек (просто строка)
    settings_hash = str(current_settings)
    
    # Если провайдер уже есть и настройки не поменялись — возвращаем его
    if _cached_provider and _cached_settings_hash == settings_hash:
        return _cached_provider
    
    # Иначе создаем новый
    new_provider = None
    if provider_type == "openrouter":
        new_provider = OpenRouterProvider(
            api_key=app_state.openrouter_api_key,
            model=app_state.openrouter_model
        )
    elif provider_type == "google":
        new_provider = ollama_provider # Placeholder
    else:
        new_provider = ollama_provider
        
    _cached_provider = new_provider
    _cached_settings_hash = settings_hash
    return new_provider

def ask_ai_worker(q, phrase, with_context):
    """Воркер для генерации перевода через выбранный AI"""
    try:
        provider = get_current_ai_provider()
        
        # Для Ollama модель берется из app_state или виджетов (для обратной совместимости)
        # Для OpenRouter модель уже внутри провайдера
        model = None
        if provider.name == "Ollama":
             if app_state.main_window_components and "vars" in app_state.main_window_components:
                 # Пытаемся взять из Var, если он есть, иначе из app_state
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
        
        # Используем существующий сигнал ollama_ok для совместимости с UI
        q.put(("ollama_ok", (translation, context)))
    except Exception as e:
        q.put(("ollama_error", e))


def get_ollama_models():
    """Получает список моделей Ollama"""
    models = ollama_provider.get_models()
    if not models and not ollama_provider.is_available():
        return "OLLAMA_CONNECT_ERROR"
    return models


# =====================================================================================
# ANKI OPERATIONS
# =====================================================================================
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


# =====================================================================================
# CLIPBOARD WORKER
# =====================================================================================
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
                # print(f"💓 Heartbeat: worker жив, PAUSE={app_state.pause_clipboard_monitoring}")
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


def process_clipboard_queue(root):
    """Обрабатывает очередь буфера обмена"""
    if not root or not root.winfo_exists():
        return
    
    try:
        new_text = app_state.clipboard_queue.get_nowait()
        print(f"📥 Обработка текста из очереди: {len(new_text)} символов")
        
        widgets = app_state.main_window_components["widgets"]
        tvars = app_state.main_window_components["vars"]
        app_state.main_window_components["original_phrase"] = new_text
        
        widgets["german_text"].delete("1.0", tk.END)
        widgets["german_text"].insert("1.0", format_clipboard_text(new_text))
        widgets["translation_text"].delete("1.0", tk.END)
        widgets["context_widget"].delete("1.0", tk.END)
        
        root.deiconify()
        root.focus_force()
        widgets["german_text"].focus_set()
        
        auto_gen_enabled = app_state.get_checkbox_value("auto_generate_var", default=False)
        if auto_gen_enabled:
            print(f"🤖 Автогенерация включена, запуск генерации")
            update_processing_indicator(animate=True)
            app_state.main_window_components["generate_function"]()
    except queue.Empty:
        pass
    except Exception as e:
        print(f"❌ Ошибка в process_clipboard_queue: {e}")
    finally:
        if root and root.winfo_exists():
            root.after(50, process_clipboard_queue, root)


def process_results_queue(root):
    """Обрабатывает очередь результатов"""
    try:
        message, data = app_state.results_queue.get_nowait()
        widgets = app_state.main_window_components["widgets"]
        tvars = app_state.main_window_components["vars"]
        
        if message == "ollama_ok":
            app_state.generation_running = False
            translation, context = data
            widgets["translation_text"].delete("1.0", tk.END)
            widgets["translation_text"].insert("1.0", translation)
            widgets["context_widget"].delete("1.0", tk.END)
            widgets["context_widget"].insert("1.0", context)
            widgets["generate_btn"].configure(text="Генерировать", state="normal", fg_color="#2CC985", hover_color="#26AD72", text_color="white")
            widgets["stop_btn"].configure(state="disabled")
            update_processing_indicator("✅ Готово", animate=False)
            root.after(2000, lambda: update_processing_indicator("", animate=False))
            
            auto_add_var = tvars.get("auto_add_to_anki_var")
            if auto_add_var and auto_add_var.get():
                print("🤖 Авто-добавление в Anki...")
                root.after(100, app_state.main_window_components.get("on_yes_action_func", lambda: None))
                
        elif message == "ollama_error":
            app_state.generation_running = False
            err_str = str(data)
            is_conn = err_str == "OLLAMA_CONNECT_ERROR"
            update_processing_indicator(f"❌ {'Ollama недоступен' if is_conn else 'Ошибка'}", animate=False)
            if not is_conn:
                messagebox.showerror("Ошибка Ollama", err_str)
            widgets["generate_btn"].configure(text="Генерировать", state="normal")
            widgets["stop_btn"].configure(state="disabled")
            root.after(3000, lambda: update_processing_indicator("", animate=False))
            
        elif message == "audio_ok":
            audio_path = data
            update_processing_indicator("📤 Добавление...", animate=False)
            
            raw_deck_name = tvars["deck_var"].get().strip() or DEFAULT_DECK_NAME
            deck_name = anki_api.clean_deck_name(raw_deck_name)
            
            threading.Thread(target=add_to_anki_worker, args=(
                app_state.results_queue,
                widgets["german_text"].get("1.0", tk.END).strip(),
                widgets["translation_text"].get("1.0", tk.END).strip(),
                widgets["context_widget"].get("1.0", tk.END).strip(),
                deck_name,
                audio_path, False, app_state.force_replace_flag
            ), daemon=True).start()
            
        elif message == "anki_duplicate":
            phrase, translation, context, deck_name, audio_path, existing_ids = data
            if messagebox.askyesno("Дубликат обнаружен", 
                                   f"В Anki уже есть карточка с фразой:\n\"{phrase}\"\n\nУдалить старую версию и добавить новую?", 
                                   parent=root):
                update_processing_indicator("🗑 Удаление...", animate=False)
                
                def delete_and_add_worker():
                    if anki_api.delete_notes(existing_ids):
                        add_to_anki_worker(app_state.results_queue, phrase, translation, context, deck_name, audio_path, confirm_delete=True)
                    else:
                        app_state.results_queue.put(("anki_error", "Не удалось удалить старую версию карточки."))
                
                threading.Thread(target=delete_and_add_worker, daemon=True).start()
            else:
                if audio_path and os.path.exists(audio_path):
                    try:
                        os.remove(audio_path)
                    except OSError:
                        pass
                update_processing_indicator("Отменено", animate=False)
                root.after(2000, lambda: update_processing_indicator("", animate=False))
                
        elif message == "audio_error":
            messagebox.showerror("Ошибка озвучки", f"Не удалось создать аудиофайл: {data}")
            update_processing_indicator("❌ Ошибка", animate=False)
            root.after(3000, lambda: update_processing_indicator("", animate=False))
            
        elif message == "anki_ok":
            if data:
                app_state.force_replace_flag = False
                audio_utils.play_sound("success")
                widgets["add_btn"].configure(fg_color="#2CC985", hover_color="#26AD72", text_color="white")
                update_processing_indicator("✅ Готово!", animate=False)
                root.after(1500, app_state.main_window_components["on_action_complete"])
                root.after(2000, lambda: update_processing_indicator("", animate=False))
                
        elif message == "anki_error":
            messagebox.showerror("Ошибка Anki", f"Не удалось добавить в Anki:\n{data}")
            update_processing_indicator("❌ Ошибка", animate=False)
            root.after(3000, lambda: update_processing_indicator("", animate=False))
            
        elif message == "models_ok":
            # Модели загружены — обновляем app_state и индикатор
            if data == "OLLAMA_CONNECT_ERROR":
                print("⚠️ Ollama недоступен")
                if "ai_model_label" in widgets:
                    widgets["ai_model_label"].configure(text="⚠️ Ollama недоступен", text_color="#ff5555")
            elif data:
                # Если текущая модель пуста или не в списке — ставим первую
                current_model = app_state.ollama_model or tvars.get("ollama_var", tk.StringVar()).get()
                if not current_model or current_model not in data:
                    app_state.ollama_model = data[0]
                    if "ollama_var" in tvars:
                        tvars["ollama_var"].set(data[0])
                    # Обновляем индикатор
                    if "ai_model_label" in widgets:
                        widgets["ai_model_label"].configure(text=f"⚡ {data[0]}")
                print(f"✅ Ollama модели загружены: {len(data)} шт, текущая: {app_state.ollama_model}")
                
        elif message == "decks_ok":
            var = tvars["deck_var"]
            combo = widgets["deck_combo"]
            
            if data == "ANKI_CONNECT_ERROR":
                combo.configure(values=["AnkiConnect недоступен"], state="disabled")
                var.set("AnkiConnect недоступен")
            elif data:
                combo.configure(state="normal", values=data)
                settings = load_settings(update_app_state=False)
                last_deck = settings.get("LAST_DECK", "")
                
                found = False
                if last_deck:
                    for deck in data:
                        if anki_api.clean_deck_name(deck) == last_deck:
                            var.set(deck)
                            found = True
                            break
                
                if not found and data:
                    var.set(data[0])
                            
        elif message in ["models_error", "decks_error"]:
            pass
            
    except queue.Empty:
        pass
    except Exception as e:
        print(f"❌ Ошибка в process_results_queue: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if root and root.winfo_exists():
            root.after(50, process_results_queue, root)


def ensure_data_setup():
    """Создает внешние папки и копирует ресурсы при первом запуске"""
    import shutil
    from core.settings_manager import get_data_dir, get_user_dir, get_resource_path
    
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
        # Копируем файлы справки из ресурсов
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


# =====================================================================================
# MAIN FUNCTION
# =====================================================================================
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
    dependencies.TTS_LANG = app_state.tts.lang
    dependencies.TTS_SPEED_LEVEL = app_state.tts.speed_level
    dependencies.TTS_TLD = app_state.tts.tld
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
            except:
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
                        widgets["generate_btn"].configure(text="Генерировать", state="normal", fg_color="#2CC985", text_color="white")
                        return

                # Таймер уже запущен
                # app_state.generation_running = True (уже True)
                
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
            
            def _restore_btn():
                if app_state.main_window_components["widgets"]["add_btn"].winfo_exists():
                    app_state.main_window_components["widgets"]["add_btn"].configure(state="normal", text="В Anki")
            root.after(1000, _restore_btn)

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
