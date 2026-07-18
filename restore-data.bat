@echo off
REM BioDockify Pharma AI — Restore from PC (Windows)
REM =================================================
REM Restores research data from a backup folder to the Docker container.
REM
REM Usage:
REM   1. Run this script, OR
REM   2. Use the in-app "Backup & Recovery" panel → "Restore from PC"
REM
REM This script restores the three data locations:
REM   - /a0/usr       (workspace, chats, projects)
REM   - /a0/.a0proj   (agent memory, instructions)
REM   - /a0/data      (knowledge base)

setlocal
set CONTAINER=biodockify
set BACKUP_DIR=%USERPROFILE%\Desktop\BioDockify-Backups

echo.
echo [BioDockify Pharma AI] Restore Tool
echo ====================================
echo.

REM Check container is running
docker ps --format "{{.Names}}" | findstr /C:"%CONTAINER%" >nul
if %errorlevel% neq 0 (
    echo [ERROR] Container '%CONTAINER%' is not running.
    echo Start it first:  docker start %CONTAINER%
    pause
    exit /b 1
)

if not exist "%BACKUP_DIR%" (
    echo [ERROR] No backup folder found at: %BACKUP_DIR%
    echo Run backup-data.bat first to create a backup.
    pause
    exit /b 1
)

echo Available backups in %BACKUP_DIR%:
echo.
dir /b /ad "%BACKUP_DIR%\*" 2>nul
echo.
set /p FOLDER="Type the backup folder name to restore (e.g. usr-20260718_101800): "
if "%FOLDER%"=="" (
    echo No folder selected. Exiting.
    pause
    exit /b 1
)

set SRC=%BACKUP_DIR%\%FOLDER%
if not exist "%SRC%" (
    echo [ERROR] Folder not found: %SRC%
    pause
    exit /b 1
)

echo.
echo Restoring from: %SRC%
echo.

REM Detect what type of backup it is by folder prefix
echo %FOLDER% | findstr /B "usr-" >nul && (
    echo [1/1] Restoring workspace to /a0/usr...
    docker cp "%SRC%/." %CONTAINER%:/a0/usr/
    goto :done
)
echo %FOLDER% | findstr /B "a0proj-" >nul && (
    echo [1/1] Restoring agent memory to /a0/.a0proj...
    docker cp "%SRC%/." %CONTAINER%:/a0/.a0proj/
    goto :done
)
echo %FOLDER% | findstr /B "data-" >nul && (
    echo [1/1] Restoring knowledge base to /a0/data...
    docker cp "%SRC%/." %CONTAINER%:/a0/data/
    goto :done
)

echo [ERROR] Could not detect backup type from folder name.
echo Folder should start with 'usr-', 'a0proj-', or 'data-'.
pause
exit /b 1

:done
echo.
echo ============================================
echo [SUCCESS] Restore complete!
echo ============================================
echo.
echo Restart the container to apply changes:
echo   docker restart %CONTAINER%
echo.
pause
endlocal
