import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import audio_utils
from theme_manager import theme_manager
from clipboard_manager import setup_text_widget_context_menu, GlobalClipboardManager
import time
import os
import json

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
    dialog.attributes("-topmost", True)
    dialog.focus_force()
    
    result = [None]
    
    ctk.CTkLabel(dialog, text=prompt, font=("Roboto", 15)).pack(pady=(20, 10), padx=20)
    
    entry = ctk.CTkEntry(dialog, font=("Roboto", 15), height=35)
    entry.pack(pady=10, padx=20, fill="x")
    if initial_value:
        entry.insert(0, initial_value)
        entry.select_range(0, tk.END)
    entry.focus_set()
    
    # Используем новый модуль для настройки буфера обмена
    setup_text_widget_context_menu(entry)
    
    
    def on_ok():
        if entry.get().strip():
            result[0] = entry.get().strip()
            dialog.destroy()
    
    entry.bind("<Return>", lambda e: on_ok())
    dialog.bind("<Escape>", lambda e: dialog.destroy())
    
    btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_frame.pack(pady=15, padx=20, fill="x")
    ctk.CTkButton(btn_frame, text="OK", command=on_ok, font=("Roboto", 13), 
                  width=100, height=35, fg_color="#2CC985", hover_color="#26AD72").pack(side="left", padx=10, expand=True)
    ctk.CTkButton(btn_frame, text="Отмена", command=dialog.destroy, font=("Roboto", 13),
                  width=100, height=35, fg_color="#FF5555", hover_color="#D63C3C").pack(side="right", padx=10, expand=True)
    
    dialog.wait_window()
    return result[0]


def populate_main_window(dependencies, root, settings, main_frame, widgets, tvars):
    """
    Заполняет основное окно виджетами.
    """
    main_window_components = dependencies.main_window_components

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
        # Update button appearance based on new state
        if new_state:
            # Pinned - show checkmark and green color
            pin_btn.configure(text="✅", fg_color="#2cc985")
        else:
            # Unpinned - show pin and blue color
            pin_btn.configure(text="📌", fg_color="#1f538d")
    pin_btn = ctk.CTkButton(header_frame, text="📌", command=toggle_pin, width=40, height=30)
    pin_btn.pack(side="left", padx=(0, 10))
    widgets["pin_btn"] = pin_btn
    
    # Простой индикатор мониторинга (без заголовка)
    animation_label = ctk.CTkLabel(header_frame, text="", font=("Roboto", 12), anchor="w")
    animation_label.pack(side="left", fill="x", expand=True)
    root.animation_label = animation_label
    
    # Радиокнопки выбора источника озвучки
    sound_source = settings.get("SOUND_SOURCE", "original")
    tvars["sound_source_var"] = tk.StringVar(value=sound_source)
    sound_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
    sound_frame.pack(side="right", padx=5)
    ctk.CTkRadioButton(sound_frame, text="Ориг", variable=tvars["sound_source_var"], value="original", width=50).pack(side="left", padx=2)
    ctk.CTkRadioButton(sound_frame, text="Перевод", variable=tvars["sound_source_var"], value="translation", width=60).pack(side="left", padx=2)
    ToolTip(sound_frame, "Выберите источник текста для озвучки")
    
    # Кнопки и чекбокс справа в header
    # Кнопка настроек
    widgets["font_settings_btn"] = ctk.CTkButton(header_frame, text="⚙", width=40, height=30, command=lambda: dependencies.open_settings_window(root, dependencies))
    widgets["font_settings_btn"].pack(side="right", padx=(5, 0))
    ToolTip(widgets["font_settings_btn"], "Открыть настройки")
    
    # Кнопка прослушивания аудио
    def play_selected_audio_wrapper():
        play_selected_audio(widgets, tvars, dependencies, root)
    
    widgets["font_sound_btn"] = ctk.CTkButton(header_frame, text="🔊", width=40, height=30, command=play_selected_audio_wrapper, fg_color="#2cc985", hover_color="#26ad72")
    widgets["font_sound_btn"].pack(side="right", padx=5)
    ToolTip(widgets["font_sound_btn"], "Воспроизвести аудио выбранного текста")
    
    # Чекбокс озвучки
    tvars["audio_enabled_var"] = tk.BooleanVar(value=settings.get("AUDIO_ENABLED", True))
    widgets["audio_enabled_check"] = ctk.CTkCheckBox(header_frame, text="Озвучка", variable=tvars["audio_enabled_var"], width=80)
    widgets["audio_enabled_check"].pack(side="right", padx=5)
    ToolTip(widgets["audio_enabled_check"], "Создавать озвучку при добавлении в Anki")

    # ========================================
    # INPUT FIELDS
    # ========================================
    widgets["german_text"] = ctk.CTkTextbox(main_frame, height=70, font=("Roboto", 14))
    widgets["german_text"].pack(pady=(0, 5), padx=5, fill="both", expand=True)
    widgets["clipboard_handlers"] = []
    widgets["clipboard_handlers"].append(setup_text_widget_context_menu(widgets["german_text"]))
    
    widgets["translation_text"] = ctk.CTkTextbox(main_frame, height=70, font=("Roboto", 14))
    widgets["translation_text"].pack(pady=(0, 5), padx=5, fill="both", expand=True)
    widgets["clipboard_handlers"].append(setup_text_widget_context_menu(widgets["translation_text"]))

    # ========================================
    # CONTROLS
    # ========================================
    controls_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    controls_frame.pack(fill="x", pady=5, padx=5)
    tvars["prompt_var"] = tk.StringVar(value="")
    widgets["prompt_combo"] = ctk.CTkComboBox(controls_frame, variable=tvars["prompt_var"], values=[""], width=200)
    widgets["prompt_combo"].pack(side="left", padx=(0, 10))
    
    # Обработчик выбора промпта
    def on_prompt_select(choice):
        """Применяет выбранный промпт к глобальным переменным"""
        if not choice or choice.strip() == "":
            return
        try:
            from anki_german_helper import PROMPTS_FILE
            if os.path.exists(PROMPTS_FILE):
                with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
                    pair_presets = json.load(f)
                if choice in pair_presets:
                    new_translate = pair_presets[choice].get("translation", "")
                    new_context = pair_presets[choice].get("context", "")
                    
                    # Обновляем активные промпты через функцию в зависимостях
                    if hasattr(dependencies, "update_active_prompts"):
                        dependencies.update_active_prompts(new_translate, new_context)
                    
                    # Обновляем индикатор промпта с визуальным фидбеком
                    if "prompt_status_label" in widgets:
                        # Мигаем зелёным для подтверждения
                        widgets["prompt_status_label"].configure(text=f"✅ {choice}", text_color="#2CC985")
                        root.after(1500, lambda: widgets["prompt_status_label"].configure(
                            text=f"Промпт: {choice}", text_color=("#888888", "#888888")))
                    
                    # Сохраняем в настройки
                    current_settings = dependencies.load_settings(update_globals=False)
                    current_settings["TRANSLATE_PROMPT"] = new_translate
                    current_settings["CONTEXT_PROMPT"] = new_context
                    current_settings["LAST_PROMPT"] = choice
                    dependencies.save_settings(current_settings)
                    
                    print(f"✅ Промпт '{choice}' применён: translate={len(new_translate)} chars, context={len(new_context)} chars")
                else:
                    print(f"⚠️ Промпт '{choice}' не найден в файле")
        except Exception as e:
            print(f"Ошибка применения промпта: {e}")
            import traceback
            traceback.print_exc()
    
    widgets["prompt_combo"].configure(command=on_prompt_select)
    
    ToolTip(widgets["prompt_combo"], "Выберите пресет промпта")

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
    widgets["context_check"] = ctk.CTkCheckBox(checks_frame, text="Контекст", variable=tvars["context_var"])
    widgets["context_check"].pack(anchor="w", pady=2)
    ToolTip(widgets["context_check"], "Включить генерацию контекста/объяснений")
    # Загружаем состояние мониторинга из настроек
    # Инвертируем: PAUSE=False (активный) -> checkbox=True (включен)
    pause_setting = settings.get("PAUSE_CLIPBOARD_MONITORING", True)  # По умолчанию пауза
    tvars["pause_monitoring_var"] = tk.BooleanVar(value=not pause_setting)
    tvars["pause_monitoring_var"].trace_add("write", dependencies.update_pause_monitoring_flag)
    widgets["pause_monitoring_check"] = ctk.CTkCheckBox(checks_frame, text="Перехват буфера", variable=tvars["pause_monitoring_var"])
    widgets["pause_monitoring_check"].pack(anchor="w", pady=2)
    ToolTip(widgets["pause_monitoring_check"], "Включить/выключить отслеживание буфера обмена")
    # Важно! Вызываем update_pause_monitoring_flag сразу, чтобы синхронизировать глобальную переменную
    dependencies.update_pause_monitoring_flag()
    
    # Кнопки генерации с чекбоксом "Авто" рядом
    btns_frame = ctk.CTkFrame(gen_frame, fg_color="transparent")
    btns_frame.pack(side="left", fill="both", expand=True, padx=10)
    
    # Верхняя строка: label "Авто" + checkbox + кнопка "Генерировать"
    top_gen_row = ctk.CTkFrame(btns_frame, fg_color="transparent")
    top_gen_row.pack(fill="x", pady=(0, 5))
    
    # Label "Авто" слева
    auto_label = ctk.CTkLabel(top_gen_row, text="Авто", font=("Roboto", 12))
    auto_label.pack(side="left", padx=(0, 2))
    
    # Checkbox без текста (текст в label выше)
    tvars["auto_generate_var"] = tk.BooleanVar(value=settings.get("AUTO_GENERATE_ON_COPY", True))
    tvars["auto_generate_var"].trace_add("write", dependencies.update_auto_generate_flag)
    widgets["auto_generate_check"] = ctk.CTkCheckBox(
        top_gen_row,
        text="",  # Нет текста, используем отдельный label
        variable=tvars["auto_generate_var"],
        width=20  # Минимальная ширина для чекбокса
    )
    widgets["auto_generate_check"].pack(side="left", padx=(0, 5))
    ToolTip(widgets["auto_generate_check"], "Автоматически генерировать перевод при копировании текста")
    # Важно! Вызываем update_auto_generate_flag сразу, чтобы синхронизировать глобальную переменную
    dependencies.update_auto_generate_flag()
    
    # Кнопка "Генерировать" с уменьшенной шириной
    widgets["generate_btn"] = ctk.CTkButton(
        top_gen_row,
        text="Генерировать",
        command=dependencies.generate_action,
        height=40,
        width=130  # Уменьшена ширина для размещения checkbox
    )
    widgets["generate_btn"].pack(side="left", fill="x", expand=True)
    
    # Кнопка "Отмена генерации" той же ширины что и "Генерировать"
    widgets["stop_btn"] = ctk.CTkButton(
        btns_frame,
        text="Отмена генерации",
        command=dependencies.stop_generation,
        state="disabled",
        fg_color="#ff5555",
        hover_color="#d63c3c",
        width=130,  # Такая же ширина как у кнопки генерации
        height=40
    )
    widgets["stop_btn"].pack(fill="x")
    model_frame = ctk.CTkFrame(gen_frame, fg_color="transparent")
    model_frame.pack(side="right", padx=5, pady=5)
    tvars["ollama_var"] = tk.StringVar(value=settings.get("OLLAMA_MODEL", ""))
    initial_ollama_values = [settings["OLLAMA_MODEL"]] if settings.get("OLLAMA_MODEL") else ["Загрузка..."]
    widgets["ollama_combo"] = ctk.CTkComboBox(model_frame, variable=tvars["ollama_var"], values=initial_ollama_values, width=150, state="disabled")
    widgets["ollama_combo"].pack(pady=(0, 5))
    ToolTip(widgets["ollama_combo"], "Выберите модель Ollama для генерации")
    def refresh_models_button():
        try:
            models = dependencies.get_ollama_models()
            if models:
                widgets["ollama_combo"].configure(values=models)
                current = tvars["ollama_var"].get()
                if not current or current not in models:
                    tvars["ollama_var"].set(models[0] if models else "")
        except Exception: pass
    widgets["refresh_models_btn"] = ctk.CTkButton(model_frame, text="🔄", width=30, command=refresh_models_button)
    widgets["refresh_models_btn"].pack()
    ToolTip(widgets["refresh_models_btn"], "Обновить список доступных моделей Ollama")
    
    # ========================================
    # DECK SELECTION
    # ========================================
    deck_frame = ctk.CTkFrame(main_frame)
    deck_frame.pack(fill="x", pady=5, padx=5)
    cached_decks = [dependencies.DEFAULT_DECK_NAME]
    tvars["deck_var"] = tk.StringVar(value=settings.get("LAST_DECK", cached_decks[0]))
    initial_deck_values = [settings["LAST_DECK"]] if settings.get("LAST_DECK") else ["Загрузка..."]
    widgets["deck_combo"] = ctk.CTkComboBox(deck_frame, variable=tvars["deck_var"], values=initial_deck_values, state="disabled")
    widgets["deck_combo"].pack(side="left", fill="x", expand=True, padx=5, pady=5)
    ToolTip(widgets["deck_combo"], "Выберите колоду Anki для добавления карточек")
    def refresh_decks_button():
        try:
            # Запоминаем текущий выбор и очищаем его от счетчика
            current_full = tvars["deck_var"].get()
            current_clean = dependencies.clean_deck_name(current_full) if hasattr(dependencies, 'clean_deck_name') else current_full
            
            decks = dependencies.get_deck_names()
            # Проверяем, что получили список, а не строку ошибки
            if isinstance(decks, list) and decks:
                cached_decks[:] = decks
                widgets["deck_combo"].configure(values=decks, state="normal")
                
                # Пытаемся найти ту же колоду в новом списке (с новым счетчиком)
                found_match = False
                if current_clean:
                    for deck_str in decks:
                        # Очищаем новое имя для сравнения
                        deck_clean = dependencies.clean_deck_name(deck_str) if hasattr(dependencies, 'clean_deck_name') else deck_str
                        if deck_clean == current_clean:
                            tvars["deck_var"].set(deck_str)
                            found_match = True
                            break
                
                # Если не нашли совпадение или текущий выбор был пуст/ошибкой
                if not found_match:
                    # Если текущее значение было "Загрузка..." или ошибкой, ставим первое
                    if not current_full or current_full in ["Загрузка...", "AnkiConnect недоступен", "Колоды не найдены"]:
                         tvars["deck_var"].set(decks[0])
                    # Иначе оставляем как есть (хотя его нет в списке, чтобы не сбивать пользователя зря)
                    elif current_full not in decks:
                         tvars["deck_var"].set(decks[0])

            elif decks == "ANKI_CONNECT_ERROR":
                widgets["deck_combo"].configure(values=["AnkiConnect недоступен"], state="disabled")
                tvars["deck_var"].set("AnkiConnect недоступен")
                messagebox.showwarning("Anki недоступен", "Не удалось подключиться к AnkiConnect.\nУбедитесь, что Anki запущен с установленным AnkiConnect.")
            else:
                widgets["deck_combo"].configure(values=["Колоды не найдены"], state="disabled")
                tvars["deck_var"].set("Колоды не найдены")
        except Exception as e:
            print(f"Ошибка обновления колод: {e}")
    widgets["refresh_decks_btn"] = ctk.CTkButton(deck_frame, text="🔄", width=30, command=refresh_decks_button)
    widgets["refresh_decks_btn"].pack(side="left", padx=5)
    ToolTip(widgets["refresh_decks_btn"], "Обновить список колод Anki")
    def on_create_deck():
        """Создает новую колоду используя универсальный диалог"""
        new_name = ask_string_dialog(root, "Создать колоду", "Название новой колоды:")
        if new_name and dependencies.create_deck(new_name):
            decks = dependencies.get_deck_names() or [new_name]
            widgets["deck_combo"].configure(values=decks)
            tvars["deck_var"].set(new_name)
            messagebox.showinfo("Готово", f"Колода '{new_name}' создана и выбрана.")
    widgets["create_deck_btn"] = ctk.CTkButton(deck_frame, text="+", width=30, command=on_create_deck)
    widgets["create_deck_btn"].pack(side="left", padx=5)
    ToolTip(widgets["create_deck_btn"], "Создать новую колоду Anki")

    # ========================================
    # BOTTOM ACTIONS
    # ========================================
    action_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    action_frame.pack(fill="x", pady=10, padx=5)
    # Индикатор состояния слева внизу
    status_left_frame = ctk.CTkFrame(action_frame, fg_color="transparent")
    status_left_frame.pack(side="left", padx=5)
    
    widgets["processing_indicator"] = ctk.CTkLabel(status_left_frame, text="", font=("Roboto", 10), text_color=("#5a9fd4", "#5a9fd4"))
    widgets["processing_indicator"].pack(side="left", padx=(0, 10))
    
    widgets["prompt_status_label"] = ctk.CTkLabel(status_left_frame, text="", font=("Roboto", 10), text_color=("#888888", "#888888"))
    widgets["prompt_status_label"].pack(side="left", padx=0)
    
    # Кнопка "Отмена" (свернуть окно)
    widgets["cancel_btn"] = ctk.CTkButton(action_frame, text="❌ Отмена", command=lambda: root.iconify(), width=100, fg_color="#FF5555", hover_color="#D63C3C")
    widgets["cancel_btn"].pack(side="right", padx=5)
    
    # Фрейм для кнопки "В Anki" с чекбоксом "Авто" рядом
    add_to_anki_frame = ctk.CTkFrame(action_frame, fg_color="transparent")
    add_to_anki_frame.pack(side="right", padx=5)
    
    # Label "Авто" слева
    auto_add_label = ctk.CTkLabel(add_to_anki_frame, text="Авто", font=("Roboto", 12))
    auto_add_label.pack(side="left", padx=(0, 2))
    
    # Checkbox автодобавления в Anki без текста
    tvars["auto_add_to_anki_var"] = tk.BooleanVar(value=settings.get("AUTO_ADD_TO_ANKI", False))
    widgets["auto_add_to_anki_check"] = ctk.CTkCheckBox(
        add_to_anki_frame,
        text="",  # Нет текста, используем отдельный label
        variable=tvars["auto_add_to_anki_var"],
        width=20  # Минимальная ширина для чекбокса
    )
    widgets["auto_add_to_anki_check"].pack(side="left", padx=(0, 5))
    ToolTip(widgets["auto_add_to_anki_check"], "Автоматически добавлять в Anki после генерации")
    
    # Кнопка "✅ В Anki"
    widgets["add_btn"] = ctk.CTkButton(
        add_to_anki_frame,
        text="✅ В Anki",
        command=dependencies.on_yes_action,
        width=100,
        fg_color="#2CC985",
        hover_color="#26AD72"
    )
    widgets["add_btn"].pack(side="left")
    main_window_components.update({"widgets": widgets, "vars": tvars, "root": root, "refresh_decks_command": refresh_decks_button})

    # ========================================
    # FINAL SETUP AND BINDINGS
    # ========================================
    def on_action_complete():
        last_phrase = main_window_components.get("original_phrase", "")
        # Restore clipboard - импорт pyperclip внутри функции для избежания конфликтов
        try:
            import pyperclip
            pyperclip.copy(last_phrase)
        except ImportError:
            pass  # pyperclip не доступен, игнорируем
        # Окно больше не сворачивается автоматически, остается на переднем плане
    main_window_components["on_action_complete"] = on_action_complete
    
    def on_close():
        dependencies.stop_clipboard_monitoring()
        current_settings = dependencies.load_settings()
        
        # Сохраняем "чистое" имя колоды без счетчика (150)
        raw_deck = tvars["deck_var"].get()
        current_settings["LAST_DECK"] = dependencies.clean_deck_name(raw_deck) if hasattr(dependencies, 'clean_deck_name') else raw_deck
        
        current_settings["OLLAMA_MODEL"] = tvars["ollama_var"].get()
        current_settings["CONTEXT_ENABLED"] = tvars["context_var"].get()
        current_settings["AUTO_GENERATE_ON_COPY"] = tvars["auto_generate_var"].get()
        # Инвертируем значение при сохранении: checked в UI = активный мониторинг = не пауза
        current_settings["PAUSE_CLIPBOARD_MONITORING"] = not tvars["pause_monitoring_var"].get()
        current_settings["SOUND_SOURCE"] = tvars["sound_source_var"].get()
        current_settings["LAST_PROMPT"] = tvars["prompt_var"].get()
        current_settings["AUDIO_ENABLED"] = tvars["audio_enabled_var"].get()  # Сохраняем состояние озвучки
        current_settings["AUTO_ADD_TO_ANKI"] = tvars["auto_add_to_anki_var"].get()  # Сохраняем автодобавление в Anki
        
        dependencies.save_settings(current_settings)
        print("🛑 Остановка мониторинга буфера обмена и завершение приложения.")
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_close)

    def play_selected_audio(widgets, tvars, dependencies, root):
        source = tvars["sound_source_var"].get()
        text_widget = widgets["translation_text"] if source == "translation" else widgets["german_text"]
        text = text_widget.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Пустое поле", "Введите текст для озвучки.")
            return
        def worker():
            try:
                # Всегда берем актуальные значения из объекта dependencies
                lang = getattr(dependencies, "TTS_LANG", "de")
                tld = getattr(dependencies, "TTS_TLD", "de")
                speed_level = getattr(dependencies, "TTS_SPEED_LEVEL", 0)
                
                audio_utils.play_text_audio(text, lang, speed_level, tld, parent=root)
            except Exception as e:
                messagebox.showerror("Ошибка озвучки", f"Не удалось воспроизвести аудио: {e}")
        dependencies.threading.Thread(target=worker, daemon=True).start()

    def deferred_load():
        from anki_german_helper import PROMPTS_FILE
        try:
            if os.path.exists(PROMPTS_FILE):
                with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
                    pair_presets = json.load(f)
                prompt_names = sorted(pair_presets.keys())
                widgets["prompt_combo"].configure(values=prompt_names)
                last_prompt = settings.get("LAST_PROMPT", "")
                if last_prompt and last_prompt in prompt_names:
                    tvars["prompt_var"].set(last_prompt)
                    # Обновляем индикатор промпта при загрузке
                    if "prompt_status_label" in widgets:
                        widgets["prompt_status_label"].configure(text=f"Промпт: {last_prompt}")
                    # Применяем промпт при загрузке
                    on_prompt_select(last_prompt)
        except Exception as e: print(f"Ошибка обновления промптов: {e}")
        
        # Инициализация анимации заголовка если мониторинг активен
        if tvars["pause_monitoring_var"].get():  # Если checkbox включен = мониторинг активен
            root.animation_label.pack(expand=True)
            root._animation_running = True
            root.start_animation()
        else:
            root.animation_label.pack(expand=True)
            root.animation_label.configure(text="")
        
        dependencies.threading.Thread(target=dependencies.load_background_data_worker, args=(dependencies.results_queue,), daemon=True).start()
    
    # Функция анимации заголовка
    def start_animation():
        """Запускает анимацию заголовка с точками"""
        if not hasattr(root, '_animation_running'):
            root._animation_running = False
        
        if not root._animation_running:
            return
        
        dots = ["", ".", "..", "..."]
        if not hasattr(root, '_animation_index'):
            root._animation_index = 0
        
        root.animation_label.configure(text=f"👁️Буфер{dots[root._animation_index]}")
        root._animation_index = (root._animation_index + 1) % len(dots)
        root._animation_job = root.after(500, start_animation)
    
    root.start_animation = start_animation
    
    root.after(100, deferred_load)
    
    # ========================================
    # ГЛОБАЛЬНЫЕ ОБРАБОТЧИКИ КЛАВИАТУРЫ (на уровне окна)
    # ========================================
    # Создаем глобальный менеджер буфера обмена
    global_clipboard_manager = GlobalClipboardManager(root, widgets["clipboard_handlers"])


def build_main_window(dependencies, root, settings, start_time=None):
    """
    Создаёт и настраивает виджеты в главном окне.
    """
    root.title("Anki German Helper")
    root.geometry("500x750")
    
    main_frame = ctk.CTkFrame(root)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    widgets = {}
    tvars = {}

    # Откладываем создание всех виджетов
    root.after(10, lambda: populate_main_window(dependencies, root, settings, main_frame, widgets, tvars))
    
    return root