# Local File Search Agent - Complete Desktop App Setup
# PowerShell Setup Script

$ErrorActionPreference = "Stop"

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  Local File Search Agent - Complete Desktop App Setup" -ForegroundColor Cyan
Write-Host "  FastAPI Backend + Electron Desktop Application" -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Cyan

$CURRENT_DIR = $PSScriptRoot
$INSTALL_DIR = Join-Path $CURRENT_DIR "Local_filesearch_agent"
$REPO_URL = "https://github.com/kshitijkumrawat20/Local_filesearch_agent/archive/refs/heads/main.zip"
$ZIP_FILE = Join-Path $env:TEMP "Local_filesearch_agent.zip"

# Step 1: Check and install uv
Write-Host "Step 1: Installing uv package manager..." -ForegroundColor Yellow
Write-Host "----------------------------------------`n"

try {
    $uvVersion = & uv --version 2>&1
    Write-Host "✓ uv is already installed: $uvVersion" -ForegroundColor Green
} catch {
    Write-Host "Installing uv..." -ForegroundColor Cyan
    irm https://astral.sh/uv/install.ps1 | iex
    
    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    
    Write-Host "✓ uv installed successfully!" -ForegroundColor Green
}

# Step 2: Download repository from GitHub
Write-Host "`nStep 2: Downloading repository from GitHub..." -ForegroundColor Yellow
Write-Host "----------------------------------------`n"

# Remove existing directory
if (Test-Path $INSTALL_DIR) {
    Write-Host "Removing existing directory..." -ForegroundColor Cyan
    Remove-Item -Recurse -Force $INSTALL_DIR
}

# Download repository
Write-Host "Downloading from GitHub..." -ForegroundColor Cyan
try {
    Invoke-WebRequest -Uri $REPO_URL -OutFile $ZIP_FILE -UseBasicParsing
    Write-Host "✓ Download complete!" -ForegroundColor Green
} catch {
    Write-Host "✗ ERROR: Failed to download repository!" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    pause
    exit 1
}

# Extract repository
Write-Host "Extracting archive..." -ForegroundColor Cyan
try {
    Expand-Archive -Path $ZIP_FILE -DestinationPath $env:TEMP -Force
    Write-Host "✓ Extraction complete!" -ForegroundColor Green
} catch {
    Write-Host "✗ ERROR: Failed to extract archive!" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    pause
    exit 1
}

# Move to target directory
Move-Item -Path (Join-Path $env:TEMP "Local_filesearch_agent-main") -Destination $INSTALL_DIR -Force
Remove-Item $ZIP_FILE -Force

Write-Host "✓ Repository downloaded and extracted to: $INSTALL_DIR" -ForegroundColor Green

# Step 3: Check and install Node.js
Write-Host "`nStep 3: Checking Node.js installation..." -ForegroundColor Yellow
Write-Host "----------------------------------------`n"

try {
    $nodeVersion = & node --version 2>&1
    $npmVersion = & npm --version 2>&1
    Write-Host "✓ Node.js is already installed: $nodeVersion" -ForegroundColor Green
    Write-Host "✓ npm is already installed: $npmVersion" -ForegroundColor Green
} catch {
    Write-Host "Node.js not found. Installing Node.js 20.11.0..." -ForegroundColor Cyan
    
    $NODE_INSTALLER = "$env:TEMP\node-installer.msi"
    $NODE_URL = "https://nodejs.org/dist/v20.11.0/node-v20.11.0-x64.msi"
    
    Write-Host "Downloading Node.js installer..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri $NODE_URL -OutFile $NODE_INSTALLER -UseBasicParsing
    
    Write-Host "Installing Node.js (this may take a few minutes)..." -ForegroundColor Cyan
    Start-Process msiexec.exe -ArgumentList "/i `"$NODE_INSTALLER`" /qn /norestart" -Wait -NoNewWindow
    
    Remove-Item $NODE_INSTALLER -Force
    
    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    
    Start-Sleep -Seconds 3
    
    $nodeVersion = & node --version 2>&1
    $npmVersion = & npm --version 2>&1
    Write-Host "✓ Node.js installed: $nodeVersion" -ForegroundColor Green
    Write-Host "✓ npm installed: $npmVersion" -ForegroundColor Green
}

# Step 4: Setup Python virtual environment
Write-Host "`nStep 4: Setting up Python virtual environment..." -ForegroundColor Yellow
Write-Host "----------------------------------------`n"

Set-Location $INSTALL_DIR

# Remove old venv if exists
if (Test-Path ".venv") {
    Write-Host "Removing old virtual environment..." -ForegroundColor Cyan
    Remove-Item -Recurse -Force ".venv"
}

Write-Host "Creating virtual environment with Python 3.13..." -ForegroundColor Cyan
try {
    & uv venv --python 3.13 2>&1 | Out-Null
    Write-Host "✓ Virtual environment created with Python 3.13" -ForegroundColor Green
} catch {
    Write-Host "Python 3.13 not found, trying with Python 3.11..." -ForegroundColor Yellow
    try {
        & uv venv --python 3.11 2>&1 | Out-Null
        Write-Host "✓ Virtual environment created with Python 3.11" -ForegroundColor Green
    } catch {
        Write-Host "Trying with default Python..." -ForegroundColor Yellow
        & uv venv
        Write-Host "✓ Virtual environment created with default Python" -ForegroundColor Green
    }
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
$venvActivate = Join-Path $INSTALL_DIR ".venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    & $venvActivate
    Write-Host "✓ Virtual environment activated!" -ForegroundColor Green
} else {
    Write-Host "✗ ERROR: Virtual environment activation script not found!" -ForegroundColor Red
    pause
    exit 1
}

# Step 5: Install Python dependencies
Write-Host "`nStep 5: Installing Python dependencies..." -ForegroundColor Yellow
Write-Host "----------------------------------------`n"

if (Test-Path "requirements.txt") {
    Write-Host "Found requirements.txt, installing packages..." -ForegroundColor Cyan
    & uv pip install -r requirements.txt
} elseif (Test-Path "pyproject.toml") {
    Write-Host "Found pyproject.toml, installing packages..." -ForegroundColor Cyan
    & uv pip install -r pyproject.toml
} else {
    Write-Host "No requirements file found, installing core dependencies..." -ForegroundColor Cyan
    & uv pip install fastapi "uvicorn[standard]" websockets python-multipart langchain langgraph langchain-openai langchain-groq chromadb python-dotenv pillow pytesseract pypdf python-docx openpyxl
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Python dependencies installed successfully!" -ForegroundColor Green
} else {
    Write-Host "✗ ERROR: Failed to install Python dependencies!" -ForegroundColor Red
    pause
    exit 1
}

# Step 6: Setup Electron frontend
Write-Host "`nStep 6: Setting up Electron frontend..." -ForegroundColor Yellow
Write-Host "----------------------------------------`n"

# Create frontend directory if not exists
$frontendDir = Join-Path $INSTALL_DIR "frontend"
if (-not (Test-Path $frontendDir)) {
    New-Item -ItemType Directory -Path $frontendDir | Out-Null
}

Set-Location $frontendDir

# Copy HTML/CSS/JS files if they exist in the installed repo
$sourceHtml = Join-Path $INSTALL_DIR "frontend\index.html"
$sourceCss = Join-Path $INSTALL_DIR "frontend\styles.css"
$sourceJs = Join-Path $INSTALL_DIR "frontend\app.js"

if (Test-Path $sourceHtml) {
    Copy-Item $sourceHtml -Destination "index.html" -Force
    Write-Host "✓ Copied index.html" -ForegroundColor Green
}
if (Test-Path $sourceCss) {
    Copy-Item $sourceCss -Destination "styles.css" -Force
    Write-Host "✓ Copied styles.css" -ForegroundColor Green
}
if (Test-Path $sourceJs) {
    Copy-Item $sourceJs -Destination "app.js" -Force
    Write-Host "✓ Copied app.js" -ForegroundColor Green
}

# Create package.json
Write-Host "Creating package.json..." -ForegroundColor Cyan
$packageJson = @'
{
  "name": "local-file-search-agent",
  "version": "1.0.0",
  "description": "AI-powered local file search desktop application",
  "main": "electron-main.js",
  "scripts": {
    "start": "electron .",
    "build": "electron-builder",
    "dist": "electron-builder --win --x64"
  },
  "keywords": ["ai", "file-search", "desktop"],
  "author": "Local File Search Agent",
  "license": "MIT",
  "devDependencies": {
    "electron": "^28.0.0",
    "electron-builder": "^24.9.1"
  },
  "build": {
    "appId": "com.filesearch.agent",
    "productName": "LocalFileSearchAgent",
    "directories": {
      "output": "dist",
      "buildResources": "assets"
    },
    "win": {
      "target": ["portable"],
      "icon": "assets/icon.ico"
    },
    "portable": {
      "artifactName": "LocalFileSearchAgent.exe"
    }
  }
}
'@
Set-Content -Path "package.json" -Value $packageJson

# Create electron-main.js
Write-Host "Creating Electron main file..." -ForegroundColor Cyan
$electronMain = @'
const { app, BrowserWindow, Tray, Menu, nativeImage, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');

let mainWindow;
let tray;
let backendProcess;

const BACKEND_PORT = 8765;
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;

// Start backend server
function startBackend() {
    const pythonPath = path.join(__dirname, '..', '.venv', 'Scripts', 'python.exe');
    
    console.log('Starting backend server...');
    backendProcess = spawn(pythonPath, ['-m', 'uvicorn', 'api_server:app', '--host', '127.0.0.1', '--port', BACKEND_PORT], {
        cwd: path.join(__dirname, '..'),
        stdio: 'inherit'
    });

    backendProcess.on('error', (err) => {
        console.error('Failed to start backend:', err);
    });

    backendProcess.on('exit', (code) => {
        console.log(`Backend exited with code ${code}`);
    });
}

// Check if backend is ready
function checkBackend(callback, attempts = 0) {
    if (attempts > 30) {
        console.error('Backend failed to start after 30 attempts');
        return;
    }

    http.get(BACKEND_URL + '/health', (res) => {
        if (res.statusCode === 200) {
            console.log('Backend is ready!');
            callback();
        } else {
            setTimeout(() => checkBackend(callback, attempts + 1), 1000);
        }
    }).on('error', () => {
        setTimeout(() => checkBackend(callback, attempts + 1), 1000);
    });
}

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
    const iconData = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAA7AAAAOwBeShxvQAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAJJSURBVFiFzZe/a1NBGMB/d3lJk5qYFEwHSSGTg4ODQwpKoYODi4NDh/4D/gMO/gMudegkCB0cXBwcHBxKaXFwKDRFbCFJm+Tek7vvHJLce7m8e4kE/ODg7r7v+OM73929gP9RgNa2k7u3VwADfwEH+ACcAG/wfX8BAEC7rQEcAHcBDRQBDegBh8AW8BJ4Bzzd2PDHM6AVQKPxCLgJ3Ab2gC3gBVADHgAPgB3gJnADuAU8Bh4CjwBtMgMgiiJEZE5ERERE1tba0mg0pN1uS7fbFc/zpNfrSb/fl9FoJJPJREajkYgMZWNj04nZC9i27fj+7wXGjDFSShmLEEJKKXVRFLLb7YoxA9nvD2QwGMh4PJYkSaRpWymKIjfGmNQYI0mSqCRJ/m4GQRDY1CwhRI4QAhHZ1e12JU1TrY1Ja62VUkoZY7TW2r0WkdwYo4QQQggx00CaplprrdI0VfP6kiSxRTrYAlrADaDdbvN2fQ3Osdb+KL4cx/mTl0Jz3+cAWAMcc3y8RdO08I+wR3B0dJQVRaE456RpShRF3Lp+DWPMwueXUp5yzrm/v890OuX9hw/8+vmTzc1NfN8nDEPiOE6A9+4G4jgGYOfKFd58/kxI+Z/H8YdPn+jt7+P7Pp7nzfTzPP9HVfnTNGXv82cq5XIZgJOTE06Pj2n7Pp7nUSqVeHJwgOd5eJ5Hs9l8U1UDIQQrV68ShmEF4MrODhsXLswW8vLFC/Z//6Zer+N5HuVymWq1Wqmqh+IiL/4BWAGeAs+BhwBUKhWo1WC/Bk+AZ8DNWu3wH7//I38AFLJS7fI3AAAAAElFTkSuQmCC';
    const trayIcon = nativeImage.createFromDataURL(iconData);
    tray = new Tray(trayIcon);

    const contextMenu = Menu.buildFromTemplate([
        { label: 'Show App', click: () => mainWindow.show() },
        { type: 'separator' },
        { label: 'Open API Docs', click: () => shell.openExternal(BACKEND_URL + '/docs') },
        { type: 'separator' },
        { label: 'Quit', click: () => { app.isQuitting = true; app.quit(); } }
    ]);

    tray.setToolTip('Local File Search Agent');
    tray.setContextMenu(contextMenu);
    tray.on('double-click', () => mainWindow.show());
}

// App lifecycle
app.whenReady().then(() => {
    startBackend();
    checkBackend(() => {
        createWindow();
        createTray();
    });
});

app.on('window-all-closed', () => { });
app.on('activate', () => {
    if (mainWindow === null) createWindow();
    else mainWindow.show();
});

app.on('before-quit', () => {
    app.isQuitting = true;
    if (backendProcess) {
        backendProcess.kill();
    }
});

app.disableHardwareAcceleration();
'@
Set-Content -Path "electron-main.js" -Value $electronMain

# Create assets directory
if (-not (Test-Path "assets")) {
    New-Item -ItemType Directory -Path "assets" | Out-Null
}

Write-Host "Installing Electron and dependencies..." -ForegroundColor Cyan
& npm install

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Electron and dependencies installed successfully!" -ForegroundColor Green
} else {
    Write-Host "✗ ERROR: Failed to install Electron dependencies!" -ForegroundColor Red
    Set-Location $INSTALL_DIR
    pause
    exit 1
}

# Step 7: Build desktop application
Write-Host "`nStep 7: Building desktop application..." -ForegroundColor Yellow
Write-Host "----------------------------------------`n"

Write-Host "Building portable executable..." -ForegroundColor Cyan
& npm run dist 2>&1 | Out-Null

$BUILD_FAILED = $LASTEXITCODE -ne 0

if (-not $BUILD_FAILED) {
    Write-Host "✓ Build successful!" -ForegroundColor Green
} else {
    Write-Host "⚠ Build failed, but you can still run with npm start" -ForegroundColor Yellow
}

# Step 8: Create desktop shortcuts
Write-Host "`nStep 8: Creating desktop shortcuts..." -ForegroundColor Yellow
Write-Host "----------------------------------------`n"

Set-Location $CURRENT_DIR

$exePath = Join-Path $INSTALL_DIR "frontend\dist\LocalFileSearchAgent.exe"
if (-not $BUILD_FAILED -and (Test-Path $exePath)) {
    Write-Host "Creating shortcut to portable executable..." -ForegroundColor Cyan
    
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\Local File Search Agent.lnk")
    $Shortcut.TargetPath = $exePath
    $Shortcut.WorkingDirectory = $INSTALL_DIR
    $Shortcut.Description = "AI-powered local file search"
    $Shortcut.Save()
    
    Write-Host "✓ Desktop shortcut created to portable executable!" -ForegroundColor Green
} else {
    Write-Host "Creating desktop shortcut to npm start..." -ForegroundColor Cyan
    
    # Create a launcher script
    $launcherPath = Join-Path $INSTALL_DIR "LAUNCH_APP.bat"
    $launcherScript = @"
@echo off
cd /d "$INSTALL_DIR\frontend"
call npm start
"@
    Set-Content -Path $launcherPath -Value $launcherScript
    
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\Local File Search Agent.lnk")
    $Shortcut.TargetPath = $launcherPath
    $Shortcut.WorkingDirectory = $INSTALL_DIR
    $Shortcut.Description = "AI-powered local file search"
    $Shortcut.Save()
    
    Write-Host "✓ Desktop shortcut created!" -ForegroundColor Green
}

# Step 9: Check environment variables
Write-Host "`nStep 9: Checking environment variables..." -ForegroundColor Yellow
Write-Host "----------------------------------------`n"

if (-not $env:GROQ_API_KEY -and -not $env:OPENAI_API_KEY) {
    Write-Host "============================================================" -ForegroundColor Yellow
    Write-Host "WARNING: No API keys found!" -ForegroundColor Yellow
    Write-Host "============================================================`n" -ForegroundColor Yellow
    Write-Host "Please set either GROQ_API_KEY or OPENAI_API_KEY`n"
    Write-Host "Option 1: Create .env file in this directory with:"
    Write-Host "  OPENAI_API_KEY=your_key_here"
    Write-Host "  or"
    Write-Host "  GROQ_API_KEY=your_key_here`n"
    Write-Host "Option 2: Set as environment variable`n"
    Write-Host "============================================================`n" -ForegroundColor Yellow
}

# Final summary
Write-Host "`n============================================================" -ForegroundColor Green
Write-Host "  ✅ Setup Complete!" -ForegroundColor Green
Write-Host "============================================================`n" -ForegroundColor Green

Write-Host "Installation Summary:" -ForegroundColor Cyan
Write-Host "  ✓ uv package manager installed" -ForegroundColor Green
Write-Host "  ✓ Node.js and npm installed" -ForegroundColor Green
Write-Host "  ✓ Python virtual environment created" -ForegroundColor Green
Write-Host "  ✓ Python dependencies installed" -ForegroundColor Green
Write-Host "  ✓ Electron desktop app configured" -ForegroundColor Green

if (-not $BUILD_FAILED) {
    Write-Host "  ✓ Portable executable built" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Portable build skipped - using npm start" -ForegroundColor Yellow
}

Write-Host "  ✓ Desktop shortcut created`n" -ForegroundColor Green

Write-Host "How to launch:" -ForegroundColor Cyan
Write-Host "  1. Double-click 'Local File Search Agent' on desktop" -ForegroundColor White

if ($BUILD_FAILED) {
    Write-Host "  2. Or run: cd frontend && npm start`n" -ForegroundColor White
}

Write-Host "`nBackend API: http://127.0.0.1:8765" -ForegroundColor Cyan
Write-Host "API Docs: http://127.0.0.1:8765/docs`n" -ForegroundColor Cyan

Write-Host "The desktop app will:" -ForegroundColor Cyan
Write-Host "  - Start backend server automatically" -ForegroundColor White
Write-Host "  - Connect to backend when ready" -ForegroundColor White
Write-Host "  - Run in system tray when minimized`n" -ForegroundColor White

Write-Host "============================================================`n" -ForegroundColor Green

pause
