@echo off
REM ============================================
REM INSPIRE Scraper - All-in-One Launcher
REM ============================================
REM This script will:
REM 1. Check if Python is installed
REM 2. Install Python if needed (with user consent)
REM 3. Install all required dependencies
REM 4. Start the application
REM 5. Open browser automatically
REM ============================================

TITLE INSPIRE Scraper - Setup and Launch

echo.
echo ========================================
echo   INSPIRE Contact Details Scraper
echo   All-in-One Setup ^& Launcher
echo ========================================
echo.

REM ============================================
REM Step 1: Check Python Installation
REM ============================================

echo [Step 1/4] Checking Python installation...
echo.

set "PYTHON_CMD="

REM Try to detect Python command
where python >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python"
    goto :PYTHON_FOUND
)

where py >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=py"
    goto :PYTHON_FOUND
)

where python3 >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python3"
    goto :PYTHON_FOUND
)

:PYTHON_check_fail
if "%PYTHON_CMD%"=="" (
    echo [ERROR] Python is not installed or not in PATH!
    echo.
    echo Python 3.9+ is required to run this application.
    echo.
    echo Would you like to:
    echo   1. Install Python automatically (requires internet)
    echo   2. Open Python download page in browser
    echo   3. Exit and install manually
    echo.
    choice /c 123 /n /m "Select option (1, 2, or 3): "
    
    if errorlevel 3 (
        echo.
        echo Please install Python 3.9+ from: https://www.python.org/downloads/
        echo.
        echo IMPORTANT: During installation, check "Add Python to PATH"
        echo.
        pause
        exit /b 1
    )
    
    if errorlevel 2 (
        echo.
        echo Opening Python download page...
        start https://www.python.org/downloads/
        echo.
        echo After installing Python:
        echo 1. Make sure to check "Add Python to PATH" during installation
        echo 2. Restart this batch file
        echo.
        pause
        exit /b 1
    )
    
    if errorlevel 1 (
        echo.
        echo Installing Python via winget...
        echo This may take a few minutes...
        echo.
        winget install Python.Python.3.12
        
        if %errorlevel% neq 0 (
            echo.
            echo [ERROR] Automatic installation failed.
            echo Please install Python manually from: https://www.python.org/downloads/
            echo.
            pause
            exit /b 1
        )
        
        echo.
        echo Python installed! Please close and reopen this file.
        echo.
        pause
        exit /b 0
    )
)

:PYTHON_FOUND
echo [OK] Python is installed using command: %PYTHON_CMD%
%PYTHON_CMD% --version
echo.


REM ============================================
REM Step 2: Check pip installation
REM ============================================

echo [Step 2/4] Checking pip (Python package manager)...
echo.

%PYTHON_CMD% -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] pip not found. Installing pip...
    %PYTHON_CMD% -m ensurepip --default-pip
    %PYTHON_CMD% -m pip install --upgrade pip
)

echo [OK] pip is ready
echo.

REM ============================================
REM Step 3: Install Dependencies
REM ============================================

echo [Step 3/4] Installing required packages...
echo.
echo This may take a few minutes on first run...
echo.

if not exist "requirements.txt" (
    echo [ERROR] requirements.txt not found!
    echo Please make sure you're running this from the correct folder.
    pause
    exit /b 1
)

echo Installing dependencies from requirements.txt...
%PYTHON_CMD% -m pip install -r requirements.txt --quiet --disable-pip-version-check

if %errorlevel% neq 0 (
    echo.
    echo [WARNING] Some packages may have failed to install.
    echo Trying again with verbose output...
    %PYTHON_CMD% -m pip install -r requirements.txt
    echo.
)

echo.
echo [OK] All dependencies installed!
echo.

REM ============================================
REM Step 4: Create output folder
REM ============================================

if not exist "output" (
    echo Creating output folder...
    mkdir output
    echo [OK] Output folder created
    echo.
)

REM ============================================
REM Step 5: Check if already running
REM ============================================

echo [Step 4/4] Starting application...
echo.

netstat -ano | findstr ":5000" | findstr "LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    echo [WARNING] Port 5000 is already in use!
    echo Another instance might be running.
    echo.
    choice /c YN /n /m "Do you want to stop it and restart? (Y/N): "
    
    if errorlevel 2 (
        echo.
        echo Opening browser to existing instance...
        timeout /t 2 /nobreak >nul
        start http://localhost:5000
        exit /b 0
    )
    
    if errorlevel 1 (
        echo Stopping existing instance...
        for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000" ^| findstr "LISTENING"') do (
            taskkill /F /PID %%a >nul 2>&1
        )
        timeout /t 2 /nobreak >nul
    )
)

REM ============================================
REM Step 6: Launch Application
REM ============================================

echo.
echo ========================================
echo   Starting INSPIRE Scraper...
echo ========================================
echo.
echo Application will start in a moment...
echo Browser will open automatically at:
echo   http://localhost:5000
echo.
echo To stop the application, close this window
echo or press Ctrl+C
echo.
echo ========================================
echo.

REM Open browser after 4 seconds
start "" cmd /c "timeout /t 4 /nobreak >nul && start http://localhost:5000"

REM Start the Flask application
%PYTHON_CMD% app.py

REM If app exits, show message
echo.
echo ========================================
echo Application has stopped.
echo ========================================
echo.
pause
