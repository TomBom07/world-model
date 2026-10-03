$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "Rook / WorldModel verified local launch" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python was not found. Install Python 3.11 or 3.12, then reopen PowerShell."
}

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

$py = ".\.venv\Scripts\python.exe"
$wm = ".\.venv\Scripts\worldmodel.exe"

& $py -m pip install --upgrade pip
& $py -m pip install -e ".[dev]"

Write-Host ""
Write-Host "Running tests..." -ForegroundColor Yellow
& $py -m pytest
if ($LASTEXITCODE -ne 0) { throw "pytest failed" }

Write-Host ""
Write-Host "Running integrated research doctor..." -ForegroundColor Yellow
& $wm doctor --seed 7
if ($LASTEXITCODE -ne 0) { throw "worldmodel doctor failed" }

Write-Host ""
Write-Host "All checks passed. Opening http://127.0.0.1:8000" -ForegroundColor Green
Start-Process "http://127.0.0.1:8000"
& $wm serve --host 127.0.0.1 --port 8000
