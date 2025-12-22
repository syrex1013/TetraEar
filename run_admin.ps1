#Requires -RunAsAdministrator

Write-Host "Running RTL-SDR diagnostic with administrator privileges..." -ForegroundColor Green

# Change to the script directory
Set-Location $PSScriptRoot

# Run the diagnostic
python check_rtl_sdr.py

Write-Host "`nPress any key to exit..." -ForegroundColor Yellow
$null = $host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")