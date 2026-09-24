@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (echo Run 1_SETUP_WINDOWS.cmd first. & pause & exit /b 1)
echo Copy the next line privately into the web sign-in field. Do not share it.
.venv\Scripts\python.exe -m scripts.issue_token user_1
pause
