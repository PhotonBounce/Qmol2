@echo off
REM Q-Mol LinkedIn Prospect Extractor Launcher
REM ===========================================
REM Safe, rate-limited LinkedIn prospect extraction for Q-Mol
REM
REM Usage:
REM   run_extractor.bat status          - Show daily safety status
REM   run_extractor.bat search-all      - Run all predefined searches
REM   run_extractor.bat search "kw"     - Search with custom keywords
REM   run_extractor.bat score           - Score existing prospects
REM   run_extractor.bat enrich          - Enrich top prospects
REM   run_extractor.bat quick           - Run quick test searches

cd /d D:\Qmol-3\scripts

set PYTHON=C:\Users\fucktrumpandrednecks\AppData\Local\Programs\Python\Python312\python.exe

if "%1"=="" goto :status
if "%1"=="status" goto :status
if "%1"=="search-all" goto :search_all
if "%1"=="search" goto :search
if "%1"=="score" goto :score
if "%1"=="enrich" goto :enrich
if "%1"=="quick" goto :quick
if "%1"=="guidelines" goto :guidelines
if "%1"=="help" goto :help

echo Unknown command: %1
goto :help

:status
%PYTHON% linkedin_prospect_extractor.py --status
goto :end

:search_all
%PYTHON% linkedin_prospect_extractor.py --search-all
goto :end

:search
if "%2"=="" (
    echo Error: search keywords required
    echo Usage: run_extractor.bat search "computational chemistry"
    goto :end
)
%PYTHON% linkedin_prospect_extractor.py --search "%2" --pages 3
goto :end

:score
if "%2"=="" (
    echo Scoring latest prospects file...
    for %%f in (D:\Qmol-3\data\linkedin\prospects_raw_*.csv) do set LATEST=%%f
    if not defined LATEST (
        echo No prospect files found in D:\Qmol-3\data\linkedin\
        goto :end
    )
    %PYTHON% linkedin_prospect_extractor.py --score-prospects --input "!LATEST!"
) else (
    %PYTHON% linkedin_prospect_extractor.py --score-prospects --input "%2"
)
goto :end

:enrich
if "%2"=="" (
    for %%f in (D:\Qmol-3\data\linkedin\*_scored.csv) do set LATEST=%%f
    if not defined LATEST (
        echo No scored files found
        goto :end
    )
    %PYTHON% linkedin_prospect_extractor.py --enrich-profiles --input "!LATEST!" --limit 5
) else (
    %PYTHON% linkedin_prospect_extractor.py --enrich-profiles --input "%2" --limit 5
)
goto :end

:quick
%PYTHON% linkedin_prospect_extractor.py --search "cheminformatics drug discovery" --pages 2
%PYTHON% linkedin_prospect_extractor.py --search "computational chemistry virtual screening" --pages 2
%PYTHON% linkedin_prospect_extractor.py --search "AI drug discovery machine learning" --pages 2
goto :end

:guidelines
%PYTHON% anti_detection.py --guidelines
goto :end

:help
echo.
echo Q-Mol LinkedIn Prospect Extractor
echo =================================
echo.
echo Commands:
echo   status              Show daily safety limits and usage
echo   search-all          Run all predefined search batches
echo   search "keywords"   Search with custom keywords
echo   score [file]        Score prospects by relevance
echo   enrich [file]       Enrich top prospects (visits profiles!)
echo   quick               Run quick test searches (3 queries)
echo   guidelines          Print safety guidelines
echo   help                Show this help
echo.
echo Examples:
echo   run_extractor.bat status
echo   run_extractor.bat search "CADD molecular docking"
echo   run_extractor.bat score
echo   run_extractor.bat enrich D:\Qmol-3\data\linkedin\prospects_scored.csv
echo.

:end
