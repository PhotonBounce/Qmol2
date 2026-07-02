@echo off
setlocal enabledelayedexpansion

title Q-Mol Cloudflare Tunnel Setup

echo.
echo   ============================================
echo    Q-Mol Cloudflare Tunnel Setup
echo    Free HTTPS for your local PC
echo   ============================================
echo.

set "CF_DIR=%USERPROFILE%\.cloudflared"
set "CF_BIN=%CF_DIR%\cloudflared.exe"

:: Check if cloudflared exists
if not exist "%CF_BIN%" (
    echo   [INFO] cloudflared not found. Downloading...
    echo.
    
    if not exist "%CF_DIR%" mkdir "%CF_DIR%"
    
    :: Download latest cloudflared for Windows
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile '%CF_BIN%'" 2>nul
    
    if not exist "%CF_BIN%" (
        echo   [ERROR] Failed to download cloudflared.
        echo   Please download manually from:
        echo   https://github.com/cloudflare/cloudflared/releases
        pause
        exit /b 1
    )
    
    echo   [OK] cloudflared downloaded
) else (
    echo   [OK] cloudflared found
)

:: Check if already authenticated
if not exist "%CF_DIR%\cert.pem" (
    echo.
    echo   [INFO] Authenticating with Cloudflare...
    echo   A browser window will open. Log in to your Cloudflare account.
    echo.
    "%CF_BIN%" tunnel login
    if errorlevel 1 (
        echo   [ERROR] Authentication failed.
        pause
        exit /b 1
    )
)

:: Create tunnel if not exists
if not exist "%CF_DIR%\qmol.json" (
    echo.
    echo   [INFO] Creating tunnel 'qmol'...
    for /f "tokens=*" %%a in ('"%CF_BIN%" tunnel create qmol 2^>^&1') do set "TUNNEL_OUT=%%a"
    echo   %TUNNEL_OUT%
    
    :: Extract tunnel ID from the output
    for /f "tokens=2 delims==" %%a in ('"%CF_BIN%" tunnel list ^| findstr qmol') do set "TUNNEL_ID=%%a"
    set "TUNNEL_ID=!TUNNEL_ID: =!"
    echo   [OK] Tunnel ID: !TUNNEL_ID!
    
    :: Create config file
    (
        echo tunnel: !TUNNEL_ID!
        echo credentials-file: %CF_DIR%\!TUNNEL_ID!.json
        echo ingress:
        echo   - hostname: qmol.photon-bounce.com
        echo     service: http://localhost:8000
        echo   - service: http_status:404
    ) > "%CF_DIR%\config.yml"
    
    echo   [OK] Config created at %CF_DIR%\config.yml
    
    :: Route DNS
    echo.
    echo   [INFO] Routing DNS qmol.photon-bounce.com...
    "%CF_BIN%" tunnel route dns qmol qmol.photon-bounce.com 2>nul
) else (
    echo   [OK] Tunnel 'qmol' already exists
)

echo.
echo   ============================================
echo    Setup Complete!
echo   ============================================
echo.
echo   To start the tunnel:
echo.
echo      start "CF Tunnel" "%CF_BIN%" tunnel run qmol
echo.
echo   To start Q-Mol API:
echo.
echo      cd D:\Qmol-3
echo      .venv\Scripts\python -m uvicorn api:app --host 0.0.0.0 --port 8000
echo.
echo   Your API will be accessible at:
echo      https://qmol.photon-bounce.com
echo.
echo   [IMPORTANT] Keep both windows open!
echo.
pause
