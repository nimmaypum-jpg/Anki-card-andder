# =====================================================================================
# Theme Manager - Управление темами интерфейса (CustomTkinter)
# =====================================================================================
import customtkinter as ctk
import os
import sys
import json

class ThemeManager:
    """Класс для управления темами интерфейса с использованием CustomTkinter"""
    
    def __init__(self):
        self.appearance_mode = "Dark"
        self.color_theme = "blue" # blue, dark-blue, green
        
        # Инициализация CustomTkinter
        ctk.set_appearance_mode(self.appearance_mode)
        ctk.set_default_color_theme(self.color_theme)
        
        # Сохраняем совместимость с некоторыми старыми вызовами, если нужно
        self.theme_colors = {
            "bg": "#2b2b2b",
            "fg": "#ffffff",
            "success": "#2cc985",
            "warning": "#eebb00", 
            "error": "#ff5555",
            "info": "#3b8ed0"
        }

    def set_appearance_mode(self, mode):
        """Установить режим внешнего вида (Dark, Light, System)"""
        self.appearance_mode = mode
        ctk.set_appearance_mode(mode)
        
    def set_color_theme(self, theme):
        """Установить цветовую тему"""
        self.color_theme = theme
        ctk.set_default_color_theme(theme)

    def get_status_colors(self):
        """Получить цвета для статусов"""
        return {
            "warning": self.theme_colors["warning"],
            "success": self.theme_colors["success"],
            "error": self.theme_colors["error"],
            "info": self.theme_colors["info"]
        }

    # Заглушки для старых методов, чтобы не ломать код сразу
    def configure_ttk_styles(self):
        pass
        
    def apply_theme_to_children(self, widget):
        pass
        
    def preview_changes(self):
        pass
        
    def save_theme_colors(self):
        pass
        
    def set_title_bar_color(self, window):
        # CustomTkinter делает это автоматически
        pass

# Глобальный экземпляр менеджера тем
theme_manager = ThemeManager()