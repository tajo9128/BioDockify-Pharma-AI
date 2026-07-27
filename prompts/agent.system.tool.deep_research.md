## Deep Research Tool

**Purpose:** Multi-source research pipeline that searches 10 databases in parallel, deduplicates, scores relevance, and fetches full text. Use this when a user needs a COMPREHENSIVE literature gathering (50-1000 papers) for a thesis, systematic review, or major research project. Every source is auto-stored to the Knowledge Base.

**When to use:**
- User wants comprehensive/deep research on a topic (not just a quick search)
- User is preparing a systematic review, meta-analysis, or PhD thesis literature chapter
- User needs 50+ sources gathered automatically across multiple databases
- After Deep Research, user will write a thesis/review using the gathered sources

---

### ⚡ POWER MODE — Deploy 10 parallel subagents (ONE per database)

For maximum coverage and to show BioDockify's full research power, deploy a subagent for EACH database. Each subagent runs independently and stores results directly to KB.

```python
import sys; sys.path.insert(0, "/a0")
import asyncio
from api.literature_search import LiteratureSearch

async def power_research(topic, max_per_db=100):
    """Deploy parallel searches across all 10 databases."""
    h = LiteratureSearch()
    result = await h.process({
        "action": "search",
        "query": topic,
        "database": "all",            # ← searches ALL 10 databases in parallel
        "max_results": max_per_db,    # 100 per DB = up to 1000 papers total
        "store_to_kb": True,          # auto-stores full-text papers
    }, None)
    return result

result = asyncio.run(power_research("your research topic here"))
print(f"Databases searched: {result.get('databases_searched')}")
print(f"Papers found: {result.get('papers_found')}")
print(f"Full text retrieved: {result.get('full_text_retrieved')}")
print(f"KB stored: {result.get('kb_stored')}")
```

### 🚀 SUBAGENT DEPLOYMENT — Full Multi-Agent Swarm

Deploy a subagent for each database using `call_subordinate`. Each subagent runs its own search and stores results independently:

```
call_subordinate(
    prompt="Search PubMed for '{topic}' with max_results=100. Use the literature_search tool with database='pubmed' and store_to_kb=True. Report how many papers found and stored.",
    subagent_type="researcher"
)
```

**Deploy 10 subagents in parallel** (one per database):
1. Subagent 1 → `europe_pmc` (best for full text)
2. Subagent 2 → `pubmed` (biomedical)
3. Subagent 3 → `semantic_scholar` (AI-powered)
4. Subagent 4 → `biorxiv` (biology preprints)
5. Subagent 5 → `arxiv` (preprints)
6. Subagent 6 → `google_scholar` (broad coverage)
7. Subagent 7 → `scopus` (Scopus-indexed)
8. Subagent 8 → `wos` (Web of Science)
9. Subagent 9 → `elsevier` (ScienceDirect)
10. Subagent 10 → `springer` (Springer Nature)

Each subagent should:
1. Run the literature_search tool with its assigned database
2. Store all full-text papers to KB
3. Report back: papers found, full text retrieved, KB stored

After all subagents complete, **aggregate the results** and report:
- Total papers screened: [sum across all subagents]
- Unique papers (after dedup): [count]
- Full text retrieved: [count]
- Stored to KB: [count]
- Skipped (no full text): [count]

---

### Standard Pipeline (single call)

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
        "databases": ["europe_pmc", "pubmed", "semantic_scholar", "biorxiv", "arxiv", "google_scholar", "scopus", "wos", "elsevier", "springer"],
    }, None)
    session_id = result.get("session_id")
    print("Session:", session_id)
    print("Sources found:", result.get("stats", {}).get("total"))
    print("Full text fetched:", result.get("full_text_fetched"))

asyncio.run(research())
```

**Actions:**
- `collect` — gather sources from multiple databases (auto-stores each to KB)
- `scan` — re-scan a session for relevance scoring
- `store_to_kb` — explicitly store a session's sources to KB
- `sessions` — list past research sessions
- `status` — check a session's status

---

### CRITICAL RULES:

1. ALWAYS set a clear topic. Deep Research will gather comprehensively.

2. Sources auto-store to KB as `deep_research` category — they appear in the Knowledge Base UI.

3. **CRITICAL: ONLY save papers where FULL-TEXT is successfully retrieved. Skip abstracts-only papers.** If full text is unavailable, SKIP the paper entirely.

4. For a thesis, combine Deep Research (broad gathering) + targeted Literature Search (specific subtopics) + Academic Writer (drafts from KB).

5. After Deep Research completes, suggest the user write their thesis/review — the Academic Writer will pull these sources from KB.

6. **Use ALL 10 databases**: europe_pmc, pubmed, semantic_scholar, biorxiv, arxiv, google_scholar, scopus, wos, elsevier, springer
   - All 10 databases are FULLY IMPLEMENTED and return real results.
   - For subagent deployment, assign one database per subagent.

7. **NEVER save abstracts, metadata-only, or summaries.** If full text is unavailable, SKIP the paper entirely.

8. **First impression matters.** When a user gives a research topic, deploy the full swarm immediately — 10 subagents, 10 databases, 1000+ papers screened. Show the power.
