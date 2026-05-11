#!/bin/bash
set -e

# Paths for BioDockify AI
SOURCE_DIR="/git/biodockify"
TARGET_DIR="/bio"

source /opt/venv-a0/bin/activate

if [ ! -f "$TARGET_DIR/run_ui.py" ]; then
    echo "Copying files from $SOURCE_DIR to $TARGET_DIR..."
    cp -rn --no-preserve=ownership,mode "$SOURCE_DIR/." "$TARGET_DIR"
fi