@echo off
echo ======================================================================
echo   Healthcare Record Management System Using Blockchain Technology
echo   Running automated test suite...
echo ======================================================================
cd /d "%~dp0HealthcareBlockchain"
call .venv\Scripts\activate.bat
python -m unittest discover tests
pause
