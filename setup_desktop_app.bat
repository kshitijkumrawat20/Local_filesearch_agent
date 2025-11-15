@echo off
echo.
echo ============================================================
echo   LEKHA - Ram Dhari Fintech Private Limited
echo   Personal Assistant to your growth
echo   Complete Desktop App Setup
echo ============================================================
echo.

REM Set variables
set INSTALL_DIR=%CD%\Local_filesearch_agent
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
echo Step 2: Downloading repository from GitHub...
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

:setup_python_env
echo.
echo Step 3: Setting up Python virtual environment...
echo ----------------------------------------

cd /d "%INSTALL_DIR%"

REM Remove old venv if exists
if exist ".venv" (
    echo Removing old virtual environment...
    rmdir /s /q ".venv"
)

echo Creating virtual environment with Python 3.13...
uv venv --python 3.13
if %ERRORLEVEL% NEQ 0 (
    echo Failed to create virtual environment with Python 3.13
    echo Trying with Python 3.11...
    uv venv --python 3.11
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to create virtual environment
        pause
        exit /b 1
    )
)

echo Activating virtual environment...
call .venv\Scripts\activate
if %ERRORLEVEL% NEQ 0 (
    echo Failed to activate virtual environment
    pause
    exit /b 1
)

echo.
echo Step 4: Installing Python dependencies...
echo ---------------------------------

echo Installing Python packages...
if exist "requirements.txt" (
    uv pip install -r requirements.txt
) else if exist "pyproject.toml" (
    uv pip install -r pyproject.toml
) else (
    echo No requirements file found!
    pause
    exit /b 1
)

if %ERRORLEVEL% NEQ 0 (
    echo Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo Step 5: Configuring auto-start backend...
echo ------------------------------------------

echo Creating silent background launcher...

REM Create silent launcher VBS script that runs without showing window
(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo WshShell.CurrentDirectory = "%INSTALL_DIR%"
echo WshShell.Run """%INSTALL_DIR%\.venv\Scripts\python.exe"" -m uvicorn api_server:app --host 127.0.0.1 --port 8765", 0, False
) > "%INSTALL_DIR%\start_backend_silent.vbs"

REM Copy to Windows Startup folder for auto-start on every login
set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
echo Adding to Windows Startup folder...
copy "%INSTALL_DIR%\start_backend_silent.vbs" "%STARTUP_DIR%\LocalFileSearchAPI.vbs" >nul
if %ERRORLEVEL% EQU 0 (
    echo Backend configured to auto-start on login!
) else (
    echo WARNING: Could not add to startup folder
)

REM Start backend with visible console to monitor indexing progress
echo.
echo ============================================================
echo   Starting FastAPI Backend - Monitoring Indexing Progress
echo ============================================================
echo.
echo Backend will now scan and index your files...
echo This may take several minutes depending on your file count.
echo.

REM Start backend in a new visible window so we can see the indexing logs
start "Local Agent Backend - File Indexing" cmd /c "cd /d "%INSTALL_DIR%" && call .venv\Scripts\activate && python -m uvicorn api_server:app --host 127.0.0.1 --port 8765"

echo Waiting for backend to start...
timeout /t 5 /nobreak >nul

REM Wait for backend to be ready and check if indexing is complete
echo Checking backend status...
:check_backend
powershell -Command "try { Invoke-WebRequest -Uri 'http://127.0.0.1:8765/health' -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Backend not ready yet, waiting...
    timeout /t 3 /nobreak >nul
    goto check_backend
)

echo Backend is running! Checking if indexing is complete...
echo.
echo Testing with a sample chat query...
powershell -Command "$body = @{message='hello'} | ConvertTo-Json; try { $response = Invoke-RestMethod -Uri 'http://127.0.0.1:8765/chat' -Method Post -Body $body -ContentType 'application/json' -TimeoutSec 10; Write-Host 'Response received:' $response; exit 0 } catch { Write-Host 'Indexing still in progress or error occurred'; exit 1 }"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================================
    echo   Backend Ready! Documents indexed and embedded.
    echo ============================================================
    echo.
) else (
    echo.
    echo ============================================================
    echo   Backend started but indexing may still be in progress.
    echo   Check the backend window for indexing status.
    echo   Press any key to continue with Electron setup...
    echo ============================================================
    pause
)

echo.
echo Step 6: Setting up Electron frontend...
echo ----------------------------------------

REM Create frontend directory if not exists
if not exist "frontend" (
    mkdir frontend
)

cd frontend

REM Copy HTML/CSS/JS files if they exist in root
if exist "..\index.html" (
    copy "..\index.html" "index.html" >nul
)
if exist "..\styles.css" (
    copy "..\styles.css" "styles.css" >nul
)
if exist "..\app.js" (
    copy "..\app.js" "app.js" >nul
)

REM Create package.json
echo Creating package.json...
(
echo {
echo   "name": "lekha-ramdhari-fintech",
echo   "version": "1.0.0",
echo   "description": "LEKHA - Personal Assistant to your growth by Ram Dhari Fintech",
echo   "main": "electron-main.js",
echo   "scripts": {
echo     "start": "electron .",
echo     "build": "electron-builder",
echo     "dist": "electron-builder --win --x64"
echo   },
echo   "keywords": ["ai", "file-search", "desktop"],
echo   "author": "Local File Search Agent",
echo   "license": "MIT",
echo   "devDependencies": {
echo     "electron": "^28.0.0",
echo     "electron-builder": "^24.9.1"
echo   },
echo   "build": {
echo     "appId": "com.ramdhari.lekha",
echo     "productName": "LEKHA",
echo     "directories": {
echo       "output": "dist",
echo       "buildResources": "assets"
echo     },
echo     "win": {
echo       "target": ["portable"],
echo       "icon": "assets/icon.ico"
echo     },
echo     "portable": {
echo       "artifactName": "LEKHA.exe"
echo     }
echo   }
echo }
) > package.json

REM Create electron-main.js
echo Creating Electron main file...
(
echo const { app, BrowserWindow, Tray, Menu, nativeImage, shell } = require^('electron'^);
echo const path = require^('path'^);
echo const http = require^('http'^);
echo.
echo let mainWindow;
echo let tray;
echo.
echo const BACKEND_PORT = 8765;
echo const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;
echo.
echo // Check if backend is ready
echo function checkBackend^(callback, attempts = 0^) {
echo     if ^(attempts ^> 30^) {
echo         console.error^('Backend is not available. Please start the backend server.'^);
echo         return;
echo     }
echo.
echo     http.get^(BACKEND_URL + '/health', ^(res^) =^> {
echo         if ^(res.statusCode === 200^) {
echo             console.log^('Backend is ready!'^);
echo             callback^(^);
echo         } else {
echo             setTimeout^(^(^) =^> checkBackend^(callback, attempts + 1^), 1000^);
echo         }
echo     }^).on^('error', ^(^) =^> {
echo         if ^(attempts === 0^) {
echo             console.log^('Waiting for backend server...'^);
echo         }
echo         setTimeout^(^(^) =^> checkBackend^(callback, attempts + 1^), 1000^);
echo     }^);
echo }
echo.
echo // Create main window
echo function createWindow^(^) {
echo     mainWindow = new BrowserWindow^({
echo         width: 1400,
echo         height: 900,
echo         minWidth: 800,
echo         minHeight: 600,
echo         webPreferences: {
echo             nodeIntegration: false,
echo             contextIsolation: true,
echo             webSecurity: true
echo         },
echo         title: 'Local Agent',
echo         backgroundColor: '#f8fafc',
echo         show: false,
echo         autoHideMenuBar: true
echo     }^);
echo.
echo     mainWindow.loadFile^('index.html'^);
echo.
echo     mainWindow.once^('ready-to-show', ^(^) =^> {
echo         mainWindow.show^(^);
echo     }^);
echo.
echo     mainWindow.webContents.setWindowOpenHandler^(^({ url }^) =^> {
echo         shell.openExternal^(url^);
echo         return { action: 'deny' };
echo     }^);
echo.
echo     mainWindow.on^('close', ^(event^) =^> {
echo         if ^(!app.isQuitting^) {
echo             event.preventDefault^(^);
echo             mainWindow.hide^(^);
echo         }
echo     }^);
echo }
echo.
echo // Create system tray
echo function createTray^(^) {
echo     const iconData = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAA7AAAAOwBeShxvQAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAJJSURBVFiFzZe/a1NBGMB/d3lJk5qYFEwHSSGTg4ODQwpKoYODi4NDh/4D/gMO/gMudegkCB0cXBwcHBxKaXFwKDRFbCFJm+Tek7vvHJLce7m8e4kE/ODg7r7v+OM73929gP9RgNa2k7u3VwADfwEH+ACcAG/wfX8BAEC7rQEcAHcBDRQBDegBh8AW8BJ4Bzzd2PDHM6AVQKPxCLgJ3Ab2gC3gBVADHgAPgB3gJnADuAU8Bh4CjwBtMgMgiiJEZE5ERERE1tba0mg0pN1uS7fbFc/zpNfrSb/fl9FoJJPJREajkYgMZWNj04nZC9i27fj+7wXGjDFSShmLEEJKKXVRFLLb7YoxA9nvD2QwGMh4PJYkSaRpWymKIjfGmNQYI0mSqCRJ/m4GQRDY1CwhRI4QAhHZ1e12JU1TrY1Ja62VUkoZY7TW2r0WkdwYo4QQQggx00CaplprrdI0VfP6kiSxRTrYAlrADaDdbvN2fQ3Osdb+KL4cx/mTl0Jz3+cAWAMcc3y8RdO08I+wR3B0dJQVRaE456RpShRF3Lp+DWPMwueXUp5yzrm/v890OuX9hw/8+vmTzc1NfN8nDEPiOE6A9+4G4jgGYOfKFd58/kxI+Z/H8YdPn+jt7+P7Pp7nzfTzPP9HVfnTNGXv82cq5XIZgJOTE06Pj2n7Pp7nUSqVeHJwgOd5eJ5Hs9l8U1UDIQQrV68ShmEF4MrODhsXLswW8vLFC/Z//6Zer+N5HuVymWq1Wqmqh+IiL/4BWAGeAs+BhwBUKhWo1WC/Bk+AZ8DNWu3wH7//I38AFLJS7fI3AAAAAElFTkSuQmCC';
echo     const trayIcon = nativeImage.createFromDataURL^(iconData^);
echo     tray = new Tray^(trayIcon^);
echo.
echo     const contextMenu = Menu.buildFromTemplate^([
echo         { label: 'Show App', click: ^(^) =^> mainWindow.show^(^) },
echo         { type: 'separator' },
echo         { label: 'Open API Docs', click: ^(^) =^> shell.openExternal^(BACKEND_URL + '/docs'^) },
echo         { type: 'separator' },
echo         { label: 'Quit', click: ^(^) =^> { app.isQuitting = true; app.quit^(^); } }
echo     ]^);
echo.
echo     tray.setToolTip^('Local Agent'^);
echo     tray.setContextMenu^(contextMenu^);
echo     tray.on^('double-click', ^(^) =^> mainWindow.show^(^)^);
echo }
echo.
echo // App lifecycle
echo app.whenReady^(^).then^(^(^) =^> {
echo     checkBackend^(^(^) =^> {
echo         createWindow^(^);
echo         createTray^(^);
echo     }^);
echo }^);
echo.
echo app.on^('window-all-closed', ^(^) =^> { }^);
echo app.on^('activate', ^(^) =^> {
echo     if ^(mainWindow === null^) createWindow^(^);
echo     else mainWindow.show^(^);
echo }^);
echo.
echo app.on^('before-quit', ^(^) =^> {
echo     app.isQuitting = true;
echo }^);
echo.
echo app.disableHardwareAcceleration^(^);
) > electron-main.js

REM Create assets directory
if not exist "assets" mkdir assets

echo Installing Electron and dependencies...
call npm install

if %ERRORLEVEL% NEQ 0 (
    echo Failed to install Electron dependencies
    cd ..
    pause
    exit /b 1
)

echo.
echo Step 6: Building desktop application...
echo ----------------------------------------

echo Building portable executable...
call npm run dist

if %ERRORLEVEL% NEQ 0 (
    echo Build failed, but you can still run with npm start
    set BUILD_FAILED=1
) else (
    echo Build successful!
    set BUILD_FAILED=0
)

echo.
echo Step 7: Creating desktop shortcuts...
echo ----------------------------------------

cd ..

if "%BUILD_FAILED%"=="0" (
    REM Create shortcut to portable exe
    if exist "frontend\dist\LEKHA.exe" (
        echo Creating shortcut to portable executable...
        powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\LEKHA.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\frontend\dist\LEKHA.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Description = 'LEKHA - Personal Assistant to your growth'; $Shortcut.Save()"
        echo Desktop shortcut created to portable executable!
    )
) else (
    REM Create shortcut to npm start
    echo Creating desktop shortcut to npm start...
    
    REM Create a launcher script
    (
    echo @echo off
    echo cd /d "%INSTALL_DIR%\frontend"
    echo call npm start
    ) > LAUNCH_APP.bat
    
    powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\LEKHA.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\LAUNCH_APP.bat'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Description = 'LEKHA - Personal Assistant to your growth'; $Shortcut.Save()"
    echo Desktop shortcut created!
)

echo.
echo Step 8: Checking environment variables...
echo ------------------------------

if not defined GROQ_API_KEY (
    if not defined OPENAI_API_KEY (
        echo.
        echo ============================================================
        echo WARNING: No API keys found!
        echo ============================================================
        echo.
        echo Please set either GROQ_API_KEY or OPENAI_API_KEY
        echo.
        echo Option 1: Create .env file in this directory with:
        echo   OPENAI_API_KEY=your_key_here
        echo   or
        echo   GROQ_API_KEY=your_key_here
        echo.
        echo Option 2: Set as environment variable
        echo.
        echo ============================================================
        echo.
    )
)

echo.
echo ============================================================
echo   Setup Complete! ✓
echo ============================================================
echo.
echo Installed to: %INSTALL_DIR%
echo.
echo Installation Summary:
echo   [✓] uv package manager installed
echo   [✓] Python virtual environment created
echo   [✓] Python dependencies installed
echo   [✓] Electron desktop app configured
if "%BUILD_FAILED%"=="0" (
    echo   [✓] Portable executable built
) else (
    echo   [⚠] Portable build skipped - using npm start
)
echo   [✓] Desktop shortcut created
echo.
echo How to launch:
echo   1. Double-click "LEKHA" on desktop
if "%BUILD_FAILED%"=="1" (
    echo   2. Or run: cd frontend ^&^& npm start
)
echo.
echo Backend API: http://127.0.0.1:8765
echo API Docs: http://127.0.0.1:8765/docs
echo.
echo The desktop app will:
echo   - Start backend server automatically
echo   - Connect to backend when ready
echo   - Run in system tray when minimized
echo.
echo ============================================================
pause
