# ==============================================================================
# CrowdShield Frontend Native Windows Startup Script
# ==============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$webDir = Resolve-Path (Join-Path $scriptDir "..")
Set-Location $webDir

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " CrowdShield Native Windows Frontend Startup" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# 1. Validate Node.js & npm
Write-Host "[1/4] Validating Node.js & npm environment..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version 2>&1
    $npmVersion = npm --version 2>&1
    Write-Host "  -> Node.js found: $nodeVersion" -ForegroundColor Green
    Write-Host "  -> npm found: $npmVersion" -ForegroundColor Green
} catch {
    Write-Error "Node.js and npm are required but were not found in PATH."
    exit 1
}

# 2. Validate Environment File
Write-Host "[2/4] Validating frontend environment file..." -ForegroundColor Yellow
$envLocalPath = Join-Path $webDir ".env.local"
if (-not (Test-Path $envLocalPath)) {
    Write-Host "  -> WARNING: .env.local not found. Creating from .env.example..." -ForegroundColor Yellow
    $examplePath = Join-Path $webDir ".env.example"
    if (Test-Path $examplePath) {
        Copy-Item $examplePath $envLocalPath
        Write-Host "  -> Created $envLocalPath from template." -ForegroundColor Green
    }
} else {
    Write-Host "  -> .env.local verified." -ForegroundColor Green
}

# 3. Verify Production Build
Write-Host "[3/4] Checking Next.js production build..." -ForegroundColor Yellow
$nextBuildPath = Join-Path $webDir ".next"
if (-not (Test-Path $nextBuildPath)) {
    Write-Host "  -> Production build (.next) missing. Triggering 'npm run build'..." -ForegroundColor Yellow
    npm run build
} else {
    Write-Host "  -> Production build (.next) verified." -ForegroundColor Green
}

# 4. Start Production Frontend Server
Write-Host "[4/4] Starting Next.js Production Server..." -ForegroundColor Yellow
Write-Host "  -> URL: http://localhost:3000" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

npm start
