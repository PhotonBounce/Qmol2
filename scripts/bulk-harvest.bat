@echo off
REM Q-Mol Bulk Harvest — Run this overnight to build your inventory
REM This will harvest molecules continuously until you close the window

cd /d "D:\Qmol-3"

echo ============================================
echo  Q-Mol Bulk Harvest
echo  This runs until you close the window
echo  Target: 1,000+ molecules
echo ============================================
echo.

:loop
  echo [%date% %time%] Running harvest batch...
  "D:\qmol\.venv\Scripts\python.exe" scripts\harvest_self.py
  echo [%date% %time%] Batch complete. Waiting 30 seconds...
  timeout /t 30 /nobreak >nul
goto loop
