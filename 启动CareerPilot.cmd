@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-careerpilot.ps1"
if errorlevel 1 (
  echo.
  echo CareerPilot failed to start. See data\logs for details.
  pause
  exit /b 1
)
