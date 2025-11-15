@echo off
echo.
echo ============================================================
echo   Local Agent - Frontend Update Script
echo   Pull Latest Code and Rebuild Electron App
echo ============================================================
echo.

REM Set variables
set INSTALL_DIR=%CD%\Local_filesearch_agent
set REPO_URL=https://github.com/kshitijkumrawat20/Local_filesearch_agent/archive/refs/heads/main.zip
set ZIP_FILE=%TEMP%\Local_filesearch_agent_update.zip

echo Step 1: Downloading latest code from GitHub...
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
echo Step 2: Extracting and updating frontend files...
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

cd /d "%INSTALL_DIR%\frontend"

REM Update frontend source files (preserve node_modules and dist)
echo Updating frontend files...

REM Copy HTML/CSS/JS files
if exist "%TEMP_EXTRACT%\Local_filesearch_agent-main\frontend\index.html" (
    copy "%TEMP_EXTRACT%\Local_filesearch_agent-main\frontend\index.html" "index.html" /Y >nul
    echo Updated index.html
) else if exist "%TEMP_EXTRACT%\Local_filesearch_agent-main\index.html" (
    copy "%TEMP_EXTRACT%\Local_filesearch_agent-main\index.html" "index.html" /Y >nul
    echo Updated index.html
)

if exist "%TEMP_EXTRACT%\Local_filesearch_agent-main\frontend\styles.css" (
    copy "%TEMP_EXTRACT%\Local_filesearch_agent-main\frontend\styles.css" "styles.css" /Y >nul
    echo Updated styles.css
) else if exist "%TEMP_EXTRACT%\Local_filesearch_agent-main\styles.css" (
    copy "%TEMP_EXTRACT%\Local_filesearch_agent-main\styles.css" "styles.css" /Y >nul
    echo Updated styles.css
)

if exist "%TEMP_EXTRACT%\Local_filesearch_agent-main\frontend\app.js" (
    copy "%TEMP_EXTRACT%\Local_filesearch_agent-main\frontend\app.js" "app.js" /Y >nul
    echo Updated app.js
) else if exist "%TEMP_EXTRACT%\Local_filesearch_agent-main\app.js" (
    copy "%TEMP_EXTRACT%\Local_filesearch_agent-main\app.js" "app.js" /Y >nul
    echo Updated app.js
)

REM Copy electron-main.js if exists
if exist "%TEMP_EXTRACT%\Local_filesearch_agent-main\frontend\electron-main.js" (
    copy "%TEMP_EXTRACT%\Local_filesearch_agent-main\frontend\electron-main.js" "electron-main.js" /Y >nul
    echo Updated electron-main.js
)

REM Copy package.json if exists (but preserve existing one as fallback)
if exist "%TEMP_EXTRACT%\Local_filesearch_agent-main\frontend\package.json" (
    copy "%TEMP_EXTRACT%\Local_filesearch_agent-main\frontend\package.json" "package.json" /Y >nul
    echo Updated package.json
)

REM Cleanup
del "%ZIP_FILE%" >nul 2>&1
rmdir /s /q "%TEMP_EXTRACT%" >nul 2>&1

echo Frontend files updated successfully!

echo.
echo Step 3: Installing/updating npm dependencies...
echo ----------------------------------------

echo Checking for new npm packages...
call npm install

if %ERRORLEVEL% NEQ 0 (
    echo Warning: npm install encountered errors
    echo You may need to run 'npm install' manually
    pause
)

echo.
echo Step 4: Building Electron application...
echo ----------------------------------------

echo Cleaning old build...
if exist "dist" (
    rmdir /s /q "dist"
    echo Old build removed
)

echo Building new portable executable...
call npm run dist

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ============================================================
    echo   Build Failed!
    echo ============================================================
    echo.
    echo The Electron build encountered errors.
    echo You can still run the app with: npm start
    echo.
    echo ============================================================
    pause
    exit /b 1
)

echo.
echo Step 5: Updating desktop shortcut...
echo ----------------------------------------

cd ..

REM Update desktop shortcut to new exe
if exist "frontend\dist\LocalAgent.exe" (
    echo Updating desktop shortcut...
    powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\Local Agent.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\frontend\dist\LocalAgent.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Description = 'AI-powered local agent'; $Shortcut.Save()"
    echo Desktop shortcut updated!
)

echo.
echo ============================================================
echo   Frontend Update Complete! ✓
echo ============================================================
echo.
echo What was updated:
echo   [✓] HTML, CSS, JavaScript files
echo   [✓] Electron main process (electron-main.js)
echo   [✓] npm dependencies
echo   [✓] Portable executable rebuilt
echo   [✓] Desktop shortcut updated
echo.
echo What was preserved:
echo   [✓] node_modules (reinstalled if needed)
echo   [✓] Backend files (Python code, API server)
echo   [✓] Indexed documents (chroma_db/)
echo   [✓] File metadata (file_metadata.json)
echo   [✓] Environment variables (.env)
echo.
echo Launch the updated app:
echo   - Double-click "LEKHA" on desktop
echo   - Or run: cd frontend ^&^& npm start
echo.
echo ============================================================
pause
