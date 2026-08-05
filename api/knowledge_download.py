"""Serve DOCX files for download from Knowledge Base."""
import os
from helpers.api import ApiHandler, Request, Response

KB_DIR = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "knowledge_base"))


def _is_safe_kb_path(filepath: str) -> bool:
    """Validate that filepath is within the knowledge base directory."""
    try:
        real = os.path.realpath(filepath)
        return real.startswith(KB_DIR + os.sep) or real == KB_DIR
    except (ValueError, OSError):
        return False


class KnowledgeDownloadHandler(ApiHandler):

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    async def process(self, input: dict, request: Request) -> dict | Response:
        filepath = request.args.get("file") or input.get("file", "")

        if not filepath:
            return Response(status=400, body="No file specified")

        if not _is_safe_kb_path(filepath):
            return Response(status=403, body="Access denied")

        if not os.path.exists(filepath):
            return Response(status=404, body="File not found")

        filename = os.path.basename(filepath)
        with open(filepath, "rb") as f:
            content = f.read()

        return Response(
            status=200,
            body=content,
            headers={
                "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(content)),
            },
        )
