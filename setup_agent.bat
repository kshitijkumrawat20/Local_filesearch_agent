@echo off
echo.
echo ============================================================
echo   Local File Search Agent - Automated Setup Script
echo ============================================================
echo.

REM Set variables
set INSTALL_DIR=%USERPROFILE%\Local_filesearch_agent
set REPO_URL=https://github.com/kshitijkumrawat20/Local_filesearch_agent/archive/refs/heads/main.zip
set ZIP_FILE=%TEMP%\Local_filesearch_agent.zip

echo Step 1: Installing uv package manager...
echo ----------------------------------------

REM Check if uv is already installed
uv --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo uv is already installed
    goto :download_repo
)

echo Installing uv...
powershell -Command "irm https://astral.sh/uv/install.ps1 | iex"
if %ERRORLEVEL% NEQ 0 (
    echo Failed to install uv
    pause
    exit /b 1
)

REM Refresh PATH
call refreshenv

:download_repo
echo.
echo Step 2: Downloading repository...
echo ---------------------------------

REM Remove existing directory
if exist "%INSTALL_DIR%" (
    echo Removing existing directory...
    rmdir /s /q "%INSTALL_DIR%"
)

REM Download repository
echo Downloading from GitHub...
powershell -Command "Invoke-WebRequest -Uri '%REPO_URL%' -OutFile '%ZIP_FILE%' -UseBasicParsing"
if %ERRORLEVEL% NEQ 0 (
    echo Failed to download repository
    pause
    exit /b 1
)

REM Extract repository
echo Extracting archive...
powershell -Command "Expand-Archive -Path '%ZIP_FILE%' -DestinationPath '%TEMP%' -Force"
if %ERRORLEVEL% NEQ 0 (
    echo Failed to extract archive
    pause
    exit /b 1
)

REM Move to target directory
move "%TEMP%\Local_filesearch_agent-main" "%INSTALL_DIR%"
del "%ZIP_FILE%"

echo.
echo Step 3: Setting up Python environment...
echo ----------------------------------------

cd /d "%INSTALL_DIR%"

echo Creating virtual environment with Python 3.13...
uv venv --python 3.13
if %ERRORLEVEL% NEQ 0 (
    echo Failed to create virtual environment
    pause
    exit /b 1
)

echo.
echo Step 4: Installing dependencies...
echo ---------------------------------

echo Installing Python packages...
uv pip install -r pyproject.toml
if %ERRORLEVEL% NEQ 0 (
    echo Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo Step 5: Checking environment...
echo ------------------------------

if not defined GROQ_API_KEY (
    if not defined OPENAI_API_KEY (
        echo.
        echo WARNING: No API keys found!
        echo Please set either GROQ_API_KEY or OPENAI_API_KEY environment variable
        echo Example: set GROQ_API_KEY=your_api_key_here
        echo.
    )
)

echo.
echo Step 6: Launching application...
echo --------------------------------
echo.
echo Starting Local File Search Agent...
echo The app will open at http://localhost:8501
echo Press Ctrl+C to stop the application
echo.
echo ============================================================

uv run streamlit run app.py --server.port 8501 --server.address localhost

echo.
echo Application stopped.
pause