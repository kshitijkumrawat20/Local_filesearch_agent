@echo off
REM Backend Management Script for Local File Search Agent
REM This script helps you manually stop or start the FastAPI backend

echo ============================================
echo   Local File Search - Backend Manager
echo ============================================
echo.
echo 1. Start Backend
echo 2. Stop Backend
echo 3. Restart Backend
echo 4. Check Backend Status
echo 5. Exit
echo.
set /p choice="Choose an option (1-5): "

if "%choice%"=="1" goto start
if "%choice%"=="2" goto stop
if "%choice%"=="3" goto restart
if "%choice%"=="4" goto status
if "%choice%"=="5" goto end
echo Invalid choice!
pause
goto end

:start
echo.
echo Starting backend...
wscript //nologo "%~dp0start_backend_silent.vbs"
timeout /t 2 >nul
goto status

:stop
echo.
echo Stopping backend...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8765" ^| find "LISTENING"') do (
    echo Killing process %%a
    taskkill /F /PID %%a >nul 2>&1
)
echo Backend stopped!
pause
goto end

:restart
echo.
echo Restarting backend...
call :stop
timeout /t 2 >nul
call :start
goto end

:status
echo.
echo Checking backend status...
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://127.0.0.1:8765/health' -UseBasicParsing -TimeoutSec 2; Write-Host 'Backend is RUNNING on port 8765' -ForegroundColor Green; exit 0 } catch { Write-Host 'Backend is NOT RUNNING' -ForegroundColor Red; exit 1 }"
echo.
echo You can access the API docs at: http://127.0.0.1:8765/docs
pause
goto end

:end
