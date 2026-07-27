## Literature Search Tool

**Purpose:** Search 10 academic databases for REAL peer-reviewed papers with FULL TEXT. Returns papers with full article text automatically retrieved. ONLY papers with full text are stored to Knowledge Base.

---

### ⚡ FAST START — ONE CALL searches all 10 databases at once:

```python
import sys; sys.path.insert(0, "/a0")
import asyncio
from api.literature_search import LiteratureSearch

async def search():
    h = LiteratureSearch()
    result = await h.process({
        "action": "search",
        "query": "your search query here",
        "database": "all",            # ← "all" searches all 10 databases IN PARALLEL
        "max_results": 100,           # per database (1000 total potential)
        "store_to_kb": True,          # auto-stores full-text papers to Knowledge Base
    }, None)
    print(f"Databases searched: {result.get('databases_searched')}")
    print(f"Papers found: {result.get('papers_found')}")
    print(f"Full text retrieved: {result.get('full_text_retrieved')}")
    print(f"KB stored: {result.get('kb_stored')}")
    print(f"KB skipped: {result.get('kb_skipped')}")

asyncio.run(search())
```

---

### Single-database search (for targeted follow-up):

```python
import sys; sys.path.insert(0, "/a0")
import asyncio
from api.literature_search import LiteratureSearch

async def search():
    h = LiteratureSearch()
    result = await h.process({
        "action": "search",
        "query": "your search query here",
        "database": "europe_pmc",     # 10 databases: europe_pmc | pubmed | semantic_scholar | biorxiv | arxiv | google_scholar | scopus | wos | elsevier | springer
        "max_results": 100,
        "store_to_kb": True,
    }, None)
    print("Found:", result.get("total"), "papers")
    print("Full text retrieved:", result.get("full_text_fetched"))
    print("KB stored:", result.get("kb_stored"))

asyncio.run(search())
```

---

### WHAT HAPPENS AUTOMATICALLY (you do NOT need to do these):
1. The tool searches the database(s) and returns papers
2. For EACH paper, it automatically tries 3 tiers of full text retrieval:
   - Tier 1: Europe PMC fullTextXML (requires PMCID)
   - Tier 2: PDF download + text extraction
   - Tier 3: Hacker Agent (6 strategies: CORE.ac.uk, Semantic Scholar, Jina AI, Playwright, Google Scholar, raw scrape)
3. ONLY papers where full text was successfully retrieved are stored to Knowledge Base
4. Papers without full text are SKIPPED automatically — they are NOT stored

---

### CRITICAL RULES — YOU MUST FOLLOW ALL OF THESE:

1. **USE THIS TOOL** for all literature searches. Do NOT search databases manually. Do NOT use web_search for academic papers.

2. **Set `store_to_kb: True`** — this is the ONLY way papers get into the Knowledge Base. The tool handles storage automatically.

3. **NEVER call `auto_store()` directly for literature papers.** The `literature_search` tool already handles storage with full text validation.

4. **NEVER store stubs.** A stub is any content like:
   - "Full article saved as PDF and DOCX."
   - "Abstract not available."
   - Just metadata (title, authors, DOI) without the full article body
   - Content shorter than 2000 characters

5. **If `kb_stored` is 0** (no papers had full text), tell the user: "No full-text articles were available for download. Try a different search query or database." Do NOT try to save them manually.

6. **Use `database: "all"` for the first search** — this searches all 10 databases in parallel for maximum coverage (up to 1000 papers). Then use single-database searches for targeted follow-up on specific subtopics.

7. **The 10 databases** (all fully implemented):
   - `europe_pmc` — BEST for full text (open access XML)
   - `pubmed` — biomedical literature (35M+ citations)
   - `semantic_scholar` — AI-powered search with citations
   - `biorxiv` — biology preprints
   - `arxiv` — physics/math/CS preprints
   - `google_scholar` — broadest coverage (via Crossref)
   - `scopus` — Scopus-indexed journals (via Crossref)
   - `wos` — Web of Science journals (via Crossref)
   - `elsevier` — ScienceDirect/Elsevier journals (via Crossref)
   - `springer` — Springer Nature journals (via Crossref)

8. **After searching**, report to the user:
   - How many databases were searched
   - How many papers were found (total)
   - How many had full text retrieved
   - How many were stored to KB
   - How many were skipped (no full text)

---

### TWO-ROUND WORKFLOW (for comprehensive research):

**Round 1:** Search all 10 databases at once using `database: "all"` with `store_to_kb: True`. This automatically downloads and stores all available full-text articles. Use multiple query variations to maximize coverage:
- Main topic: `"drug-drug interactions in elderly"`
- Specific mechanism: `"CYP450 inhibition pharmacokinetics"`
- Clinical outcome: `"adverse drug reactions polypharmacy"`
- Each query returns up to 1000 papers across 10 databases.

**Round 2:** For papers that failed Round 1 (no full text), try the Hacker Agent:
```python
import sys; sys.path.insert(0, "/a0")
from modules.literature.full_text import FullTextRetriever

retriever = FullTextRetriever()
for paper in failed_papers:
    full_text = retriever.retrieve(paper)
    if full_text and len(full_text) > 2000:
        from modules.knowledge.auto_store import auto_store
        auto_store(
            module_name="literature_search",
            title=paper["title"],
            content=f"**Authors:** {', '.join(paper.get('authors',[]))}\n\n## Full Text\n\n{full_text}",
            source="Europe PMC",
            tags=["literature", "full_text"],
            category="literature",
        )
    else:
        print(f"SKIP (no full text): {paper['title'][:50]}")
```

---

**Databases available (10 total):** europe_pmc, pubmed, semantic_scholar, arxiv, biorxiv, google_scholar, scopus, wos, elsevier, springer
