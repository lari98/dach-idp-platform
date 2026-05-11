@echo off
REM ============================================================
REM  DACH IDP Platform — Local Server (Windows)
REM  Double-click this file OR run from PowerShell/CMD
REM  Opens at: http://localhost:8000
REM  API docs: http://localhost:8000/docs
REM ============================================================

echo.
echo  ====================================================
echo   DACH Intelligent Document Processing Platform
echo   v3.0.0 — Local Development Server
echo  ====================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python not found. Install from https://python.org
    pause
    exit /b 1
)

REM Install dependencies if needed
echo  Checking dependencies...
pip install -r requirements.txt --quiet --break-system-packages 2>nul || pip install -r requirements.txt --quiet

REM Set mock mode environment variables
set APP_MODE=mock
set APP_ENV=development
set APP_HOST=0.0.0.0
set APP_PORT=8000
set LOG_LEVEL=INFO

echo.
echo  Starting server in MOCK MODE (no Azure credentials needed)
echo  API:  http://localhost:8000
echo  Docs: http://localhost:8000/docs
echo  ATS:  http://localhost:8000/api/v1/ats/jobs
echo.
echo  Press Ctrl+C to stop
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause
