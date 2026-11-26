@echo off
setlocal EnableExtensions
title TelegramScreenshot - Remove persistent startup
cd /d "%~dp0"

set "TS_MAIN=%~dp0main.py"
set "TS_LOG=%~dp0TelegramScreenshot.log"
set "TS_PID=%~dp0.telegramscreenshot.pid"

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Continue';" ^
  "$taskName='TelegramScreenshot';" ^
  "$runKey='HKCU:\Software\Microsoft\Windows\CurrentVersion\Run';" ^
  "Remove-ItemProperty -Path $runKey -Name 'TelegramScreenshot' -ErrorAction SilentlyContinue;" ^
  "if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {" ^
  "  Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue" ^
  "};" ^
  "$all=@(Get-CimInstance Win32_Process -Filter 'Name=''python.exe'' OR Name=''pythonw.exe''' -ErrorAction SilentlyContinue | Where-Object {" ^
  "  $_.CommandLine -and $_.CommandLine.IndexOf('--watch', [System.StringComparison]::OrdinalIgnoreCase) -ge 0 -and ($_.CommandLine.IndexOf($env:TS_MAIN, [System.StringComparison]::OrdinalIgnoreCase) -ge 0 -or $_.CommandLine.IndexOf('main.py', [System.StringComparison]::OrdinalIgnoreCase) -ge 0)" ^
  "});" ^
  "$owned=@($all | Where-Object { $_.CommandLine.IndexOf($env:TS_MAIN, [System.StringComparison]::OrdinalIgnoreCase) -ge 0 });" ^
  "$owned | ForEach-Object {" ^
  "  $stopped=Stop-Process -Id $_.ProcessId -Force -PassThru -ErrorAction SilentlyContinue;" ^
  "  if ($stopped) { $stopped | Wait-Process -Timeout 5 -ErrorAction SilentlyContinue }" ^
  "};" ^
  "Remove-Item -LiteralPath $env:TS_PID -Force -ErrorAction SilentlyContinue;" ^
  "Remove-Item -LiteralPath $env:TS_LOG -Force -ErrorAction SilentlyContinue;" ^
  "if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) { Write-Error 'The scheduled task is still registered.'; exit 1 };" ^
  "$key=Get-Item -LiteralPath $runKey -ErrorAction SilentlyContinue;" ^
  "if ($key -and ($key.GetValueNames() -contains 'TelegramScreenshot')) { Write-Error 'The startup value is still present.'; exit 1 };" ^
  "if (Test-Path -LiteralPath $env:TS_PID) { Write-Error 'The PID file is still present.'; exit 1 };" ^
  "if (Test-Path -LiteralPath $env:TS_LOG) { Write-Error 'The log file is still present.'; exit 1 };" ^
  "$left=@(Get-CimInstance Win32_Process -Filter 'Name=''python.exe'' OR Name=''pythonw.exe''' -ErrorAction SilentlyContinue | Where-Object {" ^
  "  $_.CommandLine -and $_.CommandLine.IndexOf('--watch', [System.StringComparison]::OrdinalIgnoreCase) -ge 0 -and ($_.CommandLine.IndexOf($env:TS_MAIN, [System.StringComparison]::OrdinalIgnoreCase) -ge 0 -or $_.CommandLine.IndexOf('main.py', [System.StringComparison]::OrdinalIgnoreCase) -ge 0)" ^
  "});" ^
  "if ($left.Count -gt 0) { Write-Error ('A watcher process is still running: PID ' + ($left.ProcessId -join ', ') + '. It could not be stopped, or it belongs to a different copy of main.py. Stop it with Ctrl+C in its console or with Task Manager.'); exit 1 }"

if errorlevel 1 (
    echo.
    echo Persistent-mode removal encountered an error, see the messages above.
    pause
    exit /b 1
)

echo.
echo TelegramScreenshot persistent mode has been stopped and removed.
echo The startup entry, the scheduled task, the PID file, and the log are gone.
echo main.py and run-once.bat remain available for manual use.
echo Restart Telegram to undo the patch in its currently running process.
pause
exit /b 0
