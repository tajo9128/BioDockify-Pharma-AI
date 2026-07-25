## Knowledge Base Storage Tool

**Purpose:** Store research outputs (literature, docking, QSAR, statistics, notes, etc.) into the user-visible Knowledge Base so they appear in the KB UI at `/components/knowledge/knowledge-modal.html`. This is the canonical way to persist any result the user needs to see later.

**When to use:**
- User says "save this to the knowledge base" / "store this" / "add to KB"
- You completed a research task (literature search, docking, analysis) and want results to persist
- You generated a report, summary, or interpretation the user should be able to reopen
- Any time you would otherwise be tempted to use `memory_save` for content the user needs to SEE in the UI

**When NOT to use:**
- For agent-only recall across conversations → use `memory_save` instead (separate system)
- For ephemeral working state → keep in chat
- For raw tool output that the calling module already auto-stores (most modules auto-store — check first)

**How to use:** You do NOT have a `callJsonApi` tool. Use `code_execution_tool` (runtime: python) with the `auto_store` helper:

```python
import sys; sys.path.insert(0, "/a0")
from modules.knowledge.auto_store import auto_store

entry = auto_store(
    module_name="literature_search",   # see MODULE_TO_CATEGORY for valid module names
    title="Aspirin COX-2 inhibition review",
    content="**Authors:** Smith J et al.\n\n## Abstract\n\n...",  # markdown content (string, dict, or list)
    source="PubMed",                    # where it came from
    tags=["literature", "review"],      # list of tags
    category="literature",              # optional — auto-detected from module_name if omitted
    metadata={"doi": "10.1038/..."},    # optional extra metadata
)
print("Stored:", entry["id"], "→", entry["file"])
```

**Module → Category auto-detection** (omit `category` to use these):
- `literature_search` → literature
- `deep_research` → deep_research
- `docking_run`, `docking_mmgbsa`, `docking_analysis` → docking
- `md_lite` → md_simulation
- `qsar3d` → qsar
- `pharmacophore` → pharmacophore
- `drug_analysis`, `admet_predict`, `drug_properties` → drug_analysis
- `statistics_analyze`, `statistics_auto` → statistics
- `faculty`, `faculty_tools`, `ppt_master` → faculty
- `pharmacology` → pharmacology
- `medicinal_chemistry` → medicinal_chemistry
- `clinical`, `clinical_trials` → clinical_trials
- `formulation`, `pharma_utils` → formulation
- `pharma_analysis` → pharma_analysis
- `natural_products` → natural_products
- `knowledge`, `upload`, `notes`, `writing` → notes
- anything else → misc

**Critical rules:**
1. `auto_store` is **stdlib-only** (os, json, time, logging). It does NOT import Flask or FastAPI. It works in your code_execution_tool environment.
2. **Do NOT** use `from api.knowledge import _store_entry` — that file imports Flask and will raise `ModuleNotFoundError: No module named 'flask'` in your environment.
3. **Do NOT** use `memory_save` for user-visible content. `memory_save` writes to your internal recall vector DB; the KB UI cannot see it. These are two separate systems.
4. **Do NOT** manually write `.md` files to `/a0/data/knowledge_base/` and edit `index.json` yourself — this risks corrupting the index. Always go through `auto_store`.
5. Content can be a string (markdown), dict, or list. Dicts/lists are pretty-formatted as markdown automatically.
6. **NEVER store stubs, abstracts, or metadata-only entries for literature.** If full text retrieval fails, DO NOT save the article. `auto_store` will reject entries shorter than 2000 chars for literature/deep_research categories. Skip and move on to the next article.

**To read the Knowledge Base** (browse what's already stored):
```python
import sys; sys.path.insert(0, "/a0")
from modules.knowledge.auto_store import _load_index
idx = _load_index()
for e in idx["entries"][-20:]:
    print(e["created_at"], e["title"], "→", e["category"])
```

**Verification after storing:** After `auto_store(...)` returns, the entry is immediately on disk and will appear in the KB UI the next time the user opens it. Confirm by reading back the index (above).
