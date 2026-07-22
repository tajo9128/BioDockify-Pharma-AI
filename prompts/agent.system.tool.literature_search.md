## Literature Search Tool

**Purpose:** Search 10 academic databases (PubMed, Semantic Scholar, Europe PMC, arXiv, bioRxiv, etc.) for real peer-reviewed papers. Returns titles, authors, abstracts, DOIs, and **automatically fetches full text** via Europe PMC (Tier 1), PDF extraction (Tier 2), or Hacker Agent (Tier 3). Every paper is auto-stored to the Knowledge Base.

**When to use:**
- User asks to find/search articles, papers, or literature on ANY topic
- User wants to build a literature review or systematic review
- User needs sources for a thesis, review article, or research paper
- User asks "what does the literature say about X"
- **DO NOT fabricate article metadata or abstracts** — always use this tool to get real papers

**How to use:** Call via `code_execution_tool` (runtime: python). The module auto-stores every result to the KB.

```python
import sys; sys.path.insert(0, "/a0")
import asyncio
from api.literature_search import LiteratureSearch

async def search():
    h = LiteratureSearch()
    result = await h.process({
        "action": "search",
        "query": "molecular dynamics simulation protein-ligand",
        "database": "pubmed",          # pubmed | semantic_scholar | europe_pmc | biorxiv | arxiv
        "max_results": 30,
        "store_to_kb": True,            # auto-stores every paper to KB
    }, None)
    print("Found:", result.get("total"), "papers")
    print("Full text fetched:", result.get("full_text_fetched"))
    print("KB stored:", result.get("kb_stored"))
    for p in result.get("papers", [])[:5]:
        print(" -", p["title"][:70])

asyncio.run(search())
```

**Critical rules:**
1. ALWAYS use this tool for literature — never fabricate DOIs, titles, or abstracts.
2. Set `store_to_kb: True` so papers flow into the Knowledge Base for the Academic Writer.
3. For comprehensive reviews, search across ALL 10 databases (pubmed, semantic_scholar, europe_pmc, openalex, crossref, arxiv, biorxiv, drugbank, chembl, kegg) and combine.
4. Full text retrieval is automatic — Europe PMC open-access papers get full text via XML; others attempt PDF download via Sci-Hub, Unpaywall, or publisher links.
5. **CRITICAL: ONLY save papers where FULL-TEXT is successfully retrieved. Skip abstracts-only papers. Save each full article as DOCX + PDF.**
6. To gather 200+ papers for a thesis, run multiple searches with related query terms across all databases.
7. **NEVER save abstracts, metadata-only, or summaries. If full text is unavailable, SKIP the paper entirely.**

**Databases available:** pubmed, semantic_scholar, europe_pmc, openalex, crossref, arxiv, biorxiv, drugbank, chembl, kegg
