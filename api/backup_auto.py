from helpers.api import ApiHandler, Request, Response
from helpers import files
import json
import os
import glob
import datetime


BACKUPS_DIR = files.get_abs_path("usr/backups")


class BackupAuto(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "create")

        os.makedirs(BACKUPS_DIR, exist_ok=True)

        if action == "create":
            return await self._create_backup(input)
        elif action == "list":
            return self._list_backups()
        elif action == "info":
            backup_id = input.get("id", "")
            return self._backup_info(backup_id)
        elif action == "delete":
            backup_id = input.get("id", "")
            return self._delete_backup(backup_id)
        elif action == "restore":
            backup_id = input.get("id", "")
            return await self._restore_backup(backup_id)
        return {"error": "Unknown action"}

    async def _create_backup(self, input: dict) -> dict:
        label = input.get("label", "manual")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"biodockify_backup_{timestamp}_{label}"
        backup_dir = os.path.join(BACKUPS_DIR, backup_name)
        os.makedirs(backup_dir, exist_ok=True)

        # Use the existing BackupService to create the backup archive
        try:
            from helpers.backup import BackupService
            service = BackupService()
            metadata = service.get_default_backup_metadata()
            metadata["backup_name"] = backup_name
            metadata["label"] = label
            metadata["created_at"] = timestamp

            # Save metadata
            with open(os.path.join(backup_dir, "metadata.json"), "w") as f:
                json.dump(metadata, f, indent=2)

            # Create the backup archive in the backup dir
            output_path = os.path.join(backup_dir, "backup.zip")
            result = await service.create_backup(metadata, output_path)

            if os.path.exists(output_path):
                size_mb = round(os.path.getsize(output_path) / (1024 * 1024), 2)
                return {
                    "success": True,
                    "backup_id": backup_name,
                    "path": output_path,
                    "size_mb": size_mb,
                    "created_at": timestamp,
                    "label": label,
                    "files": result.get("files_count", 0),
                }
            else:
                return {"success": False, "error": "Backup file was not created"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _list_backups(self) -> dict:
        backups = []
        if os.path.exists(BACKUPS_DIR):
            for entry in sorted(os.listdir(BACKUPS_DIR), reverse=True):
                backup_dir = os.path.join(BACKUPS_DIR, entry)
                if os.path.isdir(backup_dir):
                    meta_path = os.path.join(backup_dir, "metadata.json")
                    meta = {}
                    if os.path.exists(meta_path):
                        with open(meta_path) as f:
                            meta = json.load(f)
                    zip_path = os.path.join(backup_dir, "backup.zip")
                    size_mb = 0
                    if os.path.exists(zip_path):
                        size_mb = round(os.path.getsize(zip_path) / (1024 * 1024), 2)
                    backups.append({
                        "id": entry,
                        "label": meta.get("label", "unknown"),
                        "created_at": meta.get("created_at", ""),
                        "size_mb": size_mb,
                        "has_archive": os.path.exists(zip_path),
                    })
        return {"backups": backups, "backup_dir": BACKUPS_DIR}

    def _backup_info(self, backup_id: str) -> dict:
        backup_dir = os.path.join(BACKUPS_DIR, backup_id)
        if not os.path.isdir(backup_dir):
            return {"error": f"Backup {backup_id} not found"}
        meta_path = os.path.join(backup_dir, "metadata.json")
        meta = {}
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                meta = json.load(f)
        return {"backup_id": backup_id, "metadata": meta}

    def _delete_backup(self, backup_id: str) -> dict:
        backup_dir = os.path.join(BACKUPS_DIR, backup_id)
        if not os.path.isdir(backup_dir):
            return {"error": f"Backup {backup_id} not found"}
        import shutil
        shutil.rmtree(backup_dir)
        return {"success": True, "deleted": backup_id}

    async def _restore_backup(self, backup_id: str) -> dict:
        backup_dir = os.path.join(BACKUPS_DIR, backup_id)
        zip_path = os.path.join(backup_dir, "backup.zip")
        if not os.path.exists(zip_path):
            return {"error": f"Backup archive not found for {backup_id}"}
        try:
            from helpers.backup import BackupService
            service = BackupService()
            meta_path = os.path.join(backup_dir, "metadata.json")
            with open(meta_path) as f:
                metadata = json.load(f)
            result = service.restore_backup(zip_path, metadata)
            return {"success": True, "restored": result.get("restored_count", 0)}
        except Exception as e:
            return {"success": False, "error": str(e)}
