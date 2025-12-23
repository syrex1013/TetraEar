@echo off
REM TETRA Decoder Pro - Silent Quick Launch
REM Minimal output version for desktop shortcuts

cd /d "%~dp0"

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found! Please install Python 3.8+
    pause
    exit /b 1
)

REM Activate venv if exists
if exist ".venv\Scripts\activate.bat" call .venv\Scripts\activate.bat >nul 2>&1

REM Compile modules silently
python -m compileall -q tetraear\ >nul 2>&1

REM Run application
start "TETRA Decoder Pro" python -m tetraear

exit /b 0
