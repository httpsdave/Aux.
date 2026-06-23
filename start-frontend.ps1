#!/usr/bin/env pwsh
# Start the Aux frontend dev server
# Requires Node.js / npm

$ErrorActionPreference = "Stop"
$FrontendDir = "$PSScriptRoot\frontend"

if (-not (Test-Path "$FrontendDir\node_modules")) {
    Write-Host "node_modules not found, running npm install..." -ForegroundColor Yellow
    Set-Location $FrontendDir
    npm install
}

Write-Host "Starting Aux frontend on http://localhost:3000 ..." -ForegroundColor Cyan
Set-Location $FrontendDir
npm run dev
