@echo off
REM Q-Mol LinkedIn Automation — Quick Start Menu
REM Run this batch file to access all automation workflows safely

echo ========================================
echo   Q-MOL LINKEDIN AUTOMATION MENU
echo ========================================
echo.
echo 1. Check Safety Status
echo 2. Search for Prospects (Read-Only, Safe)
echo 3. Send Connection Requests (Interactive)
echo 4. Send Messages (Interactive)
echo 5. Create LinkedIn Post
echo 6. View Outreach Status
echo 7. Emergency STOP
echo 8. Resume from STOP
echo 9. Open Runbook Index
echo 0. Exit
echo.
set /p choice="Enter choice (0-9): "

if "%choice%"=="1" goto status
if "%choice%"=="2" goto search
if "%choice%"=="3" goto connect
if "%choice%"=="4" goto message
if "%choice%"=="5" goto post
if "%choice%"=="6" goto viewstatus
if "%choice%"=="7" goto stop
if "%choice%"=="8" goto resume
if "%choice%"=="9" goto openrunbook
if "%choice%"=="0" goto exit

:status
cls
cd /d D:\Qmol-3\scripts
python safety_guard.py --status
pause
goto menu

:search
cls
cd /d D:\Qmol-3\scripts
set /p query="Enter search query (e.g., 'cheminformatics scientist'): "
set /p pages="Number of pages to scan (1-3): "
python webbridge_linkedin_automation.py --workflow search_prospects --query "%query%" --pages %pages%
pause
goto menu

:connect
cls
cd /d D:\Qmol-3\scripts
python linkedin_outreach.py --action generate_messages
echo.
echo Starting interactive connection sender...
echo You will be prompted before EACH request.
python webbridge_linkedin_automation.py --workflow send_connections --limit 5 --interactive
pause
goto menu

:message
cls
cd /d D:\Qmol-3\scripts
python linkedin_outreach.py --action execute_daily --limit 5
echo.
echo Starting interactive message sender...
echo You will be prompted before EACH message.
python webbridge_linkedin_automation.py --workflow send_messages --limit 5 --interactive
pause
goto menu

:post
cls
cd /d D:\Qmol-3\scripts
python webbridge_linkedin_automation.py --workflow create_post
echo.
echo ^>^>^> MANUAL STEP: Review the post in Chrome and click 'Post' to publish.
pause
goto menu

:viewstatus
cls
cd /d D:\Qmol-3\scripts
python linkedin_outreach.py --action status
pause
goto menu

:stop
cls
cd /d D:\Qmol-3\scripts
python safety_guard.py --stop
echo.
echo ALL AUTOMATION HALTED. Remove STOP.txt to resume.
pause
goto menu

:resume
cls
cd /d D:\Qmol-3\scripts
python safety_guard.py --resume
pause
goto menu

:openrunbook
cls
start "" "D:\Qmol-3\scripts\runbooks\INDEX.md"
goto menu

:exit
cls
echo Goodbye.
exit /b 0

:menu
call D:\Qmol-3\scripts\qmol-linkedin-menu.bat
