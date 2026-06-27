#!/usr/bin/env python3
"""Build EXE - run this if build.bat doesn't work"""
import subprocess, sys, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("=" * 50)
print("  LIS Sender Tool - Build EXE")
print("=" * 50)

# Install deps
print("\n[1/3] Installing dependencies...")
subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"])
print("      Done")

# Build
print("\n[2/3] Building EXE...")
subprocess.check_call([
    sys.executable, "-m", "PyInstaller",
    "--noconfirm", "--onefile", "--windowed",
    "--name", "LIS_Sender",
    "--hidden-import", "openpyxl",
    "--hidden-import", "paho.mqtt",
    "--hidden-import", "paho.mqtt.client",
    "lis_sender_gui.py"
])
print("      Done")

print("\n[3/3] Complete!")
print("=" * 50)
print(f"  EXE: {os.path.join(os.getcwd(), 'dist', 'LIS_Sender.exe')}")
print("=" * 50)

# Open folder
if sys.platform == "win32":
    os.startfile("dist")
