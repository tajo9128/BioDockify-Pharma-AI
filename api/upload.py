from helpers.api import ApiHandler, Request, Response
from helpers import files
from helpers.security import safe_filename
import os


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
                except Exception as e:
                    return {"error": f"Failed to save '{filename}': {str(e)}", "filenames": saved_filenames}

        if not saved_filenames:
            return {"error": "No valid files found", "filenames": []}

        return {"filenames": saved_filenames}


    def allowed_file(self,filename):
        return True
        # ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "txt", "pdf", "csv", "html", "json", "md"}
        # return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS