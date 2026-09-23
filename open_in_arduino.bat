@echo off
setlocal
echo ======================================================
echo Membuka Firmware ESP32-C3 di Arduino IDE...
echo Port ESP32-C3 terdeteksi pada: COM4
echo ======================================================

set "INO_FILE=%~dp0firmware\esp32c3_buzzer\esp32c3_buzzer.ino"
set "ARDUINO_EXE=%LOCALAPPDATA%\Programs\Arduino IDE\Arduino IDE.exe"

if exist "%ARDUINO_EXE%" (
    start "" "%ARDUINO_EXE%" "%INO_FILE%"
) else (
    start "" "%INO_FILE%"
)

endlocal
