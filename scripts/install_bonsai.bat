@echo off
REM ============================================================================
REM  BioDockify AI Engine - Bonsai-8B local model installer (Windows)
REM ============================================================================
REM  Pharma research focus:
REM    - Private inference: no PHI/compound egress, no cloud dependency
REM    - Air-gapped labs: works after one-time download
REM    - Student laptops: Bonsai-8B is 1.15 GB, fits any GPU
REM
REM  Usage:
REM    scripts\install_bonsai.bat              normal install
REM    scripts\install_bonsai.bat --dry-run    preflight only
REM ============================================================================

setlocal EnableDelayedExpansion

set MODEL_FILE=Bonsai-8B-Q1_0.gguf
set MODEL_URL=https://huggingface.co/prism-ml/Bonsai-8B-gguf/resolve/main/Bonsai-8B-Q1_0.gguf
set VOLUME_NAME=biodockify_models
set SIDECAR_SERVICE=llama-server
set HEALTH_URL=http://localhost:8081/health
set COMPOSE_FILE=docker-compose.yml
set DRY_RUN=0

if /i "%~1"=="--dry-run" set DRY_RUN=1

echo.
echo [biodockify] BioDockify AI Engine - local model installer
echo [biodockify] Model: bonsai-8b (%MODEL_FILE%, ~1.15 GB)
echo.

REM --- preflight: docker ---
where docker >nul 2>&1
if errorlevel 1 (
    echo [err] Docker CLI not found. Install Docker Desktop first.
    exit /b 1
)
docker info >nul 2>&1
if errorlevel 1 (
    echo [err] Docker daemon not running. Start Docker Desktop and retry.
    exit /b 1
)
echo [ok] Docker daemon reachable

REM --- hardware probe (basic, Windows) ---
powershell -NoProfile -Command "$ram = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB); Write-Host ('[ok] Host RAM: ' + $ram + ' GB'); if ($ram -lt 6) { Write-Host '[warn] Below 6GB minimum for Bonsai-8B' }"

powershell -NoProfile -Command "$gpu = (Get-CimInstance Win32_VideoController).Name -join ', '; if ($gpu -match 'NVIDIA') { Write-Host '[ok] NVIDIA GPU detected' } else { Write-Host '[warn] No NVIDIA GPU detected - sidecar will use CPU' }"

if "%DRY_RUN%"=="1" (
    echo [biodockify] Dry-run requested - preflight complete, no download started.
    exit /b 0
)

REM --- verify compose file ---
if not exist "%COMPOSE_FILE%" (
    echo [err] Compose file '%COMPOSE_FILE%' not found. Run from repo root.
    exit /b 1
)

REM --- ensure volume exists ---
docker volume inspect %VOLUME_NAME% >nul 2>&1
if errorlevel 1 (
    echo [biodockify] Creating Docker volume %VOLUME_NAME%
    docker volume create %VOLUME_NAME% >nul
)
echo [ok] Volume %VOLUME_NAME% ready

REM --- check if model already downloaded ---
set MODEL_PRESENT=no
for /f "delims=" %%i in ('docker run --rm -v %VOLUME_NAME%:/models alpine:3.20 sh -c "if [ -f /models/%MODEL_FILE% ]; then echo yes; else echo no; fi" 2^>nul') do set MODEL_PRESENT=%%i

if "%MODEL_PRESENT%"=="yes" (
    echo [ok] Model %MODEL_FILE% already present in %VOLUME_NAME% ^(skip download^)
) else (
    echo [biodockify] Downloading %MODEL_FILE% (~1.15 GB^) from HuggingFace
    echo [biodockify] into volume %VOLUME_NAME% (one-time, no re-download on image updates^)
    docker run --rm -v %VOLUME_NAME%:/models alpine:3.20 ^
        sh -c "apk add --no-cache curl >/dev/null 2>&1 && curl -L --fail --progress-bar -o /models/%MODEL_FILE% %MODEL_URL% && ls -la /models/%MODEL_FILE%"
    if errorlevel 1 (
        echo [err] Download failed. Check your internet connection and retry.
        exit /b 1
    )
    echo [ok] Download complete
)

REM --- bring up sidecar ---
echo [biodockify] Starting llama-server sidecar (profile local-llm^)
docker compose --profile local-llm up -d %SIDECAR_SERVICE% >nul 2>&1
if errorlevel 1 (
    echo [err] Failed to start sidecar. Try manually:
    echo [err]   docker compose --profile local-llm up -d %SIDECAR_SERVICE%
    exit /b 1
)
echo [ok] Sidecar starting

REM --- wait for health ---
echo [biodockify] Waiting for sidecar /health (max 90s^)...
set /a COUNT=0
:waitloop
powershell -NoProfile -Command "try { (Invoke-WebRequest -Uri '%HEALTH_URL%' -UseBasicParsing -TimeoutSec 2).StatusCode | Out-Null; exit 0 } catch { exit 1 }"
if not errorlevel 1 goto :healthy
set /a COUNT+=1
if !COUNT! geq 90 (
    echo [warn] Sidecar not healthy after 90s. Check: docker compose logs %SIDECAR_SERVICE%
    goto :finalmsg
)
timeout /t 1 /nobreak >nul
goto :waitloop

:healthy
echo [ok] Sidecar healthy at %HEALTH_URL%

:finalmsg
echo.
echo ============================================================
echo  Bonsai-8B is ready. Final step:
echo    1. Open BioDockify in your browser (http://localhost^)
echo    2. Go to Settings -^> Models
echo    3. In the preset switcher choose:
echo         "BioDockify AI Engine - Local (Bonsai-8B^)"
echo    4. Send a test message.
echo.
echo  Pharma use cases unlocked:
echo    - Private literature synthesis (no egress^)
echo    - Offline claim verification
echo    - Air-gapped ICH/CONSORT compliance checks
echo ============================================================
endlocal
