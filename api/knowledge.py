"""Knowledge Base API — Flask handler for research notebook upload/query."""
from helpers.api import ApiHandler, Request, Response
import os, logging

log = logging.getLogger("knowledge_api")

JOBS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "knowledge_uploads")
os.makedirs(JOBS_DIR, exist_ok=True)


class KnowledgeHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "query")

        if action == "query":
            query = input.get("query", "").strip()
            top_k = int(input.get("top_k", 10))
            if not query:
                return {"status": "error", "error": "Query required", "results": []}
            try:
                from modules.rag.vector_store import get_vector_store
                store = get_vector_store()
                results = store.search(query, k=top_k)
                return {
                    "status": "success",
                    "query": query,
                    "results": [
                        {"text": r.get("text", ""), "score": r.get("score", 0), "metadata": r.get("metadata", {})}
                        for r in results
                    ],
                }
            except Exception as e:
                log.warning(f"Knowledge query failed: {e}")
                return {"status": "error", "error": str(e), "results": []}

        if action == "import":
            # File upload handled via multipart form
            try:
                content = input.get("content", "")
                filename = input.get("filename", "upload.txt")
                if not content:
                    return {"success": False, "error": "No file content provided"}
                filepath = os.path.join(JOBS_DIR, filename)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                return {"success": True, "count": 1, "message": f"File '{filename}' uploaded successfully", "path": filepath}
            except Exception as e:
                return {"success": False, "error": str(e)}

        if action == "import_files":
            # Handle multiple files from multipart form
            try:
                files = input.get("files", [])
                if not files:
                    return {"success": False, "error": "No files provided"}
                count = 0
                for file_data in files:
                    filename = file_data.get("filename", "upload.txt")
                    content = file_data.get("content", "")
                    if content:
                        filepath = os.path.join(JOBS_DIR, filename)
                        with open(filepath, "w", encoding="utf-8") as f:
                            f.write(content)
                        count += 1
                return {"success": True, "count": count, "message": f"{count} file(s) uploaded"}
            except Exception as e:
                return {"success": False, "error": str(e)}

        return {"status": "error", "error": f"Unknown action: {action}"}
