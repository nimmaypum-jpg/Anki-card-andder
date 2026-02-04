@echo off
chcp 65001 >nul
echo ========================================
echo   Установка зависимостей Wordy
echo ========================================
echo.

REM Проверяем наличие Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден! Установите Python 3.10+ с python.org
    pause
    exit /b 1
)

REM Если .venv существует, но сломано - удаляем
if exist .venv\pyvenv.cfg (
    echo Проверяем виртуальное окружение...
    .venv\Scripts\python.exe --version >nul 2>&1
    if errorlevel 1 (
        echo ⚠️ Виртуальное окружение повреждено. Пересоздаём...
        rmdir /s /q .venv
    )
)

REM Создаём .venv если его нет
if not exist .venv (
    echo 📦 Создаём виртуальное окружение...
    python -m venv .venv
    if errorlevel 1 (
        echo ❌ Ошибка создания виртуального окружения!
        pause
        exit /b 1
    )
)

echo ✅ Виртуальное окружение готово.
echo.

echo 📦 Устанавливаем зависимости...
call .venv\Scripts\activate.bat
pip install --upgrade pip >nul
pip install -r requirements.txt
pip install pyinstaller
echo.
echo ✅ Все зависимости установлены!
echo.
echo ========================================
echo   Готово! Для запуска: run_anki_helper.bat
echo ========================================
echo.
echo Для сборки EXE:
echo   .venv\Scripts\python.exe -m PyInstaller wordy.spec --noconfirm
echo.
pause