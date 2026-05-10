#!/bin/bash

# BioDockify One-Click Launcher (Linux/Mac)
# Full Stack Edition - "Robust Agent Zero Experience"

echo "========================================================"
echo "  BioDockify AI - Pharma Research Station"
echo "  Version: 2.6.7 (Full Stack + LM Studio Ready)"
echo "========================================================"
echo ""

# 1. Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "[ERROR] Docker is NOT running!"
    echo "Please start Docker Desktop and try again."
    exit 1
fi
echo "[OK] Docker is running."

# 2. Launch Full Stack with Docker Compose
echo "[INFO] Orchestrating BioDockify Ecosystem..."
echo ""
echo "    Core App:   Port 3000"
echo "    Database:   PostgreSQL + ChromaDB"
echo "    AI Engine:  LM Studio (On Host: Port 1234)"
echo "    PDF Parser: Grobid"
echo ""
echo "[NOTE] Please ensure LM Studio is running on your machine with the local server enabled on port 1234."

docker compose up -d --build

if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to start services."
    echo "Please check if ports 3000, 7474, or 8070 are in use."
    exit 1
fi

# 3. Open in browser
echo ""
echo "[SUCCESS] BioDockify Ecosystem is live!"
echo "Opening http://localhost:3000 ..."

if [[ "$OSTYPE" == "darwin"* ]]; then
    open http://localhost:3000
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    xdg-open http://localhost:3000
fi

echo "Startup complete."
