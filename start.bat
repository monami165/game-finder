@echo off
title Aristocrat Game Finder

:: ── Setup (only runs on first launch) ────────────────────────────────────────
if not exist ".venv\Scripts\activate.bat" (
    echo Setting up for the first time. This may take a moment...
    echo.

    python --version >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Python is not installed or not on your PATH.
        echo Download it from https://www.python.org/downloads/
        pause
        exit /b 1
    )

    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )

    call .venv\Scripts\activate.bat
    pip install -r requirements.txt --quiet
    echo.
    echo Setup complete!
) else (
    call .venv\Scripts\activate.bat
)

:: ── Main menu loop ────────────────────────────────────────────────────────────
:menu
cls
echo.
echo  ===========================================
echo   Aristocrat Gaming - Game Finder
echo  ===========================================
echo.
echo   1. Create location list for a game
echo   2. Check watchlist (games_list.json)
echo   3. Compare two snapshots
echo   4. Exit
echo.
echo  ===========================================
echo.
set /p choice= Select an option (1, 2, 3, or 4):

if "%choice%"=="1" goto create_list
if "%choice%"=="2" goto watchlist
if "%choice%"=="3" goto compare
if "%choice%"=="4" goto end
echo   Invalid option. Please enter 1, 2, 3, or 4.
timeout /t 2 >nul
goto menu


:: ── Option 1: Create list ─────────────────────────────────────────────────────
:create_list
cls
echo.
echo  ===========================================
echo   Create Location List
echo  ===========================================
echo.
set /p game= Enter game name or ID:
if "%game%"=="" (
    echo   No input provided.
    timeout /t 2 >nul
    goto create_list
)
echo.
python scraper.py "%game%"
echo.
pause
goto menu


:: ── Option 2: Check watchlist ─────────────────────────────────────────────────
:watchlist
cls
echo.
echo  ===========================================
echo   Watchlist Check
echo  ===========================================
echo.
echo   Checking every game in games_list.json...
echo   A snapshot will be saved for each game, and any changes
echo   since the last check will be written to compare\
echo.
python scraper.py --watchlist
echo.
echo   Tip: edit games_list.json in a text editor to add or remove games.
echo.
pause
goto menu


:: ── Option 3: Compare snapshots ───────────────────────────────────────────────
:compare
cls
echo.
echo  ===========================================
echo   Compare Snapshots
echo  ===========================================
echo.

if not exist "data\" (
    echo   No snapshots found. Run option 1 or 2 first to generate one.
    echo.
    pause
    goto menu
)

echo   Available snapshots:
echo.
for %%f in (data\*.json) do echo     %%f
echo.
set /p file_a= Enter OLDER snapshot (e.g. data\GG382_2026-05-31_10-00-00.json):
if "%file_a%"=="" (
    echo   No file entered.
    timeout /t 2 >nul
    goto compare
)
if not exist "%file_a%" (
    echo   File not found: %file_a%
    timeout /t 2 >nul
    goto compare
)

echo.
set /p file_b= Enter NEWER snapshot (e.g. data\GG382_2026-06-07_10-00-00.json):
if "%file_b%"=="" (
    echo   No file entered.
    timeout /t 2 >nul
    goto compare
)
if not exist "%file_b%" (
    echo   File not found: %file_b%
    timeout /t 2 >nul
    goto compare
)

echo.
python compare.py "%file_a%" "%file_b%"
echo.
echo   Result saved to the compare\ folder.
echo.
pause
goto menu


:: ── Exit ──────────────────────────────────────────────────────────────────────
:end
echo.
echo  Goodbye!
timeout /t 2 >nul
exit