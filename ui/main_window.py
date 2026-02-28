# -*- coding: utf-8 -*-
"""
Главное окно приложения Anki German Helper.
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import time
import os
import json
import sys

from core import audio_utils
from ui.theme_manager import theme_manager
from core.clipboard_manager import setup_text_widget_context_menu, GlobalClipboardManager
from core.localization import localization_manager


class ToolTip:
    """Класс для создания всплывающих подсказок"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
    
    def show_tooltip(self, event=None):
        if self.tooltip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 25
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        frame = tk.Frame(self.tooltip_window, background="#2b2b2b", relief="solid", borderwidth=1)
        frame.pack()
        label = tk.Label(frame, text=self.text, justify="left",
                        background="#2b2b2b", fg="#ffffff", relief="solid", borderwidth=0,
                        font=("Arial", 10), padx=5, pady=3)
        label.pack()
    
    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


def ask_string_dialog(parent, title, prompt, initial_value=""):
    """Универсальная функция для ввода текста с поддержкой буфера обмена
    Возвращает введенный текст или None если отменено
    """
    dialog = ctk.CTkToplevel(parent)
    dialog.title(title)
    dialog.geometry("450x180")
    dialog.transient(parent)
    dialog.grab_set()
    # dialog.attributes("-topmost", True)
    dialog.focus_force()
    
    result = [None]
    
    ctk.CTkLabel(dialog, text=prompt, font=("Roboto", 15)).pack(pady=(20, 10), padx=20)
    
    entry = ctk.CTkEntry(dialog, font=("Roboto", 15), height=35)
    entry.pack(pady=10, padx=20, fill="x")
    if initial_value:
        entry.insert(0, initial_value)
        entry.select_range(0, tk.END)
    entry.focus_set()
    
    setup_text_widget_context_menu(entry)
    
    def on_ok():
        if entry.get().strip():
            result[0] = entry.get().strip()
            dialog.destroy()
    
    entry.bind("<Return>", lambda e: on_ok())
    dialog.bind("<Escape>", lambda e: dialog.destroy())
    
    btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_frame.pack(pady=15, padx=20, fill="x")
    ctk.CTkButton(btn_frame, text=localization_manager.get_text("ok"), command=on_ok, font=("Roboto", 13), 
                  width=100, height=35, fg_color="#2CC985", hover_color="#26AD72").pack(side="left", padx=10, expand=True)
    ctk.CTkButton(btn_frame, text=localization_manager.get_text("cancel"), command=dialog.destroy, font=("Roboto", 13),
                  width=100, height=35, fg_color="#FF5555", hover_color="#D63C3C").pack(side="right", padx=10, expand=True)
    
    dialog.wait_window()
    return result[0]


def show_help_window(title, file_name):
    """Открывает файл справки в стандартном редакторе (Блокнот)"""
    try:
        from core.settings_manager import get_user_dir, get_data_dir, get_resource_path
        import subprocess
        
        # Если передали md, меняем на txt для совместимости
        if file_name.endswith(".md"):
            file_name = file_name.replace(".md", ".txt")
            
        # Сначала ищем во внешней папке data
        path = os.path.join(get_data_dir(), "документация", file_name)
        
        if not os.path.exists(path):
            # Если нет во внешней, ищем во внутренней (ресурсы EXE)
            path = os.path.join(get_resource_path("документация"), file_name)
        
        if not os.path.exists(path):
            messagebox.showerror(localization_manager.get_text("error"), f"Файл справки не найден:\n{file_name}")
            return

        # Запускаем в блокноте
        subprocess.Popen(["notepad.exe", path])
        
    except Exception as e:
        messagebox.showerror(localization_manager.get_text("error"), f"Не удалось открыть справку: {e}")


def populate_main_window(dependencies, root, settings, main_frame, widgets, tvars):
    """
    Заполняет основное окно виджетами.
    """
    from core.app_state import app_state
    main_window_components = app_state.main_window_components
    last_prompt = settings.get("LAST_PROMPT", "")

    # ========================================
    # HEADER
    # ========================================
    header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    header_frame.pack(fill="x", pady=0)
    tvars["pin_var"] = tk.BooleanVar(value=False)
    
    def toggle_pin():
        current_state = tvars["pin_var"].get()
        new_state = not current_state
        tvars["pin_var"].set(new_state)
        root.attributes("-topmost", new_state)
        if new_state:
            pin_btn.configure(text="✅", fg_color="#2cc985")
        else:
            pin_btn.configure(text="📌", fg_color="#1f538d")
    
    pin_btn = ctk.CTkButton(header_frame, text="📌", command=toggle_pin, width=40, height=30)
    pin_btn.pack(side="left", padx=(0, 10))
    widgets["pin_btn"] = pin_btn

    # Логотип Wordy
    try:
        from PIL import Image
        from core.settings_manager import get_resource_path
        import os
        logo_path = get_resource_path(os.path.join("assets", "logo.png"))
        if os.path.exists(logo_path):
            img = Image.open(logo_path)
            aspect_ratio = img.width / img.height
            new_width = int(30 * aspect_ratio)
            logo_image = ctk.CTkImage(light_image=img, dark_image=img, size=(new_width, 30))
            logo_label = ctk.CTkLabel(header_frame, text="", image=logo_image)
            logo_label.pack(side="left", padx=5)
            widgets["logo_label"] = logo_label
    except Exception as e:
        print(f"Ошибка загрузки логотипа: {e}")

    # Кнопка Help в хедере (перемещена вправо)
    help_btn = ctk.CTkButton(header_frame, text=localization_manager.get_text("help"), width=50, height=30, 
                             fg_color="transparent", border_width=1, 
                             command=lambda: show_help_window("Главное окно", "Main_Window_Help.txt"))
    help_btn.pack(side="right", padx=5)
    ToolTip(help_btn, localization_manager.get_text("help_tooltip"))
    
    sound_source = settings.get("SOUND_SOURCE", "original")
    tvars["sound_source_var"] = tk.StringVar(value=sound_source)
    sound_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
    sound_frame.pack(side="right", padx=5)
    ctk.CTkRadioButton(sound_frame, text=localization_manager.get_text("sound_source_original"), variable=tvars["sound_source_var"], value="original", width=50).pack(side="left", padx=2)
    ctk.CTkRadioButton(sound_frame, text=localization_manager.get_text("sound_source_translation"), variable=tvars["sound_source_var"], value="translation", width=60).pack(side="left", padx=2)
    ToolTip(sound_frame, localization_manager.get_text("sound_source_tooltip"))
    
    widgets["font_settings_btn"] = ctk.CTkButton(header_frame, text="⚙", width=40, height=30, command=lambda: dependencies.open_settings_window(root, dependencies))
    widgets["font_settings_btn"].pack(side="right", padx=(5, 0))
    ToolTip(widgets["font_settings_btn"], localization_manager.get_text("open_settings"))
    
    def play_selected_audio_wrapper():
        play_selected_audio(widgets, tvars, dependencies, root)
    
    widgets["font_sound_btn"] = ctk.CTkButton(header_frame, text="🔊", width=40, height=30, command=play_selected_audio_wrapper, fg_color="#2cc985", hover_color="#26ad72")
    widgets["font_sound_btn"].pack(side="right", padx=5)
    ToolTip(widgets["font_sound_btn"], localization_manager.get_text("play_audio"))
    
    tvars["audio_enabled_var"] = tk.BooleanVar(value=settings.get("AUDIO_ENABLED", True))
    widgets["audio_enabled_check"] = ctk.CTkCheckBox(header_frame, text=localization_manager.get_text("audio_enabled"), variable=tvars["audio_enabled_var"], width=80)
    widgets["audio_enabled_check"].pack(side="right", padx=5)
    ToolTip(widgets["audio_enabled_check"], localization_manager.get_text("audio_enabled_tooltip"))

    # ========================================
    # INPUT FIELDS
    # ========================================
    widgets["german_text"] = ctk.CTkTextbox(main_frame, height=70, font=("Roboto", 14))
    widgets["german_text"].pack(pady=(0, 5), padx=5, fill="both", expand=True)
    widgets["clipboard_handlers"] = []
    widgets["clipboard_handlers"].append(setup_text_widget_context_menu(widgets["german_text"]))
    
    widgets["translation_text"] = ctk.CTkTextbox(main_frame, height=70, font=("Roboto", 14))
    widgets["translation_text"].pack(pady=(0, 5), padx=5, fill="both", expand=True)
    widgets["translation_text"].insert("1.0", localization_manager.get_text("placeholder_translation"))
    widgets["clipboard_handlers"].append(setup_text_widget_context_menu(widgets["translation_text"]))

    # ========================================
    # CONTROLS
    # ========================================
    controls_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    controls_frame.pack(fill="x", pady=5, padx=5)
    tvars["prompt_var"] = tk.StringVar(value="")
    widgets["prompt_combo"] = ctk.CTkComboBox(controls_frame, variable=tvars["prompt_var"], values=[""], width=200)
    widgets["prompt_combo"].pack(side="left", padx=(0, 10))
    
    # Индикатор буфера перенесен сюда
    animation_label = ctk.CTkLabel(controls_frame, text="", font=("Roboto", 12), anchor="w")
    animation_label.pack(side="left", padx=5)
    root.animation_label = animation_label

    import webbrowser
    check_updates_label = ctk.CTkLabel(
        controls_frame,
        text=localization_manager.get_text("check_updates"),
        font=("Roboto", 11, "underline"),
        text_color=("#5a9fd4", "#5a9fd4"),
        cursor="hand2"
    )
    check_updates_label.pack(side="right", padx=5)
    check_updates_label.bind("<Button-1>", lambda e: webbrowser.open("https://nimmaypum-jpg.github.io/Anki-card-andder/"))
    
    def on_prompt_select(choice):
        """Применяет выбранный промпт к приложению"""
        if not choice or choice.strip() == "":
            return
        try:
            from core.prompts_manager import prompts_manager
            preset = prompts_manager.get_preset(choice)
            if preset:
                new_translate = preset.get("translate", preset.get("translation", ""))
                new_context = preset.get("context", "")
                new_delimiter = preset.get("delimiter", "КОНТЕКСТ")
                
                if hasattr(dependencies, "update_active_prompts"):
                    dependencies.update_active_prompts(new_translate, new_context, new_delimiter)
                
                if "prompt_status_label" in widgets:
                    widgets["prompt_status_label"].configure(text=f"✅ {choice}", text_color="#2CC985")
                    root.after(1500, lambda: widgets["prompt_status_label"].configure(
                        text=f"Промпт: {choice}", text_color=("#888888", "#888888")))
                
                from core.settings_manager import load_settings, save_settings
                current_settings = load_settings(update_app_state=False)
                current_settings["TRANSLATE_PROMPT"] = new_translate
                current_settings["CONTEXT_PROMPT"] = new_context
                current_settings["CONTEXT_DELIMITER"] = new_delimiter
                current_settings["LAST_PROMPT"] = choice
                save_settings(current_settings)
                
                print(f"✅ Промпт '{choice}' применён (разделитель: {new_delimiter})")
            else:
                print(f"⚠️ Промпт '{choice}' не найден")
        except Exception as e:
            print(f"Ошибка применения промпта: {e}")
            import traceback
            traceback.print_exc()
    
    widgets["prompt_combo"].configure(command=on_prompt_select)
    ToolTip(widgets["prompt_combo"], localization_manager.get_text("prompt_saved", name=""))

    # ========================================
    # CONTEXT WIDGET
    # ========================================
    widgets["context_widget"] = ctk.CTkTextbox(main_frame, height=180, font=("Roboto", 12))
    widgets["context_widget"].pack(pady=(0, 5), padx=5, fill="both", expand=True)
    widgets["clipboard_handlers"].append(setup_text_widget_context_menu(widgets["context_widget"]))
    
    # ========================================
    # GENERATION CONTROLS
    # ========================================
    gen_frame = ctk.CTkFrame(main_frame)
    gen_frame.pack(fill="x", pady=5, padx=5)
    checks_frame = ctk.CTkFrame(gen_frame, fg_color="transparent")
    checks_frame.pack(side="left", padx=5, pady=5)
    tvars["context_var"] = tk.BooleanVar(value=settings.get("CONTEXT_ENABLED", False))
    widgets["context_check"] = ctk.CTkCheckBox(checks_frame, text=localization_manager.get_text("context_enabled"), variable=tvars["context_var"])
    widgets["context_check"].pack(anchor="w", pady=2)
    ToolTip(widgets["context_check"], localization_manager.get_text("context_enabled_tooltip"))
    
    pause_setting = settings.get("PAUSE_CLIPBOARD_MONITORING", True)
    tvars["pause_monitoring_var"] = tk.BooleanVar(value=not pause_setting)
    tvars["pause_monitoring_var"].trace_add("write", dependencies.update_pause_monitoring_flag)
    widgets["pause_monitoring_check"] = ctk.CTkCheckBox(checks_frame, text=localization_manager.get_text("clipboard_monitoring"), variable=tvars["pause_monitoring_var"])
    widgets["pause_monitoring_check"].pack(anchor="w", pady=2)
    ToolTip(widgets["pause_monitoring_check"], localization_manager.get_text("clipboard_monitoring_tooltip"))
    dependencies.update_pause_monitoring_flag()
    
    btns_frame = ctk.CTkFrame(gen_frame, fg_color="transparent")
    btns_frame.pack(side="left", fill="both", expand=True, padx=10)
    
    top_gen_row = ctk.CTkFrame(btns_frame, fg_color="transparent")
    top_gen_row.pack(fill="x", pady=(0, 5))
    
    auto_label = ctk.CTkLabel(top_gen_row, text=localization_manager.get_text("auto_generate"), font=("Roboto", 12))
    auto_label.pack(side="left", padx=(0, 2))
    
    tvars["auto_generate_var"] = tk.BooleanVar(value=settings.get("AUTO_GENERATE_ON_COPY", True))
    tvars["auto_generate_var"].trace_add("write", dependencies.update_auto_generate_flag)
    widgets["auto_generate_check"] = ctk.CTkCheckBox(top_gen_row, text="", variable=tvars["auto_generate_var"], width=20)
    widgets["auto_generate_check"].pack(side="left", padx=(0, 5))
    ToolTip(widgets["auto_generate_check"], localization_manager.get_text("auto_generate_tooltip"))
    dependencies.update_auto_generate_flag()
    
    widgets["generate_btn"] = ctk.CTkButton(top_gen_row, text=localization_manager.get_text("generate"), command=dependencies.generate_action, height=40, width=130)
    widgets["generate_btn"].pack(side="left", fill="x", expand=True)
    
    widgets["stop_btn"] = ctk.CTkButton(btns_frame, text=localization_manager.get_text("stop_btn"), command=dependencies.stop_generation, state="disabled", fg_color="#ff5555", hover_color="#d63c3c", width=130, height=40)
    widgets["stop_btn"].pack(fill="x")
    
    # Индикатор текущей AI модели (кликабельный для быстрого доступа к настройкам AI)
    ai_indicator_frame = ctk.CTkFrame(gen_frame)
    ai_indicator_frame.pack(side="right", padx=5, pady=5)
    
    # Скрытая переменная для модели (используется при генерации)
    tvars["ollama_var"] = tk.StringVar(value=settings.get("OLLAMA_MODEL", ""))
    
    ai_model_label = ctk.CTkLabel(
        ai_indicator_frame, 
        text=f"⚡ {settings.get('OLLAMA_MODEL', localization_manager.get_text('ai_not_configured'))}", 
        text_color=("#666666", "#aaaaaa"),
        cursor="hand2"
    )
    ai_model_label.pack()
    widgets["ai_model_label"] = ai_model_label
    
    def open_ai_settings():
        dependencies.open_settings_window(root, dependencies, initial_tab="AI")
    
    ai_model_label.bind("<Button-1>", lambda e: open_ai_settings())
    ToolTip(ai_model_label, localization_manager.get_text("ai_settings_btn_tooltip"))

    
    # ========================================
    # DECK SELECTION
    # ========================================
    deck_frame = ctk.CTkFrame(main_frame)
    deck_frame.pack(fill="x", pady=5, padx=5)
    cached_decks = [dependencies.DEFAULT_DECK_NAME]
    tvars["deck_var"] = tk.StringVar(value=settings.get("LAST_DECK", cached_decks[0]))
    initial_deck_values = [settings["LAST_DECK"]] if settings.get("LAST_DECK") else [localization_manager.get_text("loading")]
    widgets["deck_combo"] = ctk.CTkComboBox(deck_frame, variable=tvars["deck_var"], values=initial_deck_values, state="disabled")
    widgets["deck_combo"].pack(side="left", fill="x", expand=True, padx=5, pady=5)
    ToolTip(widgets["deck_combo"], localization_manager.get_text("deck_selection_tooltip"))
    
    def refresh_decks_button():
        try:
            current_full = tvars["deck_var"].get()
            current_clean = dependencies.clean_deck_name(current_full) if hasattr(dependencies, 'clean_deck_name') else current_full
            
            decks = dependencies.get_deck_names()
            if isinstance(decks, list) and decks:
                cached_decks[:] = decks
                widgets["deck_combo"].configure(values=decks, state="normal")
                
                found_match = False
                if current_clean:
                    for deck_str in decks:
                        deck_clean = dependencies.clean_deck_name(deck_str) if hasattr(dependencies, 'clean_deck_name') else deck_str
                        if deck_clean == current_clean:
                            tvars["deck_var"].set(deck_str)
                            found_match = True
                            break
                
                if not found_match:
                    if not current_full or current_full in [localization_manager.get_text("loading"), localization_manager.get_text("anki_not_available"), localization_manager.get_text("decks_not_found")]:
                        tvars["deck_var"].set(decks[0])
                    elif current_full not in decks:
                        tvars["deck_var"].set(decks[0])

            elif decks == "ANKI_CONNECT_ERROR":
                widgets["deck_combo"].configure(values=[localization_manager.get_text("anki_not_available")], state="disabled")
                tvars["deck_var"].set(localization_manager.get_text("anki_not_available"))
                messagebox.showwarning(localization_manager.get_text("warning"), "Не удалось подключиться к AnkiConnect.\nУбедитесь, что Anki запущен с установленным AnkiConnect.")
            else:
                widgets["deck_combo"].configure(values=[localization_manager.get_text("decks_not_found")], state="disabled")
                tvars["deck_var"].set(localization_manager.get_text("decks_not_found"))
        except Exception as e:
            print(f"Ошибка обновления колод: {e}")
    
    widgets["refresh_decks_btn"] = ctk.CTkButton(deck_frame, text="🔄", width=30, command=refresh_decks_button)
    widgets["refresh_decks_btn"].pack(side="left", padx=5)
    ToolTip(widgets["refresh_decks_btn"], localization_manager.get_text("refresh_decks"))
    
    def on_create_deck():
        """Создает новую колоду используя универсальный диалог"""
        new_name = ask_string_dialog(root, localization_manager.get_text("create_deck"), localization_manager.get_text("new_deck_name"))
        if new_name and dependencies.create_deck(new_name):
            decks = dependencies.get_deck_names() or [new_name]
            widgets["deck_combo"].configure(values=decks)
            tvars["deck_var"].set(new_name)
            messagebox.showinfo(localization_manager.get_text("success"), localization_manager.get_text("deck_created", name=new_name))
    
    widgets["create_deck_btn"] = ctk.CTkButton(deck_frame, text="+", width=30, command=on_create_deck)
    widgets["create_deck_btn"].pack(side="left", padx=5)
    ToolTip(widgets["create_deck_btn"], localization_manager.get_text("create_deck"))



    # ========================================
    # BOTTOM ACTIONS
    # ========================================
    action_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    action_frame.pack(fill="x", pady=10, padx=5)
    
    status_left_frame = ctk.CTkFrame(action_frame, fg_color="transparent")
    status_left_frame.pack(side="left", padx=5)
    
    widgets["processing_indicator"] = ctk.CTkLabel(status_left_frame, text="", font=("Roboto", 10), text_color=("#5a9fd4", "#5a9fd4"))
    widgets["processing_indicator"].pack(side="left", padx=(0, 10))
    
    widgets["prompt_status_label"] = ctk.CTkLabel(status_left_frame, text="", font=("Roboto", 10), text_color=("#888888", "#888888"))
    widgets["prompt_status_label"].pack(side="left", padx=0)
    
    widgets["cancel_btn"] = ctk.CTkButton(action_frame, text="❌ " + localization_manager.get_text("cancel"), command=lambda: root.iconify(), width=100, fg_color="#FF5555", hover_color="#D63C3C")
    widgets["cancel_btn"].pack(side="right", padx=5)
    
    add_to_anki_frame = ctk.CTkFrame(action_frame, fg_color="transparent")
    add_to_anki_frame.pack(side="right", padx=5)
    
    auto_add_label = ctk.CTkLabel(add_to_anki_frame, text=localization_manager.get_text("auto_add"), font=("Roboto", 12))
    auto_add_label.pack(side="left", padx=(0, 2))
    
    tvars["auto_add_to_anki_var"] = tk.BooleanVar(value=settings.get("AUTO_ADD_TO_ANKI", False))
    widgets["auto_add_to_anki_check"] = ctk.CTkCheckBox(add_to_anki_frame, text="", variable=tvars["auto_add_to_anki_var"], width=20)
    widgets["auto_add_to_anki_check"].pack(side="left", padx=(0, 5))
    ToolTip(widgets["auto_add_to_anki_check"], localization_manager.get_text("auto_add_tooltip"))
    
    widgets["add_btn"] = ctk.CTkButton(add_to_anki_frame, text="✅ " + localization_manager.get_text("add_to_anki"), command=dependencies.on_yes_action, width=100, fg_color="#2CC985", hover_color="#26AD72")
    widgets["add_btn"].pack(side="left")
    
    main_window_components.update({"widgets": widgets, "vars": tvars, "root": root, "refresh_decks_command": refresh_decks_button})

    # ========================================
    # FINAL SETUP AND BINDINGS
    # ========================================
    def on_action_complete():
        last_phrase = main_window_components.get("original_phrase", "")
        try:
            import pyperclip
            pyperclip.copy(last_phrase)
        except ImportError:
            pass
    
    main_window_components["on_action_complete"] = on_action_complete
    
    def on_close():
        from core.settings_manager import load_settings, save_settings
        from core.app_state import app_state
        dependencies.stop_clipboard_monitoring()
        current_settings = load_settings(update_app_state=False)
        
        raw_deck = tvars["deck_var"].get()
        current_settings["LAST_DECK"] = dependencies.clean_deck_name(raw_deck) if hasattr(dependencies, 'clean_deck_name') else raw_deck
        # OLLAMA_MODEL теперь сохраняется только через настройки AI
        current_settings["OLLAMA_MODEL"] = app_state.ollama_model
        current_settings["CONTEXT_ENABLED"] = tvars["context_var"].get()
        current_settings["AUTO_GENERATE_ON_COPY"] = tvars["auto_generate_var"].get()
        current_settings["PAUSE_CLIPBOARD_MONITORING"] = not tvars["pause_monitoring_var"].get()
        current_settings["SOUND_SOURCE"] = tvars["sound_source_var"].get()
        current_settings["LAST_PROMPT"] = tvars["prompt_var"].get()
        current_settings["AUDIO_ENABLED"] = tvars["audio_enabled_var"].get()
        current_settings["AUTO_ADD_TO_ANKI"] = tvars["auto_add_to_anki_var"].get()
        
        save_settings(current_settings)
        print("🛑 Остановка мониторинга буфера обмена и завершение приложения.")
        root.destroy()
        sys.exit(0)
    
    root.protocol("WM_DELETE_WINDOW", on_close)

    def play_selected_audio(widgets, tvars, dependencies, root):
        source = tvars["sound_source_var"].get()
        text_widget = widgets["translation_text"] if source == "translation" else widgets["german_text"]
        text = text_widget.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning(localization_manager.get_text("warning"), localization_manager.get_text("empty_field_warning"))
            return
        
        def worker():
            try:
                lang = getattr(dependencies, "TTS_LANG", "de")
                tld = getattr(dependencies, "TTS_TLD", "de")
                speed_level = getattr(dependencies, "TTS_SPEED_LEVEL", 0)
                audio_utils.play_text_audio(text, lang, speed_level, tld, parent=root)
            except Exception as e:
                messagebox.showerror(localization_manager.get_text("error"), f"Не удалось воспроизвести аудио: {e}")
        
        dependencies.threading.Thread(target=worker, daemon=True).start()

    def deferred_load():
        from core.prompts_manager import prompts_manager
        try:
            prompt_names = prompts_manager.get_preset_names()
            widgets["prompt_combo"].configure(values=prompt_names)
            if last_prompt and last_prompt in prompt_names:
                tvars["prompt_var"].set(last_prompt)
                if "prompt_status_label" in widgets:
                    widgets["prompt_status_label"].configure(text=localization_manager.get_text("prompt_label", name=last_prompt))
                on_prompt_select(last_prompt)
        except Exception as e:
            print(f"Ошибка обновления промптов: {e}")
        
        if tvars["pause_monitoring_var"].get():
            root.animation_label.pack(expand=True)
            root._animation_running = True
            root.start_animation()
        else:
            root.animation_label.pack(expand=True)
            root.animation_label.configure(text="")
        
        dependencies.threading.Thread(target=dependencies.load_background_data_worker, args=(dependencies.results_queue,), daemon=True).start()
    
    def start_animation():
        """Запускает анимацию заголовка с точками"""
        if not hasattr(root, '_animation_running'):
            root._animation_running = False
        
        if not root._animation_running:
            return
        
        dots = ["", ".", "..", "..."]
        if not hasattr(root, '_animation_index'):
            root._animation_index = 0
        
        root.animation_label.configure(text=f"{localization_manager.get_text('clipboard_indicator')}{dots[root._animation_index]}")
        root._animation_index = (root._animation_index + 1) % len(dots)
        root._animation_job = root.after(500, start_animation)
    
    root.start_animation = start_animation
    root.after(100, deferred_load)
    
    global_clipboard_manager = GlobalClipboardManager(root, widgets["clipboard_handlers"])


def build_main_window(dependencies, root, settings, start_time=None):
    """
    Создаёт и настраивает виджеты в главном окне.
    """
    root.title(localization_manager.get_text("app_title"))
    root.geometry("500x750")
    
    main_frame = ctk.CTkFrame(root)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    widgets = {}
    tvars = {}

    root.after(10, lambda: populate_main_window(dependencies, root, settings, main_frame, widgets, tvars))
    
    return root
