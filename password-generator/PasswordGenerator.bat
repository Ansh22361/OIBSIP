@echo off
:: ============================================================
::  Password Generator Launcher
::  Double-click this file to launch the app, or use the
::  desktop shortcut created by create_shortcut.vbs
:: ============================================================

:: Find Python — try py launcher first, then plain python
where py >nul 2>&1
if %errorlevel% == 0 (
    set PYTHON=py
) else (
    where python >nul 2>&1
    if %errorlevel% == 0 (
        set PYTHON=python
    ) else (
        echo Python was not found on this computer.
        echo Please install Python from https://www.python.org/downloads/
        echo Make sure to check "Add Python to PATH" during installation.
        pause
        exit /b 1
    )
)

:: Move to the folder this .bat lives in (works even if run from elsewhere)
cd /d "%~dp0"

:: Launch the app — pythonw hides the console window
where pythonw >nul 2>&1
if %errorlevel% == 0 (
    start "" pythonw "%~dp0password_generator.py"
) else (
    start "" %PYTHON% "%~dp0password_generator.py"
)
