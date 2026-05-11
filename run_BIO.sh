#!/bin/bash
# Modified for BioDockify AI
. "/ins/setup_venv.sh" "$@"
. "/ins/copy_BIO.sh" "$@"

echo "Starting BioDockify AI bootstrap manager..."
exec python /exe/self_update_manager.py docker-run-ui