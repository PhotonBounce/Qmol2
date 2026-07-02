@echo off
setlocal enabledelayedexpansion

title Q-Mol Setup Wizard

echo.
echo   ============================================
echo    Q-Mol v2.0.0 Setup Wizard
echo   ============================================
echo.

set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
set "VENV_DIR=%PROJECT_DIR%\.venv"
set "PYTHON_CMD=python"

:: === Step 1: Check Python ===
echo   [Step 1/5] Checking Python...
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Python not found.
    echo   Please install Python 3.12 from https://python.org/downloads/
    pause
    exit /b 1
)
echo   [OK] Python found

:: === Step 2: Create Virtual Environment ===
if not exist "%VENV_DIR%" (
    echo   [Step 2/5] Creating virtual environment...
    %PYTHON_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo   [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo   [OK] Virtual environment created
) else (
    echo   [Step 2/5] Virtual environment already exists
)

set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
set "PIP_EXE=%VENV_DIR%\Scripts\pip.exe"

:: === Step 3: Install Dependencies ===
echo   [Step 3/5] Installing dependencies (this takes 5-10 minutes)...
"%PIP_EXE%" install --upgrade pip -q
"%PIP_EXE%" install -q -r "%PROJECT_DIR%\requirements.txt"
if errorlevel 1 (
    echo   [WARNING] Some optional packages may have failed. Core packages should work.
)
echo   [OK] Dependencies installed

:: === Step 4: Create .env ===
if not exist "%PROJECT_DIR%\.env" (
    echo   [Step 4/5] Creating configuration file...
    (
        echo # Q-Mol Configuration
echo USE_POSTGRES=false
echo DATABASE_URL=sqlite:///%PROJECT_DIR%\data\qmol.sqlite
echo QMOL_ADMIN_TOKEN=change-me-in-production
echo API_KEY_PEPPER=
    ) > "%PROJECT_DIR%\.env"
    echo   [OK] Configuration created
) else (
    echo   [Step 4/5] Configuration file already exists
)

:: === Step 5: Initialize Database ===
if not exist "%PROJECT_DIR%\data\qmol.sqlite" (
    echo   [Step 5/5] Initializing database...
    "%PYTHON_EXE%" -c "from src import storage; import config; conn = storage.connect(config.DB_PATH); conn.close(); print('Database initialized')" 2>nul
    if errorlevel 1 (
        echo   [WARNING] Database will be created on first request.
    ) else (
        echo   [OK] Database initialized
    )
) else (
    echo   [Step 5/5] Database already exists
)

:: === Done ===
echo.
echo   ============================================
echo    Setup Complete!
echo   ============================================
echo.
echo   To start the API server:
echo.
echo      start.bat
echo.
echo   Or manually:
echo.
echo      .venv\Scripts\python -m uvicorn api:app --reload
echo.
echo   API will be available at: http://localhost:8000
echo.
echo   For a public HTTPS URL, run:
echo.
echo      deploy\cloudflare-tunnel-setup.bat
echo.
choice /C YN /M "Launch Q-Mol now"
if errorlevel 2 exit /b 0
if errorlevel 1 start "" "%PROJECT_DIR%\start.bat"
