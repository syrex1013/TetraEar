@echo off
REM TETRA Decoder GUI Launcher
REM Runs with proper environment setup

echo ============================================================
echo TETRA Decoder GUI
echo ============================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.8 or higher.
    pause
    exit /b 1
)

REM Check if required packages are installed
python -c "import PyQt6" >nul 2>&1
if errorlevel 1 (
    echo Installing GUI dependencies...
    pip install PyQt6 PyQt6-Charts sounddevice
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
)

REM Launch GUI
echo Starting TETRA Decoder GUI...
echo.
python tetra_gui.py

if errorlevel 1 (
    echo.
    echo ============================================================
    echo GUI exited with error
    echo ============================================================
    pause
)
