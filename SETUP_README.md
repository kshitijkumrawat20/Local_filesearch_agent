# 🚀 Local File Search Agent - Quick Setup

This repository contains automated setup scripts to quickly install and run the Local File Search Agent on Windows.

## 📋 Prerequisites

- Windows 10 or later
- Internet connection
- PowerShell (for .ps1 script) or Command Prompt (for .bat script)
- API Key from either:
  - [Groq](https://console.groq.com/) (free tier available)
  - [OpenAI](https://platform.openai.com/) (paid service)

## 🏃‍♂️ Quick Start

### Option 1: PowerShell Script (Recommended)

1. **Download the setup script**:
   ```powershell
   Invoke-WebRequest -Uri "https://raw.githubusercontent.com/kshitijkumrawat20/Local_filesearch_agent/main/setup_agent.ps1" -OutFile "setup_agent.ps1"
   ```

2. **Set your API key** (choose one):
   ```powershell
   # For Groq (Free tier available)
   $env:GROQ_API_KEY = "your_groq_api_key_here"
   
   # OR for OpenAI
   $env:OPENAI_API_KEY = "your_openai_api_key_here"
   ```

3. **Run the setup script**:
   ```powershell
   .\setup_agent.ps1
   ```

### Option 2: Batch File

1. **Download the setup script**:
   ```cmd
   curl -o setup_agent.bat https://raw.githubusercontent.com/kshitijkumrawat20/Local_filesearch_agent/main/setup_agent.bat
   ```

2. **Set your API key** (choose one):
   ```cmd
   # For Groq
   set GROQ_API_KEY=your_groq_api_key_here
   
   # OR for OpenAI
   set OPENAI_API_KEY=your_openai_api_key_here
   ```

3. **Run the setup script**:
   ```cmd
   setup_agent.bat
   ```

## 🔧 What the Script Does

The setup script automatically:

1. ✅ **Installs uv package manager** - Fast Python package installer
2. ✅ **Downloads the repository** - Gets the latest version from GitHub
3. ✅ **Extracts the files** - Unpacks to `%USERPROFILE%\Local_filesearch_agent`
4. ✅ **Creates Python environment** - Uses Python 3.13 with uv
5. ✅ **Installs dependencies** - All required packages from pyproject.toml
6. ✅ **Launches Streamlit app** - Opens at http://localhost:8501

## 🌟 Features

- **🔍 File Search**: Find files and folders across your Windows system
- **🤖 AI Assistant**: Natural language queries to locate your files
- **📄 Document Search**: Search inside PDF, DOCX, XLSX, and text files using vector embeddings
- **🔧 Tool Integration**: File management and shell tools
- **💬 Chat Interface**: Interactive Streamlit web interface
- **🎯 Drive Detection**: Automatically detects available drives

## 🔑 API Keys

### Groq (Recommended - Free Tier)
1. Visit [Groq Console](https://console.groq.com/)
2. Create a free account
3. Generate an API key
4. Set: `$env:GROQ_API_KEY = "your_key"`

### OpenAI (Paid Service)
1. Visit [OpenAI Platform](https://platform.openai.com/)
2. Create an account and add billing
3. Generate an API key
4. Set: `$env:OPENAI_API_KEY = "your_key"`

## 📂 Installation Location

The application will be installed to:
```
%USERPROFILE%\Local_filesearch_agent\
```

## 🛠️ Manual Installation

If you prefer manual installation:

1. **Install uv**:
   ```powershell
   irm https://astral.sh/uv/install.ps1 | iex
   ```

2. **Clone repository**:
   ```bash
   git clone https://github.com/kshitijkumrawat20/Local_filesearch_agent.git
   cd Local_filesearch_agent
   ```

3. **Setup environment**:
   ```bash
   uv venv --python 3.13
   uv pip install -r pyproject.toml
   ```

4. **Run application**:
   ```bash
   uv run streamlit run app.py
   ```

## 🐛 Troubleshooting

### Common Issues:

**1. PowerShell Execution Policy**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**2. Missing API Key**
- Make sure to set either `GROQ_API_KEY` or `OPENAI_API_KEY` before running

**3. Port Already in Use**
- The app uses port 8501, make sure it's available

**4. Python Version Issues**
- The script installs Python 3.13 automatically with uv

### Getting Help:

- 📧 Open an issue on GitHub
- 💬 Check existing issues for solutions
- 📖 Review the documentation

## 🚀 Usage

Once running:

1. Open your browser to http://localhost:8501
2. Configure your search directory in the sidebar
3. Ask natural language questions like:
   - "Find all PDF files in my Documents folder"
   - "Search for files containing 'budget' in their name"
   - "Look for documents about machine learning"
   - "Open the latest Excel file in Downloads"

## 🎉 Enjoy!

You now have a powerful AI-powered file search assistant running locally on your Windows machine!