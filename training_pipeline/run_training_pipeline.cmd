@echo off
echo ======================================
echo   SMART REDACTION MODEL TRAINING
echo ======================================
echo.

REM Move into backend folder (where training_pipeline lives)
cd /d "%~dp0"

echo Running training pipeline...
python -m training_pipeline.master

echo.
echo Training complete.
pause