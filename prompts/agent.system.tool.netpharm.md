## Network Pharmacology Tool

**Purpose:** TCM/network-pharmacology style analysis — build a compound-target network against a disease target set: rank compounds by disease-target overlap (multi-target compounds flagged), identify target hubs (most-connected intervention points), and run pathway enrichment on the covered targets. 68-compound curated offline database (phytochemicals + common drugs) plus user-supplied custom compounds.

**When to use:**
- User asks "which compounds act on this disease's targets" or network pharmacology / multi-target / TCM-style analysis
- User has a gene list (e.g. from Target ID or omics) and wants compounds hitting those genes → `analyze`
- User wants to know the hubs of a disease network (attractive drug targets)
- User studies herbal extracts / multi-component therapies → custom compounds + `analyze`
- After Target Identification → this extends target selection with compound perspective

**How to use:** Call via `code_execution_tool`.

```python
import sys; sys.path.insert(0, "/a0")
import asyncio
from api.netpharm import NetPharmHandler

async def main():
    h = NetPharmHandler()
    r = await h.process({
        "action": "analyze_disease", "disease": "inflammation",
    }, None)
    for c in r["ranked_compounds"][:5]:
        print(c["compound"], c["num_hits"], "hits")
    print("hubs:", [(x["target"], x["degree"]) for x in r["target_hubs"][:5]])

asyncio.run(main())
```

**Actions:**
- `compounds` — the curated compound-target database (name → HGNC target list)
- `compound_targets` — one compound's target list (`compound`)
- `analyze` — network vs gene list (`gene_list`, optional `custom_compounds` {name: [targets]}, `use_curated_db`)
- `analyze_disease` — full pipeline: disease → targets (via Target Identification) → network (`disease`, `limit`, `custom_compounds`)

**Critical rules:**
1. The curated DB is a starter set — for publication-grade networks, have the user supply literature-backed `custom_compounds`.
2. Pathway enrichment is offline-curated; recommend STRING/Reactome/GO validation for publication.
3. Report multi-target compounds explicitly — they are the interesting ones in network pharmacology.
4. Hubs with high degree are both attractive (one target, many compounds confirm) and potentially promiscuous — present both views.

**Pipeline context:** Target ID → Network Pharmacology (compounds + hubs) → prioritize → Docking/ADMET on top compounds; Pharmacognosy: extract compounds → netpharm → hubs
