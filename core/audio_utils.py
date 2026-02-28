import os
import re
import hashlib
import time
import subprocess
# NOTE: gtts импортируется лениво в generate_audio() для ускорения старта
import tkinter as tk
from tkinter import messagebox
import threading
import winsound  # Стандартная библиотека Windows
import wave      # Для создания wav файла
import math
import struct
import sys

# =====================================================================================
# ГЛОБАЛЬНЫЕ НАСТРОЙКИ
# =====================================================================================
TTS_SPEED_LEVEL = 0   # 0: Норм (1.0x), 1: Медл (0.8x), 2: Очень медл (0.5x)
TTS_TLD = "de"
TTS_LANG = "de"

# =====================================================================================
# ФУНКЦИИ ОЗВУЧКИ
# =====================================================================================

def get_audio_folder():
    """Возвращает путь к папке для хранения аудиофайлов"""
    from core.settings_manager import get_base_data_dir
    return os.path.join(get_base_data_dir(), "user_files")

def _ensure_sound(name, freqs, duration, volume):
    """
    Проверяет наличие wav файла в папке assets, создаёт при отсутствии.
    
    Args:
        name: Имя файла (без .wav)
        freqs: Список частот нот (or single frequency)
        duration: Длительность одной ноты в секундах
        volume: Громкость (0.0 - 1.0)
    """
    import sys
    
    from core.settings_manager import get_base_data_dir
    assets_dir = os.path.join(get_base_data_dir(), "assets")
    if not os.path.exists(assets_dir):
        try:
            os.makedirs(assets_dir)
        except Exception as e:
            print(f"Не удалось создать папку assets: {e}")
            return None
    
    filepath = os.path.join(assets_dir, f"{name}.wav")
    if os.path.exists(filepath):
        return filepath
    
    try:
        sample_rate = 44100
        audio_data = []
        
        if isinstance(freqs, (int, float)):
            freqs = [freqs]
        
        for freq in freqs:
            num_samples = int(sample_rate * duration)
            for i in range(num_samples):
                t = float(i) / sample_rate
                value = math.sin(2.0 * math.pi * freq * t)
                # Плавная огибающая
                if i < 500:
                    value *= (i / 500)
                fade_out = min(500, num_samples // 4)
                if i > num_samples - fade_out:
                    value *= ((num_samples - i) / fade_out)
                
                sample = int(value * volume * 32767.0)
                audio_data.append(struct.pack('<h', sample))
            
            # Пауза между нотами
            pause_samples = int(sample_rate * 0.05)
            for _ in range(pause_samples):
                audio_data.append(struct.pack('<h', 0))
        
        with wave.open(filepath, 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b''.join(audio_data))
        
        return filepath
    except Exception as e:
        print(f"Ошибка создания {name}.wav: {e}")
        return None


def ensure_success_sound():
    """Проверяет/создаёт звук успеха (три ноты До-мажор)"""
    return _ensure_sound("success", [523.25, 659.25, 783.99], duration=0.1, volume=0.15)


def ensure_notify_sound():
    """Проверяет/создаёт звук уведомления (один тон)"""
    return _ensure_sound("notify", [800.0], duration=0.15, volume=0.4)

def play_sound(sound_type="success"):
    """
    Воспроизводит звуковой сигнал.
    Теперь использует встроенный winsound и wav файлы.
    """
    def _play():
        try:
            wav_path = None
            if sound_type == "success":
                wav_path = ensure_success_sound()
            elif sound_type == "notify":
                wav_path = ensure_notify_sound()
                
            if wav_path and os.path.exists(wav_path):
                winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            
        except Exception as e:
            print(f"Не удалось воспроизвести звук '{sound_type}': {e}")

    threading.Thread(target=_play, daemon=True).start()

def process_text_for_speed(text, speed_level=0):
    if speed_level == 0:
        return text
    
    # print(f"DEBUG: Processing text for speed level {speed_level}")
    processed_text = text
    
    if speed_level == 1: # Медленно (0.8x-like)
        # Увеличиваем паузы между словами (больше пробелов)
        processed_text = re.sub(r' ', r'   ', processed_text)
        # Увеличиваем паузы после знаков препинания
        processed_text = re.sub(r'([,.!?;:])', r'\1    ', processed_text)
    
    elif speed_level >= 2: # Очень медленно (0.5x-like)
        # Еще больше пробелов
        processed_text = re.sub(r' ', r'      ', processed_text)
        # Много пробелов после знаков препинания
        processed_text = re.sub(r'([,.!?;:])', r'\1       ', processed_text)
        
    return processed_text

def generate_unique_filename(text, lang, speed_level, tld):
    """Генерирует уникальное имя файла"""
    file_data = f"{text}_{lang}_{speed_level}_{tld}_{time.time()}"
    file_hash = hashlib.md5(file_data.encode('utf-8')).hexdigest()
    return f"anki_audio_{file_hash}.mp3"

def generate_audio(text, lang=None, speed_level=None, tld=None, debug=True):
    """Генерирует аудиофайл"""
    lang = lang or TTS_LANG
    speed_level = speed_level if speed_level is not None else TTS_SPEED_LEVEL
    tld = tld or TTS_TLD
    
    if debug:
        print("\n" + "="*50)
        print(f"!!! AUDIO GENERATION !!!")
        print(f"Speed Level: {speed_level}")
        print(f"Language:    {lang}")
        print(f"TLD:         {tld}")
        print(f"Text snippet: {text[:40]}...")
        print("="*50 + "\n")
    
    # gTTS поддерживает параметр slow (True/False)
    # Используем slow=True ТОЛЬКО для уровня Very Slow (2), 
    # так как он ОЧЕНЬ медленный сам по себе.
    gtts_slow = speed_level >= 2
    
    audio_folder = get_audio_folder()
    os.makedirs(audio_folder, exist_ok=True)
    
    # Обрабатываем текст в зависимости от уровня скорости
    processed_text = process_text_for_speed(text, speed_level)
    
    filename = generate_unique_filename(processed_text, lang, speed_level, tld)
    filepath = os.path.join(audio_folder, filename)
    
    try:
        from gtts import gTTS  # Lazy import
        tts = gTTS(text=processed_text, lang=lang, slow=gtts_slow, tld=tld)
        tts.save(filepath)
        return filepath if os.path.exists(filepath) else None
    except Exception as e:
        if debug: print(f"❌ Ошибка TTS: {e}")
        return None

def play_text_audio(text, lang=None, speed_level=None, tld=None, parent=None, debug=False):
    """Воспроизводит текст"""
    try:
        if not text: return False
        audio_path = generate_audio(text, lang, speed_level, tld, debug=debug)
        if audio_path:
            # Используем subprocess.Popen с командой start для Windows
            # Это надежнее os.startfile в многопоточном окружении
            subprocess.Popen(['start', '', audio_path], shell=True)
            return True
        return False
    except Exception as e:
        if parent: messagebox.showerror("Ошибка озвучки", str(e), parent=parent)
        return False

def update_tts_settings(lang=None, speed_level=None, tld=None):
    """Обновляет глобальные настройки"""
    global TTS_LANG, TTS_SPEED_LEVEL, TTS_TLD
    if lang is not None: TTS_LANG = lang
    if speed_level is not None: TTS_SPEED_LEVEL = speed_level
    if tld is not None: TTS_TLD = tld

def test_tts(text, lang, speed_level, tld, parent=None):
    """Тестовая функция для окна настроек"""
    play_text_audio(text, lang, speed_level, tld, parent=parent)
