## Deep Research Tool

**Purpose:** Multi-source research pipeline that searches 10+ databases in parallel, deduplicates, scores relevance, and fetches full text. Use this when a user needs a COMPREHENSIVE literature gathering (50-300 papers) for a thesis, systematic review, or major research project. Every source is auto-stored to the Knowledge Base.

**When to use:**
- User wants comprehensive/deep research on a topic (not just a quick search)
- User is preparing a systematic review, meta-analysis, or PhD thesis literature chapter
- User needs 50+ sources gathered automatically across multiple databases
- After Deep Research, user will write a thesis/review using the gathered sources

**How to use:** Call via `code_execution_tool`. The pipeline has stages — collect sources, then optionally scan/store.

```python
import sys; sys.path.insert(0, "/a0")
import asyncio
from api.deep_research import DeepResearch

async def research():
    h = DeepResearch()
    # Stage 1: collect sources from all databases
    result = await h.process({
        "action": "collect",
        "topic": "EGFR inhibitors in non-small cell lung cancer",
        "max_sources": 100,
        "databases": ["pubmed", "semantic_scholar", "europe_pmc", "biorxiv", "arxiv"],
    }, None)
    session_id = result.get("session_id")
    print("Session:", session_id)
    print("Sources found:", result.get("stats", {}).get("total"))
    print("Full text fetched:", result.get("full_text_fetched"))
    # Sources auto-stored to KB with category=deep_research

asyncio.run(research())
```

**Actions:**
- `collect` — gather sources from multiple databases (auto-stores each to KB)
- `scan` — re-scan a session for relevance scoring
- `store_to_kb` — explicitly store a session's sources to KB
- `sessions` — list past research sessions
- `status` — check a session's status

**Critical rules:**
1. ALWAYS set a clear topic. Deep Research will gather comprehensively.
2. Sources auto-store to KB as `deep_research` category — they appear in the Knowledge Base UI.
3. **CRITICAL: ONLY save papers where FULL-TEXT is successfully retrieved. Skip abstracts-only papers. Save each full article as DOCX + PDF.**
4. For a thesis, combine Deep Research (broad gathering) + targeted Literature Search (specific subtopics).
5. After Deep Research completes, suggest the user write their thesis/review — the Academic Writer will pull these sources from KB.
6. Use these databases: pubmed, semantic_scholar, europe_pmc, biorxiv, arxiv
   - These 5 databases are FULLY IMPLEMENTED and return real results with full text.
   - Do NOT use drugbank, chembl, kegg, openalex, crossref — they return 0 results.
7. **NEVER save abstracts, metadata-only, or summaries. If full text is unavailable, SKIP the paper entirely.**
