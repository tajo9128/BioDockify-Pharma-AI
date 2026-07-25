import asyncio
from helpers.api import ApiHandler, Request, Response, send_file
from helpers.backup import BackupService
from helpers.persist_chat import save_tmp_chats


class BackupCreate(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return False  # localhost backup panel — non-technical users

    @classmethod
    def requires_loopback(cls) -> bool:
        return False

    async def process(self, input: dict, request: Request) -> dict | Response:
        try:
            # Get input parameters
            include_patterns = input.get("include_patterns", [])
            exclude_patterns = input.get("exclude_patterns", [])
            include_hidden = input.get("include_hidden", True)
            backup_name = input.get("backup_name", "BioDockify-AI-backup")

            # Support legacy string patterns format for backward compatibility
            patterns_string = input.get("patterns", "")
            if patterns_string and not include_patterns and not exclude_patterns:
                # Parse legacy format
                lines = [line.strip() for line in patterns_string.split('\n') if line.strip() and not line.strip().startswith('#')]
                for line in lines:
                    if line.startswith('!'):
                        exclude_patterns.append(line[1:])
                    else:
                        include_patterns.append(line)

            # Save all chats to the chats folder
            save_tmp_chats()

            # Create backup service and generate backup
            backup_service = BackupService()
            zip_path = await backup_service.create_backup(
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
                include_hidden=include_hidden,
                backup_name=backup_name
            )

            # Return file for download
            return send_file(
                zip_path,
                as_attachment=True,
                download_name=f"{backup_name}.zip",
                mimetype='application/zip'
            )

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


class AutoBackupQuickHandler(ApiHandler):
    """Auto-backup and restore for accidental data loss."""

    BACKUP_DIR = "/app/data"
    DATA_DIR = "/a0/usr"
    MAX_BACKUPS = 7

    @classmethod
    def requires_auth(cls) -> bool:
        return False

    @classmethod
    def requires_loopback(cls) -> bool:
        return False

    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "status")

        if action == "create":
            return self._create_backup()
        elif action == "restore":
            return self._restore_latest()
        elif action == "restore_specific":
            return self._restore_specific(input.get("backup_name", ""))
        elif action == "restore_from_upload":
            return await self._restore_from_upload(input, request)
        elif action == "download":
            return self._download_backup(input.get("backup_id", ""))
        elif action == "delete":
            return self._delete_backup(input.get("id", ""))
        elif action == "status":
            return self._get_status()
        elif action == "list":
            return self._list_backups()

        return {"status": "error", "error": f"Unknown action: {action}"}

    def _create_backup(self) -> dict:
        """Create a timestamped auto-backup of critical data."""
        import os, shutil
        from datetime import datetime

        os.makedirs(self.BACKUP_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(self.BACKUP_DIR, f"auto_backup_{ts}")

        critical_dirs = ["data", "knowledge", "memory", "projects", "agents", "skills", "prompts"]
        critical_files = ["settings.json", "identity.md"]

        backed = []
        for d in critical_dirs:
            src = os.path.join(self.DATA_DIR, d)
            if os.path.isdir(src):
                dst = os.path.join(backup_path, d)
                shutil.copytree(src, dst, dirs_exist_ok=True)
                backed.append(d)

        for f in critical_files:
            src = os.path.join(self.DATA_DIR, f)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(backup_path, f))
                backed.append(f)

        self._clean_old_backups()
        return {"status": "ok", "backup": backup_path, "backed_up": backed, "message": f"Backup created: {ts}"}

    def _restore_latest(self) -> dict:
        """Restore from the most recent auto-backup."""
        import os, shutil
        all_backups = sorted([d for d in os.listdir(self.BACKUP_DIR) if d.startswith("auto_backup_")])
        if not all_backups:
            return {"status": "error", "error": "No auto-backups found"}
        return self._do_restore(all_backups[-1])

    def _restore_specific(self, name: str) -> dict:
        """Restore from a specific backup."""
        import os
        backup_path = os.path.join(self.BACKUP_DIR, name)
        if not os.path.isdir(backup_path):
            return {"status": "error", "error": f"Backup not found: {name}"}
        return self._do_restore(name)

    def _do_restore(self, backup_name: str) -> dict:
        """Internal restore implementation."""
        import os, shutil
        backup_path = os.path.join(self.BACKUP_DIR, backup_name)
        restored = []
        for item in os.listdir(backup_path):
            src = os.path.join(backup_path, item)
            dst = os.path.join(self.DATA_DIR, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
            restored.append(item)
        return {"status": "ok", "restored": restored, "backup": backup_name, "message": f"Restored from {backup_name}"}

    async def _restore_from_upload(self, input: dict, request: Request) -> dict:
        """Restore from an uploaded ZIP file."""
        import os, shutil, zipfile, tempfile

        try:
            # Get uploaded file from request
            upload = None
            if hasattr(request, 'files') and request.files:
                upload = request.files.get('backup_file')
            if not upload and hasattr(request, 'form'):
                upload = (await request.form()).get('backup_file')
            if not upload:
                return {"success": False, "error": "No file uploaded"}

            # Save uploaded ZIP to temp
            tmp_dir = tempfile.mkdtemp()
            zip_path = os.path.join(tmp_dir, "upload.zip")
            if hasattr(upload, 'read'):
                data = upload.read()
                if asyncio.iscoroutine(data):
                    data = await data
                with open(zip_path, "wb") as f:
                    f.write(data)
            else:
                shutil.copy2(upload.filename if hasattr(upload, 'filename') else str(upload), zip_path)

            # Extract ZIP
            extract_dir = os.path.join(tmp_dir, "extracted")
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(extract_dir)

            # Find the actual backup content (may be nested in a subfolder)
            items = os.listdir(extract_dir)
            source_dir = extract_dir
            if len(items) == 1 and os.path.isdir(os.path.join(extract_dir, items[0])):
                source_dir = os.path.join(extract_dir, items[0])

            # Restore files to DATA_DIR
            restored = []
            for item in os.listdir(source_dir):
                src = os.path.join(source_dir, item)
                dst = os.path.join(self.DATA_DIR, item)
                if os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
                restored.append(item)

            # Cleanup
            shutil.rmtree(tmp_dir, ignore_errors=True)

            return {"success": True, "restored_files": len(restored), "restored": restored,
                    "message": f"Restored {len(restored)} items from uploaded backup"}

        except Exception as e:
            return {"success": False, "error": f"Upload restore failed: {str(e)}"}

    def _download_backup(self, backup_id: str) -> Response:
        """Download a backup as ZIP."""
        import os, shutil, tempfile

        if not backup_id:
            # Use latest backup
            all_backups = sorted([d for d in os.listdir(self.BACKUP_DIR) if d.startswith("auto_backup_")])
            if not all_backups:
                return Response("No backups found", status_code=404)
            backup_id = all_backups[-1]

        backup_path = os.path.join(self.BACKUP_DIR, backup_id)
        if not os.path.isdir(backup_path):
            return Response(f"Backup not found: {backup_id}", status_code=404)

        # Create ZIP from backup directory
        tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        tmp.close()
        shutil.make_archive(tmp.name.replace(".zip", ""), 'zip', backup_path)

        return send_file(
            tmp.name,
            as_attachment=True,
            download_name=f"{backup_id}.zip",
            mimetype='application/zip'
        )

    def _delete_backup(self, backup_id: str) -> dict:
        """Delete a specific backup."""
        import os, shutil

        if not backup_id:
            return {"status": "error", "error": "No backup ID provided"}

        backup_path = os.path.join(self.BACKUP_DIR, backup_id)
        if not os.path.isdir(backup_path):
            return {"status": "error", "error": f"Backup not found: {backup_id}"}

        shutil.rmtree(backup_path, ignore_errors=True)
        return {"status": "ok", "message": f"Deleted backup: {backup_id}"}

    def _get_status(self) -> dict:
        """Get auto-backup status."""
        import os
        from datetime import datetime
        all_backups = sorted([d for d in os.listdir(self.BACKUP_DIR) if d.startswith("auto_backup_")])
        latest = all_backups[-1] if all_backups else None
        return {
            "status": "ok",
            "total_backups": len(all_backups),
            "latest": latest,
            "max_backups": self.MAX_BACKUPS,
            "backup_dir": self.BACKUP_DIR,
        }

    def _list_backups(self) -> dict:
        """List all auto-backups."""
        import os
        from datetime import datetime

        all_backups = sorted([d for d in os.listdir(self.BACKUP_DIR) if d.startswith("auto_backup_")], reverse=True)
        backup_list = []
        for b in all_backups:
            bp = os.path.join(self.BACKUP_DIR, b)
            size_mb = round(sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fns in os.walk(bp) for f in fns) / 1048576, 2) if os.path.isdir(bp) else 0
            created = datetime.fromtimestamp(os.path.getmtime(bp)).strftime("%Y-%m-%d %H:%M") if os.path.isdir(bp) else ""
            backup_list.append({"id": b, "zip_size_mb": size_mb, "has_zip": size_mb > 0, "complete": True, "created_at": created})
        return {"status": "ok", "backups": backup_list}

    def _clean_old_backups(self):
        """Keep only the last MAX_BACKUPS backups."""
        import os, shutil
        all_backups = sorted([d for d in os.listdir(self.BACKUP_DIR) if d.startswith("auto_backup_")])
        if len(all_backups) > self.MAX_BACKUPS:
            for old in all_backups[:-self.MAX_BACKUPS]:
                shutil.rmtree(os.path.join(self.BACKUP_DIR, old), ignore_errors=True)

