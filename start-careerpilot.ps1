[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$frontend = Join-Path $projectRoot "frontend"
$logDirectory = Join-Path $projectRoot "data\logs"
$welcomeUrl = "http://127.0.0.1:9999/#/welcome"

function Test-Url([string]$Url) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    } catch {
        return $false
    }
}

function Test-Port([int]$Port) {
    return $null -ne (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
}

function Wait-Url([string]$Url, [string]$Name) {
    foreach ($attempt in 1..30) {
        if (Test-Url $Url) { return }
        Start-Sleep -Seconds 1
    }
    throw "$Name 启动超时。请查看 data\logs 中的日志。"
}

if (-not (Test-Path -LiteralPath $python)) {
    throw "缺少 Python 虚拟环境。请先按 README 创建 .venv 并安装 requirements.txt。"
}
if (-not (Test-Path -LiteralPath (Join-Path $frontend "node_modules"))) {
    throw "缺少前端依赖。请先在 frontend 目录运行 npm install。"
}
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    throw "未找到 npm.cmd。请先安装 Node.js。"
}

New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null

$apiHealthy = Test-Url "http://127.0.0.1:9998/api/v1/health"
if (-not $apiHealthy -and (Test-Port 9998)) {
    throw "端口 9998 已被其他程序占用。请关闭占用程序后重试。"
}
if (-not $apiHealthy) {
    Write-Host "正在启动 CareerPilot 后端..."
    Start-Process -FilePath $python -WorkingDirectory $projectRoot -WindowStyle Hidden `
        -ArgumentList @("-m", "uvicorn", "careerpilot.api:app", "--app-dir", "backend\src", "--host", "127.0.0.1", "--port", "9998") `
        -RedirectStandardOutput (Join-Path $logDirectory "backend.out.log") `
        -RedirectStandardError (Join-Path $logDirectory "backend.err.log")
    Wait-Url "http://127.0.0.1:9998/api/v1/health" "后端"
}

$frontendHealthy = Test-Url "http://127.0.0.1:9999"
if (-not $frontendHealthy -and (Test-Port 9999)) {
    throw "端口 9999 已被其他程序占用。请关闭占用程序后重试。"
}
if (-not $frontendHealthy) {
    Write-Host "正在启动 CareerPilot 前端..."
    Start-Process -FilePath "npm.cmd" -WorkingDirectory $frontend -WindowStyle Hidden `
        -ArgumentList @("run", "dev") `
        -RedirectStandardOutput (Join-Path $logDirectory "frontend.out.log") `
        -RedirectStandardError (Join-Path $logDirectory "frontend.err.log")
    Wait-Url "http://127.0.0.1:9999" "前端"
}

Write-Host "CareerPilot 已就绪：$welcomeUrl" -ForegroundColor Green
Start-Process $welcomeUrl
