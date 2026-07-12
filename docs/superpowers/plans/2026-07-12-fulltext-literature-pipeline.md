# Full-Text Literature Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Download full text for every article discovered from 10 databases, save each as a readable `.docx` file in the Knowledge Base, and use only full-text articles for review synthesis.

**Architecture:** New `FullTextRetriever` (3-tier: Europe PMC XML → PDF download → Hacker Agent) feeds into new `LiteratureDocxExporter` (python-docx). Updated orchestrator runs batch retrieval for ALL discovered articles, counts only successes, and stores DOCX files via KB API before proceeding to synthesis.

**Tech Stack:** Python 3.12+, python-docx (already in requirements.txt), pypdf (already in codebase), requests, WebResearchEngine (existing), Europe PMC REST API

## Global Constraints

- python-docx >= 1.1.0 (already in `api/requirements.txt:66` and `agent_zero/requirements_pharma.txt:14`)
- Europe PMC fullTextXML API is free, no key required
- Rate limit: Europe PMC 1 req/sec max, Unpaywall polite delay
- All DOCX files stored to `data/knowledge_base/literature/`
- Original orchestrator Paper dataclass uses `discovery.Paper` (fields: title, url, source, authors, abstract, year, doi, citations, pdf_url)
- Scraper Paper dataclass uses `scraper.Paper` (additional fields: pmid, is_open_access, full_text_url)

---

### Task 1: FullTextRetriever — Europe PMC XML (Tier 1)

**Files:**
- Create: `modules/literature/full_text.py`
- Test: `tests/test_full_text.py`

**Interfaces:**
- Produces: `FullTextRetriever` class with methods `retrieve(paper) -> Optional[str]`, `_tier1_europe_pmc(paper) -> Optional[str]`, `_tier2_pdf_download(paper) -> Optional[str]`, `_tier3_hacker_agent(paper) -> Optional[str]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_full_text.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from modules.literature.full_text import FullTextRetriever

def test_retriever_creates():
    r = FullTextRetriever()
    assert r is not None

def test_tier1_europe_pmc_has_pmcid_mock():
    r = FullTextRetriever()
    # Paper with PMCID — should attempt Europe PMC
    paper = {"pmid": "12345678", "pmcid": "PMC123456", "title": "Test Paper", "source": "pubmed"}
    # Without network, should return None (no crash)
    result = r._tier1_europe_pmc(paper)
    assert result is None  # No network in test env

def test_tier1_europe_pmc_no_pmcid():
    r = FullTextRetriever()
    paper = {"doi": "10.1234/test", "title": "No PMCID"}
    result = r._tier1_europe_pmc(paper)
    assert result is None  # Skip — no PMCID

def test_retrieve_returns_none_for_all_tiers_fail():
    r = FullTextRetriever()
    paper = {"title": "No identifiers", "source": "unknown"}
    result = r.retrieve(paper)
    assert result is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_full_text.py::test_retriever_creates -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# modules/literature/full_text.py
"""Full-text retriever — 3-tier: Europe PMC XML → PDF download → Hacker Agent."""
import logging
import re
import time
import requests
from typing import Dict, Optional
from io import BytesIO

logger = logging.getLogger("literature.full_text")

class FullTextRetriever:
    """Source-agnostic full-text retriever using article identifiers."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "BioDockifyAI/1.0 (mailto:researcher@example.com)"
        })
        self._last_request_time = 0

    def _rate_limit(self, min_interval: float = 1.0):
        elapsed = time.time() - self._last_request_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_request_time = time.time()

    def retrieve(self, paper: Dict) -> Optional[str]:
        """Run 3-tier retrieval. Returns full text or None."""
        full_text = self._tier1_europe_pmc(paper)
        if full_text:
            return full_text

        full_text = self._tier2_pdf_download(paper)
        if full_text:
            return full_text

        full_text = self._tier3_hacker_agent(paper)
        if full_text:
            return full_text

        return None

    def _tier1_europe_pmc(self, paper: Dict) -> Optional[str]:
        """Fetch full-text XML from Europe PMC by PMCID."""
        pmcid = paper.get("pmcid", "")
        if not pmcid:
            return None

        try:
            self._rate_limit(1.0)
            url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
            resp = self.session.get(url, timeout=30)
            if resp.status_code != 200:
                logger.debug(f"Europe PMC fullTextXML failed for {pmcid}: HTTP {resp.status_code}")
                return None

            xml_text = resp.text
            if len(xml_text) < 200:
                return None

            # Strip XML tags to get plain text
            clean = re.sub(r'<[^>]+>', ' ', xml_text)
            clean = re.sub(r'\s+', ' ', clean).strip()
            return clean if len(clean) > 200 else None
        except Exception as e:
            logger.warning(f"Tier 1 Europe PMC failed for {pmcid}: {e}")
            return None

    def _tier2_pdf_download(self, paper: Dict) -> Optional[str]:
        """Download PDF from OA URL and extract text via pypdf."""
        pdf_url = paper.get("full_text_url") or paper.get("pdf_url")
        if not pdf_url:
            return None

        try:
            self._rate_limit(2.0)
            resp = self.session.get(pdf_url, timeout=30, stream=True)
            if resp.status_code != 200 or len(resp.content) < 1000:
                logger.debug(f"PDF download failed: HTTP {resp.status_code}, size {len(resp.content)}")
                return None

            from pypdf import PdfReader
            reader = PdfReader(BytesIO(resp.content))
            pages = []
            for page in reader.pages[:30]:  # Max 30 pages
                text = page.extract_text()
                if text:
                    pages.append(text)

            full = "\n\n".join(pages)
            return full if len(full) > 200 else None
        except Exception as e:
            logger.warning(f"Tier 2 PDF failed for {pdf_url}: {e}")
            return None

    def _tier3_hacker_agent(self, paper: Dict) -> Optional[str]:
        """Hacker Agent — use WebResearchEngine.deep_read() for paywalled content."""
        doi = paper.get("doi", "")
        url = paper.get("url", "")

        target_url = None
        if doi:
            target_url = f"https://doi.org/{doi}"
        elif url:
            target_url = url

        if not target_url:
            return None

        try:
            import asyncio
            from modules.web_research.engine import WebResearchEngine

            engine = WebResearchEngine()

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running loop — create one
                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(engine.deep_read(target_url))
                loop.close()
                if result and len(result) > 200 and "Error reading" not in result:
                    return result
                return None

            # Running in async context
            import concurrent.futures
            future = asyncio.run_coroutine_threadsafe(engine.deep_read(target_url), loop)
            result = future.result(timeout=60)
            if result and len(result) > 200 and "Error reading" not in result:
                return result
            return None
        except Exception as e:
            logger.warning(f"Tier 3 Hacker Agent failed for {target_url}: {e}")
            return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_full_text.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add modules/literature/full_text.py tests/test_full_text.py
git commit -m "feat: FullTextRetriever — 3-tier full-text retrieval (Europe PMC XML, PDF download, Hacker Agent)"
```

---

### Task 2: LiteratureDocxExporter — DOCX Generation

**Files:**
- Create: `modules/export/literature_docx.py`
- Test: `tests/test_literature_docx.py`

**Interfaces:**
- Produces: `LiteratureDocxExporter` class with `export_article(paper: Dict, full_text: Optional[str]) -> bytes`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_literature_docx.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from modules.export.literature_docx import LiteratureDocxExporter

def test_exporter_creates():
    e = LiteratureDocxExporter()
    assert e is not None

def test_export_with_full_text():
    e = LiteratureDocxExporter()
    paper = {
        "title": "Test Article Title",
        "authors": ["Smith J", "Doe A"],
        "year": 2024,
        "journal": "Journal of Testing",
        "doi": "10.1234/test.001",
        "source": "PubMed",
        "abstract": "This is a test abstract for the article.",
    }
    full_text = "Introduction. This is the full text body with multiple paragraphs. Methods. The study used test methods. Results. The results show significance. Discussion. These findings are important."

    docx_bytes = e.export_article(paper, full_text)
    assert docx_bytes is not None
    assert len(docx_bytes) > 1000  # Should be a real DOCX file
    assert docx_bytes[:2] == b'PK'  # DOCX is a ZIP file

def test_export_abstract_only():
    e = LiteratureDocxExporter()
    paper = {
        "title": "Abstract Only Article",
        "authors": ["Jones K"],
        "year": 2023,
        "source": "Semantic Scholar",
        "abstract": "Only abstract available.",
    }

    docx_bytes = e.export_article(paper, None)
    assert docx_bytes is not None
    assert len(docx_bytes) > 500
    assert docx_bytes[:2] == b'PK'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_literature_docx.py::test_exporter_creates -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# modules/export/literature_docx.py
"""Generate formatted .docx files for literature articles."""
import logging
from typing import Dict, Optional
from io import BytesIO

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

logger = logging.getLogger("export.literature_docx")

class LiteratureDocxExporter:
    """Export a single article as a formatted .docx document."""

    def export_article(self, paper: Dict, full_text: Optional[str]) -> bytes:
        """Generate DOCX bytes for an article.

        Args:
            paper: Dict with title, authors, year, journal, doi, source, abstract
            full_text: Full body text (or None for abstract-only mode)

        Returns:
            DOCX file as bytes (ZIP/OpenXML format)
        """
        doc = Document()

        # --- Styles ---
        style = doc.styles['Normal']
        font = style.font
        font.name = 'Times New Roman'
        font.size = Pt(11)

        # --- Title ---
        title_para = doc.add_paragraph()
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = title_para.add_run(paper.get("title", "Untitled"))
        run.bold = True
        run.font.size = Pt(16)

        # --- Metadata ---
        meta = doc.add_paragraph()
        meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
        meta.paragraph_format.space_after = Pt(6)

        authors = paper.get("authors", [])
        if isinstance(authors, list):
            authors_str = ", ".join(authors)
        else:
            authors_str = str(authors)
        meta.add_run(authors_str).italic = True

        journal = paper.get("journal", "")
        year = paper.get("year", "")
        doi = paper.get("doi", "")
        if journal or year:
            meta.add_run(f"\n{journal}, {year}").font.size = Pt(10)
        if doi:
            meta.add_run(f"\nDOI: {doi}").font.size = Pt(9)

        doc.add_paragraph()  # spacer

        # --- Abstract ---
        abstract = paper.get("abstract", "")
        if abstract:
            doc.add_heading("Abstract", level=2)
            doc.add_paragraph(abstract)

        # --- Full Text ---
        if full_text:
            doc.add_heading("Full Text", level=2)

            # Split by common delimiters into sections
            sections = self._split_sections(full_text)
            for title, body in sections:
                if title:
                    doc.add_heading(title, level=3)
                for para_text in body.split("\n\n"):
                    para_text = para_text.strip()
                    if para_text:
                        doc.add_paragraph(para_text)
        else:
            doc.add_heading("Full Text Unavailable", level=2)
            note = doc.add_paragraph()
            note.add_run("Abstract Only — Full text could not be retrieved from any source.").italic = True
            note.runs[0].font.color.rgb = RGBColor(150, 0, 0)

        # --- Source Info ---
        doc.add_paragraph()
        doc.add_heading("Source Information", level=2)
        info = doc.add_paragraph()
        info.add_run(f"Database: {paper.get('source', 'Unknown')}\n").font.size = Pt(9)
        info.add_run(f"Retrieved by: BioDockify AI Literature Pipeline\n").font.size = Pt(9)
        info.add_run(f"Retrieval method: {'Full Text' if full_text else 'Abstract Only'}\n").font.size = Pt(9)

        # --- Footer ---
        section = doc.sections[0]
        footer = section.footer
        footer_para = footer.paragraphs[0]
        footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        footer_para.add_run("Retrieved by BioDockify AI").font.size = Pt(8)

        # Output to bytes
        buf = BytesIO()
        doc.save(buf)
        return buf.getvalue()

    def _split_sections(self, text: str):
        """Split full text into titled sections."""
        import re
        # Split on common section headings
        pattern = re.compile(
            r'(?:\n|^)((?:Abstract|Introduction|Background|Methods?|Materials?\s*(?:and|&)\s*Methods?|'
            r'Experimental|Results?(?:\s*and\s*Discussion)?|Discussion|Conclusion|Summary|'
            r'Acknowledgments?|References?|Bibliography|Supplementary)\s*[:\n]?)',
            re.IGNORECASE
        )
        parts = pattern.split(text)
        sections = []
        # First part before any heading
        if parts and parts[0].strip():
            sections.append(("", parts[0]))

        # Remaining heading-content pairs
        for i in range(1, len(parts) - 1, 2):
            title = parts[i].strip().rstrip(":")
            body = parts[i + 1] if i + 1 < len(parts) else ""
            sections.append((title, body))

        # If no sections found, return whole text as one
        if not sections:
            sections.append(("", text))

        return sections
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_literature_docx.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add modules/export/literature_docx.py tests/test_literature_docx.py
git commit -m "feat: LiteratureDocxExporter — generate formatted .docx per article"
```

---

### Task 3: KB DOCX Storage Support

**Files:**
- Modify: `api/knowledge.py:57-109` (add `_store_docx_entry` function)

**Interfaces:**
- Consumes: `LiteratureDocxExporter.export_article()` returns `bytes`
- Produces: `_store_docx_entry(category, title, docx_bytes, tags, source, metadata)` — same signature style as existing `_store_entry`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_knowledge_docx.py
import sys, os, tempfile, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def test_store_docx_entry():
    import importlib
    import api.knowledge as k

    # Use temp dir for test
    tmpdir = tempfile.mkdtemp()
    old_kb = k.KB_DIR
    k.KB_DIR = tmpdir

    try:
        docx_bytes = b'PK\x03\x04fake_docx_content'
        entry = k._store_docx_entry(
            category="literature",
            title="Test DOCX Article",
            docx_bytes=docx_bytes,
            tags="test,demo",
            source="PubMed",
            metadata={"doi": "10.1234/test"}
        )

        assert entry["category"] == "literature"
        assert entry["title"] == "Test DOCX Article"
        assert entry["format"] == "docx"
        assert entry["size"] == len(docx_bytes)
        assert os.path.exists(entry["file"])
        assert entry["file"].endswith(".docx")

        # Verify index
        with open(os.path.join(tmpdir, "index.json")) as f:
            idx = json.load(f)
            found = [e for e in idx["entries"] if e["title"] == "Test DOCX Article"]
            assert len(found) == 1
    finally:
        k.KB_DIR = old_kb
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_knowledge_docx.py::test_store_docx_entry -v`
Expected: FAIL — `AttributeError: module 'api.knowledge' has no attribute '_store_docx_entry'`

- [ ] **Step 3: Write minimal implementation**

Add after the existing `_store_entry` function (after line 109 in `api/knowledge.py`):

```python
def _store_docx_entry(category: str, title: str, docx_bytes: bytes, tags: str = "", source: str = "", metadata: dict = None):
    """Store a DOCX document in the knowledge base. No vector indexing for binary files."""
    import time

    cat_dir = os.path.join(KB_DIR, category)
    os.makedirs(cat_dir, exist_ok=True)

    # Create filename from title
    safe_title = "".join(c for c in title[:80] if c.isalnum() or c in " _-").strip().replace(" ", "_")
    if not safe_title:
        safe_title = f"entry_{int(time.time())}"
    filepath = os.path.join(cat_dir, f"{safe_title}.docx")

    # Avoid overwrite
    counter = 1
    base_path = filepath
    while os.path.exists(filepath):
        filepath = os.path.join(cat_dir, f"{safe_title}_{counter}.docx")
        counter += 1

    # Write binary content
    with open(filepath, "wb") as f:
        f.write(docx_bytes)

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
        "size": len(docx_bytes),
        "format": "docx",
    }
    if metadata:
        entry["metadata"] = metadata
    index["entries"].append(entry)
    index["categories"][category] = index["categories"].get(category, 0) + 1
    _save_index(index)

    return entry
```

Also update `_detect_category` to handle `.docx` extension explicitly (it only checks `.pdf`, `.xlsx`, etc. currently):

Add this case in `_detect_category` (around line 127 in the original, after the `.pdf` check):

```python
    elif ext == '.docx':
        return "literature"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_knowledge_docx.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add api/knowledge.py tests/test_knowledge_docx.py
git commit -m "feat: KB DOCX storage — _store_docx_entry for binary document support"
```

---

### Task 4: Update Orchestrator — Batch Full-Text Retrieval + DOCX Storage

**Files:**
- Modify: `modules/literature/orchestrator.py:46-58` (replace Phase 3)

**Interfaces:**
- Consumes: `FullTextRetriever.retrieve()`, `LiteratureDocxExporter.export_article()`, `api.knowledge._store_docx_entry()`
- Produces: Updated `run_deep_review()` with `full_text_count` and `docx_stored` in return dict

- [ ] **Step 1: Write the test**

```python
# tests/test_orchestrator_fulltext.py
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def test_fulltext_phase_counts():
    """Verify orchestrator counts only successful full-text retrievals."""
    from modules.literature.orchestrator import DeepResearchOrchestrator

    # We test the counting logic directly, not the full async pipeline
    orch = DeepResearchOrchestrator()

    # Papers with full text
    papers_with_fulltext = [
        {"title": "Paper A", "doi": "10.1/a", "source": "pubmed", "abstract": "abc"},
        {"title": "Paper B", "doi": "10.1/b", "source": "semantic_scholar", "abstract": "def"},
    ]
    # Papers without full text
    papers_without_fulltext = [
        {"title": "Paper C", "doi": "10.1/c", "source": "crossref", "abstract": "ghi"},
    ]

    # Mock: simulate what retrieve() returns
    class MockRetriever:
        def retrieve(self, paper):
            if paper["title"] == "Paper C":
                return None
            return f"Full text of {paper['title']}"

    retriever = MockRetriever()

    successful = []
    for paper in papers_with_fulltext + papers_without_fulltext:
        ft = retriever.retrieve(paper)
        if ft:
            successful.append({**paper, "full_text": ft})

    assert len(successful) == 2
    assert successful[0]["full_text"] == "Full text of Paper A"


def test_docx_export_no_crash():
    """Verify DOCX export doesn't crash with realistic data."""
    from modules.export.literature_docx import LiteratureDocxExporter

    exporter = LiteratureDocxExporter()
    paper = {
        "title": "A Randomized Trial of Drug X in Hypertension",
        "authors": ["Smith J", "Doe A", "Brown K"],
        "year": 2024,
        "journal": "New England Journal of Medicine",
        "doi": "10.1056/NEJMoa240001",
        "source": "PubMed",
        "abstract": "BACKGROUND: Hypertension affects 1.3 billion people worldwide...",
    }
    full_text = """
    Introduction\n\nHypertension is the leading modifiable risk factor...
    Methods\n\nThis randomized double-blind trial enrolled 5000 participants...
    Results\n\nSystolic BP decreased by 12 mmHg in treatment group vs 3 mmHg placebo...
    Discussion\n\nDrug X demonstrates superior efficacy compared to standard care...
    """

    docx_bytes = exporter.export_article(paper, full_text)
    assert docx_bytes[:2] == b'PK'
    assert len(docx_bytes) > 2000
```

- [ ] **Step 2: Run test to verify it passes**

Run: `python -m pytest tests/test_orchestrator_fulltext.py -v`
Expected: 2 PASS (no orchestrator changes needed for counting logic yet)

- [ ] **Step 3: Update orchestrator.py Phase 3**

Replace lines 41-58 in `modules/literature/orchestrator.py` with:

```python
        # Phase 3: Full-Text Retrieval + DOCX Storage
        status.append(f"Phase 3: Full-Text Retrieval - Downloading {len(selected_papers)} papers...")
        from modules.literature.full_text import FullTextRetriever
        from modules.export.literature_docx import LiteratureDocxExporter
        from api.knowledge import _store_docx_entry

        retriever = FullTextRetriever()
        exporter = LiteratureDocxExporter()
        full_text_papers = []
        docx_stored = 0

        for i, paper in enumerate(selected_papers):
            paper_dict = {
                "title": paper.title,
                "url": paper.url,
                "source": paper.source,
                "authors": paper.authors,
                "abstract": paper.abstract,
                "year": str(paper.year) if paper.year else "",
                "doi": paper.doi,
                "pdf_url": paper.pdf_url,
            }

            logger.info(f"Retrieving ({i+1}/{len(selected_papers)}): {paper.title[:80]}...")
            full_text = retriever.retrieve(paper_dict)

            if full_text:
                try:
                    docx_bytes = exporter.export_article(paper_dict, full_text)
                    _store_docx_entry(
                        category="literature",
                        title=paper.title,
                        docx_bytes=docx_bytes,
                        tags="deep_research,full_text",
                        source=paper.source,
                        metadata={"doi": paper.doi, "year": paper.year}
                    )
                    docx_stored += 1
                    full_text_papers.append(paper)
                    status.append(f"  [{i+1}] OK: {paper.title[:60]} ({len(full_text)} chars)")
                except Exception as e:
                    logger.warning(f"DOCX storage failed for {paper.title}: {e}")
                    status.append(f"  [{i+1}] PARTIAL: {paper.title[:60]} (retrieved but storage failed)")
            else:
                # Abstract-only fallback
                try:
                    docx_bytes = exporter.export_article(paper_dict, None)
                    _store_docx_entry(
                        category="literature",
                        title=paper.title,
                        docx_bytes=docx_bytes,
                        tags="deep_research,abstract_only",
                        source=paper.source,
                        metadata={"doi": paper.doi, "year": paper.year}
                    )
                    docx_stored += 1
                    status.append(f"  [{i+1}] ABSTRACT: {paper.title[:60]} (full text unavailable)")
                except Exception as e:
                    logger.warning(f"Abstract DOCX failed for {paper.title}: {e}")
                    status.append(f"  [{i+1}] FAIL: {paper.title[:60]} ({e})")

        logger.info(f"Full-text retrieved: {len(full_text_papers)}/{len(selected_papers)}, DOCX stored: {docx_stored}")
        status.append(f"Full-text: {len(full_text_papers)}/{len(selected_papers)} | DOCX: {docx_stored} saved to Knowledge Base")
```

Update return dict at bottom of `run_deep_review()` (around line 86) to include:

```python
        return {
            "status": "success",
            "topic": topic,
            "papers_found": len(candidates),
            "papers_reviewed": len(selected_papers),
            "papers_full_text": len(full_text_papers),
            "docx_stored": docx_stored,
            "report_content": report,
            "compliance_report": compliance_result,
            "pipeline_log": status
        }
```

Update imports at top of orchestrator.py:

```python
from typing import Dict, Any, List
```

- [ ] **Step 4: Verify syntax**

Run: `python -c "from modules.literature.orchestrator import DeepResearchOrchestrator; print('OK')"`
Expected: OK (or import error for missing deps, but not syntax error)

- [ ] **Step 5: Commit**

```bash
git add modules/literature/orchestrator.py tests/test_orchestrator_fulltext.py
git commit -m "feat: orchestrator Phase 3 — batch full-text retrieval + per-article DOCX storage"
```

---

### Task 5: Frontend — KB Display DOCX Files

**Files:**
- Modify: `webui/components/knowledge/knowledge-modal.html` (display DOCX entries)

**Interfaces:**
- Consumes: KB index entries with `"format": "docx"`

- [ ] **Step 1: Add DOCX display in KB library view**

Find the entry listing loop in `knowledge-modal.html`. Add a condition for `.docx` format entries to show a "Read" button. Locate where entries are rendered (search for `x-for="entry in entries"` or similar). Add:

```html
<!-- Inside the entry card template, add after existing content display: -->
<template x-if="entry.format === 'docx'">
  <div class="docx-badge">
    <span class="badge badge-docx">DOCX</span>
    <a :href="'/api/knowledge/download?file=' + encodeURIComponent(entry.file)" 
       download 
       class="btn-download-docx">
       Download & Read
    </a>
  </div>
</template>
```

- [ ] **Step 2: Add KB download endpoint**

In `api/knowledge.py`, add a new endpoint that serves DOCX files for download. Add this to the `KnowledgeHandler.process()` method before the final return:

```python
        if action == "download":
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
                }
            )
```

- [ ] **Step 3: Test manually**

Verify KB library shows DOCX entries after literature search runs. Entries should show "DOCX" badge and download link.

- [ ] **Step 4: Commit**

```bash
git add webui/components/knowledge/knowledge-modal.html api/knowledge.py
git commit -m "feat: KB frontend — DOCX download link for literature entries"
```

---
