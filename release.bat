@echo off
setlocal enabledelayedexpansion

title Q-Mol Release Builder

echo.
echo   ============================================
echo    Q-Mol Release Builder
echo    Packages everything into a distributable ZIP
echo   ============================================
echo.

set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
set "RELEASE_NAME=qmol-v2.0.0-windows"
set "RELEASE_DIR=%PROJECT_DIR%\release"
set "RELEASE_ZIP=%PROJECT_DIR%\%RELEASE_NAME%.zip"

:: Create release directory
if exist "%RELEASE_DIR%" rmdir /s /q "%RELEASE_DIR%"
mkdir "%RELEASE_DIR%"
mkdir "%RELEASE_DIR%\data"
mkdir "%RELEASE_DIR%\logs"
mkdir "%RELEASE_DIR%\jobs"

:: Copy core files
echo   [1/6] Copying core files...
copy "%PROJECT_DIR%\api.py" "%RELEASE_DIR%\"
copy "%PROJECT_DIR%\config.py" "%RELEASE_DIR%\"
copy "%PROJECT_DIR%\requirements.txt" "%RELEASE_DIR%\"
copy "%PROJECT_DIR%\requirements-lite.txt" "%RELEASE_DIR%\"
copy "%PROJECT_DIR%\requirements-postgres.txt" "%RELEASE_DIR%\"
copy "%PROJECT_DIR%\requirements-full.txt" "%RELEASE_DIR%\"

:: Copy start scripts
copy "%PROJECT_DIR%\start.bat" "%RELEASE_DIR%\"
copy "%PROJECT_DIR%\setup.bat" "%RELEASE_DIR%\"
copy "%PROJECT_DIR%\build-apk.bat" "%RELEASE_DIR%\"

:: Copy source
echo   [2/6] Copying source code...
xcopy /s /e /q /i "%PROJECT_DIR%\src" "%RELEASE_DIR%\src\"

:: Copy tests
xcopy /s /e /q /i "%PROJECT_DIR%\tests" "%RELEASE_DIR%\tests\"

:: Copy docs
echo   [3/6] Copying documentation...
xcopy /s /e /q /i "%PROJECT_DIR%\docs" "%RELEASE_DIR%\docs\"

:: Copy deploy scripts
echo   [4/6] Copying deployment scripts...
xcopy /s /e /q /i "%PROJECT_DIR%\deploy" "%RELEASE_DIR%\deploy\"

:: Copy landing page
echo   [5/6] Copying web assets...
if exist "%PROJECT_DIR%\landing" (
    xcopy /s /e /q /i "%PROJECT_DIR%\landing" "%RELEASE_DIR%\landing\"
)
if exist "%PROJECT_DIR%\demo_output.png" (
    copy "%PROJECT_DIR%\demo_output.png" "%RELEASE_DIR%\"
)

:: Copy APK if available
if exist "%PROJECT_DIR%\deploy\qmol.apk" (
    copy "%PROJECT_DIR%\deploy\qmol.apk" "%RELEASE_DIR%\"
)

:: Create release README
echo   [6/6] Creating release README...
(
    echo # Q-Mol v2.0.0 — Windows Release
echo.
echo ## Quick Start
echo.
echo 1. Double-click `setup.bat` to install Python dependencies
echo 2. Double-click `start.bat` to start the API server
echo 3. Open http://localhost:8000 in your browser
echo.
echo ## Files
echo.
echo - `setup.bat` — First-time setup (installs Python deps)
echo - `start.bat` — Start the API server
echo - `build-apk.bat` — Build Android APK (requires Flutter SDK)
echo - `deploy/` — Hosting scripts (Cloudflare, Oracle Cloud, etc.)
echo - `docs/` — Documentation (hosting guide, GitHub setup)
echo - `qmol.apk` — Android app (if included in this release)
echo.
echo ## Free Hosting Options
echo.
echo See `docs\FREE_HOSTING.md` for 6 free hosting options ranked by cost and performance.
echo.
echo ## Crypto Payments
echo.
echo Wallet: 0x75B30d0dE751D9628510f3cb273F09f7137f9E3F
echo See `deploy\pay.html` for payment options.
echo.
echo ## License
echo.
echo Open source. See GitHub for full license.
echo.
) > "%RELEASE_DIR%\README-RELEASE.txt"

:: Create ZIP
echo   Creating ZIP archive...
if exist "%RELEASE_ZIP%" del "%RELEASE_ZIP%"

powershell -Command "Compress-Archive -Path '%RELEASE_DIR%\*' -DestinationPath '%RELEASE_ZIP%' -Force"

if exist "%RELEASE_ZIP%" (
    for %%F in ("%RELEASE_ZIP%") do set "SIZE=%%~zF"
    echo.
    echo   ============================================
    echo    Release Built Successfully!
    echo   ============================================
    echo.
    echo   File: %RELEASE_ZIP%
    echo   Size: %SIZE% bytes
    echo.
    echo   Upload this file to your hosting or share directly.
) else (
    echo   [ERROR] Failed to create ZIP archive.
)

:: Cleanup
rmdir /s /q "%RELEASE_DIR%"

echo.
pause
