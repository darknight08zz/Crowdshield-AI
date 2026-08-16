# ==============================================================================
# CrowdShield Full Native Windows System Orchestration Startup Script
# ==============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$rootDir = Resolve-Path (Join-Path $scriptDir "..")
Set-Location $rootDir

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " CrowdShield Complete Native Platform Startup (ZERO DOCKER)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# 1. Start Backend in separate process window
Write-Host "[1/4] Launching Backend Server process..." -ForegroundColor Yellow
$backendScript = Join-Path $rootDir "backend\scripts\start_backend.ps1"

$backendProcess = Start-Process powershell -ArgumentList "-NoExit -File `"$backendScript`"" -PassThru
Write-Host "  -> Backend launched with Process ID: $($backendProcess.Id)" -ForegroundColor Green

# 2. Poll Backend Health & Readiness
Write-Host "[2/4] Waiting for Backend /health and /readiness endpoints to become active..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0
$backendReady = $false

while ($attempt -lt $maxAttempts) {
    $attempt++
    try {
        $healthResponse = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($healthResponse -and $healthResponse.status -eq "ok") {
            $readinessResponse = Invoke-RestMethod -Uri "http://localhost:8000/readiness" -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($readinessResponse) {
                Write-Host "  -> Backend online! Health: OK | System Status: $($readinessResponse.status)" -ForegroundColor Green
                $backendReady = $true
                break
            }
        }
    } catch {
        # Waiting for backend to bind port
    }
    Start-Sleep -Seconds 1
    Write-Host "." -NoNewline -ForegroundColor Gray
}

Write-Host ""

if (-not $backendReady) {
    Write-Host "ERROR: Backend failed to respond to health probes within 30 seconds." -ForegroundColor Red
    exit 1
}

# 3. Check / Build Frontend Production Asset
Write-Host "[3/4] Checking Frontend build status..." -ForegroundColor Yellow
$nextDir = Join-Path $rootDir "web\.next"
if (-not (Test-Path $nextDir)) {
    Write-Host "  -> Building Next.js production bundle..." -ForegroundColor Yellow
    Set-Location (Join-Path $rootDir "web")
    npm run build
    Set-Location $rootDir
}

# 4. Start Frontend in separate process window
Write-Host "[4/4] Launching Frontend Server process..." -ForegroundColor Yellow
$frontendScript = Join-Path $rootDir "web\scripts\start_frontend.ps1"
$frontendProcess = Start-Process powershell -ArgumentList "-NoExit -File `"$frontendScript`"" -PassThru
Write-Host "  -> Frontend launched with Process ID: $($frontendProcess.Id)" -ForegroundColor Green

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " CrowdShield Native Platform Successfully Started!" -ForegroundColor Green
Write-Host " Backend URL:  http://localhost:8000" -ForegroundColor Cyan
Write-Host " Frontend URL: http://localhost:3000" -ForegroundColor Cyan
Write-Host " Health API:   http://localhost:8000/health" -ForegroundColor Cyan
Write-Host " Readiness API:http://localhost:8000/readiness" -ForegroundColor Cyan
Write-Host " Realtime WS:  ws://localhost:8000/api/v1/realtime/stream" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
