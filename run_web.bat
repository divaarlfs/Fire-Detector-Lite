@echo off
setlocal
set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"

if not exist "%PY_EXE%" (
    where python >nul 2>&1
    if %errorlevel% equ 0 (
        set "PY_EXE=python"
    ) else (
        echo [ERROR] Python not found.
        pause
        exit /b 1
    )
)

echo ======================================================
echo Starting Fire Detection Web Dashboard...
echo Opening: http://127.0.0.1:5000
echo ======================================================

start "" http://127.0.0.1:5000
"%PY_EXE%" web_app.py --port 5000 %*

endlocal
