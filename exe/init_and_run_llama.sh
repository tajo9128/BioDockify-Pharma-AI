#!/bin/bash
# BioDockify AI Engine — start llama-server for local LLM inference
# Called by supervisord on container startup. Downloads the model on first
# run, then starts the server. Model persists in /a0/usr/ai_models/.
# If download fails, the server exits gracefully (autorestart=none).

MODEL_PATH=${MODEL_PATH:-/a0/usr/ai_models/Bonsai-8B-Q1_0.gguf}

# ─── Step 1: Ensure model is downloaded ───
/a0/exe/init_bonsai.sh

# ─── Step 2: Start llama-server if model exists ───
if [ -f "$MODEL_PATH" ]; then
    ACTUAL_SIZE=$(stat -c%s "$MODEL_PATH" 2>/dev/null || stat -f%z "$MODEL_PATH" 2>/dev/null || echo 0)
    if [ "$ACTUAL_SIZE" -ge 1100000000 ]; then
        echo "[llama] Starting BioDockify AI Engine (Bonsai-8B, 1-bit)..."
        echo "[llama] Model: $MODEL_PATH ($((ACTUAL_SIZE/1024/1024)) MB)"
        echo "[llama] Endpoint: http://localhost:8080/v1 (OpenAI-compatible)"
        exec llama-server \
            -m "$MODEL_PATH" \
            --host 0.0.0.0 \
            --port 8080 \
            -c 32768 \
            -a bonsai-8b \
            --log-disable
    else
        echo "[llama] Model file too small ($((ACTUAL_SIZE/1024/1024)) MB). Skipping."
        exit 0
    fi
else
    echo "[llama] Model not available. Server will not start."
    echo "[llama] The rest of BioDockify still works — use cloud presets in Settings."
    # Do not restart — there's no point retrying without internet
    exit 0
fi
