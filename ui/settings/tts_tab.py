# -*- coding: utf-8 -*-
"""
Вкладка настроек TTS (Озвучка).
"""
import customtkinter as ctk
import tkinter as tk
import threading

from core import audio_utils
from core.localization import localization_manager


def create_tts_tab(tab_tts, settings, win):
    """
    Создает содержимое вкладки TTS.
    
    Returns:
        dict: Словарь с переменными для сохранения настроек
    """
    speed_map = {"1.0x (Норм)": 0, "0.8x (Медл)": 1, "0.5x (Очень медл)": 2}
    speed_map_rev = {v: k for k, v in speed_map.items()}
    
    ctk.CTkLabel(tab_tts, text=localization_manager.get_text("speed_label")).pack(anchor="w", padx=10, pady=(10, 0))
    speed_var = tk.StringVar(value=speed_map_rev.get(settings.get("TTS_SPEED_LEVEL", 0), "1.0x (Норм)"))
    speed_combo = ctk.CTkComboBox(tab_tts, variable=speed_var, values=list(speed_map.keys()))
    speed_combo.pack(anchor="w", padx=10, pady=(0, 10))
    
    ctk.CTkLabel(tab_tts, text=localization_manager.get_text("lang_label")).pack(anchor="w", padx=10)
    lang_var = tk.StringVar(value=settings.get("TTS_LANG", "de"))
    ctk.CTkComboBox(tab_tts, variable=lang_var, values=["de", "en", "ru", "fr", "es"]).pack(anchor="w", padx=10, pady=(0, 10))
    
    ctk.CTkLabel(tab_tts, text=localization_manager.get_text("tld_label")).pack(anchor="w", padx=10)
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
    
    ctk.CTkButton(tab_tts, text="🔊 " + localization_manager.get_text("test_audio"), command=test_tts).pack(padx=10, pady=20)
    
    return {
        "speed_var": speed_var,
        "lang_var": lang_var,
        "tld_var": tld_var,
        "speed_map": speed_map
    }
