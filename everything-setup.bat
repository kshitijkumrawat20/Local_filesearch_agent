@echo off
setlocal

REM === Step 1: Download Everything Installer (64-bit) ===
echo Downloading Everything installer...
powershell -Command "Invoke-WebRequest -Uri 'https://www.voidtools.com/Everything-1.4.1.1024.x64-Setup.exe' -OutFile Everything-Setup.exe"

REM === Step 2: Install Everything silently ===
echo Installing Everything silently...
start /wait "" Everything-Setup.exe /S

REM Wait a bit to allow install to complete
timeout /t 3 >nul

REM === Step 3: Stop Everything if running ===
echo Stopping Everything if running...
taskkill /IM Everything.exe /F >nul 2>&1

REM === Step 4: Update Everything.ini to enable HTTP server ===
set INI=%APPDATA%\Everything\Everything.ini

REM Create INI if it doesn't exist
if not exist "%INI%" (
    echo [Everything] > "%INI%"
)

REM Remove any old settings that conflict
findstr /v "allow_http_server" "%INI%" > "%INI%.tmp"
move /Y "%INI%.tmp" "%INI%" >nul
findstr /v "http_server_port" "%INI%" > "%INI%.tmp"
move /Y "%INI%.tmp" "%INI%" >nul

REM Ensure [Everything] header is present
findstr /C:"[Everything]" "%INI%" >nul 2>&1
if errorlevel 1 (
    echo [Everything] >> "%INI%"
)

REM Enable HTTP server on port 8888 (correct Everything config)
echo allow_http_server=1 >> "%INI%"
echo http_server_port=8888 >> "%INI%"

REM === Step 5: Start Everything ===
echo Starting Everything...
start "" "C:\Program Files\Everything\Everything.exe"

echo Done! Open your browser and test: http://127.0.0.1:8888
endlocal
pause
