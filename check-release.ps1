[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$frontend = Join-Path $projectRoot "frontend"

function Invoke-Checked([string]$Name, [scriptblock]$Command) {
    Write-Host "`n== $Name ==" -ForegroundColor Cyan
    & $Command
    if ($LASTEXITCODE -ne 0) { throw "$Name 失败（退出码 $LASTEXITCODE）。" }
}

if (-not (Test-Path -LiteralPath $python)) { throw "缺少 .venv，无法执行发布检查。" }
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) { throw "未找到 npm.cmd。" }

Push-Location $projectRoot
try {
    Invoke-Checked "后端测试" { & $python -m pytest backend\tests }
    Invoke-Checked "Python 静态检查" { & $python -m ruff check backend }
    Push-Location $frontend
    try {
        Invoke-Checked "前端类型检查" { & npm.cmd run check }
        Invoke-Checked "前端生产构建" { & npm.cmd run build }
    } finally {
        Pop-Location
    }
} finally {
    Pop-Location
}

Write-Host "`nStage 4C-Windows 发布检查全部通过。" -ForegroundColor Green
