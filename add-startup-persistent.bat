@echo off
setlocal
title TelegramScreenshot - Add persistent startup
cd /d "%~dp0"

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

set "PYTHONW_PATH="
for /f "usebackq delims=" %%I in (`%PYTHON_COMMAND% -c "import pathlib,sys; print(pathlib.Path(sys.executable).with_name('pythonw.exe'))"`) do set "PYTHONW_PATH=%%I"

if not defined PYTHONW_PATH (
    echo Could not locate pythonw.exe.
    pause
    exit /b 1
)
if not exist "%PYTHONW_PATH%" (
    echo pythonw.exe was not found at:
    echo %PYTHONW_PATH%
    pause
    exit /b 1
)

set "TS_PYTHONW=%PYTHONW_PATH%"
set "TS_MAIN=%~dp0main.py"
set "TS_LOG=%~dp0TelegramScreenshot.log"
set "TS_PID=%~dp0.telegramscreenshot.pid"

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "trap { [Console]::Error.WriteLine($_.Exception.Message); exit 1 };" ^
  "$runKey='HKCU:\Software\Microsoft\Windows\CurrentVersion\Run';" ^
  "$quote=[char]34;" ^
  "$arguments=$quote+$env:TS_MAIN+$quote+' --watch --log-file '+$quote+$env:TS_LOG+$quote+' --pid-file '+$quote+$env:TS_PID+$quote;" ^
  "$command=$quote+$env:TS_PYTHONW+$quote+' '+$arguments;" ^
  "New-ItemProperty -Path $runKey -Name 'TelegramScreenshot' -Value $command -PropertyType String -Force -ErrorAction Stop | Out-Null;" ^
  "$saved=Get-ItemPropertyValue -Path $runKey -Name 'TelegramScreenshot' -ErrorAction Stop;" ^
  "if ($saved -ne $command) { throw 'The startup value could not be verified.' };" ^
  "Start-Process -WindowStyle Hidden -FilePath $env:TS_PYTHONW -ArgumentList $arguments -ErrorAction Stop"

if errorlevel 1 (
    echo Failed to install or start persistent mode.
    pause
    exit /b 1
)

echo.
echo TelegramScreenshot persistent mode is installed and running invisibly.
echo It will start automatically when you sign in to Windows.
echo Use remove-startup-persistent.bat to stop and remove it completely.
pause
exit /b 0
