# Full-Text Literature Pipeline — Design Spec

**Date:** 2026-07-12 | **Version:** 1.0 | **For:** BioDockify Pharma AI v7.2.0

---

## 1. Problem

Current literature pipeline discovers articles from 10 databases but stores only abstracts as individual `.md` files. The Deep Research orchestrator retrieves full text via Playwright but stores it as one markdown blob — not per-article readable documents. Users with 100-200 article literature reviews cannot view individual full-text articles.

## 2. Solution

### 2.1 New Module: `modules/literature/full_text.py`

Source-agnostic full-text retriever using article identifiers (not database origin).

**`FullTextRetriever` class:**

```
retrieve(article: Dict) -> Optional[str]
```

Three-tier retrieval, tried in order per article:

| Tier | Method | Trigger | How |
|------|--------|---------|-----|
| 1 | Europe PMC XML | article has `pmcid` | `GET /webservices/rest/{pmcid}/fullTextXML` → strip XML tags → clean text |
| 2 | PDF download | article has `full_text_url` or `openAccessPdf` | `requests.get(pdf_url)` → `pypdf.PdfReader` → extract text per page |
| 3 | Hacker Agent | DOI exists, tiers 1-2 failed | `WebResearchEngine.deep_read(doi_url)` (Jina AI first, Playwright stealth fallback) |

**Return:** Full text as plain string, or `None` if all tiers fail.

**Counting:** Only articles where retrieval succeeds (non-None) are counted toward the final total.

### 2.2 New Module: `modules/export/literature_docx.py`

**`LiteratureDocxExporter` class:**

```
export_article(paper: Dict, full_text: Optional[str]) -> bytes
```

Generates a formatted `.docx` using `python-docx`:

| Section | Content |
|---------|---------|
| Title page | Title, authors, journal, year, DOI |
| Abstract | Structured abstract |
| Full text | Page-by-page body (if available) |
| Source info | Database origin, retrieval method, OA status |
| Footer | Page numbers, "Retrieved by BioDockify AI" |

**Output:** `.docx` bytes written to `data/knowledge_base/literature/{safe_title}.docx`

**Abstract-only mode:** If `full_text` is None, generate DOCX with "Full Text Unavailable — Abstract Only" header.

### 2.3 Updated: `modules/literature/orchestrator.py`

**New Phase 3 (replaces current): Batch Full-Text Retrieval**

```python
# After discovery + screening, for ALL selected papers:
retriever = FullTextRetriever()
exporter = LiteratureDocxExporter()
successful = []

for paper in selected_papers:  # all 100-200
    full_text = await retriever.retrieve(paper)
    if full_text:
        docx_bytes = exporter.export_article(paper, full_text)
        kb_store.save_docx(paper['title'], docx_bytes, category='literature')
        successful.append(paper)

logger.info(f"Full-text retrieved: {len(successful)}/{len(selected_papers)}")
# Phase 4 synthesis uses only `successful` articles
```

### 2.4 Updated: KB Storage

New action `store_docx` in `api/knowledge.py`:
- Writes `.docx` to `data/knowledge_base/literature/`
- Updates `index.json` with entry (category=literature, format=docx)
- NO vector indexing for DOCX (binary format)
- Frontend: KB displays `.docx` entries with download/view button

### 2.5 Hacker Agent

When Tier 1 and Tier 2 fail on a paywalled article:
- Pass DOI/URL to existing `WebResearchEngine.deep_read()`
- Jina AI reader first (fast, free tier)
- Falls back to Playwright stealth browser
- Captures whatever page content is accessible (sometimes abstract + figures/tables even behind paywall)
- Tagged in DOCX as "Partial Access — Paywall Limited"

## 3. Files Changed

| File | Change |
|------|--------|
| `modules/literature/full_text.py` | **NEW** — FullTextRetriever |
| `modules/export/literature_docx.py` | **NEW** — LiteratureDocxExporter |
| `modules/literature/orchestrator.py` | Phase 3 rewritten: batch retrieve + DOCX store |
| `api/knowledge.py` | New `store_docx` action, DOCX entry support in `library` action |
| `webui/components/knowledge/knowledge-modal.html` | Display DOCX entries with read/download buttons |
| `requirements2.txt` | Add `python-docx>=1.0.0` (if not present) |

## 4. Dependencies

- `python-docx` — DOCX generation (new)
- `pypdf` — PDF text extraction (already in codebase)
- `requests` — HTTP downloads (already in codebase)
- `WebResearchEngine` — existing module for Tier 3 scraping
- `Europe PMC API` — free, no key required for fullTextXML

## 5. Edge Cases

- **No full text available for any article:** Fall back to abstract-only DOCX for all, clearly labeled
- **Partial scrape:** Hacker Agent may only get first page behind paywall — label as "Partial Access"
- **Very large articles (50+ pages):** Truncate at 30 pages in DOCX to avoid file bloat; note truncation
- **Duplicate titles:** Append `_2`, `_3` to filename
- **Rate limiting:** Europe PMC: 1 req/sec. Unpaywall: polite delay. Playwright: sequential only.

## 6. Success Metrics

- Full-text retrieved for 70-80% of discovered articles
- Each article stored as individual `.docx` in KB
- User can browse all articles in Knowledge Base under "Literature" category
- Review article synthesis uses only articles with full text (better quality)
