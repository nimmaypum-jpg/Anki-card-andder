# -*- coding: utf-8 -*-
"""
Модуль настроек - инициализация пакета.
"""
from ui.settings.tts_tab import create_tts_tab
from ui.settings.font_tab import create_font_tab
from ui.settings.theme_tab import create_theme_tab

__all__ = [
    "create_tts_tab",
    "create_font_tab", 
    "create_theme_tab"
]
