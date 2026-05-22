from helpers.api import ApiHandler, Request, Response
from helpers import files
import os
import logging

log = logging.getLogger("docking_download")
JOBS_DIR = files.get_abs_path("tmp/docking_jobs")


class DockingDownload(ApiHandler):
    """Download docking output files (PDBQT poses, SDF, log) via GET query params."""

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    async def process(self, input: dict, request: Request) -> dict | Response:
        # Support both GET query params and POST JSON body
        job_id = request.args.get("job_id") or input.get("job_id", "")
        filename = request.args.get("filename") or input.get("filename", "docked_output.pdbqt")

        if not job_id:
            return {"error": "Missing job_id"}

        # Sanitize filename to prevent path traversal
        safe_name = os.path.basename(filename)
        filepath = os.path.join(JOBS_DIR, job_id, safe_name)

        if not os.path.exists(filepath):
            return {"error": f"File not found: {safe_name}"}

        ext = os.path.splitext(safe_name)[1].lower()
        mime_map = {
            ".pdbqt": "chemical/x-pdbqt",
            ".pdb": "chemical/x-pdb",
            ".sdf": "chemical/x-sdf",
            ".mol": "chemical/x-mdl-molfile",
            ".txt": "text/plain",
            ".log": "text/plain",
            ".csv": "text/csv",
        }
        mime = mime_map.get(ext, "application/octet-stream")

        with open(filepath, "r") as f:
            content = f.read()

        return Response(
            response=content,
            status=200,
            mimetype=mime,
            headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
        )
