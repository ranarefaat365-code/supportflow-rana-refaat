@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (echo Run 1_SETUP_WINDOWS.cmd first. & pause & exit /b 1)
echo If the backend is already running, keep its original window open instead.
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
pause
