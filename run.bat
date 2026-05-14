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
REM
REM To stop:    docker compose down
REM To update:  docker compose pull && docker compose up -d
REM To backup:  run backup-data.bat

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
    echo ===== Useful Commands =====
    echo To stop:           docker compose down
    echo To view logs:      docker compose logs -f
    echo To backup data:    backup-data.bat
    echo To backup volume:  docker run --rm -v biodockify_pharma_usr:/volume -v %CD%:/backup alpine tar czf /backup/biodockify-backup.tar.gz -C /volume .
    echo To restore volume: docker run --rm -v biodockify_pharma_usr:/volume -v %CD%:/backup alpine sh -c "rm -rf /volume/* ^&^& tar xzf /backup/biodockify-backup.tar.gz -C /volume"
    echo.
) else (
    echo.
    echo [ERROR] Failed to start container.
    echo Make sure Docker Desktop is running.
)

pause