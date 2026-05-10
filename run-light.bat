@echo off
setlocal

:: BioDockify AI - One-Click Launcher
:: Version 3.7.0 (Lightweight)

echo ========================================================
echo   BioDockify AI - Pharma Research Assistant
echo   Version: 3.7.0 (Lightweight)
echo ========================================================
echo.

:: 1. Stop existing containers
echo [INFO] Cleaning up...
docker stop biodockify-ai >nul 2>&1
docker rm biodockify-ai >nul 2>&1
echo [OK] Clean complete.

:: 2. Check Docker
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is NOT running!
    echo Please start Docker Desktop.
    pause
    exit /b 1
)
echo [OK] Docker is running.

:: 3. Check Ollama (optional)
curl -s http://localhost:11434 >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Ollama detected on localhost:11434
) else (
    echo [INFO] Ollama not running (optional - install from ollama.ai)
)

:: 4. Run container
echo [INFO] Starting BioDockify AI...
docker run -d ^
  --name biodockify-ai ^
  -p 3000:3000 ^
  -e PORT=3000 ^
  -e OLLAMA_URL=http://host.docker.internal:11434 ^
  -e DEFAULT_PROVIDER=ollama ^
  --extra-hosts "host.docker.internal:host-gateway" ^
  tajo9128/biodockify-ai:latest

if %errorlevel% neq 0 (
    echo [ERROR] Failed to start container.
    pause
    exit /b 1
)

echo.
echo ========================================================
echo [SUCCESS] BioDockify AI is running!
echo.
echo   Open http://localhost:3000
echo.
echo   Features:
echo   - Chat with 11 AI providers
echo   - Literature Search (PubMed, arXiv)
echo   - Knowledge Base with file upload
echo   - PhD Journey tracking
echo   - Skills system
echo ========================================================

:: Open browser
timeout /t 2
start http://localhost:3000
pause