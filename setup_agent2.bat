@echo off
echo.
echo ============================================================
echo   Local File Search Agent - Complete Desktop App Setup
echo   FastAPI Backend + Electron Frontend
echo ============================================================
echo.

REM Set variables
set INSTALL_DIR=%CD%
set PYTHON_VERSION=3.11

echo [1/8] Checking Python installation...
echo ----------------------------------------

REM Check Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python %PYTHON_VERSION% or higher from python.org
    pause
    exit /b 1
)

echo Python found!
python --version

echo.
echo [2/8] Checking Node.js and npm...
echo ----------------------------------------

REM Check Node.js
node --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Node.js is not installed!
    echo Please install Node.js from nodejs.org
    pause
    exit /b 1
)

echo Node.js found!
node --version

REM Check npm
npm --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: npm is not installed!
    pause
    exit /b 1
)

echo npm found!
npm --version

echo.
echo [3/8] Installing Python dependencies...
echo ----------------------------------------

echo Installing backend dependencies...
pip install fastapi uvicorn[standard] websockets python-multipart pywin32

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install Python dependencies
    pause
    exit /b 1
)

echo Backend dependencies installed successfully!

echo.
echo [4/8] Setting up Windows Service for Backend...
echo ----------------------------------------

echo Creating Windows service configuration...

REM Create the service installation script
call :create_service_installer

echo Running service installer...
python install_backend_service.py install

if %ERRORLEVEL% EQU 0 (
    echo Backend service installed successfully!
    echo Starting service...
    python install_backend_service.py start
    timeout /t 3 /nobreak >nul
) else (
    echo WARNING: Service installation failed. Backend will run normally.
)

echo.
echo [5/8] Setting up Electron frontend...
echo ----------------------------------------

cd frontend

REM Check if package.json exists, if not create it
if not exist "package.json" (
    echo Creating package.json...
    call :create_package_json
)

echo Installing frontend dependencies...
call npm install

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install frontend dependencies
    cd ..
    pause
    exit /b 1
)

echo Frontend dependencies installed!

echo.
echo [6/8] Creating Electron main file...
echo ----------------------------------------

call :create_electron_main

echo Electron configuration created!

echo.
echo [7/8] Building desktop application...
echo ----------------------------------------

echo Building Electron app...
call npm run build

echo.
echo [8/8] Final setup...
echo ----------------------------------------

cd ..

REM Create desktop shortcut
call :create_desktop_shortcut

echo.
echo ============================================================
echo   Setup Complete!
echo ============================================================
echo.
echo The Local File Search Agent is now installed!
echo.
echo Backend: Running as Windows Service (auto-starts on boot)
echo Frontend: Electron desktop app
echo.
echo To launch the app:
echo   1. Double-click "Local File Search Agent" on your desktop
echo   2. Or run: npm start (from frontend folder)
echo.
echo Backend Status:
python install_backend_service.py status
echo.
echo ============================================================
pause
goto :eof

REM ============================================================
REM Helper Functions
REM ============================================================

:create_service_installer
echo Creating service installer script...
(
echo import win32serviceutil
echo import win32service
echo import win32event
echo import servicemanager
echo import socket
echo import sys
echo import os
echo import subprocess
echo import time
echo.
echo class FileSearchAgentService^(win32serviceutil.ServiceFramework^):
echo     _svc_name_ = "FileSearchAgent"
echo     _svc_display_name_ = "Local File Search Agent Backend"
echo     _svc_description_ = "AI-powered local file search and analysis service"
echo.
echo     def __init__^(self, args^):
echo         win32serviceutil.ServiceFramework.__init__^(self, args^)
echo         self.stop_event = win32event.CreateEvent^(None, 0, 0, None^)
echo         self.process = None
echo.
echo     def SvcStop^(self^):
echo         self.ReportServiceStatus^(win32service.SERVICE_STOP_PENDING^)
echo         win32event.SetEvent^(self.stop_event^)
echo         if self.process:
echo             self.process.terminate^(^)
echo             self.process.wait^(^)
echo.
echo     def SvcDoRun^(self^):
echo         servicemanager.LogMsg^(
echo             servicemanager.EVENTLOG_INFORMATION_TYPE,
echo             servicemanager.PYS_SERVICE_STARTED,
echo             ^(self._svc_name_, ''^^)
echo         ^)
echo         script_dir = os.path.dirname^(os.path.abspath^(__file__^^)^)
echo         self.process = subprocess.Popen^(
echo             [sys.executable, "-m", "uvicorn", "api_server:app",
echo              "--host", "127.0.0.1", "--port", "8765"],
echo             cwd=script_dir
echo         ^)
echo         win32event.WaitForSingleObject^(self.stop_event, win32event.INFINITE^)
echo.
echo if __name__ == '__main__':
echo     if len^(sys.argv^) == 1:
echo         servicemanager.Initialize^(^)
echo         servicemanager.PrepareToHostSingle^(FileSearchAgentService^)
echo         servicemanager.StartServiceCtrlDispatcher^(^)
echo     else:
echo         win32serviceutil.HandleCommandLine^(FileSearchAgentService^)
) > install_backend_service.py
goto :eof

:create_package_json
(
echo {
echo   "name": "local-file-search-agent",
echo   "version": "1.0.0",
echo   "description": "AI-powered local file search desktop application",
echo   "main": "electron-main.js",
echo   "scripts": {
echo     "start": "electron .",
echo     "build": "electron-builder",
echo     "pack": "electron-builder --dir",
echo     "dist": "electron-builder"
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
echo     "productName": "Local File Search Agent",
echo     "directories": {
echo       "output": "dist"
echo     },
echo     "win": {
echo       "target": ["nsis"],
echo       "icon": "assets/icon.ico"
echo     },
echo     "nsis": {
echo       "oneClick": false,
echo       "allowToChangeInstallationDirectory": true,
echo       "createDesktopShortcut": true,
echo       "createStartMenuShortcut": true
echo     }
echo   }
echo }
) > package.json
goto :eof

:create_electron_main
(
echo const { app, BrowserWindow, Tray, Menu, nativeImage } = require^('electron'^);
echo const path = require^('path'^);
echo const { spawn } = require^('child_process'^);
echo.
echo let mainWindow;
echo let tray;
echo let backendProcess;
echo.
echo const BACKEND_URL = 'http://127.0.0.1:8765';
echo.
echo // Create main window
echo function createWindow^(^) {
echo     mainWindow = new BrowserWindow^({
echo         width: 1400,
echo         height: 900,
echo         webPreferences: {
echo             nodeIntegration: false,
echo             contextIsolation: true
echo         },
echo         icon: path.join^(__dirname, 'assets', 'icon.png'^),
echo         title: 'Local File Search Agent',
echo         backgroundColor: '#f8fafc',
echo         show: false
echo     }^);
echo.
echo     mainWindow.loadFile^('index.html'^);
echo.
echo     mainWindow.once^('ready-to-show', ^(^) =^> {
echo         mainWindow.show^(^);
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
echo     const iconPath = path.join^(__dirname, 'assets', 'tray-icon.png'^);
echo     tray = new Tray^(nativeImage.createFromPath^(iconPath^)^);
echo.
echo     const contextMenu = Menu.buildFromTemplate^([
echo         {
echo             label: 'Show App',
echo             click: ^(^) =^> {
echo                 mainWindow.show^(^);
echo             }
echo         },
echo         {
echo             label: 'Quit',
echo             click: ^(^) =^> {
echo                 app.isQuitting = true;
echo                 app.quit^(^);
echo             }
echo         }
echo     ]^);
echo.
echo     tray.setToolTip^('Local File Search Agent'^);
echo     tray.setContextMenu^(contextMenu^);
echo.
echo     tray.on^('double-click', ^(^) =^> {
echo         mainWindow.show^(^);
echo     }^);
echo }
echo.
echo // App lifecycle
echo app.whenReady^(^).then^(^(^) =^> {
echo     createWindow^(^);
echo     createTray^(^);
echo }^);
echo.
echo app.on^('window-all-closed', ^(^) =^> {
echo     // Keep app running in background
echo }^);
echo.
echo app.on^('activate', ^(^) =^> {
echo     if ^(mainWindow === null^) {
echo         createWindow^(^);
echo     } else {
echo         mainWindow.show^(^);
echo     }
echo }^);
echo.
echo app.on^('before-quit', ^(^) =^> {
echo     app.isQuitting = true;
echo }^);
) > electron-main.js
goto :eof

:create_desktop_shortcut
echo Creating desktop shortcut...
set SCRIPT="%TEMP%\create_shortcut.vbs"
(
echo Set oWS = WScript.CreateObject^("WScript.Shell"^)
echo sLinkFile = oWS.SpecialFolders^("Desktop"^) ^& "\Local File Search Agent.lnk"
echo Set oLink = oWS.CreateShortcut^(sLinkFile^)
echo oLink.TargetPath = "%INSTALL_DIR%\frontend\node_modules\.bin\electron.cmd"
echo oLink.Arguments = "."
echo oLink.WorkingDirectory = "%INSTALL_DIR%\frontend"
echo oLink.Description = "AI-powered local file search"
echo oLink.Save
) > %SCRIPT%
cscript //nologo %SCRIPT%
del %SCRIPT%
goto :eof
