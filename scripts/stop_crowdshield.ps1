# ==============================================================================
# CrowdShield Graceful Native Windows Shutdown Script
# ==============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " CrowdShield Native Platform Shutdown" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# Find processes running CrowdShield backend or frontend
Write-Host "Locating active CrowdShield processes..." -ForegroundColor Yellow

$stoppedAny = $false

# 1. Stop Uvicorn Backend Processes
try {
    $backendProcesses = Get-CimInstance Win32_Process | Where-Object { 
        $_.CommandLine -like "*app.main:app*" -or 
        $_.CommandLine -like "*start_backend.ps1*" 
    }
    foreach ($proc in $backendProcesses) {
        Write-Host "Stopping Backend Process ID: $($proc.ProcessId)..." -ForegroundColor Yellow
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
        $stoppedAny = $true
    }
} catch {
    Write-Host "No active backend processes found." -ForegroundColor Gray
}

# 2. Stop Next.js Frontend Processes
try {
    $frontendProcesses = Get-CimInstance Win32_Process | Where-Object { 
        ($_.CommandLine -like "*next start*" -or $_.CommandLine -like "*start_frontend.ps1*") -and
        $_.CommandLine -notlike "*stop_crowdshield.ps1*"
    }
    foreach ($proc in $frontendProcesses) {
        Write-Host "Stopping Frontend Process ID: $($proc.ProcessId)..." -ForegroundColor Yellow
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
        $stoppedAny = $true
    }
} catch {
    Write-Host "No active frontend processes found." -ForegroundColor Gray
}

if ($stoppedAny) {
    Write-Host "CrowdShield processes successfully stopped." -ForegroundColor Green
} else {
    Write-Host "No running CrowdShield processes were detected." -ForegroundColor Yellow
}
Write-Host "======================================================================" -ForegroundColor Cyan
