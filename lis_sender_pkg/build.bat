@echo off
echo ============================================
echo   LIS Sender Tool - Build EXE
echo ============================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.8+
    pause
    exit /b 1
)

echo [1/3] Installing dependencies...
pip install -r requirements.txt -q
echo       Done
echo.

echo [2/3] Building EXE (1-3 minutes)...
pyinstaller --noconfirm --onefile --windowed --name "LIS_Sender" --hidden-import openpyxl --hidden-import paho.mqtt --hidden-import paho.mqtt.client lis_sender_gui.py
if %errorlevel% neq 0 (
    echo [ERROR] Build failed
    pause
    exit /b 1
)
echo       Done
echo.

echo [3/3] Complete!
echo.
echo ============================================
echo   EXE:  dist\LIS_Sender.exe
echo   Double-click to run, no Python needed.
echo ============================================
echo.
explorer dist
pause
