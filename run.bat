@echo off
REM Batch script to run the Local File Search Agent
REM This script checks if the virtual environment is active and starts Streamlit

echo.
echo ============================================================
echo   Local File Search Agent - Run Script
echo ============================================================
echo.

REM Get the script directory
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM Check if .venv directory exists
if not exist ".venv\" (
    echo [ERROR] Virtual environment not found!
    echo Please run the setup script first: setup_agent.bat
    pause
    exit /b 1
)

REM Check if virtual environment is already activated
if defined VIRTUAL_ENV (
    echo [OK] Virtual environment is already active
    goto :check_python
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    if %ERRORLEVEL% EQU 0 (
        echo [OK] Virtual environment activated successfully
    ) else (
        echo [ERROR] Failed to activate virtual environment
        pause
        exit /b 1
    )
) else (
    echo [ERROR] Activation script not found: .venv\Scripts\activate.bat
    echo Please run the setup script first: setup_agent.bat
    pause
    exit /b 1
)

:check_python
REM Verify Python is available
echo [INFO] Checking Python installation...
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo [OK] %%i
) else (
    echo [ERROR] Python not found in virtual environment
    pause
    exit /b 1
)

REM Check if app.py exists
if not exist "app.py" (
    echo [ERROR] app.py not found in current directory
    pause
    exit /b 1
)

REM Check if Streamlit is already running
echo [INFO] Checking if Streamlit is already running...

REM First check if port is in use
netstat -ano | findstr ":8501" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    REM Port is in use, verify if it's actually responding
    echo [INFO] Port 8501 is in use. Verifying if server is responsive...
    
    REM Try to connect to the server using curl or powershell
    powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:8501' -TimeoutSec 2 -UseBasicParsing; exit 0 } catch { exit 1 }" >nul 2>&1
    
    if %ERRORLEVEL% EQU 0 (
        echo [INFO] Streamlit server is running and responsive!
        echo [INFO] Opening browser at http://localhost:8501
        echo.
        start http://localhost:8501
        timeout /t 2 /nobreak >nul
        echo [OK] Browser opened. You can close this window.
        exit /b 0
    ) else (
        echo [WARNING] Port 8501 is occupied but not responsive. Cleaning up...
        
        REM Get the PID using the port and kill it
        for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8501"') do (
            echo [INFO] Killing stale process: %%a
            taskkill /F /PID %%a >nul 2>&1
        )
        
        REM Wait for port to be released
        timeout /t 2 /nobreak >nul
        echo [INFO] Port cleaned up. Starting fresh server...
    )
)

REM Start Streamlit server in background
echo.
echo [INFO] Starting Streamlit server in background...
echo The app will open in your default browser at http://localhost:8501
echo The server will run in the background without showing logs.
echo ============================================================
echo.

REM Create a temporary VBScript to launch Streamlit without console window
set VBS_SCRIPT=%TEMP%\start_streamlit.vbs
echo Set WshShell = CreateObject("WScript.Shell") > "%VBS_SCRIPT%"
echo WshShell.Run "cmd /c cd /d ""%SCRIPT_DIR%"" && .venv\Scripts\activate.bat && streamlit run app.py --server.port 8501 --server.address localhost", 0, False >> "%VBS_SCRIPT%"

REM Execute the VBScript to start Streamlit invisibly
cscript //nologo "%VBS_SCRIPT%"

REM Delete the temporary VBScript
del "%VBS_SCRIPT%"

REM Wait a moment for the server to start
echo [INFO] Waiting for server to start...
timeout /t 5 /nobreak >nul

REM Check if server started successfully
netstat -ano | findstr ":8501" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Streamlit server started successfully!
    echo [INFO] Opening browser at http://localhost:8501
    echo.
    start http://localhost:8501
    timeout /t 2 /nobreak >nul
    echo.
    echo [INFO] The server is running in the background.
    echo [INFO] To stop the server, run: stop.bat
    echo.
    echo You can now close this window. The server will continue running.
) else (
    echo [ERROR] Failed to start Streamlit server
    echo [ERROR] Please check if all dependencies are installed.
    pause
    exit /b 1
)
=======
@echo off
REM Batch script to run the Local File Search Agent
REM This script checks if the virtual environment is active and starts Streamlit

echo.
echo ============================================================
echo   Local File Search Agent - Run Script
echo ============================================================
echo.

REM Get the script directory
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM Check if .venv directory exists
if not exist ".venv\" (
    echo [ERROR] Virtual environment not found!
    echo Please run the setup script first: setup_agent.bat
    pause
    exit /b 1
)

REM Check if virtual environment is already activated
if defined VIRTUAL_ENV (
    echo [OK] Virtual environment is already active
    goto :check_python
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    if %ERRORLEVEL% EQU 0 (
        echo [OK] Virtual environment activated successfully
    ) else (
        echo [ERROR] Failed to activate virtual environment
        pause
        exit /b 1
    )
) else (
    echo [ERROR] Activation script not found: .venv\Scripts\activate.bat
    echo Please run the setup script first: setup_agent.bat
    pause
    exit /b 1
)

:check_python
REM Verify Python is available
echo [INFO] Checking Python installation...
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo [OK] %%i
) else (
    echo [ERROR] Python not found in virtual environment
    pause
    exit /b 1
)

REM Check if app.py exists
if not exist "app.py" (
    echo [ERROR] app.py not found in current directory
    pause
    exit /b 1
)

REM Check if Streamlit is already running
echo [INFO] Checking if Streamlit is already running...

REM First check if port is in use
netstat -ano | findstr ":8501" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    REM Port is in use, verify if it's actually responding
    echo [INFO] Port 8501 is in use. Verifying if server is responsive...
    
    REM Try to connect to the server using curl or powershell
    powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:8501' -TimeoutSec 2 -UseBasicParsing; exit 0 } catch { exit 1 }" >nul 2>&1
    
    if %ERRORLEVEL% EQU 0 (
        echo [INFO] Streamlit server is running and responsive!
        echo [INFO] Opening browser at http://localhost:8501
        echo.
        start http://localhost:8501
        timeout /t 2 /nobreak >nul
        echo [OK] Browser opened. You can close this window.
        exit /b 0
    ) else (
        echo [WARNING] Port 8501 is occupied but not responsive. Cleaning up...
        
        REM Get the PID using the port and kill it
        for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8501"') do (
            echo [INFO] Killing stale process: %%a
            taskkill /F /PID %%a >nul 2>&1
        )
        
        REM Wait for port to be released
        timeout /t 2 /nobreak >nul
        echo [INFO] Port cleaned up. Starting fresh server...
    )
)

REM Start Streamlit server in background
echo.
echo [INFO] Starting Streamlit server in background...
echo The app will open in your default browser at http://localhost:8501
echo The server will run in the background without showing logs.
echo ============================================================
echo.

REM Create a temporary VBScript to launch Streamlit without console window
set VBS_SCRIPT=%TEMP%\start_streamlit.vbs
echo Set WshShell = CreateObject("WScript.Shell") > "%VBS_SCRIPT%"
echo WshShell.Run "cmd /c cd /d ""%SCRIPT_DIR%"" && .venv\Scripts\activate.bat && streamlit run app.py --server.port 8501 --server.address localhost", 0, False >> "%VBS_SCRIPT%"

REM Execute the VBScript to start Streamlit invisibly
cscript //nologo "%VBS_SCRIPT%"

REM Delete the temporary VBScript
del "%VBS_SCRIPT%"

REM Wait a moment for the server to start
echo [INFO] Waiting for server to start...
timeout /t 5 /nobreak >nul

REM Check if server started successfully
netstat -ano | findstr ":8501" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Streamlit server started successfully!
    echo [INFO] Opening browser at http://localhost:8501
    echo.
    start http://localhost:8501
    timeout /t 2 /nobreak >nul
    echo.
    echo [INFO] The server is running in the background.
    echo [INFO] To stop the server, run: stop.bat
    echo.
    echo You can now close this window. The server will continue running.
) else (
    echo [ERROR] Failed to start Streamlit server
    echo [ERROR] Please check if all dependencies are installed.
    pause
    exit /b 1
)
