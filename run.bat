@echo off
echo ======================================================================
echo   Healthcare Record Management System Using Blockchain Technology
echo   Starting local Flask server...
echo ======================================================================
cd /d "%~dp0HealthcareBlockchain"
call .venv\Scripts\activate.bat
python app.py
pause
