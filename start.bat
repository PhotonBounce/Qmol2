@echo off
setlocal enabledelayedexpansion

title Q-Mol v2.0.0 - Molecular Informatics Platform

echo.
echo   ============================================
echo    Q-Mol v2.0.0 - Molecular Informatics
echo   ============================================
echo.

:: Set paths
set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
set "VENV_DIR=D:\qmol\.venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
set "PIP_EXE=%VENV_DIR%\Scripts\pip.exe"
set "DATA_DIR=%PROJECT_DIR%\data"
set "LOGS_DIR=%PROJECT_DIR%\logs"
set "JOBS_DIR=%PROJECT_DIR%\jobs"

:: Check if venv exists
if not exist "%PYTHON_EXE%" (
    echo   [ERROR] Virtual environment not found at %VENV_DIR%
    echo.
    echo   Expected Python at: %PYTHON_EXE%
    echo.
    echo   To fix this:
    echo   1. Open a command prompt
    echo   2. cd /d %PROJECT_DIR%
    echo   3. python -m venv .venv
    echo   4. .venv\Scripts\pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo   [OK] Python found: %PYTHON_EXE%

:: Create necessary directories
if not exist "%DATA_DIR%" mkdir "%DATA_DIR%"
if not exist "%LOGS_DIR%" mkdir "%LOGS_DIR%"
if not exist "%JOBS_DIR%" mkdir "%JOBS_DIR%"

:: Create .env if not exists
if not exist "%PROJECT_DIR%\.env" (
    echo   [INFO] Creating default .env file...
    (
        echo # Q-Mol Configuration
        echo USE_POSTGRES=false
        echo DATABASE_URL=sqlite:///%PROJECT_DIR%\data\qmol.sqlite
        echo QMOL_ADMIN_TOKEN=change-me-in-production
        echo API_KEY_PEPPER=
        echo STRIPE_SECRET_KEY=
        echo STRIPE_WEBHOOK_SECRET=
        echo STRIPE_PRICE_ID=
    ) > "%PROJECT_DIR%\.env"
)

:: Initialize database if not exists
if not exist "%DATA_DIR%\qmol.sqlite" (
    echo   [INFO] Initializing database...
    "%PYTHON_EXE%" -c "from src import storage; import config; conn = storage.connect(config.DB_PATH); conn.close(); print('Database initialized')" 2>nul
    if errorlevel 1 (
        echo   [WARNING] Could not initialize database. Will retry on first request.
    ) else (
        echo   [OK] Database initialized
    )
)

:: Syntax check
echo   [INFO] Checking syntax...
"%PYTHON_EXE%" -m py_compile "%PROJECT_DIR%\api.py" 2>nul
if errorlevel 1 (
    echo   [WARNING] Syntax issues detected in api.py
) else (
    echo   [OK] api.py syntax check passed
)

:: Quick import test
echo   [INFO] Testing imports...
"%PYTHON_EXE%" -c "import api; print('All imports OK')" 2>nul
if errorlevel 1 (
    echo   [WARNING] Import test had issues (may still work)
) else (
    echo   [OK] Import test passed
)

:: Start the server
echo.
echo   ============================================
echo    Starting Q-Mol API Server...
echo   ============================================
echo.
echo   API URL:    http://localhost:8000/v1
echo   Docs:       http://localhost:8000/v1/docs
echo   Health:     http://localhost:8000/v1/health
echo.
echo   Press Ctrl+C to stop the server.
echo.

:: Open browser in background
start /b cmd /c "timeout /t 3 >nul && start http://localhost:8000/v1/docs"

:: Start uvicorn
cd /d "%PROJECT_DIR%"
"%PYTHON_EXE%" -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload --reload-dir src

echo.
echo   Server stopped.
pause
