@echo off
cd /d "%~dp0"
if not exist "frontend\dist\index.html" (echo Prebuilt frontend missing. Download the complete archive. & pause & exit /b 1)
if not exist ".venv\Scripts\python.exe" (echo Run 1_SETUP_WINDOWS.cmd first. & pause & exit /b 1)
echo Open http://127.0.0.1:5173 in your browser.
.venv\Scripts\python.exe -m http.server 5173 --bind 127.0.0.1 -d frontend/dist
pause
