$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "Rook / WorldModel local setup" -ForegroundColor Cyan
Write-Host "=============================" -ForegroundColor Cyan

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python was not found. Install Python 3.11 or 3.12, then reopen PowerShell."
}

$version = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "Python $version"

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -e ".[dev]"

Write-Host ""
Write-Host "Running full test suite..." -ForegroundColor Yellow
& ".\.venv\Scripts\python.exe" -m pytest
if ($LASTEXITCODE -ne 0) { throw "pytest failed" }

Write-Host ""
Write-Host "Running V4 frontier falsification suite..." -ForegroundColor Yellow
& ".\.venv\Scripts\worldmodel.exe" frontier --seed 7
if ($LASTEXITCODE -ne 0) { throw "V4 frontier suite failed" }

Write-Host ""
Write-Host "Running cross-domain physics proof..." -ForegroundColor Yellow
& ".\.venv\Scripts\worldmodel.exe" physics --seed 7 | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Physics suite failed" }

Write-Host ""
Write-Host "All checks passed." -ForegroundColor Green
Write-Host "Starting Rook at http://127.0.0.1:8000" -ForegroundColor Green
Start-Process "http://127.0.0.1:8000"
& ".\.venv\Scripts\worldmodel.exe" serve --host 127.0.0.1 --port 8000
