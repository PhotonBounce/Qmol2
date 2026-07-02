@echo off
REM Q-Mol Continuous QA Runner
REM Run this to continuously test and audit the Q-Mol app
REM Usage: qa.bat [cycles]  (default: 5)

cd /d "D:\Qmol-3"

if "%~1"=="" (
    set CYCLES=5
) else (
    set CYCLES=%~1
)

echo ============================================
echo  Q-Mol Continuous QA Runner
echo  Cycles: %CYCLES%
echo  Start: %date% %time%
echo ============================================

"D:\qmol\.venv\Scripts\python.exe" scripts\qa_runner.py --loops %CYCLES% --delay 5

echo.
echo ============================================
echo  QA Complete
echo  Report: D:\Qmol-3\data\qa_report.md
echo  End: %date% %time%
echo ============================================
pause
