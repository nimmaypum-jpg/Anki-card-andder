@echo off
echo Установка зависимостей Anki German Helper (локальная версия)...
echo.
echo Активируем виртуальное окружение...
call .venv\Scripts\activate.bat
echo.
echo Устанавливаем пакеты из requirements.txt...
pip install -r requirements.txt
echo.
echo ✅ Зависимости установлены!
echo.
echo Проверьте Ollama (устанавливается отдельно):
echo 1. Скачайте с https://ollama.com
echo 2. ollama pull gemma3:1b
echo 3. Запустите Ollama перед использованием программы
echo.
echo Для запуска программы используйте: run_anki_helper.bat
pause