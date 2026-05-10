import os
import shutil
import zipfile
import tempfile
from datetime import datetime
from .drive_client import DriveClient
from .crypto import BackupCrypto

class BackupManager:
    def __init__(self, drive_client: DriveClient):
        self.drive = drive_client
        self.crypto = BackupCrypto(password="biodockify_secure_default") # In prod, get from user settings
        self.temp_dir = os.path.join(tempfile.gettempdir(), "agent_zero_backup_temp")
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)

    def create_backup(self, source_dirs: list[str]) -> dict:
        """
        Creates a snapshot of the source directories, encrypts it, and uploads to Drive.
        """
        if not self.drive.is_connected():
            return {"status": "error", "message": "Not connected to Cloud Storage"}

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        archive_name = f"snapshot_{timestamp}"
        zip_path = os.path.join(self.temp_dir, f"{archive_name}.zip")
        enc_path = os.path.join(self.temp_dir, f"{archive_name}.enc")

        try:
            # 1. Zip
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for folder in source_dirs:
                    if os.path.exists(folder):
                        base_name = os.path.basename(folder)
                        for root, _, files in os.walk(folder):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.join(base_name, os.path.relpath(file_path, folder))
                                zipf.write(file_path, arcname)

            # 2. Encrypt
            self.crypto.encrypt_file(zip_path, enc_path)

            # 3. Upload
            file_id = self.drive.upload_snapshot(enc_path, f"{archive_name}.enc")

            return {
                "status": "success", 
                "file_id": file_id, 
                "timestamp": timestamp,
                "size_bytes": os.path.getsize(enc_path)
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            # Cleanup
            if os.path.exists(zip_path): os.remove(zip_path)
            if os.path.exists(enc_path): os.remove(enc_path)

    def restore_backup(self, snapshot_id: str, dest_root: str) -> dict:
        """
        Restores a backup to the dest_root.
        """
        if not self.drive.is_connected():
            return {"status": "error", "message": "Not connected"}

        enc_path = os.path.join(self.temp_dir, "restore_temp.enc")
        zip_path = os.path.join(self.temp_dir, "restore_temp.zip")

        try:
            # 1. Download
            self.drive.download_snapshot(snapshot_id, enc_path)

            # 2. Decrypt
            self.crypto.decrypt_file(enc_path, zip_path)

            # 3. Unzip
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                zipf.extractall(dest_root)

            return {"status": "success", "message": "Restored successfully"}

        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            if os.path.exists(enc_path): os.remove(enc_path)
            if os.path.exists(zip_path): os.remove(zip_path)
