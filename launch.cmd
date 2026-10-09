@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto setup
".venv\Scripts\python.exe" -c "import requests, imageio_ffmpeg, xiaoetong_assistant; imageio_ffmpeg.get_ffmpeg_exe()" >nul 2>&1
if errorlevel 1 goto setup
goto launch
:setup
python scripts\setup.py
if errorlevel 1 (
  pause
  exit /b 1
)
:launch
start "" /b ".venv\Scripts\pythonw.exe" -m xiaoetong_assistant.app
