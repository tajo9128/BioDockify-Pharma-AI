## Target Identification Tool

**Purpose:** Find and prioritize drug targets — disease-target associations from OpenTargets Platform, UniProt, and ChEMBL (live REST APIs), with curated local fallback when offline. Includes gene lookup, pathway enrichment, and druggability assessment. This is the STARTING POINT of target-based drug discovery.

**When to use:**
- User asks "what targets are involved in X disease?" (cancer, Alzheimer, diabetes...)
- User wants details about a specific target gene (EGFR, BRAF, TP53...)
- User has a gene list (e.g. from omics data) and wants pathway enrichment
- User asks whether a target is druggable (has ligands, antibodies, or is safety-critical)
- Before docking/pharmacophore work — to choose and justify the protein target

**How to use:** Call via `code_execution_tool`. NOTE: `search_disease` and `search_gene` hit live APIs (OpenTargets/UniProt/ChEMBL) — works in Docker with internet; falls back to curated local data offline.

```python
import sys; sys.path.insert(0, "/a0")
import asyncio
from api.target_identification import TargetIdentificationHandler

async def find_targets():
    h = TargetIdentificationHandler()
    result = await h.process({
        "action": "search_disease",
        "disease": "alzheimer",
        "limit": 10,
    }, None)
    print(result)  # ranked targets with association scores

asyncio.run(find_targets())
```

**Actions:**
- `search_disease` — ranked disease-target associations (`disease`, `limit`)
- `search_gene` — gene summary: function, associated diseases, known drugs
- `target_details` — deep dive on one gene: UniProt data, ChEMBL compounds, class
- `pathways` — pathway enrichment for a gene list (`genes` array)
- `druggability` — druggability assessment: tractability, ligands, safety

**Critical rules:**
1. Report the data source (API vs local fallback) — offline results are less complete.
2. Association scores ≠ causality; recommend literature validation for top targets.
3. After picking a target, hand off naturally: Docking (structure-based), Pharmacophore (ligand-based), Bioactivity Predictor (activity class), Deep Research (evidence).
4. For a gene list from user data, use `pathways` — it finds over-represented pathways.

**Pipeline context:** Target ID → Literature/Deep Research → Pharmacophore/Docking → Molecule Designer → Bioactivity Predictor
