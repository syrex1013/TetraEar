@echo off
echo Running RTL-SDR diagnostic as administrator...
echo.

cd /d "%~dp0"

python check_rtl_sdr.py > diagnostic_output.txt 2>&1

echo.
echo Diagnostic output saved to diagnostic_output.txt
echo.
pause