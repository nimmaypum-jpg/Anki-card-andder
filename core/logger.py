# -*- coding: utf-8 -*-
"""
Модуль логирования для дебага.
Единое место для файлового и консольного логирования.
"""
import os
import sys
import datetime


def _get_log_dir() -> str:
    """Возвращает директорию для логов"""
    from core.settings_manager import get_base_data_dir
    log_dir = os.path.join(get_base_data_dir(), "user_files")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def _get_log_path(log_name: str = "audio_debug.log") -> str:
    """Возвращает путь к файлу лога"""
    return os.path.join(_get_log_dir(), log_name)


def debug_log(msg: str, prefix: str = "", log_name: str = "audio_debug.log"):
    """
    Записывает сообщение в файл лога и выводит в консоль.

    Args:
        msg: Сообщение для логирования
        prefix: Префикс (например, "[API]")
        log_name: Имя файла лога
    """
    full_msg = f"{prefix} {msg}".strip() if prefix else msg
    try:
        log_path = _get_log_path(log_name)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now()}] {full_msg}\n")
    except Exception:
        pass
    print(full_msg)
