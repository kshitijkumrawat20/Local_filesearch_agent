# PowerShell script to automatically setup and run the Local File Search Agent
# This script will:
# 1. Install uv package manager
# 2. Download the repository
# 3. Extract it
# 4. Setup Python environment with uv
# 5. Install dependencies
# 6. Launch the Streamlit app

param(
    [string]$InstallDir = "$env:USERPROFILE\Local_filesearch_agent",
    [string]$RepoUrl = "https://github.com/kshitijkumrawat20/Local_filesearch_agent/archive/refs/heads/main.zip"
)

Write-Host "🚀 Local File Search Agent Setup Script" -ForegroundColor Green
Write-Host "=" * 50 -ForegroundColor Green

# Function to check if command exists
function Test-Command($cmdname) {
    return [bool](Get-Command -Name $cmdname -ErrorAction SilentlyContinue)
}

# Step 1: Install uv package manager
Write-Host "📦 Step 1: Installing uv package manager..." -ForegroundColor Yellow
if (Test-Command "uv") {
    Write-Host "✅ uv is already installed" -ForegroundColor Green
} else {
    try {
        Write-Host "Downloading and installing uv..." -ForegroundColor Cyan
        Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
        
        # Refresh PATH for current session
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
        
        Write-Host "✅ uv installed successfully" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Failed to install uv: $_" -ForegroundColor Red
        exit 1
    }
}

# Step 2: Create installation directory and download repository
Write-Host "📁 Step 2: Setting up project directory..." -ForegroundColor Yellow
try {
    # Remove existing directory if it exists
    if (Test-Path $InstallDir) {
        Write-Host "Removing existing directory: $InstallDir" -ForegroundColor Cyan
        Remove-Item -Path $InstallDir -Recurse -Force
    }
    
    # Create parent directory
    $parentDir = Split-Path $InstallDir -Parent
    if (!(Test-Path $parentDir)) {
        New-Item -ItemType Directory -Path $parentDir -Force | Out-Null
    }
    
    Write-Host "✅ Directory prepared: $InstallDir" -ForegroundColor Green
}
catch {
    Write-Host "❌ Failed to prepare directory: $_" -ForegroundColor Red
    exit 1
}

# Step 3: Download and extract repository
Write-Host "⬇️ Step 3: Downloading repository..." -ForegroundColor Yellow
try {
    $zipPath = "$env:TEMP\Local_filesearch_agent.zip"
    
    Write-Host "Downloading from: $RepoUrl" -ForegroundColor Cyan
    Invoke-WebRequest -Uri $RepoUrl -OutFile $zipPath -UseBasicParsing
    
    Write-Host "Extracting archive..." -ForegroundColor Cyan
    Expand-Archive -Path $zipPath -DestinationPath $env:TEMP -Force
    
    # Move extracted content to target directory
    $extractedPath = "$env:TEMP\Local_filesearch_agent-main"
    Move-Item -Path $extractedPath -Destination $InstallDir -Force
    
    # Clean up
    Remove-Item -Path $zipPath -Force
    
    Write-Host "✅ Repository downloaded and extracted" -ForegroundColor Green
}
catch {
    Write-Host "❌ Failed to download repository: $_" -ForegroundColor Red
    exit 1
}

# Step 4: Setup Python environment with uv
Write-Host "🐍 Step 4: Setting up Python environment..." -ForegroundColor Yellow
try {
    Set-Location $InstallDir
    
    Write-Host "Creating virtual environment with Python 3.13..." -ForegroundColor Cyan
    & uv venv --python 3.13
    
    Write-Host "✅ Virtual environment created" -ForegroundColor Green
}
catch {
    Write-Host "❌ Failed to create virtual environment: $_" -ForegroundColor Red
    exit 1
}

# Step 5: Install dependencies
Write-Host "📚 Step 5: Installing dependencies..." -ForegroundColor Yellow
try {
    Write-Host "Installing Python dependencies..." -ForegroundColor Cyan
    & uv pip install -r pyproject.toml
    
    Write-Host "✅ Dependencies installed successfully" -ForegroundColor Green
}
catch {
    Write-Host "❌ Failed to install dependencies: $_" -ForegroundColor Red
    exit 1
}

# Step 6: Setup environment variables
Write-Host "🔧 Step 6: Setting up environment..." -ForegroundColor Yellow
try {
    # Check for API keys
    $groqKey = $env:GROQ_API_KEY
    $openaiKey = $env:OPENAI_API_KEY
    
    if (!$groqKey -and !$openaiKey) {
        Write-Host "⚠️  Warning: No API keys found!" -ForegroundColor Yellow
        Write-Host "Please set either GROQ_API_KEY or OPENAI_API_KEY environment variable" -ForegroundColor Yellow
        Write-Host "Example: `$env:GROQ_API_KEY='your_api_key_here'" -ForegroundColor Cyan
    } else {
        Write-Host "✅ API keys configured" -ForegroundColor Green
    }
}
catch {
    Write-Host "⚠️  Warning: Could not verify API keys" -ForegroundColor Yellow
}

# Step 7: Launch the Streamlit app
Write-Host "🚀 Step 7: Launching Streamlit app..." -ForegroundColor Yellow
try {
    Write-Host "Starting the Local File Search Agent..." -ForegroundColor Cyan
    Write-Host "The app will open in your default browser at http://localhost:8501" -ForegroundColor Cyan
    Write-Host "Press Ctrl+C to stop the application" -ForegroundColor Cyan
    Write-Host "=" * 50 -ForegroundColor Green
    
    # Launch streamlit with uv
    & uv run streamlit run app.py --server.port 8501 --server.address localhost
}
catch {
    Write-Host "❌ Failed to launch Streamlit app: $_" -ForegroundColor Red
    Write-Host "You can manually run the app with: uv run streamlit run app.py" -ForegroundColor Yellow
    exit 1
}

Write-Host "🎉 Setup completed successfully!" -ForegroundColor Green