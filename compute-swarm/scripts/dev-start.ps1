#Requires -Version 5.1

# dev-start.ps1 — Start infrastructure and print dev commands for ComputeSwarm (Windows)
# Usage: .\scripts\dev-start.ps1
# ------------------------------------------------------------------------------

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path -Path (Join-Path $ScriptDir "..")
Push-Location $ProjectRoot

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "===============================================================" -ForegroundColor Cyan
    Write-Host "  $Title" -ForegroundColor Cyan
    Write-Host "===============================================================" -ForegroundColor Cyan
}

Write-Section "ComputeSwarm — Development Mode"

# ------------------------------------------------------------------
# 1. Detect Docker Compose
# ------------------------------------------------------------------
$DockerCompose = $null
$dcVersion = $null
try { $dcVersion = docker compose version 2>$null } catch {}
if ($dcVersion) {
    $DockerCompose = "docker compose"
    Write-Host "  Using Docker Compose (v2): docker compose" -ForegroundColor Gray
} else {
    Exit-Error "Docker Compose is required but not found."
}

# ------------------------------------------------------------------
# 2. Ensure .env exists
# ------------------------------------------------------------------
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Write-Host "  →  Copying .env.example → .env" -ForegroundColor Gray
        Copy-Item ".env.example" ".env"
    } else {
        Write-Host "  ⚠  No .env or .env.example found. Continuing anyway." -ForegroundColor Yellow
    }
}

# ------------------------------------------------------------------
# 3. Start infrastructure
# ------------------------------------------------------------------
Write-Host "  →  Starting infrastructure (db, redis, minio) ..." -ForegroundColor Gray
Invoke-Expression "$DockerCompose up -d db redis minio"
Write-Host "  ✓  Infrastructure containers started." -ForegroundColor Green

Write-Host "  →  Waiting for services to warm up (5s) ..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# ------------------------------------------------------------------
# 4. Initialize MinIO
# ------------------------------------------------------------------
Write-Host "  →  Initializing MinIO ..." -ForegroundColor Gray
$gitBash = $null
$gitBashCandidates = @(
    "C:\Program Files\Git\bin\bash.exe",
    "C:\Program Files (x86)\Git\bin\bash.exe"
)
foreach ($candidate in $gitBashCandidates) {
    if (Test-Path $candidate) { $gitBash = $candidate; break }
}
if (-not $gitBash) {
    $found = (Get-Command bash.exe -ErrorAction SilentlyContinue)
    if ($found) { $gitBash = $found.Source }
}

if ($gitBash) {
    $env:MSYS_NO_PATHCONV = 1
    $initMinio = Join-Path $ScriptDir "init-minio.sh"
    & $gitBash "$initMinio"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ⚠  MinIO init failed (may already be configured)." -ForegroundColor Yellow
    } else {
        Write-Host "  ✓  MinIO initialized." -ForegroundColor Green
    }
} else {
    Write-Host "  ⚠  Git Bash not found — skipping MinIO init." -ForegroundColor Yellow
}

# ------------------------------------------------------------------
# 5. Print dev commands
# ------------------------------------------------------------------
Write-Section "Infrastructure is running!"

Write-Host ""
Write-Host "  ✅  Infrastructure is running." -ForegroundColor Green
Write-Host ""
Write-Host "===============================================================" -ForegroundColor Cyan
Write-Host "  OPEN THESE IN SEPARATE POWERSHELL WINDOWS" -ForegroundColor Cyan
Write-Host "===============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Window 1 — API Server:" -ForegroundColor White
Write-Host "  ─────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "  cd backend; .\venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --host 0.0.0.0 --port 8000" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Window 2 — Worker Client:" -ForegroundColor White
Write-Host "  ─────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "  cd worker; python -m src.main --register" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Window 3 — Dashboard Dev Server:" -ForegroundColor White
Write-Host "  ─────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "  cd dashboard; npm run dev" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Or simply open your browser to:" -ForegroundColor White
Write-Host "    • API Docs:   http://localhost:8000/docs" -ForegroundColor DarkGray
Write-Host "    • Dashboard:  http://localhost:5173  (after npm run dev)" -ForegroundColor DarkGray
Write-Host ""
Write-Host "===============================================================" -ForegroundColor Cyan
Write-Host "  DOCKER SHORTCUT" -ForegroundColor Cyan
Write-Host "===============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  To run everything inside Docker instead:" -ForegroundColor White
Write-Host "    $DockerCompose up -d" -ForegroundColor DarkGray
Write-Host ""

Pop-Location
