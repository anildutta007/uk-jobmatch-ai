@echo off
echo ========================================================
echo Starting UK JobMatch AI Web Application...
echo ========================================================
echo.

:: Check python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found on your PATH. Please ensure Python is installed.
    pause
    exit /b 1
)

echo Starting FastAPI server at http://127.0.0.1:8000
echo Opening web browser...
start http://127.0.0.1:8000

python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
pause
