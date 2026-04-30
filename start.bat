@echo off
echo ========================================
echo  Game Master Agent - Launcher
echo ========================================
echo.

REM Check if .env exists
if not exist ".env" (
    echo [WARNING] .env file not found, API may not work
    echo [TIP] Create .env file with DEEPSEEK_API_KEY
    echo.
)

REM Start backend
echo [1/2] Starting backend service...
start "Game Master Agent Backend" cmd /k "dist\python_backend\python_backend.exe 8000"

REM Wait for backend
echo [2/2] Waiting for backend to be ready...
timeout /t 3 /nobreak >nul

REM Open browser
echo Opening browser...
start http://localhost:8000

echo.
echo ========================================
echo  Service started!
echo  URL: http://localhost:8000
echo  Press Ctrl+C in backend window to stop
echo ========================================
