"""Auto-Backup System — one-click backup/restore for non-technical users.

Backups are stored INSIDE the volume (/a0/usr/backups/) so they survive
container deletion, Docker restarts, and software upgrades.

One click backup → data persists in volume → delete container → install new
version → one click restore → all data comes back.
"""
import os
import json
import shutil
import zipfile
import datetime
import logging
import glob
from helpers.api import ApiHandler, Request, Response

log = logging.getLogger("backup_auto")

BACKUPS_DIR = "/a0/usr/backups"
DATA_DIR = "/a0/usr"
MAX_BACKUPS = 7
BACKUP_MARKER = ".backup_complete"


def _get_backup_size(backup_dir):
    """Calculate total size of a backup directory in MB."""
    total = 0
    for root, dirs, files in os.walk(backup_dir):
        for f in files:
            total += os.path.getsize(os.path.join(root, f))
    return round(total / (1024 * 1024), 2)


def _count_files(backup_dir):
    """Count files in a backup directory."""
    count = 0
    for root, dirs, files in os.walk(backup_dir):
        count += len(files)
    return count


def _create_zip_backup(backup_dir, data_dir):
    """Create a zip archive of all user data."""
    zip_path = os.path.join(backup_dir, "backup.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(data_dir):
            # Skip the backups directory itself to avoid recursion
            if 'backups' in root.split(os.sep):
                continue
            for f in files:
                filepath = os.path.join(root, f)
                arcname = os.path.relpath(filepath, data_dir)
                try:
                    zf.write(filepath, arcname)
                except Exception as e:
                    log.warning(f"Could not backup {filepath}: {e}")
    return zip_path


def _restore_from_zip(zip_path, data_dir):
    """Restore all data from a zip archive."""
    restored = 0
    errors = []
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for member in zf.namelist():
            try:
                # Extract to data directory
                zf.extract(member, data_dir)
                restored += 1
            except Exception as e:
                errors.append(f"{member}: {e}")
    return restored, errors


def _restore_from_dir(backup_dir, data_dir):
    """Restore from directory-based backup (copy files back)."""
    restored = 0
    errors = []
    for item in os.listdir(backup_dir):
        if item in ("metadata.json", "backup.zip", BACKUP_MARKER):
            continue
        src = os.path.join(backup_dir, item)
        dst = os.path.join(data_dir, item)
        if os.path.isdir(src):
            try:
                if os.path.exists(dst):
                    # Merge: copy newer files
                    for root, dirs, files in os.walk(src):
                        rel = os.path.relpath(root, src)
                        target_dir = os.path.join(dst, rel)
                        os.makedirs(target_dir, exist_ok=True)
                        for f in files:
                            src_file = os.path.join(root, f)
                            dst_file = os.path.join(target_dir, f)
                            try:
                                if not os.path.exists(dst_file) or os.path.getmtime(src_file) > os.path.getmtime(dst_file):
                                    shutil.copy2(src_file, dst_file)
                                    restored += 1
                            except Exception as e:
                                errors.append(f"{f}: {e}")
                else:
                    shutil.copytree(src, dst)
                    restored += sum(1 for _, _, files in os.walk(src) for f in files)
            except Exception as e:
                errors.append(f"{item}: {e}")
        else:
            try:
                shutil.copy2(src, dst)
                restored += 1
            except Exception as e:
                errors.append(f"{item}: {e}")
    return restored, errors


def _prune_old_backups():
    """Keep only MAX_BACKUPS most recent backups."""
    if not os.path.exists(BACKUPS_DIR):
        return
    backups = sorted(
        [d for d in os.listdir(BACKUPS_DIR) if os.path.isdir(os.path.join(BACKUPS_DIR, d))],
        reverse=True
    )
    for old in backups[MAX_BACKUPS:]:
        try:
            shutil.rmtree(os.path.join(BACKUPS_DIR, old))
            log.info(f"Pruned old backup: {old}")
        except Exception:
            pass


class AutoBackupHandler(ApiHandler):
    """One-click backup/restore. Backups live in the volume so they survive everything."""

    @classmethod
    def requires_auth(cls) -> bool:
        return False

    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "status")

        if action == "status":
            return self._status()
        elif action == "create":
            return self._create()
        elif action == "list":
            return self._list()
        elif action == "restore":
            return self._restore(input.get("backup_id", ""))
        elif action == "delete":
            return self._delete(input.get("backup_id", ""))
        elif action == "download":
            return self._download(input.get("backup_id", ""))
        elif action == "restore_from_upload":
            return self._restore_from_upload(input, request)

        return {"actions": ["status", "create", "list", "restore", "delete", "download", "restore_from_upload"]}

    def _status(self):
        """Quick status check."""
        os.makedirs(BACKUPS_DIR, exist_ok=True)
        backups = self._get_backup_list()
        return {
            "status": "ok",
            "backup_count": len(backups),
            "max_backups": MAX_BACKUPS,
            "backup_dir": BACKUPS_DIR,
            "data_dir": DATA_DIR,
            "latest": backups[0] if backups else None,
        }

    def _create(self):
        """One-click backup: zip all user data into a timestamped backup."""
        os.makedirs(BACKUPS_DIR, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_id = f"backup_{timestamp}"
        backup_dir = os.path.join(BACKUPS_DIR, backup_id)
        os.makedirs(backup_dir, exist_ok=True)

        try:
            # Create zip archive of all user data
            zip_path = _create_zip_backup(backup_dir, DATA_DIR)
            zip_size = round(os.path.getsize(zip_path) / (1024 * 1024), 2) if os.path.exists(zip_path) else 0

            # Also copy directory structure for direct-restore fallback
            for item in os.listdir(DATA_DIR):
                if item == "backups":
                    continue
                src = os.path.join(DATA_DIR, item)
                dst = os.path.join(backup_dir, item)
                try:
                    if os.path.isdir(src):
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
                except Exception as e:
                    log.warning(f"Could not copy {item}: {e}")

            # Save metadata
            metadata = {
                "backup_id": backup_id,
                "created_at": datetime.datetime.now().isoformat(),
                "label": "Quick Backup",
                "zip_size_mb": zip_size,
                "file_count": _count_files(backup_dir),
            }
            with open(os.path.join(backup_dir, "metadata.json"), "w") as f:
                json.dump(metadata, f, indent=2)

            # Mark as complete
            with open(os.path.join(backup_dir, BACKUP_MARKER), "w") as f:
                f.write(datetime.datetime.now().isoformat())

            # Prune old backups
            _prune_old_backups()

            return {
                "success": True,
                "backup_id": backup_id,
                "size_mb": _get_backup_size(backup_dir),
                "zip_size_mb": zip_size,
                "message": f"Backup created: {backup_id} ({zip_size} MB). Stored in volume — survives container deletion."
            }

        except Exception as e:
            log.error(f"Backup failed: {e}")
            # Clean up partial backup
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir, ignore_errors=True)
            return {"success": False, "error": str(e)}

    def _list(self):
        """List all available backups."""
        return {"status": "ok", "backups": self._get_backup_list()}

    def _get_backup_list(self):
        """Get sorted list of backups."""
        backups = []
        if not os.path.exists(BACKUPS_DIR):
            return backups
        for entry in sorted(os.listdir(BACKUPS_DIR), reverse=True):
            backup_dir = os.path.join(BACKUPS_DIR, entry)
            if not os.path.isdir(backup_dir):
                continue
            meta_path = os.path.join(backup_dir, "metadata.json")
            meta = {}
            if os.path.exists(meta_path):
                try:
                    with open(meta_path) as f:
                        meta = json.load(f)
                except Exception:
                    pass
            zip_path = os.path.join(backup_dir, "backup.zip")
            has_zip = os.path.exists(zip_path)
            zip_size = round(os.path.getsize(zip_path) / (1024 * 1024), 2) if has_zip else 0
            has_marker = os.path.exists(os.path.join(backup_dir, BACKUP_MARKER))

            # Count directory contents
            dir_items = [d for d in os.listdir(backup_dir) if d not in ("metadata.json", "backup.zip", BACKUP_MARKER)]

            backups.append({
                "id": entry,
                "label": meta.get("label", "Backup"),
                "created_at": meta.get("created_at", ""),
                "size_mb": _get_backup_size(backup_dir),
                "zip_size_mb": zip_size,
                "has_zip": has_zip,
                "complete": has_marker,
                "contents": dir_items,
            })
        return backups

    def _restore(self, backup_id):
        """One-click restore: extract backup and restore all data."""
        if not backup_id:
            # Find latest backup
            backups = self._get_backup_list()
            if not backups:
                return {"success": False, "error": "No backups available"}
            backup_id = backups[0]["id"]

        backup_dir = os.path.join(BACKUPS_DIR, backup_id)
        if not os.path.isdir(backup_dir):
            return {"success": False, "error": f"Backup not found: {backup_id}"}

        zip_path = os.path.join(backup_dir, "backup.zip")
        restored = 0
        errors = []

        try:
            # Method 1: Restore from zip (preferred)
            if os.path.exists(zip_path):
                log.info(f"Restoring from zip: {zip_path}")
                restored, zip_errors = _restore_from_zip(zip_path, DATA_DIR)
                errors.extend(zip_errors)
            else:
                # Method 2: Restore from directory contents
                log.info(f"Restoring from directory: {backup_dir}")
                restored, dir_errors = _restore_from_dir(backup_dir, DATA_DIR)
                errors.extend(dir_errors)

            if restored > 0:
                return {
                    "success": True,
                    "backup_id": backup_id,
                    "restored_files": restored,
                    "errors": errors[:5] if errors else [],
                    "message": f"Restored {restored} files from {backup_id}. Restart container to apply."
                }
            else:
                return {
                    "success": False,
                    "error": f"No files restored from {backup_id}",
                    "errors": errors[:5]
                }

        except Exception as e:
            log.error(f"Restore failed: {e}")
            return {"success": False, "error": str(e)}

    def _delete(self, backup_id):
        """Delete a specific backup."""
        backup_dir = os.path.join(BACKUPS_DIR, backup_id)
        if not os.path.isdir(backup_dir):
            return {"error": f"Backup not found: {backup_id}"}
        try:
            shutil.rmtree(backup_dir)
            return {"success": True, "deleted": backup_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _download(self, backup_id):
        """Download a backup zip file."""
        backup_dir = os.path.join(BACKUPS_DIR, backup_id)
        zip_path = os.path.join(backup_dir, "backup.zip")
        if not os.path.exists(zip_path):
            return {"error": "Backup zip not found"}
        return {
            "success": True,
            "path": zip_path,
            "filename": f"{backup_id}.zip"
        }

    def _restore_from_upload(self, input: dict, request) -> dict:
        """Restore from an uploaded ZIP backup file — no Docker commands needed.

        User uploads a .zip file through the web UI → this extracts it
        into /a0/usr/ and restores all data.
        """
        try:
            # Check for uploaded file
            if not hasattr(request, 'files') or 'backup_file' not in request.files:
                return {"success": False, "error": "No backup file uploaded. Please select a .zip file."}

            backup_file = request.files['backup_file']
            if not backup_file or not backup_file.filename:
                return {"success": False, "error": "No file selected."}

            # Save uploaded file to temp location
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            upload_dir = os.path.join(BACKUPS_DIR, f"uploaded_{timestamp}")
            os.makedirs(upload_dir, exist_ok=True)
            upload_path = os.path.join(upload_dir, "backup.zip")
            backup_file.save(upload_path)

            # Verify it's a valid zip
            if not zipfile.is_zipfile(upload_path):
                shutil.rmtree(upload_dir, ignore_errors=True)
                return {"success": False, "error": "File is not a valid ZIP archive."}

            # Extract and restore
            restored, errors = _restore_from_zip(upload_path, DATA_DIR)

            # Save metadata
            metadata = {
                "backup_id": f"uploaded_{timestamp}",
                "created_at": datetime.datetime.now().isoformat(),
                "label": f"Uploaded: {backup_file.filename}",
                "zip_size_mb": round(os.path.getsize(upload_path) / (1024 * 1024), 2),
                "restored_files": restored,
            }
            with open(os.path.join(upload_dir, "metadata.json"), "w") as f:
                json.dump(metadata, f, indent=2)
            with open(os.path.join(upload_dir, BACKUP_MARKER), "w") as f:
                f.write(datetime.datetime.now().isoformat())

            if restored > 0:
                return {
                    "success": True,
                    "backup_id": f"uploaded_{timestamp}",
                    "restored_files": restored,
                    "errors": errors[:5] if errors else [],
                    "message": f"Backup restored: {restored} files extracted from {backup_file.filename}. Your data is back."
                }
            else:
                return {
                    "success": False,
                    "error": f"No files restored from {backup_file.filename}. The zip may not contain expected data.",
                    "errors": errors[:5]
                }

        except Exception as e:
            log.error(f"Upload restore failed: {e}")
            return {"success": False, "error": str(e)}
