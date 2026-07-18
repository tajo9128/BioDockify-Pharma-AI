from helpers.api import ApiHandler, Request, Response
from helpers import files
from helpers.security import safe_filename
import os
import logging

log = logging.getLogger("upload")


class UploadFile(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        if "file" not in request.files:
            return {"error": "No file uploaded", "filenames": []}

        file_list = request.files.getlist("file")  # Handle multiple files
        saved_filenames = []

        upload_dir = files.get_abs_path("usr/uploads")
        os.makedirs(upload_dir, exist_ok=True)

        for file in file_list:
            if file and file.filename and self.allowed_file(file.filename):
                filename = safe_filename(file.filename)
                if not filename:
                    continue
                filepath = os.path.join(upload_dir, filename)
                try:
                    file.save(filepath)
                    saved_filenames.append(filename)

                    # ── AUTO-STORE every uploaded file to Knowledge Base ──
                    try:
                        from modules.knowledge.auto_store import auto_store_file
                        ext = os.path.splitext(filename)[1].lower().lstrip(".")
                        # Auto-detect category from extension
                        cat = "notes"
                        if ext in ("pdf",):
                            cat = "books"
                        elif ext in ("csv", "xlsx", "xls"):
                            cat = "data_files"
                        elif ext in ("pdb", "sdf", "mol", "mol2", "pdbqt"):
                            cat = "docking"
                        elif ext in ("doc", "docx", "txt", "md"):
                            cat = "notes"
                        elif ext in ("mp3", "wav", "mp4", "avi"):
                            cat = "audio_video"

                        auto_store_file("upload", filename, filepath,
                                       source="User Upload", category=cat,
                                       tags=[cat, ext] if ext else [cat])
                    except Exception as kb_err:
                        log.debug(f"KB auto-store upload (non-fatal): {kb_err}")

                except Exception as e:
                    return {"error": f"Failed to save '{filename}': {str(e)}", "filenames": saved_filenames}

        if not saved_filenames:
            return {"error": "No valid files found", "filenames": []}

        return {"filenames": saved_filenames}


    def allowed_file(self,filename):
        """Validate file extension against whitelist."""
        ALLOWED_EXTENSIONS = {
            '.txt', '.md', '.pdf', '.docx', '.doc', '.xlsx', '.xls', '.csv',
            '.json', '.sdf', '.mol', '.mol2', '.pdb', '.pdbqt', '.html', '.htm',
            '.mp3', '.wav', '.ogg', '.m4a', '.flac', '.mp4', '.avi', '.mkv', '.mov', '.webm',
            '.png', '.jpg', '.jpeg', '.gif', '.svg', '.bmp', '.tiff',
            '.py', '.ipynb', '.r', '.R', '.ipynb',
        }
        ext = '.' + filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        return ext in ALLOWED_EXTENSIONS