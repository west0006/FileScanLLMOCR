# Backend only
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:PYTHONPATH = "$root\backend"

if (Test-Path "$root\.venv\Scripts\python.exe") {
    $py = "$root\.venv\Scripts\python.exe"
} else {
    $py = "python"
}

Write-Host "[Backend] http://localhost:8000/docs" -ForegroundColor Green
& $py -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
