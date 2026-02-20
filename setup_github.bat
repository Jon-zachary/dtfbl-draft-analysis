@echo off
REM Quick GitHub Setup Script for Windows
REM Run this after creating your repo on GitHub

echo ================================================
echo DTFBL Draft Analysis - GitHub Setup
echo ================================================
echo.

REM Check if git is installed
git --version >nul 2>&1
if errorlevel 1 (
    echo X Git is not installed. 
    echo   Download from: https://git-scm.com/download/win
    pause
    exit /b 1
)

echo [OK] Git is installed
echo.

echo Step 1: Create a new repo on GitHub.com
echo   Go to: https://github.com/new
echo   Name: dtfbl-draft-analysis
echo   Make it: Private (to keep your draft data secret!)
echo   Do NOT initialize with README
echo.

set /p REPO_URL="Enter your GitHub repo URL: "

if "%REPO_URL%"=="" (
    echo X No URL provided. Exiting.
    pause
    exit /b 1
)

echo.
echo Step 2: Setting up local git repo...

REM Initialize git repo if not already
if not exist .git (
    git init
    echo [OK] Initialized git repo
) else (
    echo [OK] Git repo already initialized
)

REM Add all files
git add .

REM Create initial commit
git commit -m "Initial commit: 16 years of DTFBL draft analysis + mock auction simulator"

echo [OK] Created initial commit
echo.

REM Add remote
git remote add origin "%REPO_URL%" 2>nul
if errorlevel 1 (
    git remote set-url origin "%REPO_URL%"
)
echo [OK] Added remote: %REPO_URL%
echo.

REM Push to GitHub
echo Step 3: Pushing to GitHub...
echo (You may be prompted for your GitHub username/password or token)
echo.

git branch -M main
git push -u origin main

if errorlevel 0 (
    echo.
    echo ================================================
    echo [SUCCESS]
    echo ================================================
    echo.
    echo Your draft analysis is now on GitHub!
    echo.
    set REPO_VIEW=%REPO_URL:.git=%
    echo View it at: %REPO_VIEW%
    echo.
) else (
    echo.
    echo X Push failed. Common issues:
    echo.
    echo Authentication problems?
    echo   - Use a Personal Access Token instead of password
    echo   - Create one at: https://github.com/settings/tokens
    echo   - Use token as password when prompted
    echo.
)

pause
