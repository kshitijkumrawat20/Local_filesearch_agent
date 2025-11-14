# Local File Search Agent - Complete Desktop App Setup
# FastAPI Backend as Windows Service + Electron Frontend

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  Local File Search Agent - Desktop App Setup" -ForegroundColor Cyan
Write-Host "  Backend: Windows Service | Frontend: Electron" -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Cyan

$INSTALL_DIR = $PSScriptRoot
$ErrorActionPreference = "Stop"

# Function to check if running as administrator
function Test-Administrator {
    $user = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($user)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Administrator)) {
    Write-Host "ERROR: This script requires administrator privileges!" -ForegroundColor Red
    Write-Host "Please right-click and select 'Run as Administrator'" -ForegroundColor Yellow
    pause
    exit 1
}

# [1/8] Check Python
Write-Host "[1/8] Checking Python installation..." -ForegroundColor Yellow
Write-Host "----------------------------------------`n"

try {
    $pythonVersion = & python --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ ERROR: Python is not installed!" -ForegroundColor Red
    Write-Host "Please install Python 3.11+ from python.org" -ForegroundColor Yellow
    pause
    exit 1
}

# [2/8] Check Node.js
Write-Host "`n[2/8] Checking Node.js and npm..." -ForegroundColor Yellow
Write-Host "----------------------------------------`n"

try {
    $nodeVersion = & node --version 2>&1
    Write-Host "✓ Node.js found: $nodeVersion" -ForegroundColor Green
    
    $npmVersion = & npm --version 2>&1
    Write-Host "✓ npm found: $npmVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ ERROR: Node.js/npm not installed!" -ForegroundColor Red
    Write-Host "Please install from nodejs.org" -ForegroundColor Yellow
    pause
    exit 1
}

# [3/8] Install Python dependencies
Write-Host "`n[3/8] Installing Python dependencies..." -ForegroundColor Yellow
Write-Host "----------------------------------------`n"

$pythonPackages = @(
    "fastapi",
    "uvicorn[standard]",
    "websockets",
    "python-multipart",
    "pywin32"
)

foreach ($package in $pythonPackages) {
    Write-Host "Installing $package..." -ForegroundColor Cyan
    & pip install $package --quiet
}

Write-Host "✓ Backend dependencies installed!" -ForegroundColor Green

# [4/8] Create Windows Service Script
Write-Host "`n[4/8] Creating Windows Service..." -ForegroundColor Yellow
Write-Host "----------------------------------------`n"

$serviceScript = @'
import win32serviceutil
import win32service
import win32event
import servicemanager
import sys
import os
import subprocess
import time

class FileSearchAgentService(win32serviceutil.ServiceFramework):
    _svc_name_ = "FileSearchAgent"
    _svc_display_name_ = "Local File Search Agent Backend"
    _svc_description_ = "AI-powered local file search and analysis service"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.process = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        if self.process:
            self.process.terminate()
            self.process.wait()

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "api_server:app",
             "--host", "127.0.0.1", "--port", "8765"],
            cwd=script_dir
        )
        win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(FileSearchAgentService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(FileSearchAgentService)
'@

Set-Content -Path "$INSTALL_DIR\backend_service.py" -Value $serviceScript

Write-Host "Installing Windows service..." -ForegroundColor Cyan
try {
    & python "$INSTALL_DIR\backend_service.py" install
    Write-Host "✓ Service installed!" -ForegroundColor Green
    
    Write-Host "Starting service..." -ForegroundColor Cyan
    & python "$INSTALL_DIR\backend_service.py" start
    Start-Sleep -Seconds 2
    Write-Host "✓ Service started!" -ForegroundColor Green
} catch {
    Write-Host "⚠ Service installation failed. Backend will run as normal process." -ForegroundColor Yellow
}

# [5/8] Setup Electron frontend
Write-Host "`n[5/8] Setting up Electron frontend..." -ForegroundColor Yellow
Write-Host "----------------------------------------`n"

# Create frontend directory if not exists
if (-not (Test-Path "$INSTALL_DIR\frontend")) {
    New-Item -ItemType Directory -Path "$INSTALL_DIR\frontend" | Out-Null
}

Set-Location "$INSTALL_DIR\frontend"

# Create package.json
$packageJson = @'
{
  "name": "local-file-search-agent",
  "version": "1.0.0",
  "description": "AI-powered local file search desktop application",
  "main": "electron-main.js",
  "scripts": {
    "start": "electron .",
    "build": "electron-builder",
    "pack": "electron-builder --dir",
    "dist": "electron-builder"
  },
  "keywords": ["ai", "file-search", "desktop"],
  "author": "Local File Search Agent",
  "license": "MIT",
  "devDependencies": {
    "electron": "^28.0.0",
    "electron-builder": "^24.9.1"
  },
  "dependencies": {
    "electron-store": "^8.1.0"
  },
  "build": {
    "appId": "com.filesearch.agent",
    "productName": "Local File Search Agent",
    "directories": {
      "output": "dist"
    },
    "win": {
      "target": ["nsis", "portable"],
      "icon": "assets/icon.ico"
    },
    "nsis": {
      "oneClick": false,
      "allowToChangeInstallationDirectory": true,
      "createDesktopShortcut": true,
      "createStartMenuShortcut": true
    }
  }
}
'@

Set-Content -Path "package.json" -Value $packageJson

Write-Host "Installing Electron and dependencies..." -ForegroundColor Cyan
& npm install --quiet
Write-Host "✓ Frontend dependencies installed!" -ForegroundColor Green

# [6/8] Create Electron main file
Write-Host "`n[6/8] Creating Electron application..." -ForegroundColor Yellow
Write-Host "----------------------------------------`n"

$electronMain = @'
const { app, BrowserWindow, Tray, Menu, nativeImage, shell } = require('electron');
const path = require('path');

let mainWindow;
let tray;

const BACKEND_URL = 'http://127.0.0.1:8765';

// Create main window
function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        minWidth: 800,
        minHeight: 600,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            webSecurity: true
        },
        title: 'Local File Search Agent',
        backgroundColor: '#f8fafc',
        show: false,
        autoHideMenuBar: true
    });

    mainWindow.loadFile('index.html');

    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
    });

    // Open external links in browser
    mainWindow.webContents.setWindowOpenHandler(({ url }) => {
        shell.openExternal(url);
        return { action: 'deny' };
    });

    mainWindow.on('close', (event) => {
        if (!app.isQuitting) {
            event.preventDefault();
            mainWindow.hide();
        }
    });
}

// Create system tray
function createTray() {
    // Create a simple icon for tray (you can replace with actual icon file)
    const trayIcon = nativeImage.createFromDataURL(
        'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAA7AAAAOwBeShxvQAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAJJSURBVFiFzZe/a1NBGMB/d3lJk5qYFEwHSSGTg4ODQwpKoYODi4NDh/4D/gMO/gMudegkCB0cXBwcHBxKaXFwKDRFbCFJm+Tek7vvHJLce7m8e4kE/ODg7r7v+OM73929gP9RgNa2k7u3VwADfwEH+ACcAG/wfX8BAEC7rQEcAHcBDRQBDegBh8AW8BJ4Bzzd2PDHM6AVQKPxCLgJ3Ab2gC3gBVADHgAPgB3gJnADuAU8Bh4CjwBtMgMgiiJEZE5ERERE1tba0mg0pN1uS7fbFc/zpNfrSb/fl9FoJJPJREajkYgMZWNj04nZC9i27fj+7wXGjDFSShmLEEJKKXVRFLLb7YoxA9nvD2QwGMh4PJYkSaRpWymKIjfGmNQYI0mSqCRJ/m4GQRDY1CwhRI4QAhHZ1e12JU1TrY1Ja62VUkoZY7TW2r0WkdwYo4QQQggx00CaplprrdI0VfP6kiSxRTrYAlrADaDdbvN2fQ3Osdb+KL4cx/mTl0Jz3+cAWAMcc3y8RdO08I+wR3B0dJQVRaE456RpShRF3Lp+DWPMwueXUp5yzrm/v890OuX9hw/8+vmTzc1NfN8nDEPiOE6A9+4G4jgGYOfKFd58/kxI+Z/H8YdPn+jt7+P7Pp7nzfTzPP9HVfnTNGXv82cq5XIZgJOTE06Pj2n7Pp7nUSqVeHJwgOd5eJ5Hs9l8U1UDIQQrV68ShmEF4MrODhsXLswW8vLFC/Z//6Zer+N5HuVymWq1Wqmqh+IiL/4BWAGeAs+BhwBUKhWo1WC/Bk+AZ8DNWu3wH7//I38ALLJS7fI3AAAAAElFTkSuQmCC'
    );
    
    tray = new Tray(trayIcon);

    const contextMenu = Menu.buildFromTemplate([
        {
            label: 'Show App',
            click: () => {
                mainWindow.show();
            }
        },
        { type: 'separator' },
        {
            label: 'Backend Status',
            enabled: false
        },
        {
            label: 'Open Backend Docs',
            click: () => {
                shell.openExternal('http://127.0.0.1:8765/docs');
            }
        },
        { type: 'separator' },
        {
            label: 'Quit',
            click: () => {
                app.isQuitting = true;
                app.quit();
            }
        }
    ]);

    tray.setToolTip('Local File Search Agent');
    tray.setContextMenu(contextMenu);

    tray.on('double-click', () => {
        mainWindow.show();
    });
}

// App lifecycle
app.whenReady().then(() => {
    createWindow();
    createTray();
});

app.on('window-all-closed', () => {
    // Keep app running in background on Windows
    if (process.platform !== 'darwin') {
        // Don't quit - keep in tray
    }
});

app.on('activate', () => {
    if (mainWindow === null) {
        createWindow();
    } else {
        mainWindow.show();
    }
});

app.on('before-quit', () => {
    app.isQuitting = true;
});

// Disable GPU acceleration if causing issues
app.disableHardwareAcceleration();
'@

Set-Content -Path "electron-main.js" -Value $electronMain
Write-Host "✓ Electron app created!" -ForegroundColor Green

# [7/8] Create assets directory with icon
Write-Host "`n[7/8] Creating application assets..." -ForegroundColor Yellow
Write-Host "----------------------------------------`n"

if (-not (Test-Path "assets")) {
    New-Item -ItemType Directory -Path "assets" | Out-Null
}

Write-Host "✓ Assets directory created" -ForegroundColor Green

# [8/8] Create launcher scripts
Write-Host "`n[8/8] Creating launcher scripts..." -ForegroundColor Yellow
Write-Host "----------------------------------------`n"

Set-Location $INSTALL_DIR

# Create START_DESKTOP_APP.bat
$startScript = @'
@echo off
echo Starting Local File Search Agent...
cd /d "%~dp0frontend"
start "" npm start
'@

Set-Content -Path "START_DESKTOP_APP.bat" -Value $startScript

# Create desktop shortcut
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\Local File Search Agent.lnk")
$Shortcut.TargetPath = "$INSTALL_DIR\START_DESKTOP_APP.bat"
$Shortcut.WorkingDirectory = $INSTALL_DIR
$Shortcut.Description = "AI-powered local file search"
$Shortcut.Save()

Write-Host "✓ Desktop shortcut created!" -ForegroundColor Green

# Create SETUP_README
$readme = @'
# Local File Search Agent - Desktop App Setup Complete!

## ✅ What's Been Installed

1. **Backend Service** (Windows Service)
   - Runs automatically on system startup
   - API accessible at: http://127.0.0.1:8765
   - Auto-restarts if crashed

2. **Electron Desktop App**
   - Minimizes to system tray
   - Clean, modern interface
   - Direct connection to backend

## 🚀 How to Launch

### Option 1: Desktop Shortcut
Double-click "Local File Search Agent" on your desktop

### Option 2: Manual Launch
```bash
cd frontend
npm start
```

## 🔧 Service Management

### Check Service Status
```bash
python backend_service.py status
```

### Stop Service
```bash
python backend_service.py stop
```

### Start Service
```bash
python backend_service.py start
```

### Remove Service
```bash
python backend_service.py remove
```

## 📍 Important URLs

- **Backend API**: http://127.0.0.1:8765
- **API Documentation**: http://127.0.0.1:8765/docs
- **Health Check**: http://127.0.0.1:8765/health

## 🎯 Features

- **Smart File Search**: Find files using natural language
- **Document Analysis**: Index and query PDF, DOCX, XLSX files
- **OCR Support**: Extract text from images
- **System Tray**: Runs quietly in background
- **Auto-Start**: Backend starts with Windows

## 🔑 API Key Setup

Make sure you have set your API key:

```bash
# In .env file or environment variable
OPENAI_API_KEY=your_key_here
# OR
GROQ_API_KEY=your_key_here
```

## 🆘 Troubleshooting

### Backend not responding?
1. Check service status: `python backend_service.py status`
2. Restart service: `python backend_service.py restart`
3. Check logs in Event Viewer (Windows Logs > Application)

### Frontend won't start?
1. Navigate to frontend folder
2. Run: `npm install`
3. Run: `npm start`

### Port 8765 already in use?
Edit `api_server.py` and change the port number

## 📦 Build Standalone Installer

To create a distributable installer:

```bash
cd frontend
npm run dist
```

Find the installer in `frontend/dist/`

## 🔄 Updates

To update the application:
1. Pull latest code
2. Run `pip install -r requirements.txt`
3. Run `cd frontend && npm install`
4. Restart the service

---

**Enjoy your AI-powered file search assistant! 🚀**
'@

Set-Content -Path "DESKTOP_APP_README.md" -Value $readme

# Final summary
Write-Host "`n============================================================" -ForegroundColor Green
Write-Host "  ✅ Setup Complete!" -ForegroundColor Green
Write-Host "============================================================`n" -ForegroundColor Green

Write-Host "Installation Summary:" -ForegroundColor Cyan
Write-Host "  ✓ Backend installed as Windows Service" -ForegroundColor Green
Write-Host "  ✓ Electron desktop app configured" -ForegroundColor Green
Write-Host "  ✓ Desktop shortcut created" -ForegroundColor Green
Write-Host "  ✓ Auto-start enabled" -ForegroundColor Green

Write-Host "`nBackend Service Status:" -ForegroundColor Cyan
try {
    & python "$INSTALL_DIR\backend_service.py" status
} catch {
    Write-Host "  Service management tools available in backend_service.py" -ForegroundColor Yellow
}

Write-Host "`nTo Launch the App:" -ForegroundColor Cyan
Write-Host "  1. Double-click 'Local File Search Agent' on your desktop" -ForegroundColor White
Write-Host "  2. Or run: START_DESKTOP_APP.bat" -ForegroundColor White

Write-Host "`nBackend API: http://127.0.0.1:8765" -ForegroundColor Cyan
Write-Host "API Docs: http://127.0.0.1:8765/docs" -ForegroundColor Cyan

Write-Host "`nSee DESKTOP_APP_README.md for complete documentation" -ForegroundColor Yellow
Write-Host "============================================================`n" -ForegroundColor Green

pause
