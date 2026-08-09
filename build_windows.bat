@echo off
REM Bygger en fristn projekt.exe fr Windows som dus n kan skicka till vnner.
REM Kr p EN Windows-dator som har Python installerat:
REM   1. cd till den hr mappen
REM   2. pip install -r requirements.txt pyinstaller
REM   3. build_windows.bat
REM Resultat: dist\MattisClicker.exe

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python saknas! Installera det fran https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Installerar beroenden...
python -m pip install -r requirements.txt pyinstaller

echo Bygger exe-filen...
python -m PyInstaller --onefile --noconsole --name MattisClicker main.py

echo.
echo KLART! Skicka filen: dist\MattisClicker.exe
echo Vnner behver INTE installera Python - bara dubbej.dll klicka pa exe-filen.
pause