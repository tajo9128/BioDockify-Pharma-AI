@echo off
REM BioDockify Pharma AI — Backup Volume to Desktop (Windows)
REM ==========================================================
REM This backs up the ENTIRE Docker volume containing all research data:
REM   - Memory (FAISS vector database)
REM   - Chat history
REM   - Settings and secrets
REM   - Knowledge base
REM   - Projects
REM   - User plugins, skills, workdir files
REM   - Backups created via the in-app Backup panel
REM
REM Backup is saved to: %USERPROFILE%\Desktop\BioDockify-Backups\
REM
REM To restore this backup later:
REM   docker run --rm -v biodockify_pharma_usr:/volume -v %CD%:/backup alpine sh -c "rm -rf /volume/* && tar xzf /backup/biodockify-backup-XXXXXXXX.tar.gz -C /volume"

set BACKUP_DIR=%USERPROFILE%\Desktop\BioDockify-Backups
set TIMESTAMP=%DATE:~10,4%%DATE:~4,2%%DATE:~7,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set BACKUP_FILE=%BACKUP_DIR%\biodockify-volume-backup-%TIMESTAMP%.tar.gz

echo.
echo [BioDockify Pharma AI] Volume Backup Tool
echo ==========================================
echo.
echo Backup destination: %BACKUP_DIR%
echo.

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

echo [1/3] Creating backup from Docker volume...
docker run --rm -v biodockify_pharma_usr:/volume -v "%BACKUP_DIR%:/backup" alpine tar czf "/backup/biodockify-volume-backup-%TIMESTAMP%.tar.gz" -C /volume . 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create backup. Make sure the container exists and the volume 'biodockify_pharma_usr' is present.
    echo.
    echo Check available volumes: docker volume ls
    pause
    exit /b 1
)

echo [2/3] Verifying backup file...
if exist "%BACKUP_FILE%" (
    for %%F in ("%BACKUP_FILE%") do echo File size: %%~zF bytes
) else (
    echo [ERROR] Backup file not found.
    pause
    exit /b 1
)

echo [3/3] Done!
echo.
echo [SUCCESS] Backup saved to:
echo   %BACKUP_FILE%
echo.
echo Your ENTIRE research data (memory, chats, knowledge, projects, backups) is now safe.
echo This file includes: memory DB, chat history, settings, knowledge base, projects.
echo.
echo === How to restore ===
echo To restore this backup to a new container:
echo   1. docker compose down
echo   2. docker volume rm biodockify_pharma_usr
echo   3. docker run --rm -v biodockify_pharma_usr:/volume -v "%CD%:/backup" alpine sh -c "rm -rf /volume/* ^&^& tar xzf /backup/biodockify-volume-backup-%TIMESTAMP%.tar.gz -C /volume"
echo   4. docker compose up -d
echo.
echo Or restore from a different backup file:
echo   docker run --rm -v biodockify_pharma_usr:/volume -v "%CD%:/backup" alpine sh -c "rm -rf /volume/* ^&^& tar xzf /backup/YOUR_BACKUP_FILE.tar.gz -C /volume"
echo.

pause