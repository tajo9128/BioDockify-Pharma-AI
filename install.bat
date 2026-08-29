@echo off
title BioDockify Pharma AI — Installer
echo.
echo  ====================================================
echo   BioDockify Pharma AI — One-Click Installer
echo  ====================================================
echo.
echo  This will download and start BioDockify Pharma AI.
echo  First-time download is ~18 GB (takes 10-30 minutes).
echo  After that, it starts in seconds.
echo.
echo  Prerequisites: Docker Desktop must be installed and running.
echo  Download it from: https://www.docker.com/products/docker-desktop/
echo.
pause

echo.
echo  [1/3] Checking Docker...
docker version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERROR: Docker is not running.
    echo  Please install Docker Desktop and start it first.
    echo  Download: https://www.docker.com/products/docker-desktop/
    echo.
    pause
    exit /b 1
)
echo  Docker is running.

echo.
echo  [2/3] Downloading BioDockify Pharma AI (this may take a while)...
docker pull tajo9128/biodockify-pharma-ai:latest
if errorlevel 1 (
    echo.
    echo  Docker Hub download failed. Trying GitHub mirror...
    docker pull ghcr.io/tajo9128/biodockify-pharma-ai:latest
    if errorlevel 1 (
        echo.
        echo  ERROR: Download failed from both sources.
        echo  Check your internet connection and try again.
        pause
        exit /b 1
    )
    docker tag ghcr.io/tajo9128/biodockify-pharma-ai:latest tajo9128/biodockify-pharma-ai:latest
)
echo  Download complete.

echo.
echo  [3/3] Starting BioDockify...
docker rm -f biodockify >nul 2>&1
docker run -d -p 80:80 -v biodockify_data:/a0/usr --name biodockify --restart unless-stopped tajo9128/biodockify-pharma-ai:latest
if errorlevel 1 (
    echo.
    echo  Port 80 might be in use. Trying port 8080...
    docker run -d -p 8080:80 -v biodockify_data:/a0/usr --name biodockify --restart unless-stopped tajo9128/biodockify-pharma-ai:latest
    if errorlevel 1 (
        echo  ERROR: Could not start. Check Docker Desktop for details.
        pause
        exit /b 1
    )
    echo.
    echo  ====================================================
    echo   BioDockify is running at: http://localhost:8080
    echo  ====================================================
    goto :done
)

echo.
echo  ====================================================
echo   BioDockify is running at: http://localhost
echo  ====================================================

:done
echo.
echo  Open the URL above in your browser (Chrome/Edge/Firefox).
echo  BioDockify will restart automatically when you reboot.
echo.
echo  To stop: open Docker Desktop, go to Containers, click Stop.
echo  To start again: click Play, or just run this script again.
echo.
start http://localhost
pause
