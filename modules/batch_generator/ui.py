# -*- coding: utf-8 -*-
import customtkinter as ctk
import tkinter as tk
import os
import threading
from core.clipboard_manager import setup_text_widget_context_menu

class BatchSidebarPanel(ctk.CTkFrame):
    def __init__(self, parent, start_callback, stop_callback):
        # Инициализируем как полноценный фрейм (не прозрачный), чтобы он выглядел как левая панель
        super().__init__(parent)
        self.parent = parent
        
        # 1. Заголовок с кнопками очистки текста
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", pady=(10, 5), padx=5)
        
        # Кнопка очистки текста через ИИ
        self.clean_btn = ctk.CTkButton(
            header_frame, 
            text="🧹 Очистить текст",
            height=30,
            width=130,
            fg_color="#6366F1", 
            hover_color="#4F46E5",
            command=self._clean_text_with_ai
        )
        self.clean_btn.pack(side="left", padx=(0, 5))
        
        # Кнопка редактирования промпта
        self.edit_prompt_btn = ctk.CTkButton(
            header_frame, 
            text="✏️",
            height=30,
            width=40,
            fg_color="#8B5CF6", 
            hover_color="#7C3AED",
            command=self._edit_clean_prompt
        )
        self.edit_prompt_btn.pack(side="left")

        # Кнопка Собиратель
        def toggle_collector_mode():
            from core.app_state import app_state
            tvars = app_state.main_window_components.setdefault("vars", {})
            if "collector_mode_var" not in tvars:
                tvars["collector_mode_var"] = tk.BooleanVar(value=False)
            
            current_state = tvars["collector_mode_var"].get()
            new_state = not current_state
            tvars["collector_mode_var"].set(new_state)
            
            if new_state:
                self.collector_btn.configure(
                    text="📋 Собиратель: ON", 
                    fg_color="#2CC985", 
                    hover_color="#26AD72",
                    text_color="white"
                )
            else:
                self.collector_btn.configure(
                    text="📋 Собиратель: OFF", 
                    fg_color="transparent", 
                    hover_color="#1f538d",
                    text_color=("gray10", "gray90")
                )

        self.collector_btn = ctk.CTkButton(
            header_frame, 
            text="📋 Собиратель: OFF", 
            width=130, 
            height=30,
            fg_color="transparent", 
            border_width=1,
            hover_color="#1f538d",
            command=toggle_collector_mode
        )
        self.collector_btn.pack(side="right", padx=(5, 0))
        
        # Проверяем начальное состояние
        from core.app_state import app_state
        tvars = app_state.main_window_components.get("vars", {})
        if tvars.get("collector_mode_var") and tvars["collector_mode_var"].get():
            self.collector_btn.configure(
                text="📋 Собиратель: ON", 
                fg_color="#2CC985", 
                hover_color="#26AD72",
                text_color="white"
            )
        
        ctk.CTkLabel(self, text="Вставьте список фраз (каждая с новой строки):", font=("Roboto", 12)).pack(anchor="w", pady=(0, 5), padx=5)

        # 2. Поле ввода
        self.batch_input = ctk.CTkTextbox(self, height=220, font=("Roboto", 14))
        self.batch_input.pack(fill="both", expand=True, pady=(0, 10), padx=5)
        setup_text_widget_context_menu(self.batch_input)
        
        # 3. Кнопки
        controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        controls_frame.pack(fill="x", pady=5, padx=5)
        
        # Состояние кнопки: "start", "pause", "continue"
        self.button_state = "start"
        
        def on_start_pause_click():
            from core.app_state import app_state
            
            if self.button_state == "start":
                # Запуск обработки
                text = self.batch_input.get("1.0", "end-1c")
                if not text.strip():
                    return
                
                self.button_state = "pause"
                self.start_btn.configure(
                    text="⏸ Пауза",
                    fg_color="#F59E0B",
                    hover_color="#D97706"
                )
                self.stop_btn.configure(state="normal")
                app_state.batch_paused = False
                start_callback(text)
                
            elif self.button_state == "pause":
                # Пауза обработки
                app_state.batch_paused = True
                self.button_state = "continue"
                self.start_btn.configure(
                    text="▶ Продолжить",
                    fg_color="#3B82F6",
                    hover_color="#2563EB"
                )
                
            elif self.button_state == "continue":
                # Продолжение обработки с новыми настройками
                app_state.batch_paused = False
                self.button_state = "pause"
                self.start_btn.configure(
                    text="⏸ Пауза",
                    fg_color="#F59E0B",
                    hover_color="#D97706"
                )
        
        def on_stop_click():
            from core.app_state import app_state
            
            # Полная остановка
            app_state.batch_running = False
            app_state.batch_paused = False
            self.button_state = "start"
            
            self.start_btn.configure(
                text="▶ Запустить",
                fg_color="#10B981",
                hover_color="#059669"
            )
            self.stop_btn.configure(state="disabled")
            stop_callback()
        
        self.start_btn = ctk.CTkButton(
            controls_frame, 
            text="▶ Запустить", 
            height=45,
            fg_color="#10B981", 
            hover_color="#059669",
            text_color="white",
            command=on_start_pause_click
        )
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.stop_btn = ctk.CTkButton(
            controls_frame, 
            text="⏹ Стоп", 
            height=45,
            fg_color="#EF4444", 
            hover_color="#DC2626",
            text_color="white",
            state="disabled",
            command=on_stop_click
        )
        self.stop_btn.pack(side="left")

        # 4. Прогресс
        progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        progress_frame.pack(fill="x", pady=10, padx=5)
        
        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.pack(fill="x", side="top", pady=(0, 5))
        self.progress_bar.set(0)

        # 5. Лог
        ctk.CTkLabel(self, text="Журнал событий:", font=("Roboto", 12, "bold")).pack(anchor="w", pady=(10, 5), padx=5)
        self.batch_log = ctk.CTkTextbox(self, height=200, font=("Consolas", 11), state="disabled")
        self.batch_log.pack(fill="both", expand=True, padx=5, pady=(0, 10))
        setup_text_widget_context_menu(self.batch_log)

        # Регистрация в app_state
        from core.app_state import app_state
        app_state.batch_panel = self  # Сохраняем ссылку на панель
        app_state.main_window_components.setdefault("widgets", {}).update({
            "batch_input": self.batch_input,
            "batch_start_btn": self.start_btn,
            "batch_stop_btn": self.stop_btn,
            "batch_progress_bar": self.progress_bar,
            "batch_log": self.batch_log
        })
        
    def reset_state(self):
        """Сбрасывает состояние кнопок к исходному"""
        self.button_state = "start"
        self.start_btn.configure(
            text="▶ Запустить",
            fg_color="#10B981",
            hover_color="#059669"
        )
        self.stop_btn.configure(state="disabled")

    def _get_prompt_path(self):
        """Возвращает путь к файлу промпта для очистки текста"""
        import os
        from core.settings_manager import get_user_dir
        user_files_dir = os.path.join(get_user_dir(), "user_files")
        if not os.path.exists(user_files_dir):
            os.makedirs(user_files_dir, exist_ok=True)
        return os.path.join(user_files_dir, "clean_prompt.txt")
    
    def _load_clean_prompt(self):
        """Загружает промпт из файла"""
        prompt_path = self._get_prompt_path()
        default_prompt = "Следующий немецкий текст напиши каждое предложение с новой строки. Только предложения и ничего лишнего. Исправь ошибки если есть."
        
        try:
            if os.path.exists(prompt_path):
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            else:
                # Создаем файл с дефолтным промптом
                with open(prompt_path, 'w', encoding='utf-8') as f:
                    f.write(default_prompt)
                return default_prompt
        except Exception as e:
            print(f"Ошибка загрузки промпта: {e}")
            return default_prompt
    
    def _save_clean_prompt(self, prompt):
        """Сохраняет промпт в файл"""
        prompt_path = self._get_prompt_path()
        try:
            with open(prompt_path, 'w', encoding='utf-8') as f:
                f.write(prompt)
            return True
        except Exception as e:
            print(f"Ошибка сохранения промпта: {e}")
            return False
    
    def _edit_clean_prompt(self):
        """Открывает окно редактирования промпта"""
        import os
        dialog = ctk.CTkToplevel(self)
        dialog.title("Редактировать промпт для очистки текста")
        dialog.geometry("600x300")
        dialog.transient(self)
        dialog.grab_set()
        dialog.focus_force()
        
        ctk.CTkLabel(dialog, text="Промпт для очистки текста:", font=("Roboto", 14, "bold")).pack(pady=(20, 10), padx=20)
        
        prompt_text = ctk.CTkTextbox(dialog, height=150, font=("Roboto", 12))
        prompt_text.pack(pady=10, padx=20, fill="both", expand=True)
        
        # Загружаем текущий промпт
        current_prompt = self._load_clean_prompt()
        prompt_text.insert("1.0", current_prompt)
        
        setup_text_widget_context_menu(prompt_text)
        
        def on_save():
            new_prompt = prompt_text.get("1.0", "end-1c").strip()
            if new_prompt:
                if self._save_clean_prompt(new_prompt):
                    from tkinter import messagebox
                    messagebox.showinfo("Готово", "Промпт сохранён!", parent=dialog)
                    dialog.destroy()
        
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=15, padx=20, fill="x")
        
        ctk.CTkButton(
            btn_frame, 
            text="💾 Сохранить", 
            command=on_save, 
            font=("Roboto", 13), 
            width=120, 
            height=35, 
            fg_color="#2CC985", 
            hover_color="#26AD72"
        ).pack(side="left", padx=10, expand=True)
        
        ctk.CTkButton(
            btn_frame, 
            text="❌ Отмена", 
            command=dialog.destroy, 
            font=("Roboto", 13),
            width=120, 
            height=35, 
            fg_color="#FF5555", 
            hover_color="#D63C3C"
        ).pack(side="right", padx=10, expand=True)
    
    def _clean_text_with_ai(self):
        """Отправляет текст ИИ для очистки"""
        import os
        import threading
        from tkinter import messagebox
        
        # Получаем текст из поля ввода
        dirty_text = self.batch_input.get("1.0", "end-1c").strip()
        
        if not dirty_text:
            messagebox.showwarning("Пусто", "Вставьте текст для очистки!", parent=self)
            return
        
        # Загружаем промпт
        clean_prompt = self._load_clean_prompt()
        
        # Формируем полный запрос для ИИ
        full_request = f"{clean_prompt}\n\n{dirty_text}"
        
        # Блокируем кнопку
        self.clean_btn.configure(state="disabled", text="⏳ Очистка...")
        
        def worker():
            try:
                # Получаем AI провайдер и текущую модель
                from core.workers import get_current_ai_provider
                from core.app_state import app_state
                ai_provider = get_current_ai_provider()
                
                # Получаем текущую модель в зависимости от провайдера
                current_model = None
                if app_state.ai_provider == "ollama":
                    current_model = app_state.ollama_model
                elif app_state.ai_provider == "openrouter":
                    current_model = app_state.openrouter_model
                
                # Отправляем запрос напрямую через generate()
                cleaned_text = ai_provider.generate(full_request, model=current_model)
                
                # Обновляем поле ввода с очищенным текстом
                def update_ui():
                    self.batch_input.delete("1.0", "end")
                    self.batch_input.insert("1.0", cleaned_text)
                    self.clean_btn.configure(state="normal", text="🧹 Очистить текст")
                    
                    # Добавляем запись в лог
                    self.batch_log.configure(state="normal")
                    self.batch_log.insert("end", f"✅ Текст очищен ({len(cleaned_text)} символов)\n")
                    self.batch_log.see("end")
                    self.batch_log.configure(state="disabled")
                
                self.after(0, update_ui)
                
            except Exception as e:
                error_msg = str(e)
                def show_error():
                    self.clean_btn.configure(state="normal", text="🧹 Очистить текст")
                    messagebox.showerror("Ошибка", f"Не удалось очистить текст:\n{error_msg}", parent=self)
                    
                    # Добавляем ошибку в лог
                    self.batch_log.configure(state="normal")
                    self.batch_log.insert("end", f"❌ Ошибка очистки: {error_msg}\n")
                    self.batch_log.see("end")
                    self.batch_log.configure(state="disabled")
                
                self.after(0, show_error)
        
        # Запускаем в отдельном потоке
        threading.Thread(target=worker, daemon=True).start()

def create_batch_panel(parent, start_callback, stop_callback):
    """Создает и возвращает панель пакетной обработки"""
    return BatchSidebarPanel(parent, start_callback, stop_callback)
