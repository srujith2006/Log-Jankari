@echo off
REM Master Launcher Script for Windows
REM Starts all services: GPS Server, Detection Backend, Web Server

setlocal enabledelayedexpansion

cls
echo.
echo ========================================================================
echo  MyVerse Survivor Detection System - Master Launcher
echo ========================================================================
echo.
echo Starting all services...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Get the script directory
set SCRIPT_DIR=%~dp0

echo.
echo ========================================================================
echo Starting Services:
echo ========================================================================
echo.

REM Start GPS Server (Port 8888)
echo [1/3] Starting GPS Server (Port 8888)...
start "GPS Server - Port 8888" /D "%SCRIPT_DIR%" cmd /k "python gps_server.py"
timeout /t 2 /nobreak

REM Start Detection Backend (App.py)
echo [2/3] Starting Detection Backend...
start "Detection Backend - Video Processing" /D "%SCRIPT_DIR%" cmd /k "python app.py"
timeout /t 3 /nobreak

REM Start Web Server (Port 5000)
echo [3/3] Starting Web Server (Port 5000)...
start "Web Server - http://localhost:5000" /D "%SCRIPT_DIR%" cmd /k "python web_server.py"
timeout /t 2 /nobreak

cls
echo.
echo ========================================================================
echo  All Services Started Successfully!
echo ========================================================================
echo.
echo [OK] GPS Server ................. Running (Port 8888)
echo [OK] Detection Backend .......... Running (Video from Mobile)
echo [OK] Web Server ................. Running (http://localhost:5000)
echo.
echo ========================================================================
echo Access Points:
echo ========================================================================
echo.
echo   WEB INTERFACE: http://localhost:5000
echo     - Register new account
echo     - View survivors
echo     - Identify survivors
echo     - Admin dashboard
echo.
echo   GPS SERVER: localhost:8888
echo     - Provides location data to detection system
echo.
echo   DETECTION BACKEND:
echo     - Processes video from mobile
echo     - Detects survivors
echo     - Sends data to database
echo.
echo ========================================================================
echo Important Notes:
echo ========================================================================
echo.
echo 1. EACH SERVICE runs in its OWN WINDOW
echo    - You can see logs/errors for each independently
echo    - Close any window to stop that service
echo    - All 3 can run simultaneously
echo.
echo 2. VIDEO STREAMING:
echo    - Connect your mobile to video stream URL configured in app.py
echo    - Detection will process frames in real-time
echo    - Results appear on website automatically
echo.
echo 3. WEBSITE:
echo    - Open http://localhost:5000 in your browser
echo    - Survivors from detection appear automatically
echo    - Users can identify them
echo.
echo 4. TO STOP ALL:
echo    - Close each window, or
echo    - Press Ctrl+C in each window
echo.
echo ========================================================================
echo.
echo Opening website in browser...
timeout /t 3 /nobreak

REM Try to open browser
start http://localhost:5000

echo.
echo All systems ready! Keep all windows open for continuous operation.
echo.
pause
