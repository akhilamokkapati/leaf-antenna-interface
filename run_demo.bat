@echo off
REM ============================================================
REM  Leaf Antenna Design Interface - DEMO mode (no CST needed)
REM  Double-click this file. Needs: Python 3.10+ only.
REM ============================================================
setlocal
cd /d "%~dp0"

set PYCMD=
where python >nul 2>nul && set PYCMD=python
if "%PYCMD%"=="" ( where py >nul 2>nul && set PYCMD=py )
if "%PYCMD%"=="" (
  echo.
  echo [!] Python was not found.
  echo     Install Python 3.10+ from https://python.org
  echo     ^(tick "Add Python to PATH" during install^), then run this again.
  echo.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo First-time setup: creating environment and installing packages ^(~1 min^)...
  %PYCMD% -m venv .venv || ( echo Could not create environment. & pause & exit /b 1 )
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt || ( echo Install failed. & pause & exit /b 1 )
)

set DEMO_MODE=true
echo.
echo ============================================================
echo  Starting in DEMO mode (instant, synthetic data, no CST).
echo  A browser tab will open. Close this window to stop.
echo ============================================================
echo.
".venv\Scripts\python.exe" server.py
pause
