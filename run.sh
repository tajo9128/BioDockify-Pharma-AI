#!/bin/bash
# BioDockify Pharma AI — Quick Start (macOS / Linux)
# ===================================================
# This starts the container using a persistent Docker volume.
# ALL data survives container deletion.
#
# Usage:  ./run.sh
# After starting, open: http://localhost:3000

echo ""
echo "[BioDockify Pharma AI] Starting container..."
echo ""

docker compose up -d

if [ $? -eq 0 ]; then
    echo ""
    echo "[OK] Container started successfully!"
    echo ""
    echo "Open http://localhost:3000 in your browser."
    echo ""
    echo "===== Useful Commands ====="
    echo "Stop:           docker compose down"
    echo "View logs:      docker compose logs -f"
    echo "Update:         docker compose pull && docker compose up -d"
    echo "Backup volume:  docker run --rm -v biodockify_pharma_usr:/volume -v \$(pwd):/backup alpine tar czf /backup/biodockify-backup.tar.gz -C /volume ."
    echo "Restore volume: docker run --rm -v biodockify_pharma_usr:/volume -v \$(pwd):/backup alpine sh -c \"rm -rf /volume/* && tar xzf /backup/biodockify-backup.tar.gz -C /volume\""
    echo ""
else
    echo ""
    echo "[ERROR] Failed to start container."
    echo "Make sure Docker is installed and running."
fi