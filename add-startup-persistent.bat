@echo off
setlocal EnableExtensions
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

%PYTHON_COMMAND% -c "import struct; raise SystemExit(0 if struct.calcsize('P') == 8 else 1)"
if errorlevel 1 (
    echo The Python on PATH is not a working 64-bit Python 3.
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

rem pythonw.exe is a GUI-subsystem binary, so it never owns a console window.
rem The watcher is therefore started without creating a window at all:
rem CreateNoWindow plus UseShellExecute=false tells Windows to allocate no
rem console and no visible frame. Start-Process -WindowStyle Hidden is
rem deliberately not used any more, because SW_HIDE leaves a window that was
rem already created on screen as an unclickable white ghost on some systems.
rem
rem Everything from the start attempt to the confirmation runs in one try
rem block. Any failure rolls the startup entry back again, stops the process
rem this script started, and removes its PID file and log, so a failed run
rem never leaves a half-installed startup entry or an orphaned watcher.
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "trap { [Console]::Error.WriteLine('Error: ' + $_.Exception.Message); exit 1 };" ^
  "$ErrorActionPreference='Stop';" ^
  "$taskName='TelegramScreenshot';" ^
  "$runKey='HKCU:\Software\Microsoft\Windows\CurrentVersion\Run';" ^
  "$quote=[char]34;" ^
  "$argLine=$quote+$env:TS_MAIN+$quote+' --watch --log-file '+$quote+$env:TS_LOG+$quote+' --pid-file '+$quote+$env:TS_PID+$quote;" ^
  "$workDir=Split-Path -Parent $env:TS_MAIN;" ^
  "$user=[Security.Principal.WindowsIdentity]::GetCurrent().Name;" ^
  "$registered=$false;" ^
  "$problem='';" ^
  "try {" ^
  "  $action=New-ScheduledTaskAction -Execute $env:TS_PYTHONW -Argument $argLine -WorkingDirectory $workDir;" ^
  "  $logon=New-ScheduledTaskTrigger -AtLogOn -User $user;" ^
  "  try { $logon.Delay='PT20S' } catch { };" ^
  "  $repeat=New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5);" ^
  "  $settings=New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances Queue -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1);" ^
  "  $principal=New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited;" ^
  "  Register-ScheduledTask -TaskName $taskName -Action $action -Trigger @($logon,$repeat) -Settings $settings -Principal $principal -Description 'Restore Telegram screenshot capture after every sign-in.' -Force | Out-Null;" ^
  "  $stored=Get-ScheduledTask -TaskName $taskName;" ^
  "  if ($stored.Actions[0].Execute -ne $env:TS_PYTHONW) { throw 'The scheduled task action could not be verified.' };" ^
  "  if ($stored.Actions[0].Arguments -ne $argLine) { throw 'The scheduled task arguments could not be verified.' };" ^
  "  if ($stored.Triggers.Count -lt 2) { throw 'The scheduled task triggers could not be verified.' };" ^
  "  $repeatCheck=@($stored.Triggers | Where-Object { $_.Repetition -and $_.Repetition.Interval -eq 'PT5M' });" ^
  "  if ($repeatCheck.Count -lt 1) { throw 'The 5-minute self-check could not be verified.' };" ^
  "  $registered=$true;" ^
  "} catch { $problem=$_.Exception.Message }" ^
  "if (-not $registered) {" ^
  "  Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue" ^
  "};" ^
  "$watcherPid=0;" ^
  "$watcherName='';" ^
  "$confirmed=$false;" ^
  "$failure='';" ^
  "try {" ^
  "  if ($registered) {" ^
  "    Remove-ItemProperty -Path $runKey -Name 'TelegramScreenshot' -ErrorAction SilentlyContinue;" ^
  "    Start-ScheduledTask -TaskName $taskName -ErrorAction Stop" ^
  "  } else {" ^
  "    $psi=New-Object System.Diagnostics.ProcessStartInfo;" ^
  "    $psi.FileName=$env:TS_PYTHONW;" ^
  "    $psi.Arguments=$argLine;" ^
  "    $psi.UseShellExecute=$false;" ^
  "    $psi.CreateNoWindow=$true;" ^
  "    $psi.WindowStyle=[System.Diagnostics.ProcessWindowStyle]::Hidden;" ^
  "    $psi.WorkingDirectory=$workDir;" ^
  "    $command=$quote+$env:TS_PYTHONW+$quote+' '+$argLine;" ^
  "    New-ItemProperty -Path $runKey -Name 'TelegramScreenshot' -Value $command -PropertyType String -Force | Out-Null;" ^
  "    if ((Get-ItemPropertyValue -Path $runKey -Name 'TelegramScreenshot') -ne $command) { throw 'The startup value could not be verified.' };" ^
  "    [void][System.Diagnostics.Process]::Start($psi)" ^
  "  };" ^
  "  for ($i=0; $i -lt 24; $i++) {" ^
  "    $found=Get-CimInstance Win32_Process -Filter 'Name=''pythonw.exe'' OR Name=''python.exe''' -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -and $_.CommandLine.IndexOf('--watch', [System.StringComparison]::OrdinalIgnoreCase) -ge 0 -and $_.CommandLine.IndexOf($env:TS_MAIN, [System.StringComparison]::OrdinalIgnoreCase) -ge 0 } | Select-Object -First 1;" ^
  "    if ($found) { $watcherPid=$found.ProcessId; $watcherName=$found.Name; break };" ^
  "    Start-Sleep -Milliseconds 500" ^
  "  };" ^
  "  if ($watcherPid -gt 0) {" ^
  "    Start-Sleep -Seconds 2;" ^
  "    if (Get-Process -Id $watcherPid -ErrorAction SilentlyContinue) { $confirmed=$true }" ^
  "  };" ^
  "  if (-not $confirmed -and (Test-Path -LiteralPath $env:TS_PID)) {" ^
  "    $wpid=[string](Get-Content -LiteralPath $env:TS_PID -TotalCount 1 -ErrorAction SilentlyContinue);" ^
  "    if ($wpid -match '^\d+$') {" ^
  "      $wp=Get-CimInstance Win32_Process -Filter ('ProcessId=' + $wpid) -ErrorAction SilentlyContinue;" ^
  "      if ($wp -and (@('python.exe','pythonw.exe') -contains $wp.Name) -and $wp.CommandLine -and $wp.CommandLine.IndexOf('--watch', [System.StringComparison]::OrdinalIgnoreCase) -ge 0 -and $wp.CommandLine.IndexOf($env:TS_MAIN, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) { $confirmed=$true; $watcherPid=[int]$wpid; $watcherName=$wp.Name }" ^
  "    }" ^
  "  };" ^
  "  if (-not $confirmed) { throw 'The background watcher did not start.' }" ^
  "} catch {" ^
  "  $failure=$_.Exception.Message;" ^
  "  if ($watcherPid -gt 0) { Stop-Process -Id $watcherPid -Force -ErrorAction SilentlyContinue };" ^
  "  Remove-Item -LiteralPath $env:TS_PID -Force -ErrorAction SilentlyContinue;" ^
  "  Remove-Item -LiteralPath $env:TS_LOG -Force -ErrorAction SilentlyContinue;" ^
  "  if ($registered) { Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue } else { Remove-ItemProperty -Path $runKey -Name 'TelegramScreenshot' -ErrorAction SilentlyContinue };" ^
  "  Start-Sleep -Milliseconds 1500;" ^
  "  Get-CimInstance Win32_Process -Filter 'Name=''pythonw.exe'' OR Name=''python.exe''' -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -and $_.CommandLine.IndexOf('--watch', [System.StringComparison]::OrdinalIgnoreCase) -ge 0 -and $_.CommandLine.IndexOf($env:TS_MAIN, [System.StringComparison]::OrdinalIgnoreCase) -ge 0 } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue };" ^
  "  Write-Output 'The startup entry was rolled back: nothing was left installed.';" ^
  "  throw $failure" ^
  "};" ^
  "Write-Output '';" ^
  "Write-Output 'TelegramScreenshot persistent mode is installed.';" ^
  "if ($registered) { Write-Output 'Startup entry  : scheduled task, at sign-in, re-checked every 5 minutes' } else { Write-Output ('Startup entry  : registry Run key, at sign-in (task scheduler failed: ' + $problem + ')') };" ^
  "Write-Output ('Watcher process: ' + $watcherName + ' PID ' + $watcherPid);" ^
  "Write-Output ('Log file       : ' + $env:TS_LOG);" ^
  "$telegram=@(Get-Process -Name Telegram -ErrorAction SilentlyContinue);" ^
  "if ($telegram.Count -eq 0) {" ^
  "  Write-Output 'Telegram state : not running yet, it is patched within 2 s after it starts'" ^
  "} else {" ^
  "  $patched=$false;" ^
  "  for ($i=0; $i -lt 20; $i++) {" ^
  "    $text='';" ^
  "    if (Test-Path -LiteralPath $env:TS_LOG) { $text=[string](Get-Content -LiteralPath $env:TS_LOG -Raw -ErrorAction SilentlyContinue) };" ^
  "    if ($text.Contains('Telegram PID ' + $telegram[0].Id)) { $patched=$true; break };" ^
  "    Start-Sleep -Milliseconds 500" ^
  "  };" ^
  "  if ($patched) { Write-Output ('Telegram state : PID ' + $telegram[0].Id + ' is patched') } else { Write-Output ('Telegram state : PID ' + $telegram[0].Id + ' not confirmed yet, check the log file') }" ^
  "}"

if errorlevel 1 (
    echo.
    echo Failed to install or start persistent mode.
    pause
    exit /b 1
)

echo.
echo It starts automatically every time you sign in to Windows.
echo No window is created for it, at sign-in or now.
echo Use remove-startup-persistent.bat to stop and remove it completely.
pause
exit /b 0
