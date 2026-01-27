# -*- coding: utf-8 -*-
"""
Обработка очередей сообщений.
"""
import tkinter as tk
from tkinter import messagebox
import queue
import threading
import os

from core.app_state import app_state
from core.settings_manager import load_settings, DEFAULT_DECK_NAME
from core import audio_utils
from api.anki_api import anki_api
from core.workers import add_to_anki_worker, format_clipboard_text
from core.ui_callbacks import update_processing_indicator


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
            if data == "OLLAMA_CONNECT_ERROR":
                print("⚠️ Ollama недоступен")
                if "ai_model_label" in widgets:
                    widgets["ai_model_label"].configure(text="⚠️ Ollama недоступен", text_color="#ff5555")
            elif data:
                current_model = app_state.ollama_model or tvars.get("ollama_var", tk.StringVar()).get()
                if not current_model or current_model not in data:
                    app_state.ollama_model = data[0]
                    if "ollama_var" in tvars:
                        tvars["ollama_var"].set(data[0])
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
