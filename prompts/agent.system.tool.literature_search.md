## Literature Search Tool

**Purpose:** Search 10 academic databases for REAL peer-reviewed papers with FULL TEXT. Returns papers with full article text automatically retrieved. ONLY papers with full text are stored to Knowledge Base.

---

### HOW TO USE — Follow this EXACT workflow:

**IMPORTANT: Use the framework Python which has all dependencies:**
```python
import sys; sys.path.insert(0, "/a0")
import asyncio
from api.literature_search import LiteratureSearch

async def search():
    h = LiteratureSearch()
    result = await h.process({
        "action": "search",
        "query": "your search query here",
        "database": "europe_pmc",       # BEST for full text: europe_pmc | pubmed | semantic_scholar | biorxiv | arxiv
        "max_results": 50,
        "store_to_kb": True,            # ONLY stores papers that have full text
    }, None)
    print("Found:", result.get("total"), "papers")
    print("Full text retrieved:", result.get("full_text_fetched"))
    print("KB stored:", result.get("kb_stored"))
    print("KB skipped (no full text):", result.get("kb_skipped"))

asyncio.run(search())
```

---

### WHAT HAPPENS AUTOMATICALLY (you do NOT need to do these):
1. The tool searches the database and returns papers
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

3. **NEVER call `auto_store()` directly for literature papers.** The `literature_search` tool already handles storage with full text validation. Calling `auto_store` directly bypasses the full text check and stores empty stubs.

4. **NEVER store stubs.** A stub is any content like:
   - "Full article saved as PDF and DOCX."
   - "Abstract not available."
   - Just metadata (title, authors, DOI) without the full article body
   - Content shorter than 2000 characters

5. **If `kb_stored` is 0** (no papers had full text), tell the user: "No full-text articles were available for download. Try a different search query or database." Do NOT try to save them manually.

6. **Search ALL 10 databases** for comprehensive coverage: `europe_pmc`, `pubmed`, `semantic_scholar`, `biorxiv`, `arxiv`, `openalex`, `crossref`, `drugbank`, `chembl`, `kegg`

7. **Run multiple searches** with different query terms to get 50-200 papers for a thesis.

8. **After searching**, report to the user:
   - How many papers were found
   - How many had full text retrieved
   - How many were stored to KB
   - How many were skipped (no full text)

---

### WHAT TO DO IF FULL TEXT RETRIEVAL FAILS:
- Do NOT try to save the paper anyway
- Do NOT write metadata to the Knowledge Base
- Simply SKIP the paper and move to the next one
- Tell the user how many papers were skipped

---

### TWO-ROUND WORKFLOW (for comprehensive research):

**Round 1:** Search all 10 databases with `store_to_kb: True`. This automatically downloads and stores all available full-text articles.

**Round 2:** For papers that failed Round 1 (no full text), try the Hacker Agent:
```python
import sys; sys.path.insert(0, "/a0")
from modules.literature.full_text import FullTextRetriever

retriever = FullTextRetriever()
for paper in failed_papers:
    full_text = retriever.retrieve(paper)
    if full_text and len(full_text) > 2000:
        # Only NOW store it
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

**Databases available:** europe_pmc, pubmed, semantic_scholar, openalex, crossref, arxiv, biorxiv, drugbank, chembl, kegg
