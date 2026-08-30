@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$stateFile = Join-Path '%~dp0' 'data\careerpilot-processes.json'; if (-not (Test-Path -LiteralPath $stateFile)) { Write-Host 'CareerPilot is not running.'; exit 0 }; $state = Get-Content -Raw -LiteralPath $stateFile | ConvertFrom-Json; foreach ($entry in @($state.backend, $state.frontend)) { $process = Get-Process -Id $entry.pid -ErrorAction SilentlyContinue; if ($null -eq $process) { continue }; $startedAt = $process.StartTime.ToUniversalTime().ToString('o'); if ($startedAt -ne $entry.started_at_utc) { Write-Warning ('PID {0} belongs to another process; skipped.' -f $entry.pid); continue }; & taskkill.exe /PID $entry.pid /T /F | Out-Null }; Remove-Item -LiteralPath $stateFile -Force -ErrorAction SilentlyContinue; Write-Host 'CareerPilot stopped.'"
if errorlevel 1 (
  echo.
  echo CareerPilot failed to stop.
  pause
  exit /b 1
)
