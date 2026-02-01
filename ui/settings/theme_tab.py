# -*- coding: utf-8 -*-
"""
Вкладка настроек Темы.
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox

from ui.theme_manager import theme_manager
from core.localization import localization_manager


def create_theme_tab(tab_theme, settings, win):
    """
    Создает содержимое вкладки настроек темы.
    
    Returns:
        dict: Словарь с переменными для сохранения настроек
    """
    # Appearance Mode
    appearance_mode_map = {
        localization_manager.get_text("appearance_dark"): "Dark",
        localization_manager.get_text("appearance_light"): "Light",
        localization_manager.get_text("appearance_system"): "System"
    }
    appearance_mode_map_rev = {v: k for k, v in appearance_mode_map.items()}
    
    ctk.CTkLabel(tab_theme, text=localization_manager.get_text("appearance_mode")).pack(anchor="w", padx=10, pady=10)
    
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
    
    # Language Switcher
    ctk.CTkLabel(tab_theme, text=localization_manager.get_text("language_label")).pack(anchor="w", padx=10, pady=10)
    
    language_map = {"Русский": "ru", "English": "en"}
    language_map_rev = {v: k for k, v in language_map.items()}
    
    current_lang = localization_manager.language
    language_var = tk.StringVar(value=language_map_rev.get(current_lang, "Русский"))
    
    def change_language(new_lang_display):
        new_lang_code = language_map.get(new_lang_display, "ru")
        if new_lang_code != localization_manager.language:
            localization_manager.language = new_lang_code
            msg = "Language changed. Please restart the application to apply changes fully." if new_lang_code == "en" else "Язык изменен. Пожалуйста, перезапустите приложение для полного применения изменений."
            messagebox.showinfo(localization_manager.get_text("success"), msg, parent=win)
    
    ctk.CTkOptionMenu(tab_theme, values=list(language_map.keys()), command=change_language, variable=language_var).pack(padx=10, pady=10)

    # Color Theme
    ctk.CTkLabel(tab_theme, text=localization_manager.get_text("color_theme")).pack(anchor="w", padx=10, pady=10)
    
    color_theme_map = {
        localization_manager.get_text("theme_blue"): "blue",
        localization_manager.get_text("theme_green"): "green",
        localization_manager.get_text("theme_dark_blue"): "dark-blue"
    }
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
    
    return {
        "appearance_mode_var": appearance_mode_var,
        "language_var": language_var,
        "color_theme_var": color_theme_var,
        "language_map": language_map
    }
