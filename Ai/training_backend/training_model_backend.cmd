@echo off
echo ============================================
echo   RASESH AI TRAINING BACKEND (spaCy + YOLO)
echo ============================================

cd /d "%~dp0"

echo Running unified training pipeline...
python run_all_training.py

echo.
echo Training complete.
pause
