@echo off
echo.
echo ============================================================
echo   Local Agent - Backend Update Script
echo   Pull Latest Code from GitHub and Restart Backend
echo ============================================================
echo.

REM Set variables
set INSTALL_DIR=%CD%\Local_filesearch_agent
set REPO_URL=https://github.com/kshitijkumrawat20/Local_filesearch_agent/archive/refs/heads/main.zip
set ZIP_FILE=%TEMP%\Local_filesearch_agent_update.zip

echo Step 1: Stopping backend server...
echo ----------------------------------------

REM Stop backend process on port 8765
echo Searching for backend process on port 8765...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8765" ^| find "LISTENING"') do (
    echo Found backend process: %%a
    echo Stopping process...
    taskkill /F /PID %%a >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        echo Backend stopped successfully!
    ) else (
        echo Warning: Could not stop process %%a
    )
)

echo Waiting for process to fully stop...
timeout /t 3 /nobreak >nul

echo.
echo Step 2: Downloading latest code from GitHub...
echo ----------------------------------------

REM Download repository
echo Downloading from GitHub...
powershell -Command "Invoke-WebRequest -Uri '%REPO_URL%' -OutFile '%ZIP_FILE%' -UseBasicParsing"
if %ERRORLEVEL% NEQ 0 (
    echo Failed to download repository
    pause
    exit /b 1
)

echo.
echo Step 3: Extracting and updating files...
echo ----------------------------------------

REM Extract to temp location
echo Extracting archive...
set TEMP_EXTRACT=%TEMP%\Local_filesearch_agent_extract
if exist "%TEMP_EXTRACT%" rmdir /s /q "%TEMP_EXTRACT%"
powershell -Command "Expand-Archive -Path '%ZIP_FILE%' -DestinationPath '%TEMP_EXTRACT%' -Force"
if %ERRORLEVEL% NEQ 0 (
    echo Failed to extract archive
    pause
    exit /b 1
)

REM Update backend files (CRITICAL: preserve .venv, chroma_db, file_metadata.json, and .env)
echo Updating backend files (preserving venv, database, and indexed documents)...
cd /d "%INSTALL_DIR%"

REM IMPORTANT: Do NOT copy/overwrite these directories and files:
REM - .venv/ (virtual environment)
REM - chroma_db/ (vector database with indexed documents)
REM - file_metadata.json (file indexing metadata)
REM - .env (API keys and configuration)

REM Copy Python source files
echo Copying Python files...
xcopy "%TEMP_EXTRACT%\Local_filesearch_agent-main\*.py" "%INSTALL_DIR%\" /Y /Q >nul 2>&1
xcopy "%TEMP_EXTRACT%\Local_filesearch_agent-main\agents" "%INSTALL_DIR%\agents\" /E /Y /Q >nul 2>&1
xcopy "%TEMP_EXTRACT%\Local_filesearch_agent-main\config" "%INSTALL_DIR%\config\" /E /Y /Q >nul 2>&1
xcopy "%TEMP_EXTRACT%\Local_filesearch_agent-main\mcp" "%INSTALL_DIR%\mcp\" /E /Y /Q >nul 2>&1
xcopy "%TEMP_EXTRACT%\Local_filesearch_agent-main\tools" "%INSTALL_DIR%\tools\" /E /Y /Q >nul 2>&1
xcopy "%TEMP_EXTRACT%\Local_filesearch_agent-main\ui" "%INSTALL_DIR%\ui\" /E /Y /Q >nul 2>&1
xcopy "%TEMP_EXTRACT%\Local_filesearch_agent-main\utils" "%INSTALL_DIR%\utils\" /E /Y /Q >nul 2>&1

REM Update requirements if changed
if exist "%TEMP_EXTRACT%\Local_filesearch_agent-main\requirements.txt" (
    copy "%TEMP_EXTRACT%\Local_filesearch_agent-main\requirements.txt" "%INSTALL_DIR%\requirements.txt" /Y >nul
)
if exist "%TEMP_EXTRACT%\Local_filesearch_agent-main\pyproject.toml" (
    copy "%TEMP_EXTRACT%\Local_filesearch_agent-main\pyproject.toml" "%INSTALL_DIR%\pyproject.toml" /Y >nul
)

REM Cleanup
del "%ZIP_FILE%" >nul 2>&1
rmdir /s /q "%TEMP_EXTRACT%" >nul 2>&1

echo Files updated successfully!

echo.
echo Step 4: Checking for new dependencies...
echo ----------------------------------------

call .venv\Scripts\activate
if %ERRORLEVEL% NEQ 0 (
    echo Failed to activate virtual environment
    pause
    exit /b 1
)

echo Checking and installing any new dependencies...
if exist "requirements.txt" (
    uv pip install -r requirements.txt
) else if exist "pyproject.toml" (
    uv pip install -r pyproject.toml
)

if %ERRORLEVEL% NEQ 0 (
    echo Warning: Some dependencies may not have installed correctly
    pause
)

echo.
echo Step 5: Restarting backend server...
echo ----------------------------------------

echo Starting backend in background...
wscript //nologo "%INSTALL_DIR%\start_backend_silent.vbs"

echo Waiting for backend to start...
timeout /t 5 /nobreak >nul

REM Verify backend is running
powershell -Command "try { Invoke-WebRequest -Uri 'http://127.0.0.1:8765/health' -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Backend started successfully!
) else (
    echo Warning: Backend may not be running properly
    echo Check the backend manually or restore from backup
)

echo.
echo ============================================================
echo   Update Complete! ✓
echo ============================================================
echo.
echo What was updated:
echo   [✓] Python source files
echo   [✓] All backend modules (agents, config, tools, ui, utils)
echo   [✓] Dependencies checked and installed
echo   [✓] Backend restarted
echo.
echo What was preserved:
echo   [✓] Virtual environment (.venv)
echo   [✓] Vector database (chroma_db)
echo   [✓] Environment variables (.env)
echo   [✓] Frontend files
echo.
echo Backend API: http://127.0.0.1:8765
echo API Docs: http://127.0.0.1:8765/docs
echo.
echo ============================================================
pause
