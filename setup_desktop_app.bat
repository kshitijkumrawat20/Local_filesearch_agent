@echo off
setlocal EnableDelayedExpansion
echo.
echo ============================================================
echo   Local File Search Agent - Complete Desktop App Setup
echo   FastAPI Backend + Electron Desktop Application
echo ============================================================
echo.

REM Set variables
set INSTALL_DIR=%CD%
set NODE_VERSION=20.11.0
set NODE_INSTALLER=%TEMP%\node-installer.msi

echo Step 1: Installing uv package manager...
echo ----------------------------------------

REM Check if uv is already installed
uv --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo uv is already installed
    uv --version
    goto :check_node
)

echo Installing uv...
powershell -Command "irm https://astral.sh/uv/install.ps1 | iex"
if %ERRORLEVEL% NEQ 0 (
    echo Failed to install uv
    pause
    exit /b 1
)

REM Refresh PATH using PowerShell
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "UserPath=%%b"
for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "SystemPath=%%b"
set "PATH=%UserPath%;%SystemPath%"

:check_node
echo.
echo Step 2: Checking Node.js installation...
echo ----------------------------------------

node --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Node.js is already installed
    node --version
    npm --version
    goto :setup_python_env
)

echo Node.js not found. Installing Node.js %NODE_VERSION%...
echo Downloading Node.js installer...

powershell -Command "Invoke-WebRequest -Uri 'https://nodejs.org/dist/v%NODE_VERSION%/node-v%NODE_VERSION%-x64.msi' -OutFile '%NODE_INSTALLER%' -UseBasicParsing"
if %ERRORLEVEL% NEQ 0 (
    echo Failed to download Node.js installer
    pause
    exit /b 1
)

echo Installing Node.js (this may take a few minutes)...
msiexec /i "%NODE_INSTALLER%" /qn /norestart
if %ERRORLEVEL% NEQ 0 (
    echo Failed to install Node.js
    pause
    exit /b 1
)

del "%NODE_INSTALLER%"

REM Refresh PATH to include Node.js
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "UserPath=%%b"
for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "SystemPath=%%b"
set "PATH=%SystemPath%;%UserPath%;%ProgramFiles%\nodejs"

echo Node.js installed successfully!
timeout /t 2 /nobreak >nul
node --version
npm --version

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
uv venv --python 3.13 2>nul
if !ERRORLEVEL! NEQ 0 (
    echo Python 3.13 not found, trying with Python 3.11...
    uv venv --python 3.11 2>nul
    if !ERRORLEVEL! NEQ 0 (
        echo Python 3.11 not found, trying with default Python...
        uv venv 2>nul
        if !ERRORLEVEL! NEQ 0 (
            echo.
            echo ERROR: Failed to create virtual environment!
            echo Please ensure Python 3.11 or higher is installed.
            pause
            exit /b 1
        )
    )
)

echo Virtual environment created!

echo Activating virtual environment...
if not exist ".venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment activation script not found!
    pause
    exit /b 1
)

call .venv\Scripts\activate
if !ERRORLEVEL! NEQ 0 (
    echo Failed to activate virtual environment
    pause
    exit /b 1
)

echo Virtual environment activated successfully!

echo.
echo Step 4: Installing Python dependencies...
echo ---------------------------------

echo Installing required packages from requirements.txt...
if exist "requirements.txt" (
    echo Found requirements.txt, installing packages...
    uv pip install -r requirements.txt
    set INSTALL_RESULT=!ERRORLEVEL!
) else if exist "pyproject.toml" (
    echo Found pyproject.toml, installing packages...
    uv pip install -r pyproject.toml
    set INSTALL_RESULT=!ERRORLEVEL!
) else (
    echo No requirements file found, installing core dependencies...
    uv pip install fastapi uvicorn[standard] websockets python-multipart langchain langgraph langchain-openai langchain-groq chromadb python-dotenv pillow pytesseract pypdf python-docx openpyxl
    set INSTALL_RESULT=!ERRORLEVEL!
)

if !INSTALL_RESULT! NEQ 0 (
    echo.
    echo ERROR: Failed to install Python dependencies!
    echo Please check the error messages above.
    pause
    exit /b 1
)

echo Python dependencies installed successfully!

echo.
echo Step 5: Setting up Electron frontend...
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
echo   "name": "local-file-search-agent",
echo   "version": "1.0.0",
echo   "description": "AI-powered local file search desktop application",
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
echo     "appId": "com.filesearch.agent",
echo     "productName": "LocalFileSearchAgent",
echo     "directories": {
echo       "output": "dist",
echo       "buildResources": "assets"
echo     },
echo     "win": {
echo       "target": ["portable"],
echo       "icon": "assets/icon.ico"
echo     },
echo     "portable": {
echo       "artifactName": "LocalFileSearchAgent.exe"
echo     }
echo   }
echo }
) > package.json

REM Create electron-main.js
echo Creating Electron main file...
(
echo const { app, BrowserWindow, Tray, Menu, nativeImage, shell } = require^('electron'^);
echo const path = require^('path'^);
echo const { spawn } = require^('child_process'^);
echo const http = require^('http'^);
echo.
echo let mainWindow;
echo let tray;
echo let backendProcess;
echo.
echo const BACKEND_PORT = 8765;
echo const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;
echo.
echo // Start backend server
echo function startBackend^(^) {
echo     const pythonPath = path.join^(__dirname, '..', '.venv', 'Scripts', 'python.exe'^);
echo     const serverPath = path.join^(__dirname, '..', 'api_server.py'^);
echo.    
echo     console.log^('Starting backend server...'^);
echo     backendProcess = spawn^(pythonPath, ['-m', 'uvicorn', 'api_server:app', '--host', '127.0.0.1', '--port', BACKEND_PORT], {
echo         cwd: path.join^(__dirname, '..'^),
echo         stdio: 'inherit'
echo     }^);
echo.
echo     backendProcess.on^('error', ^(err^) =^> {
echo         console.error^('Failed to start backend:', err^);
echo     }^);
echo.
echo     backendProcess.on^('exit', ^(code^) =^> {
echo         console.log^(`Backend exited with code ${code}`^);
echo     }^);
echo }
echo.
echo // Check if backend is ready
echo function checkBackend^(callback, attempts = 0^) {
echo     if ^(attempts ^> 30^) {
echo         console.error^('Backend failed to start after 30 attempts'^);
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
echo         title: 'Local File Search Agent',
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
echo     tray.setToolTip^('Local File Search Agent'^);
echo     tray.setContextMenu^(contextMenu^);
echo     tray.on^('double-click', ^(^) =^> mainWindow.show^(^)^);
echo }
echo.
echo // App lifecycle
echo app.whenReady^(^).then^(^(^) =^> {
echo     startBackend^(^);
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
echo     if ^(backendProcess^) {
echo         backendProcess.kill^(^);
echo     }
echo }^);
echo.
echo app.disableHardwareAcceleration^(^);
) > electron-main.js

REM Create assets directory
if not exist "assets" mkdir assets

echo Installing Electron and dependencies...
call npm install

if !ERRORLEVEL! NEQ 0 (
    echo.
    echo ERROR: Failed to install Electron dependencies!
    echo Please check the error messages above.
    cd ..
    pause
    exit /b 1
)

echo Electron and dependencies installed successfully!

echo.
echo Step 6: Building desktop application...
echo ----------------------------------------

echo Building portable executable...
call npm run dist

if !ERRORLEVEL! NEQ 0 (
    echo.
    echo WARNING: Build failed, but you can still run with npm start
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
    if exist "frontend\dist\LocalFileSearchAgent.exe" (
        echo Creating shortcut to portable executable...
        powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\Local File Search Agent.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\frontend\dist\LocalFileSearchAgent.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Description = 'AI-powered local file search'; $Shortcut.Save()"
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
    
    powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\Local File Search Agent.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\LAUNCH_APP.bat'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Description = 'AI-powered local file search'; $Shortcut.Save()"
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
echo Installation Summary:
echo   [✓] uv package manager installed
echo   [✓] Node.js and npm installed
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
echo   1. Double-click "Local File Search Agent" on desktop
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
