#!/bin/bash
# BioDockify Auto-Backup Script
# Runs on container startup + periodically via cron
# Creates timestamped backups of critical data

set -e

BACKUP_DIR="/a0/usr/backups"
DATA_DIR="/a0/usr"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="${BACKUP_DIR}/auto_backup_${TIMESTAMP}"
MAX_BACKUPS=7

# Critical directories/files to backup
CRITICAL_DIRS=("data" "knowledge" "memory" "projects" "agents" "skills" "prompts")
CRITICAL_FILES=("settings.json" "identity.md")

mkdir -p "$BACKUP_DIR"

# Only backup if data exists
if [ ! -d "$DATA_DIR/data" ] && [ ! -f "$DATA_DIR/settings.json" ]; then
    echo "[Auto-Backup] No critical data found, skipping first backup"
    exit 0
fi

echo "[Auto-Backup] Creating backup: $BACKUP_PATH"
mkdir -p "$BACKUP_PATH"

# Backup critical directories
for dir in "${CRITICAL_DIRS[@]}"; do
    src="$DATA_DIR/$dir"
    if [ -d "$src" ]; then
        cp -r "$src" "$BACKUP_PATH/$dir" 2>/dev/null || true
    fi
done

# Backup critical files
for file in "${CRITICAL_FILES[@]}"; do
    src="$DATA_DIR/$file"
    if [ -f "$src" ]; then
        cp "$src" "$BACKUP_PATH/$file" 2>/dev/null || true
    fi
done

# Clean old backups (keep last $MAX_BACKUPS)
ALL_BACKUPS=($(ls -d "$BACKUP_DIR"/auto_backup_* 2>/dev/null | sort -r))
if [ ${#ALL_BACKUPS[@]} -gt $MAX_BACKUPS ]; then
    for old in "${ALL_BACKUPS[@]:$MAX_BACKUPS}"; do
        rm -rf "$old" 2>/dev/null || true
        echo "[Auto-Backup] Removed old backup: $old"
    done
fi

echo "[Auto-Backup] Backup completed: $BACKUP_PATH"
echo "[Auto-Backup] Total backups: ${#ALL_BACKUPS[@]}"
