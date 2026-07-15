# Windows 开发环境一键启动 (无需 Docker)
# 用法: .\start-dev.ps1
# 或者: 右键 → "使用 PowerShell 运行"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  档案智能查询与开放审核系统 — 本地开发" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir
$env:PYTHONPATH = "$ScriptDir\backend"

# 检查 Python 虚拟环境
if (Test-Path ".venv\Scripts\python.exe") {
    $Python = ".venv\Scripts\python.exe"
    Write-Host "[OK] 使用虚拟环境: .venv" -ForegroundColor Green
} else {
    $Python = "python"
    Write-Host "[!] 未找到 .venv，使用系统 Python" -ForegroundColor Yellow
}

# 安装依赖
Write-Host ""
Write-Host "[1/3] 检查 Python 依赖..." -ForegroundColor Yellow
& $Python -m pip install -q fastapi uvicorn pydantic pydantic-settings sqlalchemy python-jose passlib python-multipart python-dotenv 2>&1 | Out-Null
Write-Host "      依赖就绪" -ForegroundColor Green

# 初始化 SQLite 数据库（首次运行自动创建）
Write-Host "[2/3] 初始化数据库 (SQLite)..." -ForegroundColor Yellow
& $Python -c "from app.core.config import settings; print('  DB_MODE:', settings.DB_MODE); print('  DB_URL:', settings.DATABASE_URL)"
Write-Host "      数据库就绪" -ForegroundColor Green

# 启动 FastAPI
Write-Host "[3/3] 启动 FastAPI 服务..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  ==========================================" -ForegroundColor Cyan
Write-Host "  后端 API:   http://localhost:8000" -ForegroundColor White
Write-Host "  Swagger:    http://localhost:8000/docs" -ForegroundColor White
Write-Host "  健康检查:   http://localhost:8000/api/health" -ForegroundColor White
Write-Host "  ==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  LLM 模式: $env:LLM_MODE (mock=模拟数据)" -ForegroundColor DarkGray
Write-Host "  OCR 模式: $env:OCR_MODE (mock=模拟数据)" -ForegroundColor DarkGray
Write-Host "  数据库:   SQLite (无需 MySQL)" -ForegroundColor DarkGray
Write-Host "  默认账号: admin / 任意密码" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  按 Ctrl+C 停止服务" -ForegroundColor DarkGray
Write-Host ""

& $Python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
