@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" python -m venv .venv
if not exist ".venv\Scripts\python.exe" (echo Python 3.12 required. & pause & exit /b 1)
.venv\Scripts\python.exe -m pip install -r requirements-windows.txt
if errorlevel 1 (echo Installation failed. & pause & exit /b 1)
.venv\Scripts\python.exe -m scripts.setup_local
if errorlevel 1 (echo Setup failed. & pause & exit /b 1)
echo Setup complete. Open 2_START_BACKEND.cmd and 3_START_FRONTEND.cmd.
pause
