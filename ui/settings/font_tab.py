# -*- coding: utf-8 -*-
"""
Вкладка настроек Шрифта.
"""
import customtkinter as ctk
import tkinter as tk

from core.clipboard_manager import setup_text_widget_context_menu
from core.localization import localization_manager


def create_font_tab(tab_font, settings, win):
    """
    Создает содержимое вкладки настроек шрифта.
    
    Returns:
        dict: Словарь с переменными для сохранения настроек
    """
    ctk.CTkLabel(tab_font, text=localization_manager.get_text("font_family_label")).pack(anchor="w", padx=10, pady=(10, 5))
    font_family_var = tk.StringVar(value=settings.get("FONT_FAMILY", "Roboto"))
    font_families = ["Roboto", "Arial", "Segoe UI", "Consolas", "Courier New", "Times New Roman", "Verdana", "Tahoma"]
    ctk.CTkComboBox(tab_font, variable=font_family_var, values=font_families, width=200).pack(anchor="w", padx=10, pady=(0, 10))
    
    ctk.CTkLabel(tab_font, text=localization_manager.get_text("font_size_label")).pack(anchor="w", padx=10, pady=(10, 5))
    font_size_var = tk.StringVar(value=str(settings.get("FONT_SIZE", 14)))
    
    size_frame = ctk.CTkFrame(tab_font, fg_color="transparent")
    size_frame.pack(fill="x", padx=10, pady=(0, 10))
    
    size_slider = ctk.CTkSlider(size_frame, from_=10, to=24, number_of_steps=14, width=200)
    size_slider.set(int(font_size_var.get()))
    size_slider.pack(side="left", padx=(0, 10))
    
    size_label = ctk.CTkLabel(size_frame, text=f"{int(size_slider.get())} px", width=50)
    size_label.pack(side="left")
    
    # Preview
    ctk.CTkLabel(tab_font, text=localization_manager.get_text("preview_text_label")).pack(anchor="w", padx=10, pady=(20, 5))
    preview_text = ctk.CTkTextbox(tab_font, height=80)
    preview_text.pack(fill="x", padx=10, pady=(0, 10))
    sample_text = "Hallo! Das ist ein Beispieltext.\nПривет! Это пример текста." if localization_manager.language == "ru" else "Hello! This is a sample text.\nHallo! Das ist ein Beispieltext."
    preview_text.insert("1.0", sample_text)
    preview_text.configure(font=(font_family_var.get(), int(font_size_var.get())))
    setup_text_widget_context_menu(preview_text)
    
    def update_size_label(value):
        size_label.configure(text=f"{int(value)} px")
        font_size_var.set(str(int(value)))
        preview_text.configure(font=(font_family_var.get(), int(value)))
    
    size_slider.configure(command=update_size_label)
    
    def update_preview_font(*args):
        try:
            preview_text.configure(font=(font_family_var.get(), int(font_size_var.get())))
        except Exception:
            pass
    
    font_family_var.trace_add("write", update_preview_font)
    
    return {
        "font_family_var": font_family_var,
        "font_size_var": font_size_var
    }
