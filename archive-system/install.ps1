# ============================================================
# 一键安装所有依赖
# 用法: .\install.ps1
# ============================================================

param([switch]$BackendOnly, [switch]$FrontendOnly)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "========================================" -ForegroundColor Green
Write-Host "  安装项目依赖" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

# === Python 后端依赖 ===
if (-not $FrontendOnly) {
    Write-Host ""
    Write-Host "[1/2] 安装 Python 后端依赖..." -ForegroundColor Cyan

    if (Test-Path "$root\.venv\Scripts\python.exe") {
        $py = "$root\.venv\Scripts\python.exe"
        Write-Host "  使用虚拟环境: .venv" -ForegroundColor DarkGray
    } else {
        Write-Host "  创建虚拟环境..." -ForegroundColor Yellow
        python -m venv "$root\.venv"
        $py = "$root\.venv\Scripts\python.exe"
    }

    & $py -m pip install --upgrade pip

    # 核心框架
    & $py -m pip install fastapi==0.109.0 uvicorn[standard]==0.27.0 pydantic==2.5.3 pydantic-settings==2.1.0

    # 数据库
    & $py -m pip install sqlalchemy==2.0.25 alembic==1.13.1 pymysql==1.1.0 cryptography==42.0.2 aiosqlite

    # 搜索
    & $py -m pip install elasticsearch==8.12.0

    # 任务队列
    & $py -m pip install redis==5.0.1 celery==5.3.6

    # 认证
    & $py -m pip install python-jose[cryptography]==3.3.0 passlib[bcrypt]==1.7.4 python-multipart==0.0.6

    # 文件处理
    & $py -m pip install Pillow==10.2.0 openpyxl==3.1.2 python-magic==0.4.27

    # 工具
    & $py -m pip install httpx==0.26.0 python-dotenv==1.0.0

    # 敏感词加速（可选，安装失败不影响）
    try { & $py -m pip install pyahocorasick } catch { Write-Host "  [!] pyahocorasick 安装失败（非必需，将使用降级方案）" -ForegroundColor Yellow }

    # OCR（本地开发可选）
    try { & $py -m pip install paddleocr paddlepaddle } catch { Write-Host "  [!] PaddleOCR 安装失败（非必需，mock 模式可用）" -ForegroundColor Yellow }

    # 测试
    & $py -m pip install pytest==8.0.0 pytest-cov==4.1.0 pytest-asyncio==0.23.3

    Write-Host "  [OK] 后端依赖安装完成" -ForegroundColor Green
}

# === Node 前端依赖 ===
if (-not $BackendOnly) {
    Write-Host ""
    Write-Host "[2/2] 安装前端依赖..." -ForegroundColor Cyan

    $frontendDir = "$root\frontend"
    Push-Location $frontendDir
    npm install
    Pop-Location

    Write-Host "  [OK] 前端依赖安装完成" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  安装完成！" -ForegroundColor Green
Write-Host "  启动: .\start.ps1" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Green
