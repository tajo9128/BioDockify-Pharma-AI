@echo off
:: BioDockify AI - Docker Desktop Launcher
:: ========================================
echo.
echo ========================================================
echo   BioDockify AI - Pharma Research Assistant
echo   Docker Desktop Version
echo ========================================================
echo.

:: Check Docker
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is NOT running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)
echo [OK] Docker is running.

:: Stop old container
docker stop biodockify-ai >nul 2>&1
docker rm biodockify-ai >nul 2>&1
echo [OK] Cleaned up old container.

:: Create data folder if not exists
if not exist "data" mkdir data

:: Run container
echo [INFO] Starting BioDockify AI...
docker run -d ^
  --name biodockify-ai ^
  -p 3000:3000 ^
  -v "%~dp0data:/app/data" ^
  -e OLLAMA_URL=http://host.docker.internal:11434 ^
  -e PORT=3000 ^
  -e NODE_ENV=production ^
  -e DEFAULT_PROVIDER=ollama ^
  --extra-hosts "host.docker.internal:host-gateway" ^
  tajo9128/biodockify-ai:latest

if %errorlevel% neq 0 (
    echo [ERROR] Failed to start!
    pause
    exit /b 1
)

echo.
echo ========================================================
echo [SUCCESS] BioDockify AI is running!
echo.
echo   Open: http://localhost:3000
echo.
echo   Data saved in: .\data\
echo   Logs: docker logs biodockify-ai
echo ========================================================
echo.

:: Open browser
timeout /t 2 >nul
start http://localhost:3000

pause