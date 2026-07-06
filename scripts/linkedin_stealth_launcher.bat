@echo off
chcp 65001 >nul
echo =========================================
echo Q-MOL LINKEDIN STEALTH BOT LAUNCHER
echo =========================================
echo.
echo WARNING: This automates LinkedIn actions.
echo Your account CAN still be banned.
echo Start conservative and monitor closely.
echo.

set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..

:menu
cls
echo =========================================
echo SELECT MODE
echo =========================================
echo 1. STATUS — Check today's action counts
echo 2. CONNECTIONS — Send connection requests (max 8/day)
echo 3. MESSAGES — Send messages to connected prospects (max 5/day)
echo 4. EMERGENCY STOP — Create STOP file, halt all automation
echo 5. RESUME — Remove STOP file, allow automation again
echo 6. EXIT
echo.
set /p choice="Enter choice (1-6): "

if "%choice%"=="1" goto status
if "%choice%"=="2" goto connections
if "%choice%"=="3" goto messages
if "%choice%"=="4" goto stop
if "%choice%"=="5" goto resume
if "%choice%"=="6" goto end

cls
echo Invalid choice. Press any key to continue...
pause >nul
goto menu

:status
cd /d "%PROJECT_DIR%"
python scripts\linkedin_stealth_bot.py --mode status
echo.
echo Press any key to return to menu...
pause >nul
goto menu

:connections
echo.
echo This will send connection requests to prospects.
echo Max 8 per day. Random delays 90-240s between actions.
echo.
echo IMPORTANT:
echo - LinkedIn must be open in Chrome
echo - You must be logged in as Dmitriy Buchman
echo - WebBridge daemon must be running
echo.
echo Press Ctrl+C to cancel at any time.
echo.
pause
cd /d "%PROJECT_DIR%"
python scripts\linkedin_stealth_bot.py --mode connections
echo.
echo Session complete. Press any key to return to menu...
pause >nul
goto menu

:messages
echo.
echo This will send messages to connected prospects.
echo Max 5 per day. Only sends to people who accepted your connection.
echo.
echo IMPORTANT:
echo - LinkedIn must be open in Chrome
echo - You must be logged in as Dmitriy Buchman
echo - WebBridge daemon must be running
echo.
echo Press Ctrl+C to cancel at any time.
echo.
pause
cd /d "%PROJECT_DIR%"
python scripts\linkedin_stealth_bot.py --mode messages
echo.
echo Session complete. Press any key to return to menu...
pause >nul
goto menu

:stop
cd /d "%PROJECT_DIR%"
python scripts\linkedin_stealth_bot.py --stop
echo.
echo EMERGENCY STOP activated. All automation will halt.
echo Press any key to return to menu...
pause >nul
goto menu

:resume
if exist "%PROJECT_DIR%\scripts\STOP.txt" (
    del "%PROJECT_DIR%\scripts\STOP.txt"
    echo STOP file removed. Automation can resume.
) else (
    echo No STOP file found. Automation is already active.
)
echo.
echo Press any key to return to menu...
pause >nul
goto menu

:end
echo Goodbye.
