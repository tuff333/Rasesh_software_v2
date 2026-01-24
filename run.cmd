@echo off
echo ========================================
echo 🚀 Rasesh IM PDF CRM Generator
echo ========================================
echo 📊 Starting server...
echo .

IF NOT EXIST venv (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate
    python -m pip install -r requirements.txt
) ELSE (
    call venv\Scripts\activate
)

start http://localhost:5000
python app.py
pause
