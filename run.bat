@echo off
setlocal
set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"

if not exist "%PY_EXE%" (
    where python >nul 2>&1
    if %errorlevel% equ 0 (
        set "PY_EXE=python"
    ) else (
        echo [ERROR] Python not found. Please run setup_embed_python.ps1 first.
        pause
        exit /b 1
    )
)

echo Starting Real-Time Fire Detection System...
"%PY_EXE%" main.py %*

endlocal
