#!/usr/bin/env pwsh
# Start the Aux backend API server
# Uses the .venv managed by uv (Python 3.11)

$ErrorActionPreference = "Stop"
$BackendDir = "$PSScriptRoot\backend"
$VenvPython = "$BackendDir\.venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Error "Virtual environment not found at $BackendDir\.venv"
    Write-Host "Run 'C:\Users\daved\.local\bin\uv.exe pip install -r backend\requirements.txt --python backend\.venv\Scripts\python.exe' to set it up."
    exit 1
}

Write-Host "Starting Aux backend on http://localhost:8000 ..." -ForegroundColor Cyan
Set-Location $BackendDir
& $VenvPython -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
