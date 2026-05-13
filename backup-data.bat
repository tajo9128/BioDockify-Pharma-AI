@echo off
REM BioDockify Pharma AI — Backup User Data to Desktop
REM ====================================================
REM This creates a timestamped backup of ALL research data:
REM   - Memory (FAISS vector database)
REM   - Chat history
REM   - Settings and secrets
REM   - Knowledge base
REM   - Projects
REM   - User plugins and skills
REM   - Workdir files
REM
REM Backup is saved to: %USERPROFILE%\Desktop\BioDockify-Backups\
REM
REM To restore:
REM   1. Stop the container: docker compose down
REM   2. Restore the volume data
REM   3. Restart: docker compose up -d

set BACKUP_DIR=%USERPROFILE%\Desktop\BioDockify-Backups
set TIMESTAMP=%DATE:~10,4%%DATE:~4,2%%DATE:~7,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set BACKUP_FILE=%BACKUP_DIR%\biodockify-backup-%TIMESTAMP%.zip

echo.
echo [BioDockify Pharma AI] Backup Tool
echo ==================================
echo.
echo Backup destination: %BACKUP_DIR%
echo.

REM Create backup directory if it doesn't exist
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

REM Check if container is running
docker inspect biodockify-pharma-ai >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Container 'biodockify-pharma-ai' is not running.
    echo Starting container first...
    docker compose up -d
    echo Waiting 10 seconds for startup...
    timeout /t 10 /nobreak >nul
)

echo [1/3] Creating backup archive inside container...
docker exec biodockify-pharma-ai sh -c "cd /a0 && tar czf /tmp/biodockify-backup.tar.gz usr/"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create backup inside container.
    pause
    exit /b 1
)

echo [2/3] Copying backup to desktop...
docker cp biodockify-pharma-ai:/tmp/biodockify-backup.tar.gz "%BACKUP_FILE:.zip=.tar.gz%"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to copy backup.
    pause
    exit /b 1
)

echo [3/3] Cleaning up temporary files...
docker exec biodockify-pharma-ai rm -f /tmp/biodockify-backup.tar.gz

echo.
echo [SUCCESS] Backup saved to:
echo   %BACKUP_FILE:.zip=.tar.gz%
echo.
echo File size:
dir "%BACKUP_FILE:.zip=.tar.gz%" | find "File(s)"
echo.
echo Your research data (memory, chats, knowledge, projects) is now safe on your desktop.
echo Keep this backup file in a safe location.
echo.

pause
