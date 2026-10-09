@echo off
setlocal
cd /d "%~dp0"
".venv\Scripts\python.exe" -m unittest discover -s tests -v
if errorlevel 1 exit /b 1
node --test tests/native_bridge.test.cjs
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m xiaoetong_assistant.app --smoke
