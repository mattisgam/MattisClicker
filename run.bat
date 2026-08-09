@echo off
chcp 65001 >nul
REM =============================================
REM  MattisClicker - starta pa Windows
REM  Krav: Python installerat (python.org)
REM        + "pip install -r requirements.txt"
REM =============================================

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python saknas! Installera det fran https://www.python.org/downloads/
    echo Glom inte att markera "Add Python to PATH" naer du installerar.
    pause
    exit /b 1
)

python main.py
if %errorlevel% neq 0 (
    echo.
    echo Ngt gick fel. Kor forst:
    echo   pip install -r requirements.txt
    pause
)