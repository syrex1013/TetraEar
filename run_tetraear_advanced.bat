@echo off
REM TETRA Decoder Pro - Advanced Launcher with Options
REM Compiles, optimizes, and runs the application with various modes

setlocal enabledelayedexpansion

echo ============================================================
echo TETRA Decoder Pro - Advanced Launcher
echo ============================================================
echo.

REM Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Parse command line arguments
set "MODE=gui"
set "FREQUENCY="
set "AUTO_START="
set "MONITOR_AUDIO="
set "VERBOSE="

:parse_args
if "%~1"=="" goto :check_python
if /i "%~1"=="--cli" set "MODE=cli" & shift & goto :parse_args
if /i "%~1"=="--no-gui" set "MODE=cli" & shift & goto :parse_args
if /i "%~1"=="-f" set "FREQUENCY=%~2" & shift & shift & goto :parse_args
if /i "%~1"=="--frequency" set "FREQUENCY=%~2" & shift & shift & goto :parse_args
if /i "%~1"=="--auto-start" set "AUTO_START=--auto-start" & shift & goto :parse_args
if /i "%~1"=="-m" set "MONITOR_AUDIO=-m" & shift & goto :parse_args
if /i "%~1"=="--monitor-audio" set "MONITOR_AUDIO=-m" & shift & goto :parse_args
if /i "%~1"=="-v" set "VERBOSE=-v" & shift & goto :parse_args
if /i "%~1"=="--verbose" set "VERBOSE=-v" & shift & goto :parse_args
if /i "%~1"=="--help" goto :show_help
if /i "%~1"=="-h" goto :show_help
shift
goto :parse_args

:show_help
echo Usage: run_tetraear_advanced.bat [OPTIONS]
echo.
echo Options:
echo   --cli, --no-gui         Run in CLI mode without GUI
echo   -f, --frequency FREQ    Set frequency in MHz (e.g., 392.225)
echo   --auto-start            Auto-start capture on launch
echo   -m, --monitor-audio     Enable audio monitoring
echo   -v, --verbose           Enable verbose logging
echo   -h, --help              Show this help message
echo.
echo Examples:
echo   run_tetraear_advanced.bat
echo   run_tetraear_advanced.bat -f 392.225 --auto-start
echo   run_tetraear_advanced.bat --cli -f 390.865 -m
echo.
exit /b 0

:check_python
REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

echo [1/5] Checking Python version...
python --version

REM Check if virtual environment exists
if exist ".venv\Scripts\activate.bat" (
    echo [2/5] Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo [2/5] No virtual environment found, using system Python
)

REM Check dependencies
echo [3/5] Checking dependencies...
python -c "import PyQt6" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] PyQt6 not found. Installing dependencies...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
)

REM Compile Python files to bytecode for faster startup
echo [4/5] Compiling Python modules to bytecode...
python -m compileall -q tetraear\ >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Some modules failed to compile, continuing anyway...
)

REM Optimize bytecode (Python 3.5+)
echo [5/5] Optimizing bytecode...
python -OO -m compileall -q tetraear\ >nul 2>&1

echo.
echo ============================================================
echo Starting TETRA Decoder Pro in %MODE% mode...
echo ============================================================
echo.

REM Build command line
set "CMD=python -OO -m tetraear"

if "%MODE%"=="cli" (
    set "CMD=!CMD! --no-gui"
)

if not "%FREQUENCY%"=="" (
    set "CMD=!CMD! -f %FREQUENCY%"
)

if not "%AUTO_START%"=="" (
    set "CMD=!CMD! %AUTO_START%"
)

if not "%MONITOR_AUDIO%"=="" (
    set "CMD=!CMD! %MONITOR_AUDIO%"
)

if not "%VERBOSE%"=="" (
    set "CMD=!CMD! %VERBOSE%"
)

echo Executing: !CMD!
echo.

REM Run the application
!CMD!

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
