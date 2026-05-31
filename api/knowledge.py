"""Knowledge Base API — Flask handler for research notebook upload/query/reindex."""
from helpers.api import ApiHandler, Request, Response
import os, logging

log = logging.getLogger("knowledge_api")

JOBS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "knowledge_uploads")
os.makedirs(JOBS_DIR, exist_ok=True)


def _get_vector_store():
    """Get vector store with graceful fallback."""
    try:
        from modules.rag.vector_store import get_vector_store
        return get_vector_store()
    except Exception as e:
        log.warning(f"Vector store unavailable: {e}")
        return None


def _index_content(store, content: str, filename: str, tags: str = ""):
    """Index content into vector store with chunking."""
    if not store:
        return False, "Vector store unavailable"
    try:
        add_fn = getattr(store, "add_documents", None) or getattr(store, "add_texts", None)
        if not add_fn:
            return False, "Vector store has no add method"
        
        # Split into chunks of ~500 chars
        chunks = []
        for i in range(0, len(content), 500):
            chunk = content[i:i+500].strip()
            if chunk:
                chunks.append(chunk)
        
        if not chunks:
            return False, "No content to index"
        
        metadatas = [{"source": filename, "tags": tags, "filename": filename}] * len(chunks)
        
        import asyncio
        result = add_fn(chunks, metadatas)
        if asyncio.iscoroutine(result):
            import asyncio
            asyncio.get_event_loop().run_until_complete(result)
        
        return True, f"{len(chunks)} chunks indexed"
    except Exception as e:
        return False, str(e)


class KnowledgeHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "query")

        if action == "query":
            return await self._query(input)
        elif action == "import":
            return self._import_single(input)
        elif action == "import_files":
            return self._import_multiple(input)
        elif action == "reindex":
            return self._reindex()
        elif action == "status":
            return self._status()

        return {"status": "error", "error": f"Unknown action: {action}"}

    async def _query(self, input: dict) -> dict:
        query = input.get("query", "").strip()
        top_k = int(input.get("top_k", 10))
        if not query:
            return {"status": "error", "error": "Query required", "results": []}
        try:
            store = _get_vector_store()
            if not store:
                return {"status": "error", "error": "Vector store not available. Install chromadb/faiss.", "results": []}
            search_fn = store.search
            if callable(search_fn):
                import asyncio
                result = search_fn(query, k=top_k)
                if asyncio.iscoroutine(result):
                    results = await result
                else:
                    results = result
            else:
                results = []
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

    def _import_single(self, input: dict) -> dict:
        """Import a single file and index it."""
        try:
            content = input.get("content", "")
            filename = input.get("filename", "upload.txt")
            tags = input.get("tags", "")
            if not content:
                return {"success": False, "error": "No file content provided"}
            
            # Save to disk
            filepath = os.path.join(JOBS_DIR, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            
            # Index into vector store
            store = _get_vector_store()
            indexed, index_msg = _index_content(store, content, filename, tags)
            
            return {
                "success": True,
                "count": 1,
                "indexed": indexed,
                "index_detail": index_msg,
                "message": f"File '{filename}' uploaded" + (" and indexed" if indexed else f" (index failed: {index_msg})"),
                "path": filepath,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _import_multiple(self, input: dict) -> dict:
        """Import multiple files and index them."""
        try:
            files = input.get("files", [])
            if not files:
                return {"success": False, "error": "No files provided"}
            
            store = _get_vector_store()
            count = 0
            indexed_count = 0
            for file_data in files:
                filename = file_data.get("filename", "upload.txt")
                content = file_data.get("content", "")
                tags = file_data.get("tags", "")
                if content:
                    filepath = os.path.join(JOBS_DIR, filename)
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)
                    count += 1
                    indexed, _ = _index_content(store, content, filename, tags)
                    if indexed:
                        indexed_count += 1
            
            return {
                "success": True,
                "count": count,
                "indexed": indexed_count,
                "message": f"{count} file(s) uploaded, {indexed_count} indexed",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _reindex(self) -> dict:
        """Re-index all knowledge files into vector store."""
        try:
            store = _get_vector_store()
            if not store:
                return {"status": "error", "error": "Vector store not available"}
            
            # Scan knowledge directories
            knowledge_dirs = [
                os.path.join(os.path.dirname(__file__), "..", "knowledge", "main"),
                os.path.join(os.path.dirname(__file__), "..", "usr", "knowledge"),
                JOBS_DIR,
            ]
            
            indexed = 0
            errors = 0
            for kd in knowledge_dirs:
                if not os.path.isdir(kd):
                    continue
                for root, dirs, files in os.walk(kd):
                    for f in files:
                        if f.endswith((".md", ".txt", ".json")):
                            fpath = os.path.join(root, f)
                            try:
                                with open(fpath, "r", encoding="utf-8") as fh:
                                    content = fh.read()
                                if len(content) > 50:
                                    ok, _ = _index_content(store, content, f)
                                    if ok:
                                        indexed += 1
                            except Exception:
                                errors += 1
            
            # Trigger memory reload if available
            try:
                from plugins._memory.helpers.memory import Memory
                log.info("Memory reload triggered after reindex")
            except Exception:
                pass
            
            return {
                "status": "ok",
                "indexed": indexed,
                "errors": errors,
                "message": f"Re-indexed {indexed} files" + (f" ({errors} errors)" if errors else ""),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _status(self) -> dict:
        """Get knowledge base status."""
        try:
            store = _get_vector_store()
            has_store = store is not None
            
            # Count files in knowledge dirs
            file_count = 0
            for kd in [
                os.path.join(os.path.dirname(__file__), "..", "knowledge", "main"),
                os.path.join(os.path.dirname(__file__), "..", "usr", "knowledge"),
                JOBS_DIR,
            ]:
                if os.path.isdir(kd):
                    for root, dirs, files in os.walk(kd):
                        file_count += len([f for f in files if f.endswith((".md", ".txt", ".json"))])
            
            return {
                "status": "ok",
                "vector_store": "available" if has_store else "not installed",
                "total_files": file_count,
                "upload_dir": JOBS_DIR,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
