@echo off
chcp 65001 >nul

echo ========================================
echo 🚀 Rasesh IM PDF CRM Generator
echo ========================================
echo 📊 Starting server...
echo.

REM ---------------------------------------------------------
REM Create virtual environment if missing (USE python, NOT py)
REM ---------------------------------------------------------
IF NOT EXIST venv (
    echo Creating virtual environment using Python 3.11...
    python -m venv venv
)

REM ---------------------------------------------------------
REM Activate venv
REM ---------------------------------------------------------
call venv\Scripts\activate

REM ---------------------------------------------------------
REM Install dependencies if needed
REM ---------------------------------------------------------
IF NOT EXIST venv\Lib\site-packages\flask (
    echo Installing dependencies...
    pip install -r requirements.txt
)

REM ---------------------------------------------------------
REM Open browser
REM ---------------------------------------------------------
start "" http://localhost:5000/

REM ---------------------------------------------------------
REM Run the application using the VENV Python (ALWAYS CORRECT)
REM ---------------------------------------------------------
echo Starting Flask server...
venv\Scripts\python.exe app.py

echo.
echo Server stopped.
pause
