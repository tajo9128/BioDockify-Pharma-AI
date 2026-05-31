"""Knowledge Base API — central hub for all research data.
All modules store data here. Academic Writer, Slides, Faculty CMD read from here."""
from helpers.api import ApiHandler, Request, Response
import os, json, logging, time

log = logging.getLogger("knowledge_api")

KB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "knowledge_base")
os.makedirs(KB_DIR, exist_ok=True)

# Category directories
CATEGORIES = {
    "literature": "Literature & Papers",
    "deep_research": "Deep Research",
    "faculty": "Faculty & Teaching",
    "docking": "Docking Results",
    "drug_analysis": "Drug Analysis",
    "pharmacophore": "Pharmacophore",
    "qsar": "QSAR Models",
    "statistics": "Statistical Analysis",
    "clinical_trials": "Clinical Trials",
    "patents": "Patents",
    "notes": "Research Notes",
    "misc": "Miscellaneous",
}

INDEX_FILE = os.path.join(KB_DIR, "index.json")


def _load_index():
    if os.path.exists(INDEX_FILE):
        try:
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"entries": [], "categories": {}}


def _save_index(index):
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def _store_entry(category: str, title: str, content: str, tags: str = "", source: str = "", metadata: dict = None):
    """Store an entry in the knowledge base with category."""
    cat_dir = os.path.join(KB_DIR, category)
    os.makedirs(cat_dir, exist_ok=True)

    # Create filename from title
    safe_title = "".join(c for c in title[:50] if c.isalnum() or c in " _-").strip().replace(" ", "_")
    if not safe_title:
        safe_title = f"entry_{int(time.time())}"
    filepath = os.path.join(cat_dir, f"{safe_title}.md")

    # Write content
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        if tags:
            f.write(f"**Tags:** {tags}\n\n")
        if source:
            f.write(f"**Source:** {source}\n\n")
        f.write(content)

    # Update index
    index = _load_index()
    entry = {
        "id": f"{category}_{len(index['entries'])}",
        "title": title,
        "category": category,
        "category_label": CATEGORIES.get(category, category),
        "tags": tags.split(",") if tags else [],
        "source": source,
        "file": filepath,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "size": len(content),
    }
    if metadata:
        entry["metadata"] = metadata
    index["entries"].append(entry)
    index["categories"][category] = index["categories"].get(category, 0) + 1
    _save_index(index)

    # Also index into vector store if available
    try:
        from modules.rag.vector_store import get_vector_store
        store = get_vector_store()
        if store:
            chunks = [content[i:i+500].strip() for i in range(0, len(content), 500) if content[i:i+500].strip()]
            metadatas = [{"source": title, "category": category, "tags": tags}] * len(chunks)
            add_fn = getattr(store, "add_documents", None) or getattr(store, "add_texts", None)
            if add_fn and chunks:
                add_fn(chunks, metadatas)
    except Exception as e:
        log.debug(f"Vector indexing skipped: {e}")

    return entry


class KnowledgeHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "query")

        if action == "query":
            return await self._query(input)
        elif action == "store":
            return self._store(input)
        elif action == "import":
            return self._import_single(input)
        elif action == "import_files":
            return self._import_multiple(input)
        elif action == "reindex":
            return self._reindex()
        elif action == "status":
            return self._status()
        elif action == "categories":
            return self._categories()
        elif action == "library":
            return self._library(input)

        return {"status": "error", "error": f"Unknown action: {action}"}

    async def _query(self, input: dict) -> dict:
        query = input.get("query", "").strip()
        top_k = int(input.get("top_k", 10))
        if not query:
            return {"status": "error", "error": "Query required", "results": []}
        try:
            from modules.rag.vector_store import get_vector_store
            store = get_vector_store()
            if not store:
                return {"status": "error", "error": "Vector store not available", "results": []}
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

    def _store(self, input: dict) -> dict:
        """Store content in knowledge base with category."""
        category = input.get("category", "misc")
        title = input.get("title", "Untitled")
        content = input.get("content", "")
        tags = input.get("tags", "")
        source = input.get("source", "")
        metadata = input.get("metadata", None)

        if not content:
            return {"status": "error", "error": "No content provided"}

        try:
            entry = _store_entry(category, title, content, tags, source, metadata)
            return {"status": "ok", "entry": entry, "message": f"Stored in {CATEGORIES.get(category, category)}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _import_single(self, input: dict) -> dict:
        """Import a single file and index it."""
        try:
            content = input.get("content", "")
            filename = input.get("filename", "upload.txt")
            category = input.get("category", "notes")
            tags = input.get("tags", "")
            if not content:
                return {"success": False, "error": "No file content provided"}

            entry = _store_entry(category, filename, content, tags, source="File Upload")
            return {"success": True, "count": 1, "entry": entry, "message": f"File '{filename}' stored in {CATEGORIES.get(category, category)}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _import_multiple(self, input: dict) -> dict:
        """Import multiple files."""
        try:
            files = input.get("files", [])
            category = input.get("category", "notes")
            if not files:
                return {"success": False, "error": "No files provided"}
            count = 0
            for file_data in files:
                filename = file_data.get("filename", "upload.txt")
                content = file_data.get("content", "")
                tags = file_data.get("tags", "")
                if content:
                    _store_entry(category, filename, content, tags, source="File Upload")
                    count += 1
            return {"success": True, "count": count, "message": f"{count} file(s) stored in {CATEGORIES.get(category, category)}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _reindex(self) -> dict:
        """Re-index all knowledge files."""
        try:
            index = _load_index()
            indexed = len(index.get("entries", []))
            return {"status": "ok", "indexed": indexed, "message": f"Knowledge base has {indexed} entries"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _status(self) -> dict:
        """Get knowledge base status."""
        try:
            index = _load_index()
            entries = index.get("entries", [])
            categories = index.get("categories", {})
            return {
                "status": "ok",
                "total_entries": len(entries),
                "categories": categories,
                "category_labels": CATEGORIES,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _categories(self) -> dict:
        """Get available categories."""
        return {"status": "ok", "categories": CATEGORIES}

    def _library(self, input: dict) -> dict:
        """Get library contents by category."""
        category = input.get("category", "")
        limit = int(input.get("limit", 50))

        index = _load_index()
        entries = index.get("entries", [])

        if category:
            entries = [e for e in entries if e.get("category") == category]

        entries.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return {"status": "ok", "entries": entries[:limit], "total": len(entries)}
