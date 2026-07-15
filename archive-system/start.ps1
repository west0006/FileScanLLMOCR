# 一键启动脚本 — 同时启动前后端
# 用法: .\start.ps1
# 前置: Python 3.11+ / Node.js 18+ / .venv (后端)

param([switch]$NoFrontend)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "========================================" -ForegroundColor Green
Write-Host "  档案智能查询与开放审核系统" -ForegroundColor Green
Write-Host "  v2.0 — 翡翠绿 · 极简扁平" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# === 后端 ===
Write-Host "[后端] 启动 FastAPI (端口 8000)..." -ForegroundColor Cyan
$env:PYTHONPATH = "$root\backend"

if (Test-Path "$root\.venv\Scripts\python.exe") {
    $py = "$root\.venv\Scripts\python.exe"
} else {
    $py = "python"
    Write-Host "  [!] 未找到 .venv, 使用系统 Python" -ForegroundColor Yellow
}

# 安装依赖（静默）
& $py -m pip install -q fastapi uvicorn pydantic pydantic-settings sqlalchemy python-jose passlib python-multipart python-dotenv aiosqlite 2>&1 | Out-Null

# 启动后端
$backendJob = Start-Job -Name "archive-backend" -ScriptBlock {
    param($py, $root)
    $env:PYTHONPATH = "$root\backend"
    Set-Location $root
    & $py -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload 2>&1
} -ArgumentList $py, $root

Write-Host "  [OK] 后端启动中... http://localhost:8000" -ForegroundColor Green
Write-Host "  [文档] http://localhost:8000/docs" -ForegroundColor DarkGray

# === 前端 ===
if (-not $NoFrontend) {
    $frontendDir = "$root\frontend"
    if (Test-Path "$frontendDir\node_modules") {
        Write-Host ""
        Write-Host "[前端] 启动 Vite (端口 3000)..." -ForegroundColor Cyan
        $frontendJob = Start-Job -Name "archive-frontend" -ScriptBlock {
            param($dir)
            Set-Location $dir
            npx vite --host 0.0.0.0 --port 3000 2>&1
        } -ArgumentList $frontendDir
        Write-Host "  [OK] 前端启动中... http://localhost:3000" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "[前端] 安装依赖..." -ForegroundColor Yellow
        Set-Location $frontendDir
        npm install 2>&1 | Out-Null
        Write-Host "[前端] 启动 Vite (端口 3000)..." -ForegroundColor Cyan
        $frontendJob = Start-Job -Name "archive-frontend" -ScriptBlock {
            param($dir)
            Set-Location $dir
            npx vite --host 0.0.0.0 --port 3000 2>&1
        } -ArgumentList $frontendDir
        Write-Host "  [OK] 前端启动中... http://localhost:3000" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  后端: http://localhost:8000" -ForegroundColor White
Write-Host "  API文档: http://localhost:8000/docs" -ForegroundColor White
if (-not $NoFrontend) {
    Write-Host "  前端: http://localhost:3000" -ForegroundColor White
}
Write-Host "  登录: admin / 任意密码" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "按 Ctrl+C 停止..." -ForegroundColor DarkGray

try {
    while ($true) {
        $b = Receive-Job -Name "archive-backend"
        if ($b) { Write-Host $b }
        if (-not $NoFrontend) {
            $f = Receive-Job -Name "archive-frontend"
            if ($f) { Write-Host $f }
        }
        Start-Sleep -Seconds 2
    }
} finally {
    Stop-Job -Name "archive-backend" -ErrorAction SilentlyContinue
    Remove-Job -Name "archive-backend" -ErrorAction SilentlyContinue
    if (-not $NoFrontend) {
        Stop-Job -Name "archive-frontend" -ErrorAction SilentlyContinue
        Remove-Job -Name "archive-frontend" -ErrorAction SilentlyContinue
    }
    Write-Host "已停止所有服务" -ForegroundColor Yellow
}
