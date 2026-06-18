@echo off
REM Quick Start Script for Survivor Detection Website (Windows)

echo.
echo 🚀 Starting Survivor Detection Website Setup...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed. Please install Python 3.8+
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python found
echo.

REM Install requirements
echo 📦 Installing dependencies...
echo.
pip install -r requirements.txt

if errorlevel 1 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo ✅ Dependencies installed successfully!
echo.
echo 📋 Setup Summary:
echo   - MongoDB Atlas connection configured
echo   - Flask server ready
echo   - Authentication system ready
echo   - Database models ready
echo.
echo 🚀 Ready to start the server!
echo.
echo To start the web server, run in a terminal:
echo   python web_server.py
echo.
echo Then open your browser to: http://localhost:5000
echo.
echo Keep your detection backend running in another terminal:
echo   python app.py
echo.
pause
