@echo off
setlocal EnableDelayedExpansion
title BMI Calculator Pro

:: ─────────────────────────────────────────────
::  BMI Calculator Pro — Launcher
::  Place this file in the same folder as:
::    _bmicalculator.py, bmi_logic.py, database.py
:: ─────────────────────────────────────────────

echo.
echo  =============================================
echo   BMI Calculator Pro — Launcher
echo  =============================================
echo.

:: ── 1. Locate Python ──────────────────────────
set PYTHON=
for %%P in (python python3) do (
    if "!PYTHON!"=="" (
        where %%P >nul 2>&1 && set PYTHON=%%P
    )
)

if "!PYTHON!"=="" (
    echo  [ERROR] Python not found on PATH.
    echo  Please install Python 3.10+ from https://python.org
    echo  and make sure "Add Python to PATH" is checked.
    echo.
    pause
    exit /b 1
)

:: ── 2. Check Python version (need 3.10+) ──────
for /f "tokens=2 delims= " %%V in ('!PYTHON! --version 2^>^&1') do set PYVER=%%V
echo  Python found: !PYTHON! (!PYVER!)

:: ── 3. Verify the main script exists ──────────
set SCRIPT=%~dp0_bmicalculator.py
if not exist "!SCRIPT!" (
    echo.
    echo  [ERROR] _bmicalculator.py not found next to this launcher.
    echo  Expected location: !SCRIPT!
    echo.
    pause
    exit /b 1
)

:: ── 4. Create data folder if needed ───────────
if not exist "%~dp0data" (
    mkdir "%~dp0data"
    echo  Created data\ folder for the database.
)

:: ── 5. Install missing dependencies ───────────
echo.
echo  Checking dependencies...
echo.

set MISSING=0

!PYTHON! -c "import matplotlib" >nul 2>&1
if errorlevel 1 (
    echo  Installing matplotlib...
    !PYTHON! -m pip install matplotlib --quiet
    if errorlevel 1 ( echo  [WARN] Failed to install matplotlib. & set MISSING=1 )
)

!PYTHON! -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo  [WARN] tkinter is not available. Re-install Python and include tcl/tk.
    set MISSING=1
)

if "!MISSING!"=="1" (
    echo.
    echo  [WARN] One or more dependencies could not be installed.
    echo  The app may not launch correctly.
    echo.
    pause
)

:: ── 6. Launch ─────────────────────────────────
echo  All checks passed. Launching BMI Calculator Pro...
echo.

cd /d "%~dp0"
!PYTHON! "_bmicalculator.py"

if errorlevel 1 (
    echo.
    echo  [ERROR] The application exited with an error.
    echo  Check the output above for details.
    echo.
    pause
)

endlocal
