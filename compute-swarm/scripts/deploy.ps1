#!/usr/bin/env pwsh
#Requires -Version 5.1

# ============================================================================
# ComputeSwarm — Production Deployment Script (Windows Server)
# ============================================================================
# Usage: .\scripts\deploy.ps1
#
# Prerequisites on the Windows Server:
#   • Docker Desktop or Docker Engine
#   • Docker Compose plugin (v2+)
#   • PowerShell 5.1+ or PowerShell 7+
# ============================================================================

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
Set-Location -Path $ProjectDir

Write-Host "=== ComputeSwarm Production Deployment ===" -ForegroundColor Cyan

# --- Prerequisites check ----------------------------------------------------
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker is not installed."
}
if (-not (docker compose version 2>$null)) {
    Write-Error "Docker Compose plugin is not installed."
}

# --- Environment setup ------------------------------------------------------
if (-not (Test-Path .env)) {
    if (Test-Path .env.prod) {
        Write-Host "Copying .env.prod -> .env"
        Copy-Item .env.prod .env
    } else {
        Write-Error "Neither .env nor .env.prod found. Create .env from .env.prod.example first."
    }
}

# --- Build / Pull images ----------------------------------------------------
Write-Host "Building / pulling images..."
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml build

# --- Start infrastructure ---------------------------------------------------
Write-Host "Starting infrastructure services (db, redis, minio)..."
docker compose -f docker-compose.prod.yml up -d db redis minio

Write-Host "Waiting for database to be ready..."
Start-Sleep -Seconds 5

# --- Database migrations ----------------------------------------------------
Write-Host "Running Alembic migrations..."
docker compose -f docker-compose.prod.yml run --rm api `
    python -m alembic upgrade head

# --- Start application ------------------------------------------------------
Write-Host "Starting application services (api, dashboard, worker, traefik)..."
docker compose -f docker-compose.prod.yml up -d api dashboard worker traefik

# --- Summary ----------------------------------------------------------------
Write-Host ""
Write-Host "=== Deployment Complete ===" -ForegroundColor Green
Write-Host "Health:  https://`$env:API_DOMAIN/health"
Write-Host "Metrics: https://`$env:API_DOMAIN/metrics"
Write-Host "Dashboard: https://`$env:APP_DOMAIN"
