# -*- coding: utf-8 -*-
"""
Базовый класс для AI провайдеров.
Определяет интерфейс, который должны реализовать все провайдеры.
"""
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional
from dataclasses import dataclass
import re


@dataclass
class GenerationResult:
    """Результат генерации AI"""
    translation: str
    context: str = ""
    raw_response: str = ""
    model_used: str = ""


class BaseAIProvider(ABC):
    """
    Абстрактный базовый класс для AI провайдеров.
    Наследники: OllamaProvider, OpenRouterProvider, GoogleProvider
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Имя провайдера для отображения"""
        pass
    
    @property
    @abstractmethod
    def is_local(self) -> bool:
        """True если провайдер локальный (не требует API ключа)"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Проверяет доступность провайдера"""
        pass
    
    @abstractmethod
    def get_models(self) -> List[str]:
        """
        Возвращает список доступных моделей.
        
        Returns:
            Список имен моделей или пустой список
        """
        pass
    
    @abstractmethod
    def generate(self, prompt: str, model: str = None, 
                 timeout: float = 45) -> str:
        """
        Генерирует ответ на промпт.
        
        Args:
            prompt: Текст промпта
            model: Имя модели (если None, используется дефолтная)
            timeout: Таймаут в секундах
            
        Returns:
            Сгенерированный текст
            
        Raises:
            Exception: При ошибке генерации
        """
        pass
    
    def translate(self, phrase: str, translate_prompt: str, 
                  model: str = None) -> Tuple[str, str]:
        """
        Переводит фразу (только перевод, без контекста).
        
        Args:
            phrase: Фраза для перевода
            translate_prompt: Шаблон промпта с {phrase}
            model: Имя модели
            
        Returns:
            Tuple[перевод, пустой контекст]
        """
        prompt = translate_prompt.format(phrase=phrase)
        result = self.generate(prompt, model)
        return self._clean_markdown(result), ""
    
    def translate_with_context(self, phrase: str, context_prompt: str,
                               model: str = None, delimiter: str = "КОНТЕКСТ") -> Tuple[str, str]:
        """
        Переводит фразу с контекстом.
        
        Args:
            phrase: Фраза для перевода
            context_prompt: Шаблон промпта с {phrase}
            model: Имя модели
            delimiter: Разделитель между переводом и контекстом
            
        Returns:
            Tuple[перевод, контекст]
        """
        prompt = context_prompt.format(phrase=phrase)
        result = self.generate(prompt, model)
        
        # Парсим результат
        translation, context = self._extract_translation_and_context(result, delimiter)
        return self._clean_markdown(translation), self._clean_markdown(context)
    
    def _extract_translation_and_context(self, text: str, delimiter: str = "КОНТЕКСТ") -> Tuple[str, str]:
        """Извлекает перевод и контекст из ответа AI"""
        
        # Формируем паттерн для разделителя контекста
        # Добавляем стандартные варианты для надежности + пользовательский delimiter
        context_patterns = [delimiter, 'КОНТЕКСТ', 'CONTEXT']
        # Убираем дубликаты и пустые строки, экранируем для regex
        unique_patterns = list(set([p for p in context_patterns if p]))
        escaped_patterns = [re.escape(p) for p in unique_patterns]
        
        context_regex = r'[*_]*(' + '|'.join(escaped_patterns) + r')[:*_]*'
        
        parts = re.split(context_regex, text, maxsplit=1, flags=re.IGNORECASE)
        
        # Первая часть - это перевод. 
        # Автоматически убираем любой заголовок в начале, если он есть (текст до первого двоеточия)
        # Паттерн ищет: начало строки, возможные *, затем любые символы кроме двоеточия (2-30 шт), двоеточие
        translation_part = parts[0].strip()
        translation = re.sub(r'^[*_]*[^:\n\r]{2,30}[:*_ \t]*', '', translation_part, count=1).strip()
        
        # Если после очистки ничего не осталось (вдруг перевод был очень коротким и совпал с паттерном), 
        # возвращаем оригинал
        if not translation and translation_part:
            translation = translation_part
            
        # Если в ответе был тег контекста, он будет во 2-м элементе (из-за группы в split), 
        # а сам текст контекста в 3-м.
        context = ""
        if len(parts) > 2:
            context = parts[2].strip()
        elif len(parts) > 1:
            context = parts[1].strip()
            
        return translation, context
    
    def _clean_markdown(self, text: str) -> str:
        """Убирает markdown разметку из текста"""
        
        # Убираем жирный текст
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'__(.+?)__', r'\1', text)
        
        # Убираем курсив
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        text = re.sub(r'_(.+?)_', r'\1', text)
        
        # Убираем заголовки
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
        
        # Убираем маркеры списков
        text = re.sub(r'^\s*[\*\-\+]\s+', '', text, flags=re.MULTILINE)
        
        # Убираем таблицы
        text = re.sub(r'\|[\s-]+\|', '', text)
        text = re.sub(r'\|', '', text)
        
        return text.strip()
