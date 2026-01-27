# -*- coding: utf-8 -*-
"""
Модуль управления промптами.
Загрузка, сохранение и редактирование промптов AI.
"""
import os
import json
from typing import Dict, Optional

from core.settings_manager import get_user_dir, get_data_dir, get_resource_path, DEFAULT_TRANSLATE_PROMPT, DEFAULT_CONTEXT_PROMPT


def get_prompts_file_path() -> str:
    """Возвращает путь к файлу промптов (сначала во внешней папке data)"""
    external_path = os.path.join(get_data_dir(), "prompts.json")
    if os.path.exists(external_path):
        return external_path
    
    # Если внешнего нет, возвращаем путь, куда он должен быть сохранен или взят из ресурсов
    return external_path


class PromptsManager:
    """Менеджер для работы с промптами"""
    
    def __init__(self):
        self.prompts_file = get_prompts_file_path()
        self._cache: Optional[Dict] = None
    
    def load_prompts(self, force_reload: bool = False) -> Dict:
        """
        Загружает промпты из файла.
        """
        if self._cache is not None and not force_reload:
            return self._cache
            
        # Пытаемся загрузить из внешнего файла
        if os.path.exists(self.prompts_file):
            try:
                with open(self.prompts_file, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
                    return self._cache
            except Exception as e:
                print(f"⚠️ Ошибка загрузки внешних промптов: {e}")

        # Если внешнего нет, пытаемся загрузить из внутренних ресурсов
        try:
            resource_path = get_resource_path("prompts.json")
            if os.path.exists(resource_path):
                with open(resource_path, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
                    return self._cache
        except Exception as e:
            print(f"⚠️ Ошибка загрузки встроенных промптов: {e}")
        
        self._cache = {}
        return self._cache
    
    def save_prompts(self, prompts: Dict) -> bool:
        """
        Сохраняет промпты в файл.
        
        Args:
            prompts: Dict с промптами
            
        Returns:
            True при успехе
        """
        try:
            with open(self.prompts_file, "w", encoding="utf-8") as f:
                json.dump(prompts, f, ensure_ascii=False, indent=2)
            self._cache = prompts
            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения промптов: {e}")
            return False
    
    def get_preset(self, name: str) -> Optional[Dict]:
        """Получает пресет по имени"""
        prompts = self.load_prompts()
        return prompts.get(name)
    
    def save_preset(self, name: str, translate_prompt: str, context_prompt: str) -> bool:
        """Сохраняет или обновляет пресет"""
        prompts = self.load_prompts()
        prompts[name] = {
            "translate": translate_prompt,
            "context": context_prompt
        }
        return self.save_prompts(prompts)
    
    def delete_preset(self, name: str) -> bool:
        """Удаляет пресет"""
        prompts = self.load_prompts()
        if name in prompts:
            del prompts[name]
            return self.save_prompts(prompts)
        return False
    
    def rename_preset(self, old_name: str, new_name: str) -> bool:
        """Переименовывает пресет"""
        prompts = self.load_prompts()
        if old_name not in prompts:
            return False
        if new_name in prompts:
            print(f"⚠️ Пресет '{new_name}' уже существует")
            return False
        
        prompts[new_name] = prompts.pop(old_name)
        return self.save_prompts(prompts)
    
    def get_delimiter(self, name: str) -> str:
        """Получает разделитель контекста для пресета"""
        preset = self.get_preset(name)
        if preset:
             return preset.get("delimiter", "КОНТЕКСТ")
        return "КОНТЕКСТ"

    def get_preset_names(self) -> list:
        """Возвращает отсортированный список имен пресетов"""
        return sorted(self.load_prompts().keys())
    
    def create_defaults_if_missing(self) -> bool:
        """
        Создает файл с дефолтными промптами если его нет.
        
        Returns:
            True если файл был создан или уже существует
        """
        if os.path.exists(self.prompts_file):
            return True
        
        default_prompts = self._get_default_prompts()
        return self.save_prompts(default_prompts)
    
    def _get_default_prompts(self) -> Dict:
        """Возвращает дефолтные промпты для немецкого языка"""
        return {
            "A1.1 - Начальный": {
                "translate": DEFAULT_TRANSLATE_PROMPT,
                "context": DEFAULT_CONTEXT_PROMPT,
                "delimiter": "КОНТЕКСТ"
            },
            "A1.2 - Базовый": {
                "translate": DEFAULT_TRANSLATE_PROMPT,
                "context": DEFAULT_CONTEXT_PROMPT,
                "delimiter": "КОНТЕКСТ"
            },
            "A2.1 - Элементарный": {
                "translate": DEFAULT_TRANSLATE_PROMPT,
                "context": DEFAULT_CONTEXT_PROMPT,
                "delimiter": "КОНТЕКСТ"
            },
            "A2.2 - Предсредний": {
                "translate": DEFAULT_TRANSLATE_PROMPT,
                "context": DEFAULT_CONTEXT_PROMPT,
                "delimiter": "КОНТЕКСТ"
            },
            "B1.1 - Средний": {
                "translate": DEFAULT_TRANSLATE_PROMPT,
                "context": DEFAULT_CONTEXT_PROMPT,
                "delimiter": "КОНТЕКСТ"
            },
            "B1.2 - Продвинутый средний": {
                "translate": DEFAULT_TRANSLATE_PROMPT,
                "context": DEFAULT_CONTEXT_PROMPT,
                "delimiter": "КОНТЕКСТ"
            },
            "B2.1 - Выше среднего": {
                "translate": DEFAULT_TRANSLATE_PROMPT,
                "context": DEFAULT_CONTEXT_PROMPT,
                "delimiter": "КОНТЕКСТ"
            },
            "B2.2 - Продвинутый": {
                "translate": DEFAULT_TRANSLATE_PROMPT,
                "context": DEFAULT_CONTEXT_PROMPT,
                "delimiter": "КОНТЕКСТ"
            }
        }


# Глобальный экземпляр менеджерa промптов
prompts_manager = PromptsManager()


def update_active_prompts(translate_prompt: str, context_prompt: str, delimiter: str = "КОНТЕКСТ"):
    """
    Обновляет активные промпты в текущем сеансе.
    Совместимость со старым кодом.
    """
    from core.app_state import app_state
    app_state.translate_prompt = translate_prompt
    app_state.context_prompt = context_prompt
    app_state.context_delimiter = delimiter


def rename_prompt_preset(old_name: str, new_name: str) -> bool:
    """
    Переименовывает пресет и обновляет UI.
    Совместимость со старым кодом.
    """
    from core.app_state import app_state
    
    if not prompts_manager.rename_preset(old_name, new_name):
        return False
    
    # Обновляем UI главного окна если пресет был выбран
    try:
        if app_state.main_window_components and "vars" in app_state.main_window_components:
            prompt_var = app_state.main_window_components["vars"].get("prompt_var")
            if prompt_var and prompt_var.get() == old_name:
                prompt_var.set(new_name)
            
            # Обновляем список в комбобоксе
            prompt_combo = app_state.main_window_components["widgets"].get("prompt_combo")
            if prompt_combo:
                prompt_combo.configure(values=prompts_manager.get_preset_names())
    except Exception as e:
        print(f"⚠️ Ошибка обновления UI после переименования: {e}")
    
    return True
