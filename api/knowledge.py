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


def _store_docx_entry(category: str, title: str, docx_bytes: bytes, tags: str = "", source: str = "", metadata: dict = None, serial_num: int = 0):
    """Store a DOCX/PDF document in the knowledge base. No vector indexing for binary files.

    Deduplicates by DOI (from metadata) or title. Serial numbers prefix filenames.
    """
    import time as _time

    index = _load_index()

    # ── Dedup check: DOI ──
    doi = (metadata or {}).get("doi", "")
    if doi:
        for entry in index.get("entries", []):
            entry_doi = (entry.get("metadata") or {}).get("doi", "")
            if entry_doi and entry_doi == doi:
                log.debug(f"Dedup: skipping duplicate DOI {doi} — {title[:60]}")
                return entry

    # ── Dedup check: title ──
    title_key = title.strip().lower()
    for entry in index.get("entries", []):
        if entry.get("title", "").strip().lower() == title_key:
            log.debug(f"Dedup: skipping duplicate title — {title[:60]}")
            return entry

    cat_dir = os.path.join(KB_DIR, category)
    os.makedirs(cat_dir, exist_ok=True)

    # ── Serial-numbered filename ──
    safe_title = "".join(c for c in title[:60] if c.isalnum() or c in " _-").strip().replace(" ", "_")
    if not safe_title:
        safe_title = f"entry_{int(_time.time())}"

    if serial_num > 0:
        prefix = f"{serial_num:03d}_"
    else:
        prefix = ""
    filepath = os.path.join(cat_dir, f"{prefix}{safe_title}.docx")

    # Avoid overwrite
    counter = 1
    while os.path.exists(filepath):
        filepath = os.path.join(cat_dir, f"{prefix}{safe_title}_{counter}.docx")
        counter += 1

    with open(filepath, "wb") as f:
        f.write(docx_bytes)

    entry = {
        "id": f"{category}_{len(index['entries'])}",
        "title": title,
        "serial_num": serial_num if serial_num > 0 else len(index["entries"]) + 1,
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


def _delete_entry(entry_id: str) -> bool:
    """Delete an entry from KB index and filesystem."""
    index = _load_index()
    entries = index.get("entries", [])

    for i, e in enumerate(entries):
        if e.get("id") == entry_id or e.get("file") == entry_id:
            # Remove file
            filepath = e.get("file", "")
            if filepath and os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception as ex:
                    log.warning(f"Failed to delete file {filepath}: {ex}")

            # Remove from index
            cat = e.get("category", "")
            entries.pop(i)
            if cat in index.get("categories", {}):
                index["categories"][cat] = max(0, index["categories"][cat] - 1)
            _save_index(index)
            return True

    return False


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
        elif action == "download_docx":
            return self._download_docx(input)
        elif action == "delete_entry":
            return self._delete(input)
        elif action == "list_all":
            return self._list_all(input)
        elif action == "read_entry":
            return self._read_entry(input)

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
        """Upload files to KB with text extraction and indexing.

        Supports: TXT, MD, PDF, DOCX, XLSX, CSV, HTML, JSON, SDF, PDB, PDBQT, images, audio.
        Every file gets its readable content extracted and stored — users can always click to read.
        """
        try:
            files = input.get("files", [])
            category = input.get("category", "")
            tags = input.get("tags", "")

            if not files:
                return {"status": "error", "error": "No files provided"}

            stored = 0
            chunked = 0
            for file_data in files:
                filename = file_data.get("filename", "upload.txt")
                raw_content = file_data.get("content", "")

                if not category:
                    category = _detect_category(filename)

                # ── Extract readable text from binary uploads ──
                ext = os.path.splitext(filename)[1].lower().lstrip(".")
                content = ""

                if raw_content and len(raw_content) > 50:
                    # Frontend already sent text content (TXT, MD, CSV, JSON, HTML)
                    content = raw_content
                elif ext == "pdf":
                    content = self._extract_pdf_text(raw_content, filename)
                elif ext in ("docx", "doc"):
                    content = self._extract_docx_text(raw_content, filename)
                elif ext in ("xlsx", "xls"):
                    content = self._extract_xlsx_text(raw_content, filename)
                elif ext in ("pdb", "sdf", "mol", "mol2", "pdbqt"):
                    content = raw_content if raw_content else self._read_file_as_text(filename)
                elif ext in ("csv",):
                    content = raw_content if raw_content else ""
                elif raw_content:
                    content = raw_content
                else:
                    # Last resort: try to read as text
                    content = self._read_file_as_text(filename)

                if not content or len(content.strip()) < 10:
                    content = f"[File uploaded: {filename}] — Content could not be extracted. File type: {ext}. Size: {len(raw_content) if raw_content else 0} bytes."

                # Store the extracted content
                entry = _store_entry(category, filename, content, tags, source="File Upload")
                stored += 1

                # Chunk for vector indexing
                try:
                    from modules.rag.chunker import chunk_document
                    if content and len(content) > 200:
                        chunks = chunk_document(content, doc_id=filename)
                        if chunks:
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
                            except Exception:
                                pass
                except ImportError:
                    pass  # Chunker not available — content still stored as .md

            return {
                "status": "ok",
                "stored": stored,
                "chunked": chunked,
                "category": category,
                "message": f"Uploaded {stored} file(s) to {CATEGORIES.get(category, category)}, {chunked} chunks indexed",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _extract_pdf_text(self, raw_content: str, filename: str) -> str:
        """Extract text from a PDF using PyMuPDF (pymupdf)."""
        try:
            import fitz  # PyMuPDF
            import base64
            if raw_content and len(raw_content) > 100:
                pdf_bytes = base64.b64decode(raw_content)
            else:
                return ""
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            pages = []
            for page in doc[:50]:
                pages.append(page.get_text())
            doc.close()
            return "\n\n".join(pages).strip() if pages else ""
        except Exception:
            return ""

    def _extract_docx_text(self, raw_content: str, filename: str) -> str:
        """Extract text from a DOCX using python-docx."""
        try:
            from docx import Document
            import base64, io
            if raw_content and len(raw_content) > 100:
                doc_bytes = base64.b64decode(raw_content)
            else:
                return ""
            doc = Document(io.BytesIO(doc_bytes))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n\n".join(paragraphs).strip()
        except Exception:
            return ""

    def _extract_xlsx_text(self, raw_content: str, filename: str) -> str:
        """Extract text from XLSX using openpyxl."""
        try:
            import openpyxl, base64, io
            if raw_content and len(raw_content) > 100:
                wb_bytes = base64.b64decode(raw_content)
            else:
                return ""
            wb = openpyxl.load_workbook(io.BytesIO(wb_bytes), read_only=True, data_only=True)
            texts = []
            for sheet in wb.sheetnames:
                ws = wb[sheet]
                rows = []
                for row in ws.iter_rows(values_only=True):
                    row_str = [str(c) if c is not None else "" for c in row]
                    if any(row_str):
                        rows.append(" | ".join(row_str))
                if rows:
                    texts.append(f"## Sheet: {sheet}\n" + "\n".join(rows[:200]))
            wb.close()
            return "\n\n".join(texts).strip()
        except Exception:
            return ""

    def _read_file_as_text(self, filename: str) -> str:
        """Try to read a file from common upload locations as text."""
        import glob
        for pattern in ["usr/uploads/{}", "usr/workdir/{}", "data/{}", "data/knowledge_base/*_{}"]:
            matches = glob.glob(os.path.join(os.path.dirname(__file__), "..", pattern.format(filename)))
            for path in matches:
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        text = f.read(50000)
                    if len(text) > 10:
                        return text
                except Exception:
                    continue
        return ""

    def _delete(self, input: dict) -> dict:
        """Delete an entry from KB."""
        entry_id = input.get("id", "") or input.get("file", "")
        if not entry_id:
            return {"status": "error", "error": "No entry id provided"}
        ok = _delete_entry(entry_id)
        return {"status": "ok", "deleted": ok} if ok else {"status": "error", "error": "Entry not found"}

    def _list_all(self, input: dict) -> dict:
        """List ALL KB entries with metadata — no search required.
        Every entry enriched with source module label and upload type."""
        try:
            index = _load_index()
            entries = index.get("entries", [])

            # Source module label map
            SOURCE_LABELS = {
                "docking_run": ("🧬", "Docking"), "docking_analysis": ("🧬", "Docking Analysis"),
                "docking_mmgbsa": ("🧬", "MM-GBSA"), "literature_search": ("📚", "Literature Search"),
                "deep_research": ("🔍", "Deep Research"), "qsar3d": ("📊", "3D-QSAR"),
                "pharmacophore": ("💊", "Pharmacophore"), "drug_analysis": ("💊", "Drug Analysis"),
                "admet_predict": ("💊", "ADMET"), "statistics": ("📈", "Statistics"),
                "md_lite": ("⚗️", "MD Simulation"), "faculty": ("🎓", "Faculty"),
                "notes": ("📝", "Notes"), "upload": ("📁", "User Upload"),
            }

            for entry in entries:
                src = entry.get("source", "") or entry.get("module", "") or ""
                entry["source_module"] = src
                icon, label = SOURCE_LABELS.get(src, ("📄", src or "Knowledge Base"))
                entry["source_icon"] = icon
                entry["source_label"] = label
                entry["uploaded_by"] = "auto-store" if src and src != "upload" else "user-upload"

            entries.sort(key=lambda x: x.get("created_at", ""), reverse=True)

            return {
                "status": "ok",
                "entries": entries,
                "total": len(entries),
                "categories": index.get("categories", {}),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _read_entry(self, input: dict) -> dict:
        """Read full content of a single KB entry."""
        filepath = input.get("file", "")
        entry_id = input.get("entry_id", "")

        # If we have a file path, read it directly
        if filepath and os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                return {"status": "ok", "content": content, "file": filepath}
            except Exception as e:
                return {"status": "error", "error": f"Failed to read file: {e}"}

        # Otherwise find by entry_id in the index
        index = _load_index()
        for entry in index.get("entries", []):
            if entry.get("id") == entry_id or entry.get("file") == entry_id:
                filepath = entry.get("file", "")
                if filepath and os.path.exists(filepath):
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()
                        return {"status": "ok", "content": content, "file": filepath, "entry": entry}
                    except Exception as e:
                        return {"status": "error", "error": f"Failed to read file: {e}"}

        return {"status": "error", "error": "Entry not found or file missing"}

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

    def _download_docx(self, input: dict) -> dict | Response:
        """Serve a DOCX file for download."""
        filepath = input.get("file", "")
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
