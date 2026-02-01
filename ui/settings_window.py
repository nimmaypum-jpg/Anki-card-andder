# -*- coding: utf-8 -*-
"""
Окно настроек приложения.
Вкладки: Озвучка, Промпты, AI, Шрифт, Тема.

Refactored: TTS, Font, Theme tabs extracted to ui/settings/ package.
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading

from core import audio_utils
from ui.theme_manager import theme_manager
from core.clipboard_manager import setup_text_widget_context_menu
from core.settings_manager import save_settings, get_user_dir
from core.prompts_manager import prompts_manager, update_active_prompts, rename_prompt_preset
from core.app_state import app_state
from ui.main_window import ask_string_dialog
from core.localization import localization_manager

# Импорт извлеченных модулей вкладок
from ui.settings.tts_tab import create_tts_tab
from ui.settings.font_tab import create_font_tab
from ui.settings.theme_tab import create_theme_tab


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
    win.title(localization_manager.get_text("settings"))
    win.geometry("700x750")
    win.transient(parent)
    win.grab_set()
    
    tabview = ctk.CTkTabview(win)
    tabview.pack(fill="both", expand=True, padx=10, pady=10)
    
    tab_tts = tabview.add(localization_manager.get_text("tab_audio"))
    tab_prompts = tabview.add(localization_manager.get_text("tab_prompts"))
    tab_ai = tabview.add(localization_manager.get_text("tab_ai"))
    tab_font = tabview.add(localization_manager.get_text("tab_font"))
    tab_theme = tabview.add(localization_manager.get_text("tab_theme"))
    
    # Восстанавливаем последнюю вкладку или используем запрошенную
    default_tab = localization_manager.get_text("tab_audio")
    target_tab = initial_tab if initial_tab else settings.get("LAST_SETTINGS_TAB", default_tab)
    
    tab_names = [
        localization_manager.get_text("tab_audio"),
        localization_manager.get_text("tab_prompts"),
        localization_manager.get_text("tab_ai"),
        localization_manager.get_text("tab_font"),
        localization_manager.get_text("tab_theme")
    ]
    if target_tab in tab_names:
        tabview.set(target_tab)

    # Функция для добавления кнопки помощи на вкладку
    def add_help_btn(parent_frame, title, file):
        from ui.main_window import show_help_window
        btn = ctk.CTkButton(parent_frame, text="?", width=25, height=25, 
                           command=lambda: show_help_window(title, file))
        btn.place(relx=1.0, rely=0.0, anchor="ne", x=-5, y=5)

    # Добавляем кнопки помощи
    add_help_btn(tab_tts, localization_manager.get_text("tab_audio"), "Settings_Audio_Help.txt")
    add_help_btn(tab_ai, localization_manager.get_text("tab_ai"), "Settings_AI_Help.txt")
    add_help_btn(tab_prompts, localization_manager.get_text("tab_prompts"), "Main_Window_Help.txt")
    
    # === TTS Settings (извлечено в отдельный модуль) ===
    tts_vars = create_tts_tab(tab_tts, settings, win)
    
    # === Font Settings (извлечено в отдельный модуль) ===
    font_vars = create_font_tab(tab_font, settings, win)
    
    # === Theme Settings (извлечено в отдельный модуль) ===
    theme_vars = create_theme_tab(tab_theme, settings, win)
    
    # === AI Settings ===
    ai_vars = _create_ai_tab(tab_ai, settings, win)
    
    # === Prompts Settings ===
    prompts_vars = _create_prompts_tab(tab_prompts, settings, win)
    
    # === Save and Close ===
    def save_and_close():
        # Сохраняем текущую вкладку
        settings["LAST_SETTINGS_TAB"] = tabview.get()
        
        # TTS настройки
        settings["TTS_SPEED_LEVEL"] = tts_vars["speed_map"].get(tts_vars["speed_var"].get(), 0)
        settings["TTS_LANG"] = tts_vars["lang_var"].get()
        settings["TTS_TLD"] = tts_vars["tld_var"].get()
        
        # AI настройки
        settings["AI_PROVIDER"] = ai_vars["provider_var"].get()
        settings["OLLAMA_URL"] = ai_vars["ollama_url_var"].get()
        settings["OLLAMA_MODEL"] = ai_vars["ollama_model_var"].get()
        settings["OPENROUTER_API_KEY"] = ai_vars["openrouter_key_var"].get()
        settings["OPENROUTER_MODEL"] = ai_vars["openrouter_model_var"].get()
        settings["GOOGLE_API_KEY"] = ai_vars["google_key_var"].get()
        settings["UI_LANGUAGE"] = theme_vars["language_map"].get(theme_vars["language_var"].get(), "ru")
        
        # Промпты
        settings["TRANSLATE_PROMPT"] = prompts_vars["translate_editor"].get("1.0", "end-1c")
        settings["CONTEXT_PROMPT"] = prompts_vars["context_editor"].get("1.0", "end-1c")
        
        # Шрифт
        settings["FONT_FAMILY"] = font_vars["font_family_var"].get()
        settings["FONT_SIZE"] = int(font_vars["font_size_var"].get())
        
        current_preset = prompts_vars["preset_var"].get()
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
        _update_main_window_model_indicator(settings)
        
        # Сохраняем в файл
        save_settings(settings)
        
        # Обновляем список промптов в главном окне
        _update_main_window_prompts()
        
        win.destroy()
    
    ctk.CTkButton(win, text=localization_manager.get_text("ok"), command=save_and_close, width=150, height=35, fg_color="#2CC985", hover_color="#26AD72").pack(pady=10)


def _create_ai_tab(tab_ai, settings, win):
    """Создает содержимое вкладки AI."""
    ctk.CTkLabel(tab_ai, text=localization_manager.get_text("ai_provider_settings"), font=("Roboto", 16, "bold")).pack(anchor="w", padx=10, pady=(10, 15))
    
    # Провайдер AI
    provider_row = ctk.CTkFrame(tab_ai, fg_color="transparent")
    provider_row.pack(fill="x", padx=10, pady=(0, 10))
    
    ctk.CTkLabel(provider_row, text=localization_manager.get_text("provider_label")).pack(side="left", padx=(0, 10))
    provider_var = tk.StringVar(value=settings.get("AI_PROVIDER", "ollama"))
    provider_combo = ctk.CTkComboBox(provider_row, variable=provider_var, values=["ollama", "openrouter", "google"], width=150)
    provider_combo.pack(side="left")
    
    # Контейнер для настроек провайдеров
    provider_settings_container = ctk.CTkFrame(tab_ai)
    provider_settings_container.pack(fill="both", expand=True, padx=10, pady=5)
    
    # === Ollama настройки ===
    ollama_frame = ctk.CTkFrame(provider_settings_container)
    
    ctk.CTkLabel(ollama_frame, text="⚡ " + localization_manager.get_text("ollama_local"), font=("Roboto", 14, "bold")).pack(anchor="w", padx=10, pady=(10, 15))
    
    ctk.CTkLabel(ollama_frame, text=localization_manager.get_text("server_url")).pack(anchor="w", padx=10)
    ollama_url_var = tk.StringVar(value=settings.get("OLLAMA_URL", "http://localhost:11434"))
    ollama_url_entry = ctk.CTkEntry(ollama_frame, textvariable=ollama_url_var, width=350)
    ollama_url_entry.pack(anchor="w", padx=10, pady=(0, 15))
    setup_text_widget_context_menu(ollama_url_entry)
    
    ctk.CTkLabel(ollama_frame, text=f"{localization_manager.get_text('model_label')}:").pack(anchor="w", padx=10)
    model_row = ctk.CTkFrame(ollama_frame, fg_color="transparent")
    model_row.pack(fill="x", padx=10, pady=(0, 10))
    
    ollama_model_var = tk.StringVar(value=settings.get("OLLAMA_MODEL", ""))
    ollama_model_combo = ctk.CTkComboBox(model_row, variable=ollama_model_var, values=[settings.get("OLLAMA_MODEL", localization_manager.get_text("loading"))], width=280)
    ollama_model_combo.pack(side="left")
    
    def refresh_ollama_models():
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
            else:
                messagebox.showwarning(localization_manager.get_text("warning"), "Не удалось загрузить модели.\nПроверьте, запущен ли Ollama.", parent=win)
        except Exception as e:
            messagebox.showerror(localization_manager.get_text("error"), f"Ошибка загрузки моделей:\n{e}", parent=win)
    
    ollama_refresh_btn = ctk.CTkButton(model_row, text=localization_manager.get_text("refresh_decks"), command=refresh_ollama_models, width=100)
    ollama_refresh_btn.pack(side="left", padx=10)
    
    # === OpenRouter настройки ===
    openrouter_frame = ctk.CTkFrame(provider_settings_container)
    
    ctk.CTkLabel(openrouter_frame, text="🌐 " + localization_manager.get_text("openrouter_cloud"), font=("Roboto", 14, "bold")).pack(anchor="w", padx=10, pady=(10, 15))
    
    ctk.CTkLabel(openrouter_frame, text=localization_manager.get_text("api_key_label")).pack(anchor="w", padx=10)
    openrouter_key_var = tk.StringVar(value=settings.get("OPENROUTER_API_KEY", ""))
    openrouter_key_entry = ctk.CTkEntry(openrouter_frame, textvariable=openrouter_key_var, width=400, show="•")
    openrouter_key_entry.pack(anchor="w", padx=10, pady=(0, 15))
    setup_text_widget_context_menu(openrouter_key_entry)
    
    ctk.CTkLabel(openrouter_frame, text=localization_manager.get_text("model_label")).pack(anchor="w", padx=10)
    openrouter_model_var = tk.StringVar(value=settings.get("OPENROUTER_MODEL", "openai/gpt-4o-mini"))
    openrouter_model_entry = ctk.CTkEntry(openrouter_frame, textvariable=openrouter_model_var, width=320)
    openrouter_model_entry.pack(anchor="w", padx=10, pady=(0, 10))
    setup_text_widget_context_menu(openrouter_model_entry)
    
    ctk.CTkLabel(openrouter_frame, text=localization_manager.get_text("select_or_enter_manually"), text_color="#888888", font=("Roboto", 11)).pack(anchor="w", padx=10, pady=(0, 10))
    
    # === Google AI настройки ===
    google_frame = ctk.CTkFrame(provider_settings_container)
    
    ctk.CTkLabel(google_frame, text="🔮 " + localization_manager.get_text("google_gemini"), font=("Roboto", 14, "bold")).pack(anchor="w", padx=10, pady=(10, 15))
    
    ctk.CTkLabel(google_frame, text=localization_manager.get_text("api_key_label")).pack(anchor="w", padx=10)
    google_key_var = tk.StringVar(value=settings.get("GOOGLE_API_KEY", ""))
    google_key_entry = ctk.CTkEntry(google_frame, textvariable=google_key_var, width=400, show="•")
    google_key_entry.pack(anchor="w", padx=10, pady=(0, 15))
    setup_text_widget_context_menu(google_key_entry)
    
    ctk.CTkLabel(google_frame, text="⚠️ " + localization_manager.get_text("coming_soon"), text_color="#FFD700", font=("Roboto", 12)).pack(anchor="w", padx=10, pady=10)
    
    # Словарь фреймов провайдеров
    provider_frames = {
        "ollama": ollama_frame,
        "openrouter": openrouter_frame,
        "google": google_frame
    }
    
    def show_provider_settings(provider_name):
        for name, frame in provider_frames.items():
            if name == provider_name:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()
    
    show_provider_settings(provider_var.get())
    provider_combo.configure(command=show_provider_settings)
    
    # Кнопка проверки подключения
    def test_connection():
        current_provider = provider_var.get()
        if current_provider == "ollama":
            try:
                from api.ai.ollama_provider import OllamaProvider
                url = ollama_url_var.get().strip() or "http://localhost:11434"
                provider = OllamaProvider(api_url=url)
                if provider.is_available():
                    messagebox.showinfo(localization_manager.get_text("success"), "✅ Ollama подключен успешно!", parent=win)
                else:
                    messagebox.showwarning(localization_manager.get_text("warning"), "❌ Ollama недоступен.", parent=win)
            except Exception as e:
                messagebox.showerror(localization_manager.get_text("error"), f"❌ Ошибка:\n{e}", parent=win)
        elif current_provider == "openrouter":
            if openrouter_key_var.get().strip():
                messagebox.showinfo(localization_manager.get_text("success"), "✅ Ключ сохранён", parent=win)
            else:
                messagebox.showwarning(localization_manager.get_text("warning"), localization_manager.get_text("enter_api_key_warning"), parent=win)
        elif current_provider == "google":
            if google_key_var.get().strip():
                messagebox.showinfo(localization_manager.get_text("success"), "✅ Ключ сохранён", parent=win)
            else:
                messagebox.showwarning(localization_manager.get_text("warning"), localization_manager.get_text("enter_api_key_warning"), parent=win)
    
    ctk.CTkButton(tab_ai, text="🔗 " + localization_manager.get_text("check_connection"), command=test_connection, width=200, height=35, fg_color="#1f538d").pack(pady=15)
    
    return {
        "provider_var": provider_var,
        "ollama_url_var": ollama_url_var,
        "ollama_model_var": ollama_model_var,
        "openrouter_key_var": openrouter_key_var,
        "openrouter_model_var": openrouter_model_var,
        "google_key_var": google_key_var
    }


def _create_prompts_tab(tab_prompts, settings, win):
    """Создает содержимое вкладки Промптов."""
    presets = prompts_manager.load_prompts(force_reload=True)
    preset_names = prompts_manager.get_preset_names()
    
    def sync_with_main(name, tr, ctx):
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
        
        new_name = ask_string_dialog(win, localization_manager.get_text("rename"), f"{localization_manager.get_text('rename')} '{old_name}':", initial_value=old_name)
        if new_name and new_name != old_name:
            if rename_prompt_preset(old_name, new_name):
                presets[new_name] = presets.pop(old_name)
                names = sorted(presets.keys())
                preset_combo.configure(values=names)
                preset_var.set(new_name)
                messagebox.showinfo(localization_manager.get_text("success"), f"Пресет переименован в '{new_name}'.", parent=win)
    
    ctk.CTkLabel(tab_prompts, text=localization_manager.get_text("preset_label")).pack(anchor="w", padx=5)
    
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
    
    ctk.CTkButton(preset_row, text="✏️ " + localization_manager.get_text("rename"), command=rename_preset, width=130).pack(side="left", padx=(10, 0))
    
    ctk.CTkLabel(tab_prompts, text=localization_manager.get_text("translate_prompt_label")).pack(anchor="w", padx=5)
    translate_editor = ctk.CTkTextbox(tab_prompts, height=100)
    translate_editor.pack(fill="x", padx=5, pady=5)
    translate_editor.insert("1.0", settings.get("TRANSLATE_PROMPT", ""))
    setup_text_widget_context_menu(translate_editor)
    
    ctk.CTkLabel(tab_prompts, text=localization_manager.get_text("context_prompt_label")).pack(anchor="w", padx=5)
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
            messagebox.showinfo(localization_manager.get_text("success"), f"Пресет '{name}' сохранен.", parent=win)
    
    def delete_preset():
        name = preset_var.get()
        if name in presets and messagebox.askyesno(localization_manager.get_text("delete"), f"Удалить '{name}'?", parent=win):
            del presets[name]
            sync_prompts("")
            translate_editor.delete("1.0", tk.END)
            context_editor.delete("1.0", tk.END)
    
    btn_frame = ctk.CTkFrame(tab_prompts, fg_color="transparent")
    btn_frame.pack(fill="x", padx=5, pady=10)
    ctk.CTkButton(btn_frame, text=localization_manager.get_text("save"), command=save_preset, width=100).pack(side="left", padx=5)
    ctk.CTkButton(btn_frame, text=localization_manager.get_text("new_prompt"), command=lambda: save_preset(True), width=120).pack(side="left", padx=5)
    ctk.CTkButton(btn_frame, text="🗑 " + localization_manager.get_text("delete"), command=delete_preset, width=100, fg_color="#ff5555", hover_color="#d63c3c").pack(side="left", padx=5)
    
    return {
        "preset_var": preset_var,
        "translate_editor": translate_editor,
        "context_editor": context_editor,
        "presets": presets
    }


def _update_main_window_model_indicator(settings):
    """Обновляет индикатор модели в главном окне."""
    try:
        if app_state.main_window_components and "widgets" in app_state.main_window_components:
            widgets = app_state.main_window_components["widgets"]
            
            provider = settings["AI_PROVIDER"]
            display_model = "Неизвестно"
            if provider == "ollama":
                display_model = settings["OLLAMA_MODEL"]
                app_state.ollama_model = settings["OLLAMA_MODEL"]
            elif provider == "openrouter":
                display_model = settings["OPENROUTER_MODEL"]
            elif provider == "google":
                display_model = "Gemini"
            
            if "ai_model_label" in widgets:
                widgets["ai_model_label"].configure(text=f"⚡ {display_model}")
                
            if "vars" in app_state.main_window_components:
                tvars = app_state.main_window_components["vars"]
                if "ollama_var" in tvars:
                    tvars["ollama_var"].set(display_model)
    except Exception as e:
        print(f"Ошибка обновления индикатора модели: {e}")


def _update_main_window_prompts():
    """Обновляет список промптов в главном окне."""
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
