#!/bin/bash
# BioDockify AI Engine — auto-download Bonsai-8B model on first run
# Runs inside the container. Downloads to /a0/usr/ai_models/ which persists
# in the biodockify_usr volume. Skips download if model already present.
set -e

MODEL_DIR=/a0/usr/ai_models
MODEL_FILE=$MODEL_DIR/Bonsai-8B-Q1_0.gguf
URL=https://huggingface.co/prism-ml/Bonsai-8B-gguf/resolve/main/Bonsai-8B-Q1_0.gguf
EXPECTED_SIZE=1158654496

mkdir -p "$MODEL_DIR"

# Check if model already present and complete
if [ -f "$MODEL_FILE" ]; then
    ACTUAL_SIZE=$(stat -c%s "$MODEL_FILE" 2>/dev/null || stat -f%z "$MODEL_FILE" 2>/dev/null || echo 0)
    if [ "$ACTUAL_SIZE" -ge "$EXPECTED_SIZE" ]; then
        echo "[bonsai] Model present ($((ACTUAL_SIZE/1024/1024)) MB). OK."
        exit 0
    else
        echo "[bonsai] Partial file ($((ACTUAL_SIZE/1024/1024)) MB). Re-downloading."
        rm -f "$MODEL_FILE"
    fi
fi

echo "[bonsai] Downloading Bonsai-8B model (~1.1 GB, one-time)..."
echo "[biosai] This takes a few minutes depending on your internet."
echo "[bonsai] No student interaction needed — it runs automatically."

# Try curl first (usually available in Debian base), fall back to wget
if command -v curl >/dev/null 2>&1; then
    curl -L --fail --progress-bar -o "$MODEL_FILE" "$URL"
elif command -v wget >/dev/null 2>&1; then
    wget --progress=bar:force -O "$MODEL_FILE" "$URL"
else
    echo "[bonsai] ERROR: Neither curl nor wget available. Cannot download model."
    echo "[bonsai] Local AI will not work. Install curl: apt-get install curl"
    exit 0
fi

# Verify download succeeded
if [ -f "$MODEL_FILE" ]; then
    ACTUAL_SIZE=$(stat -c%s "$MODEL_FILE" 2>/dev/null || stat -f%z "$MODEL_FILE" 2>/dev/null || echo 0)
    if [ "$ACTUAL_SIZE" -ge "$EXPECTED_SIZE" ]; then
        echo "[bonsai] Download complete ($((ACTUAL_SIZE/1024/1024)) MB). Model ready."
    else
        echo "[bonsai] WARNING: Downloaded file smaller than expected ($ACTUAL_SIZE < $EXPECTED_SIZE)."
        echo "[bonsai] Local AI may not work. Check your internet and restart the container."
    fi
else
    echo "[bonsai] WARNING: Download failed. Local AI will not be available."
    echo "[bonsai] The rest of BioDockify still works — use cloud presets in Settings."
fi
