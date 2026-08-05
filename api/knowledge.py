"""Knowledge Base API — central hub for all research data.
All modules store data here. Academic Writer, Slides, Faculty CMD read from here."""
from helpers.api import ApiHandler, Request, Response
import os, json, logging, time

log = logging.getLogger("knowledge_api")

KB_DIR = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "knowledge_base"))
os.makedirs(KB_DIR, exist_ok=True)
CONV_DIR = os.path.join(KB_DIR, "conversations")
os.makedirs(CONV_DIR, exist_ok=True)


def _is_safe_kb_path(filepath: str) -> bool:
    """Validate that filepath is within the knowledge base directory (prevents path traversal)."""
    try:
        real = os.path.realpath(filepath)
        return real.startswith(KB_DIR + os.sep) or real == KB_DIR
    except (ValueError, OSError):
        return False

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
    "md_simulation": "MD Simulations",
    # Teaching
    "faculty": "Faculty & Teaching",
    # Wet Lab
    "wetlab": "Wet Lab & Experiments",
    # Departments
    "pharmacology": "Pharmacology",
    "medicinal_chemistry": "Medicinal Chemistry",
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
_INDEX_LOCK_FILE = INDEX_FILE + ".lock"


def _lock_index():
    """Acquire a file-based lock for index.json writes (cross-platform)."""
    import time as _t
    lock_path = _INDEX_LOCK_FILE
    deadline = _t.time() + 10
    while _t.time() < deadline:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return True
        except FileExistsError:
            # Stale lock check (older than 30s = dead process)
            try:
                if _t.time() - os.path.getmtime(lock_path) > 30:
                    os.remove(lock_path)
                    continue
            except OSError:
                pass
            _t.sleep(0.05)
    # Timeout — force remove stale lock
    try:
        os.remove(lock_path)
    except OSError:
        pass
    return False


def _unlock_index():
    try:
        os.remove(_INDEX_LOCK_FILE)
    except OSError:
        pass


def _load_index():
    if os.path.exists(INDEX_FILE):
        try:
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"entries": [], "categories": {}}


def _save_index(index):
    _lock_index()
    try:
        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
    finally:
        _unlock_index()


def _store_entry(category: str, title: str, content: str, tags: str = "", source: str = "", metadata: dict = None, original_file: str = ""):
    """Store an entry in the knowledge base with category.

    Every entry is saved as BOTH a .md (fast reading) and a .docx (downloadable/podcast/review).
    If original_file is provided, the path is stored so the PDF/DOCX can be viewed/downloaded.
    """
    cat_dir = os.path.join(KB_DIR, category)
    os.makedirs(cat_dir, exist_ok=True)

    # Create filename from title + timestamp (prevents same-title overwrite & ghost index rows)
    safe_title = "".join(c for c in title[:50] if c.isalnum() or c in " _-").strip().replace(" ", "_")
    if not safe_title:
        safe_title = "entry"
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(cat_dir, f"{safe_title}_{timestamp}.md")
    docx_path = os.path.join(cat_dir, f"{safe_title}_{timestamp}.docx")

    # Write .md (fast read format)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        if tags:
            f.write(f"**Tags:** {tags}\n\n")
        if source:
            f.write(f"**Source:** {source}\n\n")
        f.write(content)

    # Generate .docx (downloadable document format)
    try:
        _generate_docx(title, content, tags, source, docx_path)
    except Exception:
        docx_path = None  # .docx generation failed — .md still works

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
        "docx_file": docx_path,  # downloadable .docx
        "original_file": original_file,  # original binary (PDF/DOCX) for viewing/downloading
        "file_type": os.path.splitext(original_file)[1].lstrip(".") if original_file else "md",
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
        import asyncio, inspect, threading
        store = get_vector_store()
        if store:
            chunk_size = 1500
            overlap = 200
            chunks = []
            for i in range(0, len(content), chunk_size - overlap):
                chunk = content[i:i + chunk_size].strip()
                if chunk:
                    chunks.append(chunk)
            metadatas = [{"source": title, "category": category, "tags": tags}] * len(chunks)
            add_fn = getattr(store, "add_documents", None) or getattr(store, "add_texts", None)
            if add_fn and chunks:
                if inspect.iscoroutinefunction(add_fn):
                    def _run_async():
                        try:
                            asyncio.run(add_fn(chunks, metadatas))
                        except Exception as exc:
                            log.warning(f"Vector indexing failed: {exc}")
                    threading.Thread(target=_run_async, daemon=True).start()
                else:
                    add_fn(chunks, metadatas)
    except Exception as e:
        log.debug(f"Vector indexing skipped: {e}")

    return entry


def _generate_docx(title: str, content: str, tags: str, source: str, docx_path: str):
    """Generate a proper .docx file from markdown content."""
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()

    # Title
    p = doc.add_heading(title, level=1)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT

    # Metadata line
    meta_parts = []
    if source:
        meta_parts.append(f"Source: {source}")
    if tags:
        meta_parts.append(f"Tags: {tags}")
    if meta_parts:
        p = doc.add_paragraph()
        run = p.add_run("  |  ".join(meta_parts))
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(128, 128, 128)

    doc.add_paragraph()  # spacer

    # Content — convert markdown to docx paragraphs
    lines = content.split("\n")
    in_list = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            doc.add_paragraph()
            in_list = False
            continue

        # Headings
        if stripped.startswith("## "):
            doc.add_heading(stripped[3:], level=2)
            in_list = False
        elif stripped.startswith("### "):
            doc.add_heading(stripped[4:], level=3)
            in_list = False
        elif stripped.startswith("#### "):
            doc.add_heading(stripped[5:], level=4)
            in_list = False
        elif stripped.startswith("# "):
            doc.add_heading(stripped[2:], level=1)
            in_list = False
        # Bold lines
        elif stripped.startswith("**") and stripped.endswith("**"):
            p = doc.add_paragraph()
            run = p.add_run(stripped.strip("*"))
            run.bold = True
            in_list = False
        # List items
        elif stripped.startswith("- ") or stripped.startswith("* "):
            p = doc.add_paragraph(stripped[2:], style="List Bullet")
            in_list = True
        # Numbered items
        elif len(stripped) > 2 and stripped[0].isdigit() and stripped[1] in (".", ")"):
            p = doc.add_paragraph(stripped[3:] if len(stripped) > 3 else stripped[2:], style="List Number")
            in_list = True
        # Regular paragraph
        else:
            doc.add_paragraph(stripped)
            in_list = False

    doc.save(docx_path)


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
            # Remove .md file
            filepath = e.get("file", "")
            if filepath and os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception as ex:
                    log.warning(f"Failed to delete file {filepath}: {ex}")

            # Remove .docx file
            docx_path = e.get("docx_file", "")
            if docx_path and os.path.exists(docx_path):
                try:
                    os.remove(docx_path)
                except Exception:
                    pass

            # Remove original binary file
            original_path = e.get("original_file", "")
            if original_path and os.path.exists(original_path):
                try:
                    os.remove(original_path)
                except Exception:
                    pass

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
    """Knowledge Base API — listing/reading is public, writing requires auth."""

    @classmethod
    def requires_auth(cls) -> bool:
        return False  # KB listing/reading is public; writing actions are gated below

    # Actions that modify data — require auth
    _WRITE_ACTIONS = {"store", "import", "import_files", "reindex",
                      "upload", "delete_entry", "create_notebook",
                      "delete_notebook", "add_source_to_notebook",
                      "remove_source_from_notebook", "add_note",
                      "delete_note", "create_transformation", "run_transformation"}

    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "query")

        # Gate write actions behind auth
        if action in self._WRITE_ACTIONS:
            from helpers import login
            from flask import session
            if login.get_credentials_hash() and session.get("authentication") != login.get_credentials_hash():
                return {"error": "Authentication required for write operations", "status": 403}

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
        elif action == "download_original":
            return self._download_original(input)
        elif action == "view_file":
            return self._view_file(input)
        elif action == "delete_entry":
            return self._delete(input)
        elif action == "list_all":
            return self._list_all(input)
        elif action == "read_entry":
            return self._read_entry(input)
        # ── Notebook LM features ──
        elif action == "create_notebook":
            return self._create_notebook(input)
        elif action == "list_notebooks":
            return self._list_notebooks()
        elif action == "delete_notebook":
            return self._delete_notebook(input)
        elif action == "add_source_to_notebook":
            return self._add_source_to_notebook(input)
        elif action == "remove_source_from_notebook":
            return self._remove_source_from_notebook(input)
        elif action == "add_note":
            return self._add_note(input)
        elif action == "list_notes":
            return self._list_notes(input)
        elif action == "delete_note":
            return self._delete_note(input)
        elif action == "create_transformation":
            return self._create_transformation(input)
        elif action == "list_transformations":
            return self._list_transformations()
        elif action == "run_transformation":
            return self._run_transformation(input)
        elif action == "generate_podcast":
            return await self._generate_podcast(input)
        elif action == "kb_chat":
            return await self._kb_chat(input)
        elif action == "list_conversations":
            return self._list_conversations(input)
        elif action == "get_conversation":
            return self._get_conversation(input)
        elif action == "delete_conversation":
            return self._delete_conversation(input)
        elif action == "generate_study_guide":
            return await self._generate_study_guide(input)
        elif action == "generate_briefing":
            return await self._generate_briefing(input)
        elif action == "suggest_questions":
            return await self._suggest_questions(input)
        elif action == "summarize_source":
            return await self._summarize_source(input)

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
        MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB per file
        MAX_TOTAL_SIZE = 200 * 1024 * 1024  # 200MB total per upload

        try:
            files = input.get("files", [])
            category = input.get("category", "")
            tags = input.get("tags", "")

            if not files:
                return {"status": "error", "error": "No files provided"}

            # Size validation
            total_size = 0
            for file_data in files:
                raw_content = file_data.get("content", "")
                file_size = len(raw_content) if raw_content else 0
                total_size += file_size
                if file_size > MAX_FILE_SIZE:
                    return {"status": "error", "error": f"File '{file_data.get('filename', 'unknown')}' exceeds 50MB limit ({file_size // (1024*1024)}MB)"}
            if total_size > MAX_TOTAL_SIZE:
                return {"status": "error", "error": f"Total upload size exceeds 200MB limit ({total_size // (1024*1024)}MB)"}

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
                original_path = ""

                # Binary formats that arrive as base64 — extract text AND save original
                BINARY_EXTS = {"pdf", "docx", "doc", "xlsx", "xls", "png", "jpg", "jpeg", "mp3", "wav", "mp4", "avi"}

                if ext in BINARY_EXTS and raw_content:
                    # Save the ORIGINAL binary file so it can be viewed/downloaded later
                    original_path = self._save_original(raw_content, filename, category)
                    # Extract text from the binary
                    if ext == "pdf":
                        content = self._extract_pdf_text(raw_content, filename)
                    elif ext in ("docx", "doc"):
                        content = self._extract_docx_text(raw_content, filename)
                    elif ext in ("xlsx", "xls"):
                        content = self._extract_xlsx_text(raw_content, filename)
                    else:
                        content = f"[Binary file: {filename}]"
                elif ext in ("pdb", "sdf", "mol", "mol2", "pdbqt"):
                    content = raw_content if raw_content else self._read_file_as_text(filename)
                elif ext in ("csv", "txt", "md", "json", "html", "htm"):
                    content = raw_content if raw_content else ""
                elif raw_content:
                    content = raw_content
                else:
                    content = self._read_file_as_text(filename)

                if not content or len(content.strip()) < 10:
                    content = f"[File uploaded: {filename}] — Content could not be extracted. File type: {ext}. Size: {len(raw_content) if raw_content else 0} bytes."

                # Store the extracted content (+ original file path if binary)
                entry = _store_entry(category, filename, content, tags, source="File Upload", original_file=original_path)
                stored += 1

                # Chunk for vector indexing
                try:
                    from modules.rag.chunker import chunk_document
                    import asyncio, inspect, threading
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
                                        if inspect.iscoroutinefunction(add_fn):
                                            def _run_async(fn=add_fn, t=texts, m=metadatas):
                                                try:
                                                    asyncio.run(fn(t, m))
                                                except Exception:
                                                    pass
                                            threading.Thread(target=_run_async, daemon=True).start()
                                        else:
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

    def _save_original(self, base64_content: str, filename: str, category: str) -> str:
        """Save the original binary file (PDF/DOCX) so it can be viewed/downloaded later.

        Returns the absolute path to the saved file, or "" on failure.
        """
        try:
            import base64
            raw_bytes = base64.b64decode(base64_content)
            cat_dir = os.path.join(KB_DIR, category, "originals")
            os.makedirs(cat_dir, exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            safe_name = "".join(c for c in filename[:60] if c.isalnum() or c in "._-") or f"upload_{timestamp}"
            filepath = os.path.join(cat_dir, f"{safe_name}_{timestamp}")
            with open(filepath, "wb") as f:
                f.write(raw_bytes)
            return filepath
        except Exception as e:
            log.warning(f"Failed to save original file {filename}: {e}")
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
        """Read full content of a single KB entry.

        Returns the extracted markdown text for the reader, plus metadata
        about whether an original binary (PDF/DOCX) is available for viewing.
        """
        filepath = input.get("file", "")
        entry_id = input.get("entry_id", "")

        # Resolve entry from index (preferred — gives us original_file path)
        entry = None
        if entry_id:
            entry = self._find_entry(entry_id)
        if not entry and filepath:
            index = _load_index()
            for e in index.get("entries", []):
                if e.get("file") == filepath:
                    entry = e
                    break

        if entry:
            filepath = entry.get("file", filepath)
            original = entry.get("original_file", "")
            file_type = entry.get("file_type", "md")
        else:
            original = ""
            file_type = "md"

        # Read the extracted .md text (always UTF-8, safe to read as text)
        if filepath and _is_safe_kb_path(filepath) and os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                return {
                    "status": "ok",
                    "content": content,
                    "file": filepath,
                    "entry": entry or {},
                    "has_original": bool(original and _is_safe_kb_path(original) and os.path.exists(original)),
                    "original_file": original,
                    "file_type": file_type,
                }
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
        if not filepath:
            return Response(response="No file specified", status=400, mimetype="text/plain")
        if not _is_safe_kb_path(filepath):
            return Response(response="Access denied", status=403, mimetype="text/plain")
        if not os.path.exists(filepath):
            return Response(response="File not found", status=404, mimetype="text/plain")

        filename = os.path.basename(filepath)
        with open(filepath, "rb") as f:
            content = f.read()

        return Response(
            response=content,
            status=200,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    def _find_entry(self, entry_id: str) -> dict:
        """Look up an entry in the index by id, file path, or entry_id."""
        index = _load_index()
        for entry in index.get("entries", []):
            if entry.get("id") == entry_id or entry.get("file") == entry_id:
                return entry
        return {}

    def _download_original(self, input: dict) -> dict | Response:
        """Download the original binary file (PDF/DOCX/XLSX) stored on upload."""
        entry_id = input.get("entry_id", "")
        entry = self._find_entry(entry_id)
        original_path = entry.get("original_file", "")

        if not original_path:
            return Response(response="Original file not found", status=404, mimetype="text/plain")
        if not _is_safe_kb_path(original_path):
            return Response(response="Access denied", status=403, mimetype="text/plain")
        if not os.path.exists(original_path):
            return Response(response="Original file not found", status=404, mimetype="text/plain")

        ext = os.path.splitext(original_path)[1].lower()
        mime_map = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".mp3": "audio/mpeg", ".mp4": "video/mp4",
        }
        mimetype = mime_map.get(ext, "application/octet-stream")
        filename = os.path.basename(original_path)

        with open(original_path, "rb") as f:
            content = f.read()

        return Response(
            response=content,
            status=200,
            mimetype=mimetype,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    def _view_file(self, input: dict) -> dict | Response:
        """Serve a file for inline viewing (PDF in iframe, image in img tag, etc.).

        Unlike download_original, this sets Content-Disposition: inline so the
        browser displays it rather than downloading.
        """
        entry_id = input.get("entry_id", "")
        entry = self._find_entry(entry_id)
        original_path = entry.get("original_file", "")

        if not original_path:
            return Response(response="File not found", status=404, mimetype="text/plain")
        if not _is_safe_kb_path(original_path):
            return Response(response="Access denied", status=403, mimetype="text/plain")
        if not os.path.exists(original_path):
            return Response(response="File not found", status=404, mimetype="text/plain")

        ext = os.path.splitext(original_path)[1].lower()
        mime_map = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".mp3": "audio/mpeg", ".mp4": "video/mp4",
        }
        mimetype = mime_map.get(ext, "application/octet-stream")

        with open(original_path, "rb") as f:
            content = f.read()

        return Response(
            response=content,
            status=200,
            mimetype=mimetype,
            headers={"Content-Disposition": "inline"},
        )

    # ═══════════════════════════════════════════════════════════════
    # Notebook LM Features — Notebooks, Notes, Transformations, Podcast
    # ═══════════════════════════════════════════════════════════════

    def _load_notebooks(self):
        path = os.path.join(KB_DIR, "notebooks.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"notebooks": [], "transformations": []}

    def _save_notebooks(self, data):
        os.makedirs(KB_DIR, exist_ok=True)
        with open(os.path.join(KB_DIR, "notebooks.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    def _create_notebook(self, input: dict) -> dict:
        name = input.get("name", "").strip()
        description = input.get("description", "")
        if not name:
            return {"status": "error", "error": "Name required"}
        data = self._load_notebooks()
        nb_id = f"nb_{int(time.time())}_{len(data['notebooks'])}"
        notebook = {
            "id": nb_id, "name": name, "description": description,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "sources": [], "notes": []
        }
        data["notebooks"].append(notebook)
        self._save_notebooks(data)
        return {"status": "ok", "notebook": notebook}

    def _list_notebooks(self) -> dict:
        data = self._load_notebooks()
        return {"status": "ok", "notebooks": data.get("notebooks", [])}

    def _delete_notebook(self, input: dict) -> dict:
        nb_id = input.get("notebook_id", "")
        data = self._load_notebooks()
        data["notebooks"] = [n for n in data["notebooks"] if n["id"] != nb_id]
        self._save_notebooks(data)
        return {"status": "ok", "deleted": nb_id}

    def _add_source_to_notebook(self, input: dict) -> dict:
        nb_id = input.get("notebook_id", "")
        entry_id = input.get("entry_id", "")
        context_level = input.get("context_level", "full")  # full | summary | off
        data = self._load_notebooks()
        for nb in data["notebooks"]:
            if nb["id"] == nb_id:
                source = {"entry_id": entry_id, "context_level": context_level,
                          "added_at": time.strftime("%Y-%m-%d %H:%M:%S")}
                nb.setdefault("sources", []).append(source)
                self._save_notebooks(data)
                return {"status": "ok", "source": source}
        return {"status": "error", "error": "Notebook not found"}

    def _remove_source_from_notebook(self, input: dict) -> dict:
        nb_id = input.get("notebook_id", "")
        entry_id = input.get("entry_id", "")
        data = self._load_notebooks()
        for nb in data["notebooks"]:
            if nb["id"] == nb_id:
                nb["sources"] = [s for s in nb.get("sources", []) if s.get("entry_id") != entry_id]
                self._save_notebooks(data)
                return {"status": "ok"}
        return {"status": "error", "error": "Notebook not found"}

    def _add_note(self, input: dict) -> dict:
        nb_id = input.get("notebook_id", "")
        content = input.get("content", "").strip()
        author = input.get("author", "manual")  # manual | ai
        if not nb_id or not content:
            return {"status": "error", "error": "Notebook ID and content required"}
        data = self._load_notebooks()
        for nb in data["notebooks"]:
            if nb["id"] == nb_id:
                note = {
                    "id": f"note_{int(time.time())}",
                    "content": content, "author": author,
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                nb.setdefault("notes", []).append(note)
                self._save_notebooks(data)
                return {"status": "ok", "note": note}
        return {"status": "error", "error": "Notebook not found"}

    def _list_notes(self, input: dict) -> dict:
        nb_id = input.get("notebook_id", "")
        data = self._load_notebooks()
        for nb in data["notebooks"]:
            if nb["id"] == nb_id:
                return {"status": "ok", "notes": nb.get("notes", [])}
        return {"status": "error", "error": "Notebook not found"}

    def _delete_note(self, input: dict) -> dict:
        note_id = input.get("note_id", "")
        nb_id = input.get("notebook_id", "")
        data = self._load_notebooks()
        for nb in data["notebooks"]:
            if nb["id"] == nb_id:
                nb["notes"] = [n for n in nb.get("notes", []) if n.get("id") != note_id]
                self._save_notebooks(data)
                return {"status": "ok"}
        return {"status": "error", "error": "Notebook not found"}

    def _create_transformation(self, input: dict) -> dict:
        name = input.get("name", "").strip()
        prompt = input.get("prompt_template", "").strip()
        if not name or not prompt:
            return {"status": "error", "error": "Name and prompt template required"}
        data = self._load_notebooks()
        tf = {
            "id": f"tf_{int(time.time())}",
            "name": name, "prompt_template": prompt,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        data.setdefault("transformations", []).append(tf)
        self._save_notebooks(data)
        return {"status": "ok", "transformation": tf}

    def _list_transformations(self) -> dict:
        data = self._load_notebooks()
        return {"status": "ok", "transformations": data.get("transformations", [])}

    def _run_transformation(self, input: dict) -> dict:
        """Apply a transformation to a KB entry. Returns the prompt for Agent Zero to process."""
        tf_id = input.get("transformation_id", "")
        entry_id = input.get("entry_id", "")
        nb_id = input.get("notebook_id", "")
        data = self._load_notebooks()
        tf = None
        for t in data.get("transformations", []):
            if t["id"] == tf_id:
                tf = t
                break
        if not tf:
            return {"status": "error", "error": "Transformation not found"}
        # Find the entry content
        index = _load_index()
        entry_content = ""
        entry_title = ""
        for e in index.get("entries", []):
            if e.get("id") == entry_id:
                filepath = e.get("file", "")
                if filepath and os.path.exists(filepath):
                    with open(filepath, "r", encoding="utf-8") as f:
                        entry_content = f.read(20000)
                entry_title = e.get("title", "")
                break
        if not entry_content:
            return {"status": "error", "error": "Entry not found or empty"}
        # Build the prompt
        prompt = tf["prompt_template"].replace("{content}", entry_content[:15000]).replace("{title}", entry_title)
        return {"status": "ok", "prompt": prompt, "transformation_name": tf["name"],
                "instruction": "Send this prompt to the agent to generate an AI note. The result will be saved as a note in the notebook."}

    async def _generate_podcast(self, input: dict) -> dict:
        """Generate a real two-speaker podcast: LLM script → edge-tts per line → concat MP3."""
        import asyncio
        nb_id = input.get("notebook_id", "")
        speakers = input.get("speakers", [
            {"name": "Host", "persona": "Research host", "voice": "alloy"},
            {"name": "Expert", "persona": "Domain expert", "voice": "echo"},
        ])
        topic = input.get("topic", "")
        format_type = input.get("format", "interview")
        tone = input.get("tone", "professional")
        length = input.get("length", "medium")

        # ── Gather source content from notebook ──
        source_text = ""
        if nb_id:
            data = self._load_notebooks()
            index = _load_index()
            entry_map = {e.get("id", ""): e for e in index.get("entries", [])}
            for nb in data.get("notebooks", []):
                if nb["id"] == nb_id:
                    for src in nb.get("sources", [])[:12]:
                        e = entry_map.get(src.get("entry_id", ""), {})
                        fp = e.get("file", "")
                        if fp and os.path.isfile(fp):
                            try:
                                with open(fp, "r", encoding="utf-8") as f:
                                    source_text += f"\n\n--- {e.get('title', 'Source')} ---\n{f.read(2500)}"
                            except Exception:
                                pass
                    break

        if not source_text.strip():
            return {"status": "error", "error": "No sources in notebook. Add sources first."}

        # ── Step 1: LLM generates the dialogue script ──
        length_map = {"short": "8-12 exchanges", "medium": "18-25 exchanges", "long": "30-40 exchanges"}
        speaker_names = [s["name"] for s in speakers]
        speaker_desc = ", ".join(f"{s['name']} ({s['persona']})" for s in speakers)

        script_prompt = (
            f"You are writing a {format_type} podcast script. Speakers: {speaker_desc}.\n"
            f"Topic: {topic or 'the research below'}\nTone: {tone}\n"
            f"Length: {length_map.get(length, '18-25 exchanges')}\n\n"
            f"Research sources:\n{source_text[:10000]}\n\n"
            "Rules:\n"
            "- Each line MUST start with the speaker name followed by a colon, e.g.:\n"
            f"  {speaker_names[0]}: Hello, welcome to the show...\n"
            f"  {speaker_names[1]}: Thanks for having me...\n"
            "- Alternate between speakers naturally.\n"
            "- Include key findings, drug names, mechanisms from the sources.\n"
            "- End with a summary and key takeaways.\n"
            "Output ONLY the script, no stage directions, no metadata."
        )

        script_text = await asyncio.to_thread(self._call_llm_sync, script_prompt, max_tokens=2000)
        if not script_text:
            return {"status": "error", "error": "LLM unavailable — cannot generate script. Check model settings."}

        # ── Step 2: Parse script into (speaker, line) pairs ──
        lines = []
        for raw_line in script_text.strip().split("\n"):
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            for sp in speakers:
                prefix = sp["name"] + ":"
                if raw_line.startswith(prefix):
                    lines.append({"speaker": sp["name"], "voice": sp.get("voice", "alloy"),
                                  "text": raw_line[len(prefix):].strip()})
                    break

        if not lines:
            return {"status": "error", "error": "Script parsing failed — no speaker lines detected."}

        # ── Step 3: TTS each line, then concatenate ──
        podcast_dir = os.path.join(KB_DIR, "podcasts")
        os.makedirs(podcast_dir, exist_ok=True)
        ts = int(time.time())
        output_path = os.path.join(podcast_dir, f"podcast_{nb_id or 'kb'}_{ts}.mp3")

        try:
            from modules.surfsense.audio import generate_podcast_audio
            import tempfile, os as _os

            segment_paths = []
            tmp_dir = tempfile.mkdtemp()
            for i, line_data in enumerate(lines):
                seg_path = _os.path.join(tmp_dir, f"seg_{i:04d}.mp3")
                await generate_podcast_audio(
                    text=line_data["text"],
                    voice=line_data["voice"],
                    output_path=seg_path,
                )
                segment_paths.append(seg_path)

            # Concatenate segments — use pydub if available, fallback to binary concat
            try:
                from pydub import AudioSegment
                silence = AudioSegment.silent(duration=400)
                combined = AudioSegment.empty()
                for seg in segment_paths:
                    combined += AudioSegment.from_mp3(seg) + silence
                combined.export(output_path, format="mp3")
            except ImportError:
                # Raw binary concat — works for edge-tts mp3s (same bitrate/sample rate)
                with open(output_path, "wb") as out:
                    for seg in segment_paths:
                        with open(seg, "rb") as f:
                            out.write(f.read())
            finally:
                for seg in segment_paths:
                    try:
                        _os.remove(seg)
                    except OSError:
                        pass
                try:
                    _os.rmdir(tmp_dir)
                except OSError:
                    pass

            # Return base64 for inline playback
            import base64
            with open(output_path, "rb") as f:
                audio_b64 = base64.b64encode(f.read()).decode()

            return {
                "status": "ok",
                "audio_base64": audio_b64,
                "file": output_path,
                "script": script_text,
                "line_count": len(lines),
                "speakers": speakers,
            }

        except ImportError:
            # edge-tts not installed — return script only
            return {
                "status": "ok",
                "script": script_text,
                "audio_base64": None,
                "message": "Script generated. Install edge-tts (pip install edge-tts) to enable audio.",
            }
        except Exception as e:
            log.warning(f"Podcast TTS failed: {e}")
            return {
                "status": "ok",
                "script": script_text,
                "audio_base64": None,
                "message": f"Script generated. Audio failed: {e}",
            }

    # ─────────────────────────────────────────────────────────────────────
    # KB CHAT — Retrieval-Grounded Q&A with Citations
    # ─────────────────────────────────────────────────────────────────────
    # Replaces the broken "paste titles into textarea" approach with a real
    # RAG pipeline: hybrid search → context block → LLM → citation normalization.
    # All logic is additive — does not modify existing query/store actions.

    # ─────────────────────────────────────────────────────────────────────
    # Conversation persistence helpers
    # ─────────────────────────────────────────────────────────────────────

    def _conv_path(self, conv_id: str) -> str:
        safe = "".join(c for c in conv_id if c.isalnum() or c in "-_")[:80]
        return os.path.join(CONV_DIR, f"{safe}.json")

    def _load_conversation(self, conv_id: str) -> dict:
        p = self._conv_path(conv_id)
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"id": conv_id, "messages": [], "created_at": time.strftime("%Y-%m-%d %H:%M:%S")}

    def _save_conversation(self, conv: dict):
        p = self._conv_path(conv["id"])
        with open(p, "w", encoding="utf-8") as f:
            json.dump(conv, f, ensure_ascii=False, indent=2)

    def _list_conversations(self, input: dict) -> dict:
        nb_id = input.get("notebook_id", "")
        convs = []
        for fname in sorted(os.listdir(CONV_DIR), reverse=True)[:50]:
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(CONV_DIR, fname), "r", encoding="utf-8") as f:
                    c = json.load(f)
                if nb_id and c.get("notebook_id", "") != nb_id:
                    continue
                convs.append({
                    "id": c.get("id", ""),
                    "notebook_id": c.get("notebook_id", ""),
                    "title": c.get("title", c.get("id", "")),
                    "message_count": len(c.get("messages", [])),
                    "created_at": c.get("created_at", ""),
                    "updated_at": c.get("updated_at", ""),
                })
            except Exception:
                continue
        return {"status": "ok", "conversations": convs}

    def _get_conversation(self, input: dict) -> dict:
        conv_id = input.get("conversation_id", "")
        if not conv_id:
            return {"status": "error", "error": "conversation_id required"}
        conv = self._load_conversation(conv_id)
        return {"status": "ok", "conversation": conv}

    def _delete_conversation(self, input: dict) -> dict:
        conv_id = input.get("conversation_id", "")
        if not conv_id:
            return {"status": "error", "error": "conversation_id required"}
        p = self._conv_path(conv_id)
        if os.path.isfile(p):
            os.remove(p)
        return {"status": "ok"}

    # ─────────────────────────────────────────────────────────────────────
    # Shared LLM helper (sync, called from asyncio.to_thread)
    # ─────────────────────────────────────────────────────────────────────

    def _call_llm_sync(self, prompt: str, system: str = "", max_tokens: int = 1500,
                       history: list = None) -> str | None:
        """Call the configured LLM synchronously via litellm. Returns text or None."""
        try:
            import litellm
            config_path = os.path.join(os.path.dirname(KB_DIR),
                                       "usr", "plugins", "_model_config", "config.json")
            model_name = "gpt-4o-mini"
            api_base = ""
            provider = "openai"
            if os.path.isfile(config_path):
                try:
                    with open(config_path) as f:
                        cfg = json.load(f)
                    chat = cfg.get("chat_model", {})
                    provider = chat.get("provider", "openai")
                    model_name = chat.get("name", "gpt-4o-mini")
                    api_base = chat.get("api_base", "")
                except Exception:
                    pass

            if provider == "lm_studio" and api_base:
                llm_model, kwargs = f"lm_studio/{model_name}", {"api_base": api_base}
            elif provider == "ollama" and api_base:
                llm_model, kwargs = f"ollama/{model_name}", {"api_base": api_base}
            else:
                llm_model, kwargs = model_name, {}

            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            if history:
                messages.extend(history[-10:])  # last 10 turns for context
            messages.append({"role": "user", "content": prompt})

            resp = litellm.completion(model=llm_model, messages=messages,
                                      max_tokens=max_tokens, temperature=0.3, **kwargs)
            return resp.choices[0].message.content
        except Exception as e:
            log.warning(f"LLM call failed: {e}")
            return None

    # ─────────────────────────────────────────────────────────────────────
    # KB CHAT — Scoped, Citation-Grounded, Conversation-Persistent
    # ─────────────────────────────────────────────────────────────────────

    async def _kb_chat(self, input: dict) -> dict:
        """Retrieval-grounded KB chat.

        Scoped: when notebook_id given, searches ONLY that notebook's sources.
        Persistent: saves each exchange to data/knowledge_base/conversations/<id>.json.
        Agent Zero aware: input data flows in from Agent Zero via auto_store().
        """
        import asyncio

        query = (input.get("query") or "").strip()
        nb_id = input.get("notebook_id", "")
        category = input.get("category", "")
        top_k = int(input.get("top_k", 8))
        conv_id = input.get("conversation_id", "") or f"conv_{int(time.time())}"

        if not query:
            return {"status": "error", "error": "Query required"}

        # ── Step 1: Determine which entries to search ──
        index = _load_index()
        all_entries = index.get("entries", [])

        if nb_id:
            # Scoped to notebook sources only (NotebookLM behaviour)
            data = self._load_notebooks()
            nb_entry_ids = set()
            nb_title = ""
            for nb in data.get("notebooks", []):
                if nb["id"] == nb_id:
                    nb_entry_ids = {s["entry_id"] for s in nb.get("sources", [])}
                    nb_title = nb.get("name", "")
                    break
            if not nb_entry_ids:
                return {"status": "ok",
                        "answer": "This notebook has no sources yet. Add KB entries as sources first.",
                        "citations": [], "sources_found": 0, "conversation_id": conv_id}
            entries = [e for e in all_entries if e.get("id") in nb_entry_ids]
        elif category:
            entries = [e for e in all_entries if e.get("category") == category]
        else:
            entries = all_entries

        if not entries:
            return {"status": "ok", "answer": "No knowledge base entries found.",
                    "citations": [], "sources_found": 0, "conversation_id": conv_id}

        # ── Step 2: Load conversation history for context ──
        conv = self._load_conversation(conv_id)
        conv.setdefault("notebook_id", nb_id)
        if not conv.get("title"):
            conv["title"] = query[:60]
        history_msgs = [
            {"role": m["role"], "content": m["content"]}
            for m in conv.get("messages", [])[-10:]
        ]

        # ── Step 3: Read + chunk entries ──
        def _load_chunks():
            chunks = []
            for entry in entries:
                fp = entry.get("file", "")
                if not fp or not os.path.isfile(fp):
                    continue
                try:
                    with open(fp, "r", encoding="utf-8") as f:
                        content = f.read()
                    try:
                        from modules.rag.table_chunker import chunk_text_table_aware
                        text_chunks = chunk_text_table_aware(content, max_chars=2000)
                    except ImportError:
                        text_chunks = [content[:2000]]
                    for i, chunk_text in enumerate(text_chunks[:5]):
                        chunks.append({
                            "content": chunk_text,
                            "entry_id": entry.get("id", ""),
                            "title": entry.get("title", ""),
                            "source": entry.get("source", ""),
                            "category": entry.get("category", ""),
                            "chunk_idx": i,
                        })
                except Exception:
                    pass
            return chunks

        chunks = await asyncio.to_thread(_load_chunks)
        if not chunks:
            return {"status": "ok", "answer": "Could not read any KB entries.",
                    "citations": [], "sources_found": 0, "conversation_id": conv_id}

        # ── Step 4: Hybrid search ──
        def _search():
            try:
                from modules.rag.hybrid_search import HybridSearcher
                searcher = HybridSearcher()
                searcher.index(chunks)
                return searcher.search(query, top_k=top_k)
            except ImportError:
                q = query.lower()
                scored = [c for c in chunks
                          if sum(1 for w in q.split() if w in c.get("content", "").lower()) > 0]
                scored.sort(key=lambda x: x.get("hybrid_score", 0), reverse=True)
                return scored[:top_k]

        results = await asyncio.to_thread(_search)
        if not results:
            return {"status": "ok",
                    "answer": f"No relevant entries found for: '{query}'.",
                    "citations": [], "sources_found": 0, "conversation_id": conv_id}

        # ── Step 5: Build citation context ──
        from modules.rag.citations import CitationRegistry, render_context, normalize_citations, CITATION_PROMPT
        registry = CitationRegistry()
        context_block = render_context(results, registry, max_chars=10000)

        # ── Step 6: LLM with conversation history ──
        full_prompt = f"{context_block}\n\nUser question: {query}"
        answer = await asyncio.to_thread(
            self._call_llm_sync, full_prompt, CITATION_PROMPT, 1500, history_msgs
        )

        if not answer:
            answer = "## Retrieved Sources\n\n"
            for r in results[:5]:
                registry.register("kb", str(r.get("entry_id", "")),
                                  r.get("title", ""), r.get("content", ""))
                answer += f"**{r.get('title', 'Untitled')}**\n{r.get('content', '')[:500]}...\n\n"
        else:
            answer = normalize_citations(answer, registry)

        # ── Step 7: Persist conversation ──
        conv.setdefault("messages", []).append(
            {"role": "user", "content": query, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}
        )
        conv["messages"].append(
            {"role": "assistant", "content": answer,
             "citations": registry.to_dict()["citations"],
             "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}
        )
        conv["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self._save_conversation(conv)

        return {
            "status": "ok",
            "answer": answer,
            "citations": registry.to_dict()["citations"],
            "sources_found": len(results),
            "query": query,
            "conversation_id": conv_id,
            "notebook_id": nb_id,
        }

    # ─────────────────────────────────────────────────────────────────────
    # Study Guide, Briefing, Suggested Questions, Source Summary
    # ─────────────────────────────────────────────────────────────────────

    def _load_notebook_content(self, nb_id: str, max_per_source: int = 3000) -> tuple[list, str]:
        """Return (entries_with_content, combined_text) for a notebook's sources."""
        data = self._load_notebooks()
        index = _load_index()
        entry_map = {e.get("id", ""): e for e in index.get("entries", [])}
        results = []
        combined = ""
        for nb in data.get("notebooks", []):
            if nb["id"] == nb_id:
                for src in nb.get("sources", []):
                    e = entry_map.get(src.get("entry_id", ""), {})
                    if not e:
                        continue
                    fp = e.get("file", "")
                    content = ""
                    if fp and os.path.isfile(fp):
                        try:
                            with open(fp, "r", encoding="utf-8") as f:
                                content = f.read(max_per_source)
                        except Exception:
                            pass
                    results.append({**e, "_content": content})
                    combined += f"\n\n=== {e.get('title', 'Source')} ===\n{content}"
                break
        return results, combined

    async def _generate_study_guide(self, input: dict) -> dict:
        """Generate a study guide (key concepts, FAQ, glossary) from notebook sources."""
        import asyncio
        nb_id = input.get("notebook_id", "")
        if not nb_id:
            return {"status": "error", "error": "notebook_id required"}

        sources, combined = self._load_notebook_content(nb_id, max_per_source=2000)
        if not combined.strip():
            return {"status": "error", "error": "No sources in notebook"}

        prompt = (
            "You are a pharmaceutical science educator. Based on the research below, generate a study guide.\n\n"
            "Output EXACTLY this structure (use these exact headings):\n\n"
            "## Key Concepts\n"
            "List 6-10 key concepts as bullet points with a 1-sentence explanation each.\n\n"
            "## FAQ\n"
            "List 6-8 Q&A pairs in format:\n**Q:** question\n**A:** answer\n\n"
            "## Glossary\n"
            "List 8-12 technical terms with definitions.\n\n"
            "## Key Takeaways\n"
            "3-5 bullet points summarizing the most important findings.\n\n"
            f"Research:\n{combined[:12000]}"
        )

        guide_text = await asyncio.to_thread(self._call_llm_sync, prompt, max_tokens=2000)
        if not guide_text:
            return {"status": "error", "error": "LLM unavailable"}

        # Cache in notebook
        data = self._load_notebooks()
        for nb in data.get("notebooks", []):
            if nb["id"] == nb_id:
                nb["study_guide"] = {"content": guide_text,
                                     "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")}
                break
        self._save_notebooks(data)

        return {"status": "ok", "study_guide": guide_text,
                "source_count": len(sources), "notebook_id": nb_id}

    async def _generate_briefing(self, input: dict) -> dict:
        """Generate an executive briefing document from notebook sources."""
        import asyncio
        nb_id = input.get("notebook_id", "")
        if not nb_id:
            return {"status": "error", "error": "notebook_id required"}

        sources, combined = self._load_notebook_content(nb_id, max_per_source=2500)
        if not combined.strip():
            return {"status": "error", "error": "No sources in notebook"}

        source_titles = [s.get("title", "Untitled") for s in sources]
        prompt = (
            "You are a pharmaceutical research analyst. Write an executive briefing based on these sources.\n\n"
            f"Sources: {', '.join(source_titles)}\n\n"
            "Output this structure:\n\n"
            "## Executive Summary\n2-3 paragraph synthesis of key findings.\n\n"
            "## Key Findings\nBullet points of the most significant results.\n\n"
            "## Contradictions & Debates\nAreas where sources disagree (or 'No major contradictions identified').\n\n"
            "## Knowledge Gaps\nWhat questions remain unanswered.\n\n"
            "## Recommended Next Steps\n3-5 actionable recommendations for further research.\n\n"
            f"Research:\n{combined[:14000]}"
        )

        briefing_text = await asyncio.to_thread(self._call_llm_sync, prompt, max_tokens=2000)
        if not briefing_text:
            return {"status": "error", "error": "LLM unavailable"}

        data = self._load_notebooks()
        for nb in data.get("notebooks", []):
            if nb["id"] == nb_id:
                nb["briefing"] = {"content": briefing_text,
                                  "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")}
                break
        self._save_notebooks(data)

        return {"status": "ok", "briefing": briefing_text,
                "source_count": len(sources), "notebook_id": nb_id}

    async def _suggest_questions(self, input: dict) -> dict:
        """Generate 5-8 suggested follow-up questions for a notebook or single entry."""
        import asyncio
        nb_id = input.get("notebook_id", "")
        entry_id = input.get("entry_id", "")

        if nb_id:
            sources, combined = self._load_notebook_content(nb_id, max_per_source=1500)
            context_label = f"notebook ({len(sources)} sources)"
        elif entry_id:
            index = _load_index()
            combined = ""
            for e in index.get("entries", []):
                if e.get("id") == entry_id:
                    fp = e.get("file", "")
                    if fp and os.path.isfile(fp):
                        with open(fp, "r", encoding="utf-8") as f:
                            combined = f.read(3000)
                    break
            context_label = "entry"
        else:
            return {"status": "error", "error": "notebook_id or entry_id required"}

        if not combined.strip():
            return {"status": "error", "error": "No content found"}

        prompt = (
            "Based on the following research, generate 6 insightful follow-up questions a researcher would ask.\n"
            "Make them specific, analytical, and pharma-focused.\n"
            "Output ONLY a JSON array of strings, e.g.:\n"
            '["Question 1?", "Question 2?", ...]\n\n'
            f"Research:\n{combined[:6000]}"
        )

        raw = await asyncio.to_thread(self._call_llm_sync, prompt, max_tokens=400)
        questions = []
        if raw:
            try:
                import re
                m = re.search(r'\[.*?\]', raw, re.DOTALL)
                if m:
                    questions = json.loads(m.group())
            except Exception:
                # Fallback: split by newline, strip bullets
                questions = [line.strip().lstrip("-•0123456789. ").strip()
                             for line in raw.split("\n") if "?" in line][:8]

        if nb_id:
            # Cache questions on the notebook
            data = self._load_notebooks()
            for nb in data.get("notebooks", []):
                if nb["id"] == nb_id:
                    nb["suggested_questions"] = questions
                    nb["questions_generated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    break
            self._save_notebooks(data)

        return {"status": "ok", "questions": questions,
                "context": context_label, "notebook_id": nb_id}

    async def _summarize_source(self, input: dict) -> dict:
        """Summarize a single KB entry in 3-5 sentences."""
        import asyncio
        entry_id = input.get("entry_id", "")
        if not entry_id:
            return {"status": "error", "error": "entry_id required"}

        index = _load_index()
        content = ""
        title = ""
        for e in index.get("entries", []):
            if e.get("id") == entry_id:
                title = e.get("title", "")
                fp = e.get("file", "")
                if fp and os.path.isfile(fp):
                    try:
                        with open(fp, "r", encoding="utf-8") as f:
                            content = f.read(5000)
                    except Exception:
                        pass
                break

        if not content:
            return {"status": "error", "error": "Entry not found"}

        prompt = (
            f"Summarize this research entry in 3-5 clear sentences for a pharmaceutical scientist.\n"
            f"Focus on: key findings, methods, and implications.\n\n"
            f"Title: {title}\n\nContent:\n{content}"
        )
        summary = await asyncio.to_thread(self._call_llm_sync, prompt, max_tokens=300)
        if not summary:
            # Fallback: first 400 chars of content
            summary = content[:400].strip() + "..."

        return {"status": "ok", "summary": summary, "entry_id": entry_id, "title": title}
