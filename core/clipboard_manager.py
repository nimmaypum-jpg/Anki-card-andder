# -*- coding: utf-8 -*-
"""
Модуль для управления операциями буфера обмена (копирование, вставка, вырезание)
Поддерживает CTkTextbox, CTkEntry и обычные tkinter виджеты.
"""

import customtkinter as ctk
import tkinter as tk
import pyperclip
from typing import Union, Optional


# Типы виджетов как константы
TEXTBOX = "textbox"
ENTRY = "entry"
STANDARD = "standard"


class ClipboardHandler:
    """
    Универсальный обработчик операций буфера обмена.
    Поддерживает различные типы текстовых виджетов и обеспечивает
    единообразную работу с горячими клавишами и контекстным меню.
    """
    
    def __init__(self, widget):
        """
        Инициализация обработчика для указанного виджета.
        
        Args:
            widget: Текстовый виджет (CTkTextbox, CTkEntry или обычный tkinter виджет)
        """
        self.widget = widget
        self._setup_widget_type()
        
    def _setup_widget_type(self):
        """Определяет тип виджета и настраивает соответствующие атрибуты."""
        if hasattr(self.widget, '_textbox'):
            self.widget_type = TEXTBOX
            self.inner_widget = self.widget._textbox
        elif hasattr(self.widget, '_entry'):
            self.widget_type = ENTRY
            self.inner_widget = self.widget._entry
        else:
            self.widget_type = STANDARD
            self.inner_widget = self.widget
    
    def setup_bindings(self):
        """Настраивает все необходимые биндинги для виджета."""
        self._setup_context_menu()
        self._setup_hotkeys()
    
    def _setup_context_menu(self):
        """Создает и настраивает контекстное меню."""
        self.context_menu = tk.Menu(self.inner_widget, tearoff=0)
        
        menu_items = [
            ("Вырезать", self.cut),
            ("Копировать", self.copy),
            ("Вставить", self.paste),
            ("---", None),  # separator
            ("Выделить всё", self.select_all)
        ]
        
        for label, command in menu_items:
            if command:
                self.context_menu.add_command(label=label, command=command)
            else:
                self.context_menu.add_separator()
        
        self.inner_widget.bind("<Button-3>", self._show_context_menu)
    
    def _show_context_menu(self, event):
        """Показывает контекстное меню с учетом состояния виджета."""
        try:
            has_selection = self._has_selection()
            has_clipboard_content = self._has_clipboard_content()
            
            self.context_menu.entryconfig("Вырезать", state="normal" if has_selection else "disabled")
            self.context_menu.entryconfig("Копировать", state="normal" if has_selection else "disabled")
            self.context_menu.entryconfig("Вставить", state="normal" if has_clipboard_content else "disabled")
            
            self.context_menu.tk_popup(event.x_root, event.y_root)
            
        except Exception as e:
            print(f"Ошибка показа контекстного меню: {e}")
    
    def _setup_hotkeys(self):
        """Настраивает горячие клавиши для операций с буфером обмена."""
        if self.widget_type in [TEXTBOX, ENTRY]:
            self._unbind_standard_handlers()
        
        # Привязываем обработчик для разных регистров и раскладок через keycode
        self.inner_widget.bind("<KeyPress>", self._handle_keypress)
        
        # Оставляем стандартные биндинги для подстраховки в англ. раскладке
        for key in ['<Control-a>', '<Control-A>', '<Control-c>', '<Control-C>', 
                   '<Control-x>', '<Control-X>', '<Control-v>', '<Control-V>']:
            if key in ['<Control-a>', '<Control-A>']:
                self.inner_widget.bind(key, self._handle_select_all)
            elif key in ['<Control-c>', '<Control-C>']:
                self.inner_widget.bind(key, self._handle_copy)
            elif key in ['<Control-x>', '<Control-X>']:
                self.inner_widget.bind(key, self._handle_cut)
            else:
                self.inner_widget.bind(key, self._handle_paste)
    
    def _unbind_standard_handlers(self):
        """Отвязывает стандартные обработчики CustomTkinter для избежания конфликтов."""
        widget_class = "Text" if self.widget_type == TEXTBOX else "Entry"
        
        for combo in ["<Control-c>", "<Control-x>", "<Control-v>", 
                     "<Control-C>", "<Control-X>", "<Control-V>"]:
            try:
                self.inner_widget.unbind_class(widget_class, combo)
            except Exception:
                pass
    
    # Обработчики событий
    def _handle_keypress(self, event):
        """Обработчик нажатий клавиш с использованием кодов клавиш."""
        # Проверяем наличие модификатора Control (0x4 на Windows)
        if not (event.state & 0x4):
            return None
        
        # Маппинг keycode на операции
        # Коды клавиш: A=65, C=67, X=88, V=86
        keycode_map = {
            65: self.select_all,  # Ctrl+A
            67: self.copy,        # Ctrl+C
            88: self.cut,         # Ctrl+X
            86: self.paste        # Ctrl+V
        }
        
        operation = keycode_map.get(event.keycode)
        if operation:
            operation()
            return "break"
        
        return None

    def _handle_copy(self, event=None):
        self.copy()
        return "break"
    
    def _handle_cut(self, event=None):
        self.cut()
        return "break"
    
    def _handle_paste(self, event=None):
        self.paste()
        return "break"
    
    def _handle_select_all(self, event=None):
        self.select_all()
        return "break"
    
    def copy(self) -> bool:
        """Копирует выделенный текст в буфер обмена."""
        try:
            selected_text = self._get_selected_text()
            if selected_text:
                pyperclip.copy(selected_text)
                return True
            return False
        except Exception as e:
            print(f"Ошибка копирования: {e}")
            return False
    
    def cut(self) -> bool:
        """Вырезает выделенный текст и копирует его в буфер обмена."""
        try:
            selected_text = self._get_selected_text()
            if selected_text:
                pyperclip.copy(selected_text)
                self._delete_selection()
                return True
            return False
        except Exception as e:
            print(f"Ошибка вырезания: {e}")
            return False
    
    def paste(self) -> bool:
        """Вставляет текст из буфера обмена в позицию курсора."""
        try:
            clipboard_text = pyperclip.paste()
            if clipboard_text:
                self._delete_selection()
                self._insert_text(clipboard_text)
                return True
            return False
        except Exception as e:
            print(f"Ошибка вставки: {e}")
            return False
    
    def select_all(self) -> bool:
        """Выделяет весь текст в виджете."""
        try:
            if self.widget_type == TEXTBOX:
                self.inner_widget.tag_add("sel", "1.0", "end-1c")
            elif self.widget_type == ENTRY:
                self.widget.select_range(0, tk.END)
            else:  # standard
                self.inner_widget.tag_add("sel", "1.0", "end-1c")
            return True
        except Exception as e:
            print(f"Ошибка выделения всего: {e}")
            return False
    
    def _get_selected_text(self) -> str:
        """Получает выделенный текст в зависимости от типа виджета."""
        if self.widget_type == ENTRY:
            try:
                if self.inner_widget.selection_present():
                    start_idx = self.inner_widget.index("sel.first")
                    end_idx = self.inner_widget.index("sel.last")
                    return self.inner_widget.get()[start_idx:end_idx]
            except tk.TclError:
                pass
            return ""
        
        # Универсальный код для textbox и standard
        try:
            return self.inner_widget.get("sel.first", "sel.last")
        except tk.TclError:
            return ""
    
    def _has_selection(self) -> bool:
        """Проверяет наличие выделенного текста."""
        if self.widget_type == ENTRY:
            try:
                return self.inner_widget.selection_present()
            except Exception:
                return False
        
        # Универсальный код для textbox и standard
        try:
            self.inner_widget.get("sel.first", "sel.last")
            return True
        except tk.TclError:
            return False
    
    def _delete_selection(self):
        """Удаляет выделенный текст."""
        if self.widget_type == ENTRY:
            try:
                if self.inner_widget.selection_present():
                    self.inner_widget.delete("sel.first", "sel.last")
            except tk.TclError:
                pass
        else:
            # Универсальный код для textbox и standard
            try:
                self.inner_widget.delete("sel.first", "sel.last")
            except tk.TclError:
                pass
    
    def _insert_text(self, text: str):
        """Вставляет текст в позицию курсора."""
        if self.widget_type == ENTRY:
            try:
                self.inner_widget.insert("insert", text)
            except Exception:
                self.inner_widget.insert(tk.END, text)
        else:
            self.inner_widget.insert("insert", text)
    
    @staticmethod
    def _has_clipboard_content() -> bool:
        """Проверяет наличие текста в буфере обмена."""
        try:
            return bool(pyperclip.paste())
        except Exception:
            return False


class GlobalClipboardManager:
    """
    Глобальный менеджер для обработки горячих клавиш на уровне окна.
    Позволяет перехватывать комбинации клавиш независимо от фокуса виджета.
    """
    
    def __init__(self, root, text_widgets: list):
        """
        Инициализация глобального менеджера.
        
        Args:
            root: Корневое окно приложения
            text_widgets: Список текстовых виджетов для мониторинга
        """
        self.root = root
        self.text_widgets = text_widgets
        self.setup_global_handler()
    
    def setup_global_handler(self):
        """Настраивает глобальный обработчик нажатий клавиш."""
        self.root.bind_all("<KeyPress>", self._global_keypress_handler)
    
    def _global_keypress_handler(self, event):
        """Глобальный обработчик нажатий клавиш."""
        focused_widget = self.root.focus_get()
        if not focused_widget:
            return None
        
        target_widget = self._find_text_widget(focused_widget)
        if not target_widget:
            return None
        
        # Проверяем наличие модификатора Control
        if not (event.state & 0x4):
            return None
        
        # Маппинг keycode на операции
        keycode_map = {
            65: "select_all",  # Ctrl+A
            67: "copy",        # Ctrl+C
            88: "cut",         # Ctrl+X
            86: "paste"        # Ctrl+V
        }
        
        operation = keycode_map.get(event.keycode)
        if operation:
            self._execute_clipboard_operation(target_widget, operation)
            return "break"
        
        return None
    
    def _find_text_widget(self, focused_widget) -> Optional[ClipboardHandler]:
        """Находит соответствующий ClipboardHandler в иерархии виджетов."""
        current = focused_widget
        
        while current:
            for handler in self.text_widgets:
                if handler and hasattr(handler, 'inner_widget') and current == handler.inner_widget:
                    return handler
            current = current.master if hasattr(current, 'master') else None
        
        return None
    
    def _execute_clipboard_operation(self, handler: ClipboardHandler, operation: str):
        """Выполняет операцию с буфером обмена."""
        operation_map = {
            "copy": handler.copy,
            "cut": handler.cut,
            "paste": handler.paste,
            "select_all": handler.select_all
        }
        
        operation_func = operation_map.get(operation)
        if operation_func:
            operation_func()


# =============================================================================
# ФАСАДНЫЕ ФУНКЦИИ ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ
# =============================================================================

def setup_text_widget_context_menu(widget) -> ClipboardHandler:
    """Фасадная функция для быстрой настройки виджета с поддержкой контекстного меню."""
    handler = ClipboardHandler(widget)
    handler.setup_bindings()
    return handler


def setup_clipboard_bindings(widget) -> ClipboardHandler:
    """Фасадная функция для настройки горячих клавиш буфера обмена."""
    handler = ClipboardHandler(widget)
    handler.setup_bindings()
    return handler


def copy_cut_paste_handler(widget, action: str) -> bool:
    """Универсальная функция для выполнения операций с буфером обмена."""
    handler = ClipboardHandler(widget)
    
    operation_map = {
        "copy": handler.copy,
        "cut": handler.cut,
        "paste": handler.paste,
        "select_all": handler.select_all
    }
    
    operation_func = operation_map.get(action)
    return operation_func() if operation_func else False