@echo off
python lis_sender_gui.py
if %errorlevel% neq 0 (
    echo.
    echo Failed to run. Try: pip install openpyxl paho-mqtt
    pause
)
