#!/bin/bash
# BioDockify AI Engine — start llama-server for local LLM inference
# Called by supervisord on container startup.
# Model is BUNDLED in the Docker image at /opt/llama-server/models/ — no download needed.

MODEL_PATH=${MODEL_PATH:-/opt/llama-server/models/Bonsai-8B-Q1_0.gguf}

# ─── Verify model exists ───
if [ ! -f "$MODEL_PATH" ]; then
    echo "[llama] ERROR: Model not found at $MODEL_PATH"
    echo "[llama] The model should be bundled in the Docker image."
    echo "[llama] Local AI will not work. Use cloud presets in Settings."
    exit 0
fi

ACTUAL_SIZE=$(stat -c%s "$MODEL_PATH" 2>/dev/null || stat -f%z "$MODEL_PATH" 2>/dev/null || echo 0)
if [ "$ACTUAL_SIZE" -lt 1100000000 ]; then
    echo "[llama] ERROR: Model file too small ($((ACTUAL_SIZE/1024/1024)) MB). Expected ~1.1 GB."
    echo "[llama] Local AI will not work. Use cloud presets in Settings."
    exit 0
fi

# ─── Start llama-server ───
echo "[llama] Starting BioDockify AI Engine (Bonsai-8B, 1-bit)..."
echo "[llama] Model: $MODEL_PATH ($((ACTUAL_SIZE/1024/1024)) MB)"
echo "[llama] Endpoint: http://localhost:8080/v1 (OpenAI-compatible)"
export LD_LIBRARY_PATH=/opt/llama-server:${LD_LIBRARY_PATH:-}
exec /opt/llama-server/llama-server \
    -m "$MODEL_PATH" \
    --host 0.0.0.0 \
    --port 8080 \
    -c 32768 \
    -a bonsai-8b \
    --log-disable
