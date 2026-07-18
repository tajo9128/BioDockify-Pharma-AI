#!/bin/bash
# BioDockify Auto-Backup Script
# Runs on container startup + daily at 3 AM via cron
# Creates a zip of ALL critical data: /a0/usr, /a0/.a0proj, /a0/data
# Backups survive container deletion (stored in /a0/usr/backups volume)

set -e

BACKUP_DIR="/a0/usr/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="${BACKUP_DIR}/auto_backup_${TIMESTAMP}"
MAX_BACKUPS=7

mkdir -p "$BACKUP_DIR"

# All three critical data locations
BACKUP_PATHS=("/a0/usr" "/a0/.a0proj" "/a0/data")

# Quick check — at least one of the paths must exist
DATA_FOUND=false
for p in "${BACKUP_PATHS[@]}"; do
    if [ -d "$p" ]; then DATA_FOUND=true; break; fi
done
if [ "$DATA_FOUND" = false ]; then
    echo "[Auto-Backup] No data directories found, skipping"
    exit 0
fi

echo "[Auto-Backup] Creating backup: $BACKUP_PATH"
mkdir -p "$BACKUP_PATH"

# Create a zip of all three locations (preserving the a0/ prefix for safe restore)
ZIP_FILE="$BACKUP_PATH/backup.zip"
python3 -c "
import os, zipfile
paths = ['/a0/usr', '/a0/.a0proj', '/a0/data']
with zipfile.ZipFile('$ZIP_FILE', 'w', zipfile.ZIP_DEFLATED) as zf:
    for base in paths:
        if not os.path.exists(base): continue
        for root, dirs, files in os.walk(base):
            if 'backups' in root.split(os.sep): continue
            for f in files:
                fp = os.path.join(root, f)
                arcname = fp.lstrip('/')
                try: zf.write(fp, arcname)
                except Exception: pass
print('[Auto-Backup] Zip created at $ZIP_FILE')
" 2>&1 || echo "[Auto-Backup] WARNING: zip creation failed, directory copy fallback below"

# Also copy directory structure as a fallback
for base in "${BACKUP_PATHS[@]}"; do
    if [ -d "$base" ]; then
        base_name=$(basename "$base")
        # Skip the backups subdir inside /a0/usr to avoid recursion
        if [ "$base" = "/a0/usr" ]; then
            mkdir -p "$BACKUP_PATH/usr"
            for item in /a0/usr/*; do
                [ "$(basename "$item")" = "backups" ] && continue
                cp -r "$item" "$BACKUP_PATH/usr/" 2>/dev/null || true
            done
        else
            cp -r "$base" "$BACKUP_PATH/$base_name" 2>/dev/null || true
        fi
    fi
done

# Save metadata
cat > "$BACKUP_PATH/metadata.json" << EOF
{
    "backup_id": "auto_backup_${TIMESTAMP}",
    "created_at": "$(date -Iseconds)",
    "label": "Automatic Backup",
    "type": "auto",
    "paths": ["/a0/usr", "/a0/.a0proj", "/a0/data"]
}
EOF
touch "$BACKUP_PATH/.backup_complete"

# Clean old backups (keep last MAX_BACKUPS)
ALL_BACKUPS=($(ls -d "$BACKUP_DIR"/auto_backup_* 2>/dev/null | sort -r))
if [ ${#ALL_BACKUPS[@]} -gt $MAX_BACKUPS ]; then
    for old in "${ALL_BACKUPS[@]:$MAX_BACKUPS}"; do
        rm -rf "$old" 2>/dev/null || true
        echo "[Auto-Backup] Pruned old backup: $old"
    done
fi

echo "[Auto-Backup] Backup completed: $BACKUP_PATH"
echo "[Auto-Backup] Total auto-backups: $(ls -d "$BACKUP_DIR"/auto_backup_* 2>/dev/null | wc -l)"
