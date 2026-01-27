import os
import re
import hashlib
import time
import subprocess
from gtts import gTTS
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
    if getattr(sys, 'frozen', False):
         # Если запущен из exe - сохраняем файлы рядом с exe
        project_dir = os.path.dirname(sys.executable)
    else:
        # Если запущен из Python - используем директорию скрипта
        project_dir = os.path.dirname(__file__)
    return os.path.join(project_dir, "user_files")

def ensure_success_sound():
    """
    Проверяет наличие файла success.wav в папке assets. 
    Если его нет - создает папку и генерирует звук.
    """
    import sys
    
    # Определяем базовую директорию
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(__file__)
        
    # Путь к папке ресурсов
    assets_dir = os.path.join(base_dir, "assets")
    if not os.path.exists(assets_dir):
        try:
            os.makedirs(assets_dir)
        except Exception as e:
            print(f"Не удалось создать папку assets: {e}")
            return None
            
    filepath = os.path.join(assets_dir, "success.wav")
    
    if os.path.exists(filepath):
        return filepath
        
    try:
        # Параметры аудио
        sample_rate = 44100
        duration = 0.1  # Длительность одной ноты
        volume = 0.15   # БЫЛО 0.5
        
        # Ноты (До-Мажор: C5, E5, G5)
        freqs = [523.25, 659.25, 783.99]
        
        audio_data = []
        
        for freq in freqs:
            num_samples = int(sample_rate * duration)
            for i in range(num_samples):
                t = float(i) / sample_rate
                # Генерируем синусоиду
                value = math.sin(2.0 * math.pi * freq * t)
                # Применяем простую огибающую (envelope) чтобы не щелкало
                if i < 500: value *= (i / 500)
                if i > num_samples - 500: value *= ((num_samples - i) / 500)
                
                # Конвертируем в 16-бит integer
                sample = int(value * volume * 32767.0)
                audio_data.append(struct.pack('<h', sample))
            
            # Добавляем небольшую паузу
            pause_samples = int(sample_rate * 0.05)
            for _ in range(pause_samples):
                audio_data.append(struct.pack('<h', 0))

        with wave.open(filepath, 'w') as wav_file:
            wav_file.setnchannels(1) # Моно
            wav_file.setsampwidth(2) # 2 байта (16 бит)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b''.join(audio_data))
            
        return filepath
    except Exception as e:
        print(f"Ошибка создания success.wav: {e}")
        return None

def ensure_notify_sound():
    """
    Проверяет наличие файла notify.wav в папке assets. 
    Если его нет - генерирует мягкий сигнал.
    """
    import sys
    
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(__file__)
        
    assets_dir = os.path.join(base_dir, "assets")
    if not os.path.exists(assets_dir):
        try: os.makedirs(assets_dir)
        except Exception: return None
            
    filepath = os.path.join(assets_dir, "notify.wav")
    
    if os.path.exists(filepath):
        return filepath
        
    try:
        sample_rate = 44100
        duration = 0.15 
        volume = 0.4
        freq = 800.0
        
        audio_data = []
        num_samples = int(sample_rate * duration)
        
        for i in range(num_samples):
            t = float(i) / sample_rate
            value = math.sin(2.0 * math.pi * freq * t)
            # Плавная огибающая
            if i < 500: value *= (i / 500)
            if i > num_samples - 2000: value *= ((num_samples - i) / 2000)
            
            sample = int(value * volume * 32767.0)
            audio_data.append(struct.pack('<h', sample))

        with wave.open(filepath, 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b''.join(audio_data))
            
        return filepath
    except Exception as e:
        print(f"Ошибка создания notify.wav: {e}")
        return None

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
