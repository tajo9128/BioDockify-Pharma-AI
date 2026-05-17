from helpers.api import ApiHandler, Request, Response
from helpers import files
import os

JOBS_DIR = files.get_abs_path("tmp/docking_jobs")


class DockingDownload(ApiHandler):
    """Download docking output files (PDBQT, SDF, log)."""

    async def process(self, input: dict, request: Request) -> dict | Response:
        job_id = input.get("job_id", "")
        filename = input.get("filename", "docked_output.pdbqt")

        if not job_id:
            return {"error": "Missing job_id"}

        filepath = os.path.join(JOBS_DIR, job_id, os.path.basename(filename))

        if not os.path.exists(filepath):
            return {"error": f"File not found: {filename}"}

        # Determine MIME type
        ext = os.path.splitext(filename)[1].lower()
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
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
