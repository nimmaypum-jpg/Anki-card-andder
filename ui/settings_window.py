# -*- coding: utf-8 -*-
"""
Окно настроек приложения.
Вкладки: Озвучка, Промпты, AI, Шрифт, Тема.
"""
import customtkinter as ctk
from customtkinter import CTkInputDialog
import tkinter as tk
from tkinter import messagebox
import threading
import os
import json

from core import audio_utils
from ui.theme_manager import theme_manager
from core.clipboard_manager import setup_text_widget_context_menu
from core.settings_manager import save_settings, get_user_dir
from core.prompts_manager import prompts_manager, update_active_prompts, rename_prompt_preset
from core.app_state import app_state
from ui.main_window import ask_string_dialog


def open_settings_window(parent, dependencies=None, settings=None, initial_tab=None):
    """
    Открывает окно настроек.
    
    Args:
        parent: Родительское окно
        dependencies: Объект с зависимостями (TTS настройки и т.д.)
        settings: Текущие настройки (если None, загружаются)
        initial_tab: Название вкладки для открытия (переопределяет сохраненную)
    """
    from core.settings_manager import load_settings
    
    if settings is None:
        settings = load_settings(update_app_state=False)
    
    win = ctk.CTkToplevel(parent)
    win.title("Настройки")
    win.geometry("700x750")
    win.transient(parent)
    win.grab_set()
    # win.attributes("-topmost", True) - Убрано по просьбе пользователя
    
    tabview = ctk.CTkTabview(win)
    tabview.pack(fill="both", expand=True, padx=10, pady=10)
    
    tab_tts = tabview.add("Озвучка")
    tab_prompts = tabview.add("Промпты")
    tab_ai = tabview.add("AI")
    tab_font = tabview.add("Шрифт")
    tab_theme = tabview.add("Тема")
    
    # Восстанавливаем последнюю вкладку или используем запрошенную
    target_tab = initial_tab if initial_tab else settings.get("LAST_SETTINGS_TAB", "Озвучка")
    
    tab_names = ["Озвучка", "Промпты", "AI", "Шрифт", "Тема"]
    if target_tab in tab_names:
        tabview.set(target_tab)

    # Функция для добавления кнопки помощи на вкладку
    def add_help_btn(parent, title, file):
        from ui.main_window import show_help_window
        btn = ctk.CTkButton(parent, text="?", width=25, height=25, 
                           command=lambda: show_help_window(title, file))
        btn.place(relx=1.0, rely=0.0, anchor="ne", x=-5, y=5)

    # Добавляем кнопки помощи
    add_help_btn(tab_tts, "Озвучка", "Settings_Audio_Help.txt")
    add_help_btn(tab_ai, "AI", "Settings_AI_Help.txt")
    add_help_btn(tab_prompts, "Промпты", "Main_Window_Help.txt") # Используем общую справку
    
    # Настройка контекстного меню теперь через clipboard_manager
    # Функция add_context_menu больше не нужна, используем setup_text_widget_context_menu
    
    # === TTS Settings ===
    ctk.CTkLabel(tab_tts, text="Скорость озвучки:").pack(anchor="w", padx=10, pady=(10, 0))
    speed_map = {"1.0x (Норм)": 0, "0.8x (Медл)": 1, "0.5x (Очень медл)": 2}
    speed_map_rev = {v: k for k, v in speed_map.items()}
    speed_var = tk.StringVar(value=speed_map_rev.get(settings.get("TTS_SPEED_LEVEL", 0), "1.0x (Норм)"))
    speed_combo = ctk.CTkComboBox(tab_tts, variable=speed_var, values=list(speed_map.keys()))
    speed_combo.pack(anchor="w", padx=10, pady=(0, 10))
    
    ctk.CTkLabel(tab_tts, text="Язык (lang):").pack(anchor="w", padx=10)
    lang_var = tk.StringVar(value=settings.get("TTS_LANG", "de"))
    ctk.CTkComboBox(tab_tts, variable=lang_var, values=["de", "en", "ru", "fr", "es"]).pack(anchor="w", padx=10, pady=(0, 10))
    
    ctk.CTkLabel(tab_tts, text="Домен (tld):").pack(anchor="w", padx=10)
    tld_var = tk.StringVar(value=settings.get("TTS_TLD", "de"))
    ctk.CTkComboBox(tab_tts, variable=tld_var, values=["com", "de", "ru", "co.uk", "fr"]).pack(anchor="w", padx=10, pady=(0, 10))
    
    def test_tts():
        try:
            text = "Hallo, das ist ein kurzer Test."
            lang, level_name, tld = lang_var.get(), speed_var.get(), tld_var.get()
            speed_level = speed_map.get(level_name, 0)
            threading.Thread(target=lambda: audio_utils.test_tts(text, lang, speed_level, tld, parent=win), daemon=True).start()
        except Exception:
            pass
    
    ctk.CTkButton(tab_tts, text="🔊 Тест озвучки", command=test_tts).pack(padx=10, pady=20)
    
    # === AI Settings (NEW TAB) ===
    ctk.CTkLabel(tab_ai, text="Настройки AI провайдера", font=("Roboto", 16, "bold")).pack(anchor="w", padx=10, pady=(10, 15))
    
    # Провайдер AI
    provider_row = ctk.CTkFrame(tab_ai, fg_color="transparent")
    provider_row.pack(fill="x", padx=10, pady=(0, 10))
    
    ctk.CTkLabel(provider_row, text="Провайдер:").pack(side="left", padx=(0, 10))
    provider_var = tk.StringVar(value=settings.get("AI_PROVIDER", "ollama"))
    provider_combo = ctk.CTkComboBox(provider_row, variable=provider_var, values=["ollama", "openrouter", "google"], width=150)
    provider_combo.pack(side="left")
    
    # Контейнер для настроек провайдеров (динамический)
    provider_settings_container = ctk.CTkFrame(tab_ai)
    provider_settings_container.pack(fill="both", expand=True, padx=10, pady=5)
    
    # === Ollama настройки ===
    ollama_frame = ctk.CTkFrame(provider_settings_container)
    
    ctk.CTkLabel(ollama_frame, text="⚡ Ollama (локальный AI)", font=("Roboto", 14, "bold")).pack(anchor="w", padx=10, pady=(10, 15))
    
    ctk.CTkLabel(ollama_frame, text="URL сервера:").pack(anchor="w", padx=10)
    ollama_url_var = tk.StringVar(value=settings.get("OLLAMA_URL", "http://localhost:11434"))
    ollama_url_entry = ctk.CTkEntry(ollama_frame, textvariable=ollama_url_var, width=350)
    ollama_url_entry.pack(anchor="w", padx=10, pady=(0, 15))
    setup_text_widget_context_menu(ollama_url_entry)
    
    ctk.CTkLabel(ollama_frame, text="Модель:").pack(anchor="w", padx=10)
    model_row = ctk.CTkFrame(ollama_frame, fg_color="transparent")
    model_row.pack(fill="x", padx=10, pady=(0, 10))
    
    ollama_model_var = tk.StringVar(value=settings.get("OLLAMA_MODEL", ""))
    ollama_model_combo = ctk.CTkComboBox(model_row, variable=ollama_model_var, values=[settings.get("OLLAMA_MODEL", "Загрузка...")], width=280)
    ollama_model_combo.pack(side="left")
    
    
    def refresh_ollama_models():
        """Загружает список моделей с Ollama сервера"""
        btn = ollama_refresh_btn
        original_text = btn.cget("text")
        btn.configure(text="⏳...", state="disabled")
        win.update()
        
        try:
            from api.ai.ollama_provider import OllamaProvider
            url = ollama_url_var.get().strip() or "http://localhost:11434"
            provider = OllamaProvider(api_url=url)
            models = provider.get_models()
            
            if models:
                ollama_model_combo.configure(values=models)
                current = ollama_model_var.get()
                if not current or current not in models:
                    ollama_model_var.set(models[0])
                
                # Визуальное подтверждение успеха без попапа
                btn.configure(text="✅", fg_color="#2CC985")
                win.after(2000, lambda: btn.configure(text=original_text, fg_color=["#3a7ebf", "#1f538d"], state="normal"))
            else:
                btn.configure(text="❌", fg_color="#ff5555")
                win.after(2000, lambda: btn.configure(text=original_text, fg_color=["#3a7ebf", "#1f538d"], state="normal"))
                messagebox.showwarning("Предупреждение", "Не удалось загрузить модели.\nПроверьте, запущен ли Ollama.", parent=win)
                
        except Exception as e:
            btn.configure(text="❌", state="normal")
            win.after(2000, lambda: btn.configure(text=original_text))
            messagebox.showerror("Ошибка", f"Ошибка загрузки моделей:\n{e}", parent=win)
    
    ollama_refresh_btn = ctk.CTkButton(model_row, text="Загрузить", command=refresh_ollama_models, width=100)
    ollama_refresh_btn.pack(side="left", padx=10)
    
    # === OpenRouter настройки ===
    openrouter_frame = ctk.CTkFrame(provider_settings_container)
    
    # Заголовок и Пресеты
    or_header_frame = ctk.CTkFrame(openrouter_frame, fg_color="transparent")
    or_header_frame.pack(fill="x", padx=10, pady=(10, 15))
    
    ctk.CTkLabel(or_header_frame, text="🌐 OpenRouter (облачный AI)", font=("Roboto", 14, "bold")).pack(side="left")
    
    # Логика пресетов
    ai_presets = settings.get("AI_PRESETS", [])
    if not isinstance(ai_presets, list): ai_presets = []
    
    def get_preset_names():
        return [p.get("name", "Unknown") for p in ai_presets]

    ctk.CTkLabel(or_header_frame, text="Пресеты:", text_color="gray").pack(side="left", padx=(20, 5))
    
    def apply_preset(choice):
        for p in ai_presets:
            if p.get("name") == choice:
                 if p.get("api_key"): openrouter_key_var.set(p.get("api_key"))
                 if p.get("model"): openrouter_model_var.set(p.get("model"))
                 break
    
    p_names = get_preset_names()
    if not p_names: p_names = ["(Нет пресетов)"]
    preset_combo = ctk.CTkComboBox(or_header_frame, values=p_names, command=apply_preset, width=150)
    preset_combo.pack(side="left")
    if not get_preset_names():
        preset_combo.set("(Нет пресетов)")
    else:
        preset_combo.set("Загрузить...")
    
    def delete_preset_action():
        current = preset_combo.get()
        if not current or current in ["Загрузить...", "Нет пресетов", "(Нет пресетов)"]:
            return
        
        # Удаляем из списка
        idx = next((i for i, p in enumerate(ai_presets) if p.get("name") == current), -1)
        
        if idx >= 0:
            deleted_model = ai_presets[idx].get("model")
            ai_presets.pop(idx)
            settings["AI_PRESETS"] = ai_presets
            from core.settings_manager import save_settings
            save_settings(settings)
            
            # Обновляем комбобокс
            names = get_preset_names()
            if not names: names = ["(Нет пресетов)"]
            preset_combo.configure(values=names)
            
            if get_preset_names():
                preset_combo.set(names[0])
            else:
                preset_combo.set("(Нет пресетов)")
            
            # Обновляем звезду если нужно
            if openrouter_model_var.get() == deleted_model:
                update_star()
                
    trash_btn = ctk.CTkButton(or_header_frame, text="🗑", width=30, fg_color="transparent", hover_color="#333333", text_color="#ff5555", command=delete_preset_action, font=("Arial", 16))
    trash_btn.pack(side="left", padx=(5, 0))
    
    # API Ключ
    ctk.CTkLabel(openrouter_frame, text="API Ключ:").pack(anchor="w", padx=10)
    openrouter_key_var = tk.StringVar(value=settings.get("OPENROUTER_API_KEY", ""))
    openrouter_key_entry = ctk.CTkEntry(openrouter_frame, textvariable=openrouter_key_var, width=400, show="•")
    openrouter_key_entry.pack(anchor="w", padx=10, pady=(0, 15))
    setup_text_widget_context_menu(openrouter_key_entry)
    
    # Выбор модели из списка
    ctk.CTkLabel(openrouter_frame, text="Модель из списка:").pack(anchor="w", padx=10)
    or_model_select_row = ctk.CTkFrame(openrouter_frame, fg_color="transparent")
    or_model_select_row.pack(fill="x", padx=10, pady=(0, 10))
    
    openrouter_models_var = tk.StringVar(value="Нажмите 'Загрузить'")
    openrouter_models_combo = ctk.CTkComboBox(or_model_select_row, variable=openrouter_models_var, values=["Нажмите 'Загрузить'"], width=320, state="readonly")
    openrouter_models_combo.pack(side="left")
    
    # Хранилище загруженных моделей
    openrouter_loaded_models = {"data": []}
    
    def load_openrouter_models():
        """Загружает список моделей с OpenRouter (не требует API ключ)"""
        btn = openrouter_load_btn
        original_text = btn.cget("text")
        btn.configure(text="⏳...", state="disabled")
        win.update()
        
        try:
            import requests
            response = requests.get("https://openrouter.ai/api/v1/models", timeout=10)
            if response.status_code == 200:
                data = response.json().get("data", [])
                openrouter_loaded_models["data"] = data
                
                # Формируем список для dropdown: id (name)
                model_options = []
                for m in sorted(data, key=lambda x: x.get("id", "")):
                    model_id = m.get("id", "")
                    if model_id:
                        model_options.append(model_id)
                
                if model_options:
                    openrouter_models_combo.configure(values=model_options)
                    openrouter_models_var.set(model_options[0])
                    # Успех
                    btn.configure(text="✅", fg_color="#2CC985")
                    win.after(2000, lambda: btn.configure(text=original_text, fg_color=["#3a7ebf", "#1f538d"], state="normal"))
                else:
                    btn.configure(text="Пусто", fg_color="#ff5555")
                    win.after(2000, lambda: btn.configure(text=original_text, fg_color=["#3a7ebf", "#1f538d"], state="normal"))
            else:
                messagebox.showerror("Ошибка", f"Ошибка загрузки: HTTP {response.status_code}", parent=win)
                btn.configure(text=original_text, state="normal")
        except Exception as e:
            btn.configure(text="❌", state="normal")
            win.after(2000, lambda: btn.configure(text=original_text))
            messagebox.showerror("Ошибка", f"Ошибка загрузки моделей:\n{e}", parent=win)
    
    openrouter_load_btn = ctk.CTkButton(or_model_select_row, text="Загрузить", command=load_openrouter_models, width=100)
    openrouter_load_btn.pack(side="left", padx=10)
    
    # Текущая модель (ручной ввод или выбранная)

    # Текущая модель (ручной ввод или выбранная) с кнопкой сохранения
    ctk.CTkLabel(openrouter_frame, text="Текущая модель (используется для генерации):").pack(anchor="w", padx=10, pady=(5, 0))
    
    model_manual_row = ctk.CTkFrame(openrouter_frame, fg_color="transparent")
    model_manual_row.pack(fill="x", padx=10, pady=(0, 5))
    
    openrouter_model_var = tk.StringVar(value=settings.get("OPENROUTER_MODEL", "openai/gpt-4o-mini"))
    # Ширина такая же, как у комбобокса выше (~320)
    openrouter_model_entry = ctk.CTkEntry(model_manual_row, textvariable=openrouter_model_var, width=320) 
    openrouter_model_entry.pack(side="left")
    setup_text_widget_context_menu(openrouter_model_entry)
    
    # Кнопка "Звезда" (Избранное)
    star_btn = ctk.CTkButton(model_manual_row, text="☆", width=30, font=("Arial", 28), fg_color="transparent", hover_color="#333333", text_color="gray")
    star_btn.pack(side="left", padx=(5, 0))
    
    def update_star(*args):
        try:
            current_model = openrouter_model_var.get().strip()
            is_fav = any(p.get("model") == current_model for p in ai_presets)
            if is_fav:
                star_btn.configure(text="★", text_color="#FFD700") # Золотая звезда
            else:
                star_btn.configure(text="☆", text_color="gray")   # Пустая звезда
        except:
            pass
            
    # Следим за изменением текста модели
    openrouter_model_var.trace_add("write", update_star)

    def toggle_preset():
        current_model = openrouter_model_var.get().strip()
        current_key = openrouter_key_var.get().strip()
        
        if not current_model:
            return
            
        # Ищем, есть ли уже в избранном
        existing_index = next((i for i, p in enumerate(ai_presets) if p.get("model") == current_model), -1)
        
        if existing_index >= 0:
            # Удаляем
            ai_presets.pop(existing_index)
        else:
            # Добавляем (имя = модели)
            ai_presets.append({
                "name": current_model, 
                "model": current_model, 
                "api_key": current_key
            })
            
        settings["AI_PRESETS"] = ai_presets
        from core.settings_manager import save_settings
        save_settings(settings)
        
        update_star()
        names = get_preset_names()
        
        if not names: names = ["(Нет пресетов)"]
        preset_combo.configure(values=names)
        
        # Если добавили - можно поставить в комбобокс
        if existing_index == -1:
            preset_combo.set(current_model)
        else:
            if get_preset_names():
                preset_combo.set("Загрузить...")
            else:
                preset_combo.set("(Нет пресетов)")
            
    star_btn.configure(command=toggle_preset)
    
    # Инициализация состояния звезды
    win.after(100, update_star)
    
    # При выборе из списка — копируем в ручной ввод
    def on_openrouter_model_select(choice):
        openrouter_model_var.set(choice)
    
    openrouter_models_combo.configure(command=on_openrouter_model_select)
    
    ctk.CTkLabel(openrouter_frame, text="💡 Выберите из списка или введите вручную. Нажмите ★ чтобы сохранить в пресеты.", text_color="#888888", font=("Roboto", 11)).pack(anchor="w", padx=10, pady=(0, 10))
    
    # === Google AI настройки ===
    google_frame = ctk.CTkFrame(provider_settings_container)
    
    ctk.CTkLabel(google_frame, text="🔮 Google AI (Gemini)", font=("Roboto", 14, "bold")).pack(anchor="w", padx=10, pady=(10, 15))
    
    ctk.CTkLabel(google_frame, text="API Ключ:").pack(anchor="w", padx=10)
    google_key_var = tk.StringVar(value=settings.get("GOOGLE_API_KEY", ""))
    google_key_entry = ctk.CTkEntry(google_frame, textvariable=google_key_var, width=400, show="•")
    google_key_entry.pack(anchor="w", padx=10, pady=(0, 15))
    setup_text_widget_context_menu(google_key_entry)
    
    ctk.CTkLabel(google_frame, text="⚠️ Скоро будет доступно", text_color="#FFD700", font=("Roboto", 12)).pack(anchor="w", padx=10, pady=10)
    
    # Словарь фреймов провайдеров
    provider_frames = {
        "ollama": ollama_frame,
        "openrouter": openrouter_frame,
        "google": google_frame
    }
    
    def show_provider_settings(provider_name):
        """Показывает настройки выбранного провайдера, скрывает остальные"""
        for name, frame in provider_frames.items():
            if name == provider_name:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()
    
    # Показываем текущий провайдер
    show_provider_settings(provider_var.get())
    
    # При смене провайдера
    provider_combo.configure(command=show_provider_settings)
    
    # === Общая кнопка проверки подключения ===
    def test_connection():
        """Проверяет подключение к текущему провайдеру"""
        btn = test_btn
        original_text = btn.cget("text")
        btn.configure(text="⏳...", state="disabled")
        win.update()
        
        current_provider = provider_var.get()
        
        if current_provider == "ollama":
            try:
                from api.ai.ollama_provider import OllamaProvider
                # Исправлено: api_url вместо base_url
                url = ollama_url_var.get().strip() or "http://localhost:11434"
                provider = OllamaProvider(api_url=url)
                
                if provider.is_available():
                    models = provider.get_models()
                    # Успех
                    btn.configure(text="✅ Успешно", fg_color="#2CC985")
                    win.after(2000, lambda: btn.configure(text=original_text, fg_color="#1f538d", state="normal"))
                else:
                    btn.configure(text="❌ Недоступно", fg_color="#ff5555")
                    win.after(2000, lambda: btn.configure(text=original_text, fg_color="#1f538d", state="normal"))
                    messagebox.showwarning("Предупреждение", "❌ Ollama недоступен.\nПроверьте, запущен ли сервер.", parent=win)
            except Exception as e:
                btn.configure(text="❌ Ошибка", fg_color="#ff5555")
                win.after(2000, lambda: btn.configure(text=original_text, fg_color="#1f538d", state="normal"))
                messagebox.showerror("Ошибка", f"❌ Ошибка подключения:\n{e}", parent=win)
                
        elif current_provider == "openrouter":
            api_key = openrouter_key_var.get().strip()
            if not api_key:
                btn.configure(text="❌ Нет ключа", fg_color="#ff5555")
                win.after(2000, lambda: btn.configure(text=original_text, fg_color="#1f538d", state="normal"))
                messagebox.showwarning("Предупреждение", "Введите API ключ OpenRouter", parent=win)
            else:
                # В будущем можно делать реальный запрос на проверку баланса или моделей
                # Пока что просто имитируем проверку "ключа не пусто"
                btn.configure(text="✅ Ключ сохранён", fg_color="#2CC985")
                win.after(2000, lambda: btn.configure(text=original_text, fg_color="#1f538d", state="normal"))
                
        elif current_provider == "google":
            api_key = google_key_var.get().strip()
            if not api_key:
                btn.configure(text="❌ Нет ключа", fg_color="#ff5555")
                win.after(2000, lambda: btn.configure(text=original_text, fg_color="#1f538d", state="normal"))
                messagebox.showwarning("Предупреждение", "Введите API ключ Google AI", parent=win)
            else:
                btn.configure(text="✅ Ключ сохранён", fg_color="#2CC985")
                win.after(2000, lambda: btn.configure(text=original_text, fg_color="#1f538d", state="normal"))
                

    
    test_btn = ctk.CTkButton(tab_ai, text="🔗 Проверить подключение", command=test_connection, width=200, height=35, fg_color="#1f538d")
    test_btn.pack(pady=15)

    
    # === Prompts Settings ===
    presets = prompts_manager.load_prompts(force_reload=True)
    preset_names = prompts_manager.get_preset_names()
    
    def sync_with_main(name, tr, ctx):
        """Если отредактированный пресет — текущий, обновляем его на лету"""
        try:
            if app_state.main_window_components and "vars" in app_state.main_window_components:
                if app_state.main_window_components["vars"].get("prompt_var").get() == name:
                    update_active_prompts(tr, ctx)
        except Exception:
            pass

    def rename_preset():
        nonlocal presets
        old_name = preset_var.get()
        if not old_name or old_name not in presets:
            return
        
        new_name = ask_string_dialog(win, "Переименовать", f"Новое имя для '{old_name}':", initial_value=old_name)
        if new_name and new_name != old_name:
            if rename_prompt_preset(old_name, new_name):
                presets[new_name] = presets.pop(old_name)
                names = sorted(presets.keys())
                preset_combo.configure(values=names)
                preset_var.set(new_name)
                messagebox.showinfo("Успех", f"Пресет переименован в '{new_name}'.", parent=win)
    
    ctk.CTkLabel(tab_prompts, text="Выберите пресет:").pack(anchor="w", padx=5)
    
    # Инициализируем выбор из главного окна
    initial_preset = ""
    try:
        if app_state.main_window_components and "vars" in app_state.main_window_components:
            initial_preset = app_state.main_window_components["vars"].get("prompt_var", tk.StringVar()).get()
    except Exception:
        pass
    
    preset_var = tk.StringVar(value=initial_preset)
    
    preset_row = ctk.CTkFrame(tab_prompts, fg_color="transparent")
    preset_row.pack(fill="x", padx=5, pady=(0, 10))
    
    preset_combo = ctk.CTkComboBox(preset_row, variable=preset_var, values=preset_names)
    preset_combo.pack(side="left", fill="x", expand=True)
    
    ctk.CTkButton(preset_row, text="✏️ переименовать", command=rename_preset, width=130).pack(side="left", padx=(10, 0))
    
    ctk.CTkLabel(tab_prompts, text="Промпт перевода:").pack(anchor="w", padx=5)
    translate_editor = ctk.CTkTextbox(tab_prompts, height=100)
    translate_editor.pack(fill="x", padx=5, pady=5)
    translate_editor.insert("1.0", settings.get("TRANSLATE_PROMPT", ""))
    setup_text_widget_context_menu(translate_editor)
    
    ctk.CTkLabel(tab_prompts, text="Промпт контекста:").pack(anchor="w", padx=5)
    context_editor = ctk.CTkTextbox(tab_prompts, height=250)
    context_editor.pack(fill="both", expand=True, padx=5, pady=5)
    context_editor.insert("1.0", settings.get("CONTEXT_PROMPT", ""))
    setup_text_widget_context_menu(context_editor)
    
    def on_preset_select(choice):
        if choice in presets:
            translate_editor.delete("1.0", tk.END)
            translate_editor.insert("1.0", presets[choice].get("translate", presets[choice].get("translation", "")))
            context_editor.delete("1.0", tk.END)
            context_editor.insert("1.0", presets[choice].get("context", ""))
    
    preset_combo.configure(command=on_preset_select)
    
    def sync_prompts(new_name=None):
        """Сохраняет пресеты и обновляет UI"""
        try:
            prompts_manager.save_prompts(presets)
            names = sorted(presets.keys())
            preset_combo.configure(values=names)
            
            if app_state.main_window_components and "widgets" in app_state.main_window_components:
                mw = app_state.main_window_components
                if "prompt_combo" in mw["widgets"]:
                    mw["widgets"]["prompt_combo"].configure(values=names)
                    if new_name and "vars" in mw and "prompt_var" in mw["vars"]:
                        mw["vars"]["prompt_var"].set(new_name)
            if new_name:
                preset_var.set(new_name)
        except Exception as e:
            print(f"❌ Ошибка синхронизации промптов: {e}")
    
    def save_preset(is_new=False):
        name = ask_string_dialog(win, "Промпт", "Введите имя:") if is_new or not preset_var.get() else preset_var.get()
        if name:
            tr = translate_editor.get("1.0", "end-1c")
            ctx = context_editor.get("1.0", "end-1c")
            presets[name] = {"translate": tr, "context": ctx}
            sync_prompts(name)
            sync_with_main(name, tr, ctx)
            messagebox.showinfo("Успех", f"Пресет '{name}' {'создан' if is_new else 'сохранен'}.", parent=win)
    
    def delete_preset():
        name = preset_var.get()
        if name in presets and messagebox.askyesno("Удалить", f"Удалить '{name}'?", parent=win):
            del presets[name]
            sync_prompts("")
            translate_editor.delete("1.0", tk.END)
            context_editor.delete("1.0", tk.END)
    
    btn_frame = ctk.CTkFrame(tab_prompts, fg_color="transparent")
    btn_frame.pack(fill="x", padx=5, pady=10)
    ctk.CTkButton(btn_frame, text="Сохранить", command=save_preset, width=100).pack(side="left", padx=5)
    ctk.CTkButton(btn_frame, text="Новый промт", command=lambda: save_preset(True), width=120).pack(side="left", padx=5)
    ctk.CTkButton(btn_frame, text="🗑 Удалить", command=delete_preset, width=100, fg_color="#ff5555", hover_color="#d63c3c").pack(side="left", padx=5)
    
    # === Font Settings ===
    ctk.CTkLabel(tab_font, text="Семейство шрифта:").pack(anchor="w", padx=10, pady=(10, 5))
    font_family_var = tk.StringVar(value=settings.get("FONT_FAMILY", "Roboto"))
    font_families = ["Roboto", "Arial", "Segoe UI", "Consolas", "Courier New", "Times New Roman", "Verdana", "Tahoma"]
    ctk.CTkComboBox(tab_font, variable=font_family_var, values=font_families, width=200).pack(anchor="w", padx=10, pady=(0, 10))
    
    ctk.CTkLabel(tab_font, text="Размер шрифта:").pack(anchor="w", padx=10, pady=(10, 5))
    font_size_var = tk.StringVar(value=str(settings.get("FONT_SIZE", 14)))
    
    size_frame = ctk.CTkFrame(tab_font, fg_color="transparent")
    size_frame.pack(fill="x", padx=10, pady=(0, 10))
    
    size_slider = ctk.CTkSlider(size_frame, from_=10, to=24, number_of_steps=14, width=200)
    size_slider.set(int(font_size_var.get()))
    size_slider.pack(side="left", padx=(0, 10))
    
    size_label = ctk.CTkLabel(size_frame, text=f"{int(size_slider.get())} px", width=50)
    size_label.pack(side="left")
    
    def update_size_label(value):
        size_label.configure(text=f"{int(value)} px")
        font_size_var.set(str(int(value)))
        preview_text.configure(font=(font_family_var.get(), int(value)))
    
    size_slider.configure(command=update_size_label)
    
    ctk.CTkLabel(tab_font, text="Пример текста:").pack(anchor="w", padx=10, pady=(20, 5))
    preview_text = ctk.CTkTextbox(tab_font, height=80)
    preview_text.pack(fill="x", padx=10, pady=(0, 10))
    preview_text.insert("1.0", "Hallo! Das ist ein Beispieltext.\nПривет! Это пример текста.")
    preview_text.configure(font=(font_family_var.get(), int(font_size_var.get())))
    setup_text_widget_context_menu(preview_text)
    
    def update_preview_font(*args):
        try:
            preview_text.configure(font=(font_family_var.get(), int(font_size_var.get())))
        except Exception:
            pass
    
    font_family_var.trace_add("write", update_preview_font)
    
    # === Theme Settings ===
    appearance_mode_map = {"Темная": "Dark", "Светлая": "Light", "Системная": "System"}
    appearance_mode_map_rev = {v: k for k, v in appearance_mode_map.items()}
    
    ctk.CTkLabel(tab_theme, text="Режим отображения:").pack(anchor="w", padx=10, pady=10)
    
    current_mode = theme_manager.appearance_mode
    appearance_mode_var = tk.StringVar(value=appearance_mode_map_rev.get(current_mode, "Темная"))
    
    def change_appearance_mode(new_mode_display):
        try:
            new_mode = appearance_mode_map.get(new_mode_display, "Dark")
            if new_mode != theme_manager.appearance_mode:
                theme_manager.set_appearance_mode(new_mode)
        except Exception as e:
            print(f"Error changing appearance mode: {e}")
    
    ctk.CTkOptionMenu(tab_theme, values=list(appearance_mode_map.keys()), command=change_appearance_mode, variable=appearance_mode_var).pack(padx=10, pady=10)
    
    ctk.CTkLabel(tab_theme, text="Цветовая тема:").pack(anchor="w", padx=10, pady=10)
    
    color_theme_map = {"Синяя": "blue", "Зеленая": "green", "Темно-синяя": "dark-blue"}
    color_theme_map_rev = {v: k for k, v in color_theme_map.items()}
    
    current_theme = theme_manager.color_theme
    color_theme_var = tk.StringVar(value=color_theme_map_rev.get(current_theme, "Синяя"))
    
    def change_color_theme(new_theme_display):
        try:
            new_theme = color_theme_map.get(new_theme_display, "blue")
            theme_manager.set_color_theme(new_theme)
        except Exception:
            pass
    
    ctk.CTkOptionMenu(tab_theme, values=list(color_theme_map.keys()), command=change_color_theme, variable=color_theme_var).pack(padx=10, pady=10)
    
    # === Save and Close ===
    def save_and_close():
        # Сохраняем текущую вкладку
        settings["LAST_SETTINGS_TAB"] = tabview.get()
        
        # TTS настройки
        settings["TTS_SPEED_LEVEL"] = speed_map.get(speed_var.get(), 0)
        settings["TTS_LANG"] = lang_var.get()
        settings["TTS_TLD"] = tld_var.get()
        
        # AI настройки
        settings["AI_PROVIDER"] = provider_var.get()
        settings["OLLAMA_URL"] = ollama_url_var.get()
        settings["OLLAMA_MODEL"] = ollama_model_var.get()
        settings["OPENROUTER_API_KEY"] = openrouter_key_var.get()
        settings["OPENROUTER_MODEL"] = openrouter_model_var.get()
        settings["GOOGLE_API_KEY"] = google_key_var.get()
        
        # Промпты
        settings["TRANSLATE_PROMPT"] = translate_editor.get("1.0", "end-1c")
        settings["CONTEXT_PROMPT"] = context_editor.get("1.0", "end-1c")
        
        # Шрифт
        settings["FONT_FAMILY"] = font_family_var.get()
        settings["FONT_SIZE"] = int(font_size_var.get())
        
        current_preset = preset_var.get()
        if current_preset:
            settings["LAST_PROMPT"] = current_preset
            try:
                if app_state.main_window_components and "vars" in app_state.main_window_components:
                    app_state.main_window_components["vars"]["prompt_var"].set(current_preset)
            except Exception:
                pass
        
        # Обновляем app_state
        app_state.tts.speed_level = settings["TTS_SPEED_LEVEL"]
        app_state.tts.tld = settings["TTS_TLD"]
        app_state.tts.lang = settings["TTS_LANG"]
        
        # Обновляем AI настройки в app_state
        app_state.ai_provider = settings.get("AI_PROVIDER", "ollama")
        app_state.openrouter_api_key = settings.get("OPENROUTER_API_KEY", "")
        app_state.openrouter_model = settings.get("OPENROUTER_MODEL", "")
        app_state.google_api_key = settings.get("GOOGLE_API_KEY", "")
        
        # Обновляем зависимости для UI
        if dependencies:
            dependencies.TTS_SPEED_LEVEL = settings["TTS_SPEED_LEVEL"]
            dependencies.TTS_LANG = settings["TTS_LANG"]
            dependencies.TTS_TLD = settings["TTS_TLD"]
        
        audio_utils.update_tts_settings(settings["TTS_LANG"], settings["TTS_SPEED_LEVEL"], settings["TTS_TLD"])
        
        # Применяем шрифт
        apply_font_settings(settings["FONT_FAMILY"], settings["FONT_SIZE"])
        
        # Обновляем индикатор модели в главном окне
        try:
            if app_state.main_window_components and "widgets" in app_state.main_window_components:
                widgets = app_state.main_window_components["widgets"]
                
                # Определяем какую модель показывать
                provider = settings["AI_PROVIDER"]
                display_model = "Неизвестно"
                if provider == "ollama":
                    display_model = settings["OLLAMA_MODEL"]
                    app_state.ollama_model = settings["OLLAMA_MODEL"] # Сохраняем для обратной совместимости
                elif provider == "openrouter":
                    display_model = settings["OPENROUTER_MODEL"]
                elif provider == "google":
                    display_model = "Gemini"
                
                if "ai_model_label" in widgets:
                    widgets["ai_model_label"].configure(text=f"⚡ {display_model}")
                    
                # Обновляем ollama_var (используется как универсальная переменная активной модели в main.py пока что)
                if "vars" in app_state.main_window_components:
                    tvars = app_state.main_window_components["vars"]
                    if "ollama_var" in tvars:
                        tvars["ollama_var"].set(display_model)
        except Exception as e:
            print(f"Ошибка обновления индикатора модели: {e}")
        
        # Сохраняем в файл
        save_settings(settings)
        
        # Обновляем список промптов в главном окне
        try:
            if app_state.main_window_components and "widgets" in app_state.main_window_components:
                widgets = app_state.main_window_components["widgets"]
                tvars = app_state.main_window_components.get("vars", {})
                
                prompt_names = prompts_manager.get_preset_names()
                if "prompt_combo" in widgets:
                    widgets["prompt_combo"].configure(values=prompt_names)
                    
                    if "prompt_var" in tvars:
                        current_choice = tvars["prompt_var"].get()
                        if current_choice and current_choice in prompt_names:
                            tvars["prompt_var"].set(current_choice)
                        elif prompt_names:
                            tvars["prompt_var"].set(prompt_names[0])
        except Exception as e:
            print(f"Ошибка обновления промптов в главном окне: {e}")
        
        win.destroy()
    
    ctk.CTkButton(win, text="ОК", command=save_and_close, width=150, height=35, fg_color="#2CC985", hover_color="#26AD72").pack(pady=10)


def apply_font_settings(family: str, size: int):
    """Применяет настройки шрифта к виджетам главного окна"""
    try:
        widgets = app_state.main_window_components.get("widgets", {})
        font_tuple = (family, size)
        
        text_widgets = ["german_text", "translation_text", "context_widget"]
        for widget_name in text_widgets:
            widget = widgets.get(widget_name)
            if widget:
                widget.configure(font=font_tuple)
    except Exception as e:
        print(f"⚠️ Ошибка применения шрифта: {e}")
