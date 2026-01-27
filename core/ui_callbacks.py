# -*- coding: utf-8 -*-
"""
UI callbacks для обновления интерфейса.
"""
from core.app_state import app_state


# =============================================================================
# FLAG UPDATE CALLBACKS
# =============================================================================
def update_auto_generate_flag(*args):
    """Обновляет флаг автогенерации из UI"""
    try:
        if app_state.main_window_components and "vars" in app_state.main_window_components:
            var = app_state.main_window_components["vars"].get("auto_generate_var")
            if var is not None:
                app_state.auto_generate_on_copy = var.get()
                print(f"🔄 Автогенерация: {'☑ ВКЛ' if app_state.auto_generate_on_copy else '☐ ВЫКЛ'}")
    except Exception as e:
        print(f"⚠️ Ошибка обновления auto_generate: {e}")


def update_pause_monitoring_flag(*args):
    """Обновляет флаг паузы мониторинга из UI"""
    try:
        if app_state.main_window_components and "vars" in app_state.main_window_components:
            var = app_state.main_window_components["vars"].get("pause_monitoring_var")
            if var is not None:
                checkbox_checked = var.get()
                app_state.pause_clipboard_monitoring = not checkbox_checked
                
                print(f"🔄 Перехват буфера: {'☑ ВКЛ' if checkbox_checked else '☐ ВЫКЛ'}")
                
                if "root" in app_state.main_window_components:
                    root = app_state.main_window_components["root"]
                    if app_state.pause_clipboard_monitoring:
                        root._animation_running = False
                        if hasattr(root, '_animation_job'):
                            try:
                                root.after_cancel(root._animation_job)
                            except Exception:
                                pass
                        if hasattr(root, 'animation_label'):
                            root.animation_label.configure(text="")
                    else:
                        root._animation_running = True
                        if hasattr(root, 'start_animation'):
                            root.start_animation()
    except Exception as e:
        print(f"⚠️ Ошибка обновления pause_monitoring: {e}")
        import traceback
        traceback.print_exc()


# =============================================================================
# PROCESSING INDICATOR
# =============================================================================
def update_processing_indicator(text="", animate=False):
    """Обновляет индикатор обработки над полем немецкого текста"""
    if app_state.main_window_components and "widgets" in app_state.main_window_components:
        try:
            indicator = app_state.main_window_components["widgets"].get("processing_indicator")
            if indicator:
                indicator.configure(text=text)
                if animate and "root" in app_state.main_window_components:
                    root = app_state.main_window_components["root"]
                    _start_processing_animation(root, indicator)
                elif not animate and "root" in app_state.main_window_components:
                    root = app_state.main_window_components["root"]
                    _stop_processing_animation(root)
        except Exception:
            pass


def _start_processing_animation(root, indicator):
    """Запускает анимацию точек для индикатора обработки"""
    if not hasattr(root, '_processing_animation_running'):
        root._processing_animation_running = False
    
    if root._processing_animation_running:
        return
    
    root._processing_animation_running = True
    dots = ["", ".", "..", "..."]
    index = [0]
    
    def animate():
        if not root._processing_animation_running:
            return
        indicator.configure(text=f"⏳ Обработка{dots[index[0]]}")
        index[0] = (index[0] + 1) % len(dots)
        root._processing_animation_job = root.after(400, animate)
    
    animate()


def _stop_processing_animation(root):
    """Останавливает анимацию обработки"""
    if hasattr(root, '_processing_animation_running'):
        root._processing_animation_running = False
    if hasattr(root, '_processing_animation_job'):
        root.after_cancel(root._processing_animation_job)
