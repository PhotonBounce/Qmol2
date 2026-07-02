#Requires -Version 5.1

# setup.ps1 — Master local development setup for ComputeSwarm (Windows)
# Usage: .\scripts\setup.ps1
# ------------------------------------------------------------------------------
# PREREQUISITES:
#   • Docker Desktop (with WSL2 backend recommended)
#   • Python 3.10+ (available in PATH as python or python3)
#   • Node.js 18+ (optional — only for local dashboard dev)
#   • Git for Windows (includes Git Bash, used for init-minio.sh)
# ------------------------------------------------------------------------------

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path -Path (Join-Path $ScriptDir "..")
Push-Location $ProjectRoot

# ------------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------------
function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "===============================================================" -ForegroundColor Cyan
    Write-Host "  $Title" -ForegroundColor Cyan
    Write-Host "===============================================================" -ForegroundColor Cyan
}

function Write-Check {
    param([string]$Message)
    Write-Host "   ✓  $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "   ⚠  $Message" -ForegroundColor Yellow
}

function Write-Info {
    param([string]$Message)
    Write-Host "   ℹ  $Message" -ForegroundColor Gray
}

function Exit-Error {
    param([string]$Message)
    Write-Host ""
    Write-Host "❌  ERROR: $Message" -ForegroundColor Red
    Write-Host ""
    Pop-Location
    exit 1
}

Write-Section "ComputeSwarm — Local Development Setup (Windows)"

# ------------------------------------------------------------------
# 1. Check prerequisites
# ------------------------------------------------------------------
Write-Section "1. Checking Prerequisites"

# Docker
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Exit-Error "Docker is required but not found in PATH.`n   Please install Docker Desktop: https://www.docker.com/products/docker-desktop"
}
Write-Check "Docker found: $(docker --version)"

# Docker Compose v2
$dcVersion = $null
try { $dcVersion = docker compose version 2>$null } catch {}
if ($dcVersion) {
    Write-Check "Docker Compose (v2) found"
    $DockerCompose = "docker compose"
} else {
    Exit-Error "Docker Compose v2 is required.`n   Ensure Docker Desktop is updated to a recent version."
}

# Python
$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) { $pythonCmd = "python" }
elseif (Get-Command python3 -ErrorAction SilentlyContinue) { $pythonCmd = "python3" }
if (-not $pythonCmd) {
    Exit-Error "Python 3.10+ is required but not found in PATH.`n   Please install Python from https://www.python.org/downloads/"
}
$pyVersion = & $pythonCmd --version 2>&1
Write-Check "Python found: $pyVersion"

# Parse Python version
$pyVersionStr = $pyVersion -replace '^Python\s+',''
$pyMajor = [int]($pyVersionStr.Split('.')[0])
$pyMinor = [int]($pyVersionStr.Split('.')[1])
if ($pyMajor -lt 3 -or ($pyMajor -eq 3 -and $pyMinor -lt 10)) {
    Exit-Error "Python 3.10+ is required. Found $pyVersionStr."
}

# Node.js (optional)
if (Get-Command node -ErrorAction SilentlyContinue) {
    $nodeVersion = node --version
    Write-Check "Node.js found: $nodeVersion"
    $nodeMajor = [int]($nodeVersion -replace '^v','').Split('.')[0]
    if ($nodeMajor -lt 18) {
        Write-Warn "Node.js 18+ recommended for dashboard dev. Found $nodeVersion."
    }
} else {
    Write-Warn "Node.js not found (optional — only needed for local dashboard dev)."
}

# Git Bash (needed for init-minio.sh)
$gitBash = $null
$gitBashCandidates = @(
    "C:\Program Files\Git\bin\bash.exe",
    "C:\Program Files (x86)\Git\bin\bash.exe",
    "C:\Git\bin\bash.exe"
)
foreach ($candidate in $gitBashCandidates) {
    if (Test-Path $candidate) { $gitBash = $candidate; break }
}
if (-not $gitBash) {
    # Try to find via where
    $found = (Get-Command bash.exe -ErrorAction SilentlyContinue)
    if ($found) { $gitBash = $found.Source }
}
if (-not $gitBash) {
    Exit-Error "Git Bash not found.`n   Please install Git for Windows: https://git-scm.com/download/win"
}
Write-Check "Git Bash found: $gitBash"

# ------------------------------------------------------------------
# 2. Environment file
# ------------------------------------------------------------------
Write-Section "2. Environment File"

if (-not (Test-Path ".env")) {
    Write-Info "Copying .env.example → .env"
    Copy-Item ".env.example" ".env"
    Write-Check ".env created. Review it and adjust any secrets/URLs if needed."
} else {
    Write-Check ".env already exists. Skipping copy."
}

# ------------------------------------------------------------------
# 3. Start core infrastructure
# ------------------------------------------------------------------
Write-Section "3. Starting Infrastructure (db, redis, minio)"

try {
    Invoke-Expression "$DockerCompose up -d db redis minio"
    Write-Check "Infrastructure containers started."
} catch {
    Exit-Error "Failed to start infrastructure services: $_"
}

# ------------------------------------------------------------------
# 4. Build docker-jobs images
# ------------------------------------------------------------------
Write-Section "4. Building Docker Job Images"

function Build-Image {
    param([string]$Tag, [string]$Context)
    $existing = docker image inspect $Tag 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Check "Image $Tag already exists. Skipping build."
    } else {
        Write-Info "Building $Tag ..."
        docker build -q -t $Tag $Context
        if ($LASTEXITCODE -ne 0) { Exit-Error "Failed to build $Tag." }
        Write-Check "$Tag built."
    }
}

Build-Image "computeswarm/base:latest"          "docker-jobs/base/"
Build-Image "computeswarm/physics-sim:latest"    "docker-jobs/examples/physics-sim/"
Build-Image "computeswarm/blender-render:latest" "docker-jobs/examples/blender-render/"
Build-Image "computeswarm/molecular-dock:latest" "docker-jobs/examples/molecular-dock/"

# ------------------------------------------------------------------
# 5. Initialize MinIO bucket
# ------------------------------------------------------------------
Write-Section "5. Initializing MinIO Object Storage"

# Use the bash script via Git Bash
$env:MSYS_NO_PATHCONV = 1  # prevent Git Bash from converting paths
$initMinio = Join-Path $ScriptDir "init-minio.sh"
Write-Info "Running init-minio.sh via Git Bash ..."
& $gitBash "$initMinio"
if ($LASTEXITCODE -ne 0) {
    Exit-Error "MinIO initialization failed."
}
Write-Check "MinIO initialized."

# ------------------------------------------------------------------
# 6. Backend setup
# ------------------------------------------------------------------
Write-Section "6. Backend Setup"

if (Test-Path "backend") {
    Push-Location backend

    # Create virtual environment if not present
    if (-not (Test-Path "venv")) {
        Write-Info "Creating Python virtual environment (venv) ..."
        & $pythonCmd -m venv venv
        if ($LASTEXITCODE -ne 0) { Exit-Error "Failed to create Python venv." }
        Write-Check "venv created."
    } else {
        Write-Check "venv already exists."
    }

    # Activate venv (PowerShell)
    $venvActivate = Join-Path (Get-Location) "venv\Scripts\Activate.ps1"
    if (-not (Test-Path $venvActivate)) {
        Exit-Error "Could not find venv activation script at $venvActivate"
    }
    . $venvActivate

    Write-Info "Installing Python requirements ..."
    pip install --quiet --upgrade pip 2>$null | Out-Null
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { Exit-Error "Failed to install backend Python requirements." }
    Write-Check "Backend requirements installed."

    # Run migrations
    if (Test-Path "alembic.ini") {
        Write-Info "Running Alembic migrations ..."
        alembic upgrade head
        if ($LASTEXITCODE -ne 0) { Exit-Error "Alembic migration failed." }
        Write-Check "Database migrated to latest revision."
    } else {
        Write-Warn "No alembic.ini found; skipping migrations."
    }

    # Optional: seed admin user
    if (Test-Path "scripts\seed_admin.py") {
        Write-Info "Seeding admin user ..."
        python scripts\seed_admin.py
        if ($LASTEXITCODE -ne 0) { Write-Warn "Admin seed script returned non-zero (continuing)." }
    }

    Pop-Location
} else {
    Write-Warn "No backend/ directory found; skipping backend setup."
}

# ------------------------------------------------------------------
# 7. Dashboard setup
# ------------------------------------------------------------------
Write-Section "7. Dashboard Setup"

if (Test-Path "dashboard") {
    Push-Location dashboard
    if (Test-Path "package.json") {
        if (Test-Path "node_modules") {
            Write-Check "node_modules already exists. Skipping npm install."
        } else {
            Write-Info "Running npm install ..."
            npm install
            if ($LASTEXITCODE -ne 0) { Exit-Error "npm install failed." }
            Write-Check "Dashboard dependencies installed."
        }
    } else {
        Write-Warn "No package.json in dashboard; skipping npm install."
    }
    Pop-Location
} else {
    Write-Warn "No dashboard/ directory found; skipping dashboard setup."
}

# ------------------------------------------------------------------
# 8. Done
# ------------------------------------------------------------------
Write-Section "Setup Complete!"

Write-Host ""
Write-Host "🎉  ComputeSwarm is ready for local development." -ForegroundColor Green
Write-Host ""
Write-Host "───────────────────────────────────────────────────────────────" -ForegroundColor Cyan
Write-Host "  NEXT STEPS — Run each command in a separate PowerShell window" -ForegroundColor Cyan
Write-Host "───────────────────────────────────────────────────────────────" -ForegroundColor Cyan
Write-Host ""
Write-Host "  1. Infrastructure (already started by this script):" -ForegroundColor White
Write-Host "     $DockerCompose up -d db redis minio" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  2. Start the API server:" -ForegroundColor White
Write-Host "     cd backend; .\venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --host 0.0.0.0 --port 8000" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  3. Start the worker client:" -ForegroundColor White
Write-Host "     cd worker; python -m src.main --register" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  4. Start the dashboard dev server:" -ForegroundColor White
Write-Host "     cd dashboard; npm run dev" -ForegroundColor DarkGray
Write-Host ""
Write-Host "     (Or visit http://localhost:8000/docs for the Swagger API UI.)" -ForegroundColor DarkGray
Write-Host ""
Write-Host "───────────────────────────────────────────────────────────────" -ForegroundColor Cyan
Write-Host "  SHORTCUTS" -ForegroundColor Cyan
Write-Host "───────────────────────────────────────────────────────────────" -ForegroundColor Cyan
Write-Host ""
Write-Host "  • Run all services via Docker (production-like):" -ForegroundColor White
Write-Host "    $DockerCompose up -d" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  • Run tests:" -ForegroundColor White
Write-Host "    make test-smoke" -ForegroundColor DarkGray
Write-Host "    make test-e2e" -ForegroundColor DarkGray
Write-Host "    make test-integration" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  • Stop infrastructure:" -ForegroundColor White
Write-Host "    $DockerCompose down" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  For Linux/macOS users, run ./scripts/setup.sh instead." -ForegroundColor DarkGray
Write-Host ""

Pop-Location
