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
echo Memantau Notifikasi MQTT FlameVision AI (76.13.19.250)...
echo ======================================================

"%PY_EXE%" mqtt_subscriber_test.py
pause
endlocal
