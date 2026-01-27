# Core module - Ядро приложения
from core.app_state import AppState, app_state
from core.settings_manager import load_settings, save_settings, get_settings_path
from core.prompts_manager import PromptsManager

__all__ = ['AppState', 'app_state', 'load_settings', 'save_settings', 'get_settings_path', 'PromptsManager']
