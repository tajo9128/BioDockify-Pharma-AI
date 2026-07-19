#!/bin/bash
# BioDockify AI Engine — verify bundled Bonsai-8B model
# The model is BUNDLED in the Docker image at /opt/llama-server/models/.
# No download needed — this script just verifies the model is present.

MODEL_PATH=/opt/llama-server/models/Bonsai-8B-Q1_0.gguf
EXPECTED_SIZE=1158654496

if [ -f "$MODEL_PATH" ]; then
    ACTUAL_SIZE=$(stat -c%s "$MODEL_PATH" 2>/dev/null || stat -f%z "$MODEL_PATH" 2>/dev/null || echo 0)
    if [ "$ACTUAL_SIZE" -ge "$EXPECTED_SIZE" ]; then
        echo "[bonsai] Model present ($((ACTUAL_SIZE/1024/1024)) MB). OK."
        exit 0
    else
        echo "[bonsai] WARNING: Model file smaller than expected ($ACTUAL_SIZE < $EXPECTED_SIZE)."
        exit 1
    fi
else
    echo "[bonsai] ERROR: Model not found at $MODEL_PATH"
    echo "[bonsai] The model should be bundled in the Docker image."
    exit 1
fi
