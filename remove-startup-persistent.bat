@echo off
setlocal
title TelegramScreenshot - Remove persistent startup
cd /d "%~dp0"

set "TS_MAIN=%~dp0main.py"
set "TS_LOG=%~dp0TelegramScreenshot.log"
set "TS_PID=%~dp0.telegramscreenshot.pid"

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "$runKey='HKCU:\Software\Microsoft\Windows\CurrentVersion\Run';" ^
  "Remove-ItemProperty -Path $runKey -Name 'TelegramScreenshot' -ErrorAction SilentlyContinue;" ^
  "$watchers=Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {" ^
  "  $_.Name -in @('python.exe','pythonw.exe') -and $_.CommandLine -and $_.CommandLine.Contains($env:TS_MAIN) -and $_.CommandLine.Contains('--watch')" ^
  "};" ^
  "$watchers | ForEach-Object {" ^
  "  $stopped=Stop-Process -Id $_.ProcessId -Force -PassThru -ErrorAction SilentlyContinue;" ^
  "  if ($stopped) { $stopped | Wait-Process -Timeout 5 -ErrorAction SilentlyContinue }" ^
  "};" ^
  "Remove-Item -LiteralPath $env:TS_PID -Force -ErrorAction SilentlyContinue;" ^
  "Remove-Item -LiteralPath $env:TS_LOG -Force -ErrorAction SilentlyContinue"

if errorlevel 1 (
    echo Persistent-mode removal encountered an error.
    pause
    exit /b 1
)

echo.
echo TelegramScreenshot persistent mode has been stopped and removed.
echo The startup entry, PID file, and generated log were deleted.
echo main.py and run-once.bat remain available for manual use.
echo Restart Telegram to undo the patch in its currently running process.
pause
exit /b 0
