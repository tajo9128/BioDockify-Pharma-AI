@echo off
REM BioDockify Pharma AI — Desktop Quick Start (Windows)
REM ====================================================
REM This starts the container using a persistent Docker volume.
REM ALL data (memory, chats, settings, knowledge, projects) survives container deletion.
REM
REM Prerequisites:
REM   - Docker Desktop installed and running
REM   - Internet connection (first run pulls the image)
REM
REM Usage:
REM   Double-click this file or run: run.bat
REM
REM After starting, open: http://localhost:3000

echo.
echo [BioDockify Pharma AI] Starting container...
echo.

docker compose up -d

if %errorlevel% equ 0 (
    echo.
    echo [OK] Container started successfully!
    echo.
    echo Open http://localhost:3000 in your browser.
    echo.
    echo To stop: docker compose down
    echo To view logs: docker compose logs -f
    echo To backup data: run backup-data.bat
) else (
    echo.
    echo [ERROR] Failed to start container.
    echo Make sure Docker Desktop is running.
)

pause
