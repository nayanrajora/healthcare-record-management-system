@echo off
echo ======================================================================
echo   Healthcare Record Management System Using Blockchain Technology
echo   Pushing to: https://github.com/nayanrajora/healthcare-record-management-system
echo ======================================================================
cd /d "%~dp0"
git remote -v
echo.
echo Executing: git push -u origin main
git push -u origin main
echo.
if %errorlevel% equ 0 (
    echo ======================================================================
    echo   SUCCESS: Project successfully uploaded to GitHub!
    echo   URL: https://github.com/nayanrajora/healthcare-record-management-system
    echo ======================================================================
) else (
    echo ======================================================================
    echo   Push paused or requires authentication.
    echo   Please sign in via the browser popup window.
    echo ======================================================================
)
pause
