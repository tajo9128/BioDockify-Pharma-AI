"""Knowledge Base API — central hub for all research data.
All modules store data here. Academic Writer, Slides, Faculty CMD read from here."""
from helpers.api import ApiHandler, Request, Response
import os, json, logging, time

log = logging.getLogger("knowledge_api")

KB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "knowledge_base")
os.makedirs(KB_DIR, exist_ok=True)

# Category directories
CATEGORIES = {
    # Research Sources
    "literature": "Literature & Papers",
    "deep_research": "Deep Research",
    "web_scraping": "Web Scraping",
    "clinical_trials": "Clinical Trials",
    "patents": "Patents",
    # Computational
    "docking": "Docking Results",
    "drug_analysis": "Drug Analysis",
    "pharmacophore": "Pharmacophore",
    "qsar": "QSAR Models",
    "statistics": "Statistical Analysis",
    # Teaching
    "faculty": "Faculty & Teaching",
    # Wet Lab
    "wetlab": "Wet Lab & Experiments",
    # Uploads
    "books": "Books & References",
    "protocols": "Protocols & Methods",
    "data_files": "Data Files (CSV/XLSX)",
    "audio_video": "Audio & Video",
    # General
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


def _store_docx_entry(category: str, title: str, docx_bytes: bytes, tags: str = "", source: str = "", metadata: dict = None):
    """Store a DOCX document in the knowledge base. No vector indexing for binary files."""
    import time as _time

    cat_dir = os.path.join(KB_DIR, category)
    os.makedirs(cat_dir, exist_ok=True)

    safe_title = "".join(c for c in title[:80] if c.isalnum() or c in " _-").strip().replace(" ", "_")
    if not safe_title:
        safe_title = f"entry_{int(_time.time())}"
    filepath = os.path.join(cat_dir, f"{safe_title}.docx")

    counter = 1
    while os.path.exists(filepath):
        filepath = os.path.join(cat_dir, f"{safe_title}_{counter}.docx")
        counter += 1

    with open(filepath, "wb") as f:
        f.write(docx_bytes)

    index = _load_index()
    entry = {
        "id": f"{category}_{len(index['entries'])}",
        "title": title,
        "category": category,
        "category_label": CATEGORIES.get(category, category),
        "tags": tags.split(",") if tags else [],
        "source": source,
        "file": filepath,
        "created_at": _time.strftime("%Y-%m-%d %H:%M:%S"),
        "size": len(docx_bytes),
        "format": "docx",
    }
    if metadata:
        entry["metadata"] = metadata
    index["entries"].append(entry)
    index["categories"][category] = index["categories"].get(category, 0) + 1
    _save_index(index)

    return entry


def _detect_category(filename: str) -> str:
    """Auto-detect KB category from filename/extension."""
    ext = os.path.splitext(filename)[1].lower()
    name_lower = filename.lower()

    # By extension
    if ext == '.pdf':
        return "books"
    elif ext == '.docx':
        return "literature"
    elif ext in ('.xlsx', '.xls', '.csv'):
        return "data_files"
    elif ext in ('.mp3', '.wav', '.ogg', '.m4a', '.flac'):
        return "audio_video"
    elif ext in ('.mp4', '.avi', '.mkv', '.mov', '.webm'):
        return "audio_video"
    elif ext in ('.sdf', '.mol', '.mol2', '.pdb', '.pdbqt'):
        return "docking"

    # By filename keywords
    if any(kw in name_lower for kw in ('protocol', 'method', 'procedure', 'sop')):
        return "protocols"
    if any(kw in name_lower for kw in ('wetlab', 'experiment', 'lab_notebook', 'results')):
        return "wetlab"
    if any(kw in name_lower for kw in ('syllabus', 'lecture', 'homework', 'assignment')):
        return "faculty"
    if any(kw in name_lower for kw in ('patent', 'prior_art')):
        return "patents"
    if any(kw in name_lower for kw in ('clinical', 'trial', 'nct')):
        return "clinical_trials"
    if any(kw in name_lower for kw in ('docking', 'vina', 'pose', 'binding')):
        return "docking"
    if any(kw in name_lower for kw in ('qsar', 'model', 'prediction')):
        return "qsar"

    return "notes"


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
        elif action == "upload":
            return self._upload(input)
        elif action == "graph":
            return self._graph(input)

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
        """Re-index all knowledge files from all KB directories."""
        try:
            index = _load_index()
            existing_files = set(e.get("file", "") for e in index.get("entries", []))
            new_count = 0

            # Scan ALL knowledge directories
            scan_dirs = [
                os.path.join(os.path.dirname(__file__), "..", "data", "knowledge_base"),
                os.path.join(os.path.dirname(__file__), "..", "usr", "knowledge", "main"),
                os.path.join(os.path.dirname(__file__), "..", "usr", "knowledge", "custom"),
                os.path.join(os.path.dirname(__file__), "..", "usr", "knowledge", "solutions"),
            ]

            for scan_dir in scan_dirs:
                if not os.path.isdir(scan_dir):
                    continue
                for root, dirs, files_list in os.walk(scan_dir):
                    for fname in files_list:
                        if not fname.endswith((".md", ".txt", ".json")):
                            continue
                        fpath = os.path.join(root, fname)
                        if fpath in existing_files:
                            continue
                        try:
                            with open(fpath, "r", encoding="utf-8") as f:
                                content = f.read()
                            if len(content) < 20:
                                continue
                            # Extract category from path
                            rel_path = os.path.relpath(fpath, scan_dir)
                            parts = rel_path.split(os.sep)
                            category = parts[0] if len(parts) > 1 else "notes"
                            if category not in CATEGORIES:
                                category = "notes"
                            title = os.path.splitext(fname)[0].replace("_", " ").replace("-", " ").title()
                            entry = {
                                "id": f"{category}_{len(index['entries'])}",
                                "title": title,
                                "category": category,
                                "category_label": CATEGORIES.get(category, category),
                                "tags": [category],
                                "source": f"Re-indexed from {rel_path}",
                                "file": fpath,
                                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                                "size": len(content),
                            }
                            index["entries"].append(entry)
                            index["categories"][category] = index["categories"].get(category, 0) + 1
                            new_count += 1
                        except Exception:
                            continue

            _save_index(index)
            total = len(index.get("entries", []))
            return {"status": "ok", "indexed": total, "new": new_count, "message": f"Knowledge base: {total} entries ({new_count} new)"}
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

    def _upload(self, input: dict) -> dict:
        """Upload files to KB with chunking and indexing.
        
        Supports: TXT, MD, PDF, DOCX, XLSX, CSV, HTML, JSON, SDF, PDB, PDBQT
        Auto-detects category from file type if not specified.
        """
        try:
            files = input.get("files", [])
            category = input.get("category", "")  # Empty = auto-detect
            tags = input.get("tags", "")

            if not files:
                return {"status": "error", "error": "No files provided"}

            # Try to use chunker with multi-format support
            try:
                from modules.rag.chunker import chunk_document, extract_text_from_file
                use_chunker = True
            except ImportError:
                use_chunker = False

            stored = 0
            chunked = 0
            for file_data in files:
                filename = file_data.get("filename", "upload.txt")
                content = file_data.get("content", "")

                # Auto-detect category from file type if not specified
                if not category:
                    category = _detect_category(filename)

                if not content:
                    continue

                # Store file entry
                entry = _store_entry(category, filename, content, tags, source="File Upload")
                stored += 1

                # Chunk and index if chunker available
                if use_chunker and len(content) > 200:
                    try:
                        chunks = chunk_document(content, doc_id=filename)
                        if chunks:
                            # Store chunks in vector store
                            try:
                                from modules.rag.vector_store import get_vector_store
                                store = get_vector_store()
                                if store:
                                    texts = [c["text"] for c in chunks]
                                    metadatas = [{"doc_id": filename, "section": c.get("section_title", ""), "category": category} for c in chunks]
                                    add_fn = getattr(store, "add_documents", None) or getattr(store, "add_texts", None)
                                    if add_fn:
                                        add_fn(texts, metadatas)
                                        chunked += len(chunks)
                            except Exception as e:
                                log.debug(f"Vector indexing failed: {e}")
                    except Exception as e:
                        log.debug(f"Chunking failed: {e}")

            return {
                "status": "ok",
                "stored": stored,
                "chunked": chunked,
                "category": category,
                "message": f"Uploaded {stored} file(s) to {CATEGORIES.get(category, category)}, {chunked} chunks indexed",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _graph(self, input: dict) -> dict:
        """Build knowledge graph from KB entries."""
        try:
            from modules.rag.knowledge_graph import build_graph

            index = _load_index()
            entries = index.get("entries", [])

            # Load content for entries (limited to avoid memory issues)
            limit = min(int(input.get("limit", 50)), 100)
            graph_entries = []
            for entry in entries[:limit]:
                filepath = entry.get("file", "")
                content = ""
                if filepath and os.path.exists(filepath):
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()[:2000]  # Limit content for graph building
                    except Exception:
                        pass
                graph_entries.append({
                    "id": entry.get("id", ""),
                    "title": entry.get("title", ""),
                    "content": content,
                    "category": entry.get("category", ""),
                })

            graph = build_graph(graph_entries)
            return {"status": "ok", "graph": graph}
        except Exception as e:
            return {"status": "error", "error": str(e)}
