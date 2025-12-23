@echo off
REM TETRA Decoder Pro - Quick Launch Script
REM Compiles Python files and runs the GUI application

echo ============================================================
echo TETRA Decoder Pro - Launcher
echo ============================================================
echo.

REM Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

echo [1/3] Checking Python version...
python --version

REM Check if virtual environment exists
if exist ".venv\Scripts\activate.bat" (
    echo [2/3] Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo [2/3] No virtual environment found, using system Python
)

REM Compile Python files to bytecode for faster startup
echo [3/3] Compiling Python modules...
python -m py_compile tetraear\__init__.py >nul 2>&1
python -m py_compile tetraear\__main__.py >nul 2>&1
python -m compileall -q tetraear\ui\ >nul 2>&1
python -m compileall -q tetraear\core\ >nul 2>&1
python -m compileall -q tetraear\signal\ >nul 2>&1
python -m compileall -q tetraear\audio\ >nul 2>&1

if errorlevel 1 (
    echo [WARNING] Some modules failed to compile, continuing anyway...
)

echo.
echo ============================================================
echo Starting TETRA Decoder Pro...
echo ============================================================
echo.

REM Run the application
python -m tetraear

REM Check exit code
if errorlevel 1 (
    echo.
    echo ============================================================
    echo [ERROR] Application exited with error code %errorlevel%
    echo ============================================================
    pause
    exit /b %errorlevel%
)

echo.
echo Application closed successfully.
exit /b 0
