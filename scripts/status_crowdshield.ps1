# ==============================================================================
# CrowdShield Native Platform Status Diagnostic Script
# ==============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " CrowdShield Native Platform Health & Status Check" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# 1. Probe Backend Health
Write-Host "1. Backend Core Service (http://localhost:8000/health):" -NoNewline
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get -TimeoutSec 3
    Write-Host " ONLINE ($($health.status.ToUpper()))" -ForegroundColor Green
    Write-Host "    Version:     $($health.version)" -ForegroundColor Gray
    Write-Host "    Environment: $($health.environment)" -ForegroundColor Gray
} catch {
    Write-Host " OFFLINE / UNREACHABLE" -ForegroundColor Red
}

# 2. Probe System Readiness
Write-Host "`n2. Component Readiness (http://localhost:8000/readiness):" -NoNewline
try {
    $readiness = Invoke-RestMethod -Uri "http://localhost:8000/readiness" -Method Get -TimeoutSec 3
    $statusColor = if ($readiness.status -eq "READY") { [ConsoleColor]::Green } else { [ConsoleColor]::Yellow }
    Write-Host " $($readiness.status)" -ForegroundColor $statusColor
    
    Write-Host "    Database:    $($readiness.database)" -ForegroundColor Gray
    Write-Host "    Persistence: $($readiness.persistence) (Queue depth: $($readiness.details.persistence.queue_depth)/$($readiness.details.persistence.queue_capacity))" -ForegroundColor Gray
    Write-Host "    AI Model:    $($readiness.ai_model) (Version: $($readiness.details.ai_model.model_version), Status: $($readiness.details.ai_model.model_status))" -ForegroundColor Gray
    Write-Host "    Camera / CV: $($readiness.camera) (Degraded: $($readiness.details.camera.is_degraded))" -ForegroundColor Gray
} catch {
    Write-Host " UNREACHABLE" -ForegroundColor Red
}

# 3. Probe Frontend Dashboard
Write-Host "`n3. Next.js Frontend Dashboard (http://localhost:3000):" -NoNewline
try {
    $frontend = Invoke-WebRequest -Uri "http://localhost:3000" -Method Get -TimeoutSec 3
    if ($frontend.StatusCode -eq 200) {
        Write-Host " ONLINE (200 OK)" -ForegroundColor Green
    } else {
        Write-Host " DEGRADED ($($frontend.StatusCode))" -ForegroundColor Yellow
    }
} catch {
    Write-Host " OFFLINE / UNREACHABLE" -ForegroundColor Red
}

Write-Host "`n======================================================================" -ForegroundColor Cyan
