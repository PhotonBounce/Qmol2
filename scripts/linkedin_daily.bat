@echo off
REM Q-Mol LinkedIn Daily Automation Batch File
REM Runs the safe daily routine at conservative limits
REM 
REM Usage: Double-click or run from command line

cd /d "D:\Qmol-3"
echo ========================================
echo Q-Mol LinkedIn Daily Automation
echo Started: %date% %time%
echo ========================================
echo.

REM Check if dry-run flag passed
if "%1"=="--dry-run" (
    echo [DRY RUN MODE - No actual messages sent]
    python scripts\linkedin_safe_automation.py --mode daily --dry-run
) else (
    python scripts\linkedin_safe_automation.py --mode daily
)

echo.
echo ========================================
echo Finished: %date% %time%
echo ========================================
pause
