"""Serve DOCX files for download from Knowledge Base."""
import os
from helpers.api import ApiHandler, Request, Response


class KnowledgeDownloadHandler(ApiHandler):

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    async def process(self, input: dict, request: Request) -> dict | Response:
        filepath = request.args.get("file") or input.get("file", "")

        if not filepath or not os.path.exists(filepath):
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
