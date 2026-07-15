# Archive System - One-click Start
# Usage: .\start.ps1

param([switch]$NoFrontend)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "========================================" -ForegroundColor Green
Write-Host "  Archive AI System v2.0" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# === Backend ===
Write-Host "[Backend] Starting FastAPI (port 8000)..." -ForegroundColor Cyan
$env:PYTHONPATH = "$root\backend"

if (Test-Path "$root\.venv\Scripts\python.exe") {
    $py = "$root\.venv\Scripts\python.exe"
} else {
    $py = "python"
}

$backendProc = Start-Process -FilePath $py -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload" -NoNewWindow -PassThru
Write-Host "  [OK] http://localhost:8000" -ForegroundColor Green

# === Frontend ===
if (-not $NoFrontend) {
    Write-Host "[Frontend] Starting Vite (port 3000)..." -ForegroundColor Cyan
    $frontendDir = "$root\frontend"
    if (-not (Test-Path "$frontendDir\node_modules")) {
        Write-Host "  Installing dependencies..." -ForegroundColor Yellow
        Push-Location $frontendDir; npm install; Pop-Location
    }
    $frontendProc = Start-Process -FilePath "cmd" -ArgumentList "/c", "npx vite --host 0.0.0.0 --port 3000" -NoNewWindow -PassThru -WorkingDirectory $frontendDir
    Write-Host "  [OK] http://localhost:3000" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Backend:  http://localhost:8000/docs" -ForegroundColor White
if (-not $NoFrontend) { Write-Host "  Frontend: http://localhost:3000" -ForegroundColor White }
Write-Host "  Login:    admin / any-password" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Green

Write-Host "Press any key to stop..." -ForegroundColor DarkGray
$null = $host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

if ($backendProc) { Stop-Process -Id $backendProc.Id -Force }
if ($frontendProc) { Stop-Process -Id $frontendProc.Id -Force }
Write-Host "Stopped." -ForegroundColor Yellow
