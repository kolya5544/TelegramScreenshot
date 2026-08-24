@echo off
setlocal
title TelegramScreenshot - Run once
cd /d "%~dp0"

powershell.exe -NoProfile -Command "$identity=[Security.Principal.WindowsIdentity]::GetCurrent(); $principal=New-Object Security.Principal.WindowsPrincipal($identity); if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { exit 0 } else { exit 1 }" >nul 2>&1
if errorlevel 1 (
    echo TelegramScreenshot needs Administrator access to patch Telegram.
    echo Requesting elevation...
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

set "PYTHON_COMMAND="
where python.exe >nul 2>&1
if not errorlevel 1 set "PYTHON_COMMAND=python.exe"
if not defined PYTHON_COMMAND (
    where py.exe >nul 2>&1
    if not errorlevel 1 set "PYTHON_COMMAND=py.exe -3"
)

if not defined PYTHON_COMMAND (
    echo Python 3 was not found. Install 64-bit Python and try again.
    pause
    exit /b 1
)

%PYTHON_COMMAND% "%~dp0main.py"
set "RESULT=%ERRORLEVEL%"
echo.
if not "%RESULT%"=="0" echo TelegramScreenshot did not complete successfully.
pause
exit /b %RESULT%
