# ==============================================================================
# CrowdShield Backend Native Windows Startup Script
# ==============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$backendDir = Resolve-Path (Join-Path $scriptDir "..")
Set-Location $backendDir

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " CrowdShield Native Windows Backend Startup" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# 1. Validate Python
Write-Host "[1/5] Validating Python environment..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  -> Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Error "Python 3 is required but was not found in PATH."
    exit 1
}

# 2. Validate Environment Configuration
Write-Host "[2/5] Validating environment configuration..." -ForegroundColor Yellow
$envPath = Join-Path $backendDir ".env"
$rootEnvPath = Join-Path (Resolve-Path (Join-Path $backendDir "..")) ".env"

if (-not (Test-Path $envPath) -and -not (Test-Path $rootEnvPath)) {
    Write-Host "  -> WARNING: .env file not found. Creating from .env.example..." -ForegroundColor Yellow
    $examplePath = Join-Path $backendDir ".env.example"
    if (Test-Path $examplePath) {
        Copy-Item $examplePath $envPath
        Write-Host "  -> Created $envPath from template." -ForegroundColor Green
    }
} else {
    Write-Host "  -> Environment configuration file verified." -ForegroundColor Green
}

# 3. Validate AI Model Artifacts
Write-Host "[3/5] Validating AI model weights..." -ForegroundColor Yellow
$yoloModelPath = Join-Path $backendDir "yolov8n.pt"
$rootYoloPath = Join-Path (Resolve-Path (Join-Path $backendDir "..")) "yolov8n.pt"

if (Test-Path $yoloModelPath) {
    Write-Host "  -> YOLOv8 model weights verified at $yoloModelPath" -ForegroundColor Green
} elseif (Test-Path $rootYoloPath) {
    Write-Host "  -> YOLOv8 model weights verified at root ($rootYoloPath)" -ForegroundColor Green
} else {
    Write-Host "  -> WARNING: yolov8n.pt not found locally. It will be downloaded automatically on initial inference." -ForegroundColor Yellow
}

# 4. Set Python Path
$env:PYTHONPATH = "$backendDir"

# 5. Start Uvicorn Server
Write-Host "[4/5] Starting FastAPI/Uvicorn Backend Server..." -ForegroundColor Yellow
Write-Host "  -> Host: 0.0.0.0" -ForegroundColor Cyan
Write-Host "  -> Port: 8000" -ForegroundColor Cyan
Write-Host "  -> Health Endpoint: http://localhost:8000/health" -ForegroundColor Cyan
Write-Host "  -> Readiness Endpoint: http://localhost:8000/readiness" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
