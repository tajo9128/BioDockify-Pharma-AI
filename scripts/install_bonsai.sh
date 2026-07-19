#!/usr/bin/env bash
# BioDockify AI Engine — Bonsai-8B local model installer (Linux / macOS)
# =============================================================================
#
# Pharma research focus:
#   - Private inference: no PHI/compound egress, no cloud dependency
#   - Air-gapped labs: works after one-time download
#   - Student laptops: Bonsai-8B is 1.15 GB, fits any GPU
#
# What this script does:
#   1. Verifies Docker daemon is running and the biodockify compose project exists
#   2. Detects host RAM + GPU (CPU/CUDA/Apple Silicon)
#   3. Downloads Bonsai-8B-Q1_0.gguf into the `biodockify_models` named volume
#      via a one-shot alpine container (no curl needed on host)
#      NOTE: filename is case-sensitive (capital B). Lowercase URLs 404 on HF.
#   4. Brings up the llama-server sidecar with the local-llm profile
#   5. Polls the sidecar /health endpoint until ready
#
# What this script does NOT do:
#   - Modify the BioDockify image (the model lives in a volume)
#   - Modify Agent Zero
#   - Auto-select the preset in the UI (you do that in Settings → Models)
#
# Usage:
#   bash scripts/install_bonsai.sh            # normal install
#   bash scripts/install_bonsai.sh --dry-run  # preflight only, no download
#   bash scripts/install_bonsai.sh --model bonsai-8b   # explicit model id
#
set -euo pipefail

MODEL_ID="${BONSAI_MODEL_ID:-bonsai-8b}"
MODEL_FILE="Bonsai-8B-Q1_0.gguf"
MODEL_URL="https://huggingface.co/prism-ml/Bonsai-8B-gguf/resolve/main/Bonsai-8B-Q1_0.gguf"
MODEL_SIZE_GB_APPROX="1.15"
VOLUME_NAME="biodockify_models"
SIDECAR_SERVICE="llama-server"
HEALTH_URL="http://localhost:8081/health"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
DRY_RUN=0

# --- arg parsing ---
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --model) MODEL_ID="$2"; shift 2 ;;
    --help|-h)
      grep '^#' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

log()  { printf '\033[1;34m[biodockify]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*" >&2; }
err()  { printf '\033[1;31m[err]\033[0m %s\n' "$*" >&2; }
ok()   { printf '\033[1;32m[ok]\033[0m %s\n' "$*"; }

# --- preflight ---
log "BioDockify AI Engine — local model installer"
log "Model: $MODEL_ID ($MODEL_FILE, ~${MODEL_SIZE_GB_APPROX} GB)"

if ! command -v docker >/dev/null 2>&1; then
  err "Docker CLI not found. Install Docker Desktop first."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  err "Docker daemon not running. Start Docker Desktop and retry."
  exit 1
fi
ok "Docker daemon reachable"

# --- hardware probe ---
RAM_GB=0
if command -v awk >/dev/null 2>&1; then
  if [[ "$(uname)" == "Darwin" ]]; then
    RAM_GB=$(sysctl -n hw.memsize 2>/dev/null | awk '{printf "%.0f", $1/1024/1024/1024}')
  elif [[ -r /proc/meminfo ]]; then
    RAM_GB=$(awk '/MemTotal:/ {printf "%.0f", $2/1024/1024}' /proc/meminfo)
  fi
fi
GPU_KIND="cpu"
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
  GPU_KIND="cuda"
  ok "NVIDIA GPU detected (CUDA)"
elif [[ "$(uname)" == "Darwin" ]] && [[ "$(uname -m)" == "arm64" ]]; then
  GPU_KIND="apple"
  ok "Apple Silicon detected (unified memory)"
else
  warn "No NVIDIA GPU or Apple Silicon detected. Sidecar will run on CPU — slower but functional."
fi

if [[ "$RAM_GB" -gt 0 && "$RAM_GB" -lt 6 ]]; then
  warn "Host RAM is ${RAM_GB}GB; Bonsai-8B needs >=6GB. Expect slow inference."
elif [[ "$RAM_GB" -gt 0 ]]; then
  ok "Host RAM: ${RAM_GB}GB"
fi

if [[ "$GPU_KIND" == "cpu" ]]; then
  warn "Tip: for acceptable CPU speed on Windows/macOS, install Ollama on the"
  warn "     host and use the Ollama preset instead of this bundled sidecar."
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  log "Dry-run requested — preflight complete, no download started."
  exit 0
fi

# --- verify compose file exists ---
if [[ ! -f "$COMPOSE_FILE" ]]; then
  err "Compose file '$COMPOSE_FILE' not found. Run from repo root."
  exit 1
fi

# --- ensure volume exists ---
if ! docker volume inspect "$VOLUME_NAME" >/dev/null 2>&1; then
  log "Creating Docker volume $VOLUME_NAME"
  docker volume create "$VOLUME_NAME" >/dev/null
fi
ok "Volume $VOLUME_NAME ready"

# --- check if model already downloaded ---
MODEL_PRESENT=$(docker run --rm -v "${VOLUME_NAME}:/models" alpine:3.20 \
  sh -c "[ -f /models/${MODEL_FILE} ] && echo yes || echo no" 2>/dev/null || echo "no")

if [[ "$MODEL_PRESENT" == "yes" ]]; then
  ok "Model $MODEL_FILE already present in $VOLUME_NAME (skip download)"
else
  log "Downloading $MODEL_FILE (~${MODEL_SIZE_GB_APPROX} GB) from HuggingFace"
  log "into volume $VOLUME_NAME (one-time, no re-download on image updates)"
  docker run --rm -v "${VOLUME_NAME}:/models" alpine:3.20 \
    sh -c "apk add --no-cache curl >/dev/null 2>&1 && \
           echo 'Downloading...' && \
           curl -L --fail --progress-bar -o /models/${MODEL_FILE} ${MODEL_URL} && \
           echo 'Verifying size...' && \
           ls -la /models/${MODEL_FILE}"
  ok "Download complete"
fi

# --- bring up sidecar ---
log "Starting llama-server sidecar (profile local-llm)"
if ! docker compose --profile local-llm up -d "$SIDECAR_SERVICE" >/dev/null 2>&1; then
  err "Failed to start sidecar. Try manually:"
  err "  docker compose --profile local-llm up -d $SIDECAR_SERVICE"
  exit 1
fi
ok "Sidecar starting"

# --- wait for health ---
log "Waiting for sidecar /health (max 90s)..."
for i in $(seq 1 90); do
  if curl -sf "$HEALTH_URL" >/dev/null 2>&1; then
    ok "Sidecar healthy at $HEALTH_URL"
    break
  fi
  sleep 1
  if [[ $i -eq 90 ]]; then
    warn "Sidecar not healthy after 90s. Check: docker compose logs $SIDECAR_SERVICE"
  fi
done

cat <<EOF

============================================================
 Bonsai-8B is ready. Final step:
   1. Open BioDockify in your browser (http://localhost)
   2. Go to Settings → Models
   3. In the preset switcher choose:
        "BioDockify AI Engine — Local (Bonsai-8B)"
   4. Send a test message.

 Pharma use cases unlocked:
   - Private literature synthesis (no egress)
   - Offline claim verification
   - Air-gapped ICH/CONSORT compliance checks
============================================================
EOF
