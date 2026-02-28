@echo off
chcp 65001 >nul
echo --- DEBUG START ---
set VENV_PATH=.venv
set PYTHON_EXE=%VENV_PATH%\Scripts\python.exe

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python not found in .venv!
    pause
    exit
)

echo [INFO] Running main.py...
"%PYTHON_EXE%" main.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application crashed with code %errorlevel%
)

echo.
echo --- DEBUG END ---
pause
