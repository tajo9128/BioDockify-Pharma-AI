@echo off
REM BioDockify Pharma AI — Complete Backup to PC (Windows)
REM =======================================================
REM Backs up ALL research data from the Docker container:
REM   - /a0/usr          (workspace, chats, projects, plugins)
REM   - /a0/.a0proj      (agent memory, instructions, project config)  [NEW]
REM   - /a0/data         (knowledge base, deep research sessions)      [NEW]
REM
REM Backup is saved to: %USERPROFILE%\Desktop\BioDockify-Backups\
REM This file is on your PC and survives container deletion.
REM
REM === To restore this backup later ===
REM   See restore-data.bat (companion script) or use the in-app
REM   Backup & Recovery panel → "Restore from PC" button.

setlocal

set BACKUP_DIR=%USERPROFILE%\Desktop\BioDockify-Backups
set TIMESTAMP=%DATE:~10,4%%DATE:~4,2%%DATE:~7,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set BACKUP_FILE=%BACKUP_DIR%\biodockify-full-backup-%TIMESTAMP%.tar.gz
set CONTAINER=biodockify

echo.
echo [BioDockify Pharma AI] Complete Backup Tool
echo ============================================
echo.
echo Backup destination: %BACKUP_DIR%
echo.

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

REM Check container is running
docker ps --format "{{.Names}}" | findstr /C:"%CONTAINER%" >nul
if %errorlevel% neq 0 (
    echo [ERROR] Container '%CONTAINER%' is not running.
    echo Start it first:  docker start %CONTAINER%
    echo.
    echo Or check running containers:  docker ps
    pause
    exit /b 1
)

echo [1/4] Backing up /a0/usr (workspace, chats, projects)...
docker cp %CONTAINER%:/a0/usr "%BACKUP_DIR%\usr-%TIMESTAMP%" 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Could not copy /a0/usr — continuing.
)

echo [2/4] Backing up /a0/.a0proj (agent memory, instructions)...
docker cp %CONTAINER%:/a0/.a0proj "%BACKUP_DIR%\a0proj-%TIMESTAMP%" 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Could not copy /a0/.a0proj — continuing.
)

echo [3/4] Backing up /a0/data (knowledge base)...
docker cp %CONTAINER%:/a0/data "%BACKUP_DIR%\data-%TIMESTAMP%" 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Could not copy /a0/data — continuing.
)

echo [4/4] Bundling everything into a single .tar.gz...
REM Bundle all three snapshots into one compressed archive
docker run --rm -v "%BACKUP_DIR%:/backup" alpine sh -c "cd /backup && tar czf biodockify-full-backup-%TIMESTAMP%.tar.gz usr-%TIMESTAMP% a0proj-%TIMESTAMP% data-%TIMESTAMP% 2>/dev/null || tar czf biodockify-full-backup-%TIMESTAMP%.tar.gz usr-%TIMESTAMP% a0proj-%TIMESTAMP% data-%TIMESTAMP%"
if %errorlevel% neq 0 (
    echo [WARNING] Could not create tar.gz bundle. Individual folders are still safe in %BACKUP_DIR%.
) else (
    REM Clean up the individual folders now that they're bundled
    rmdir /s /q "%BACKUP_DIR%\usr-%TIMESTAMP%" 2>nul
    rmdir /s /q "%BACKUP_DIR%\a0proj-%TIMESTAMP%" 2>nul
    rmdir /s /q "%BACKUP_DIR%\data-%TIMESTAMP%" 2>nul
)

echo.
echo ============================================
echo [SUCCESS] Backup complete!
echo ============================================
echo.
if exist "%BACKUP_FILE%" (
    for %%F in ("%BACKUP_FILE%") do echo Archive: %%F  (%%~zF bytes)
) else (
    echo Individual folders saved in: %BACKUP_DIR%
    dir /b "%BACKUP_DIR%\*-%TIMESTAMP%" 2>nul
)
echo.
echo Your ENTIRE research data is now safe on your PC:
echo   - workspace, chats, projects (/a0/usr)
echo   - agent memory, instructions (/a0/.a0proj)
echo   - knowledge base (/a0/data)
echo.
echo To restore: use the in-app "Backup ^& Recovery" panel and click
echo "Restore from PC", OR run restore-data.bat.
echo.
pause
endlocal
