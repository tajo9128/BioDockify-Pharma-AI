## Drug Analysis Tool

**Purpose:** Structural alerts and drug-likeness filtering — PAINS (pan-assay interference, ~480 patterns via RDKit FilterCatalog), Brenk reactive fragments, NIH unwanted substructures, overall pass/fail verdict. Complements ADMET prediction (which covers physicochemical/ADME properties). Results auto-store to the Knowledge Base under `drug_analysis`.

**When to use:**
- User asks "is this compound a PAINS false positive"
- User wants to check for problematic substructures before synthesis or testing
- User is screening a library for problematic compounds
- User asks about reactivity, toxophores, or structural alerts
- Complement to ADMET prediction — use both for full screening

**How to use:** Call via `code_execution_tool`.

```python
import sys; sys.path.insert(0, "/a0")
import asyncio
from api.drug_analysis import DrugAnalysisHandler

async def check():
    h = DrugAnalysisHandler()
    result = await h.process({
        "action": "check",
        "smiles": "CC(=O)Oc1ccccc1C(=O)O",   # aspirin
    }, None)
    print("PAINS alerts:", result.get("pains_alerts", []))
    print("Brenk alerts:", result.get("brenk_alerts", []))
    print("Verdict:", result.get("verdict"))
    # Results auto-store to KB as category=drug_analysis

asyncio.run(check())
```

**Actions:**
- `check` — full structural alert scan (PAINS + Brenk + NIH)
- `filters` — list available filter catalogs

**Critical rules:**
1. Results auto-store to KB under `drug_analysis` — same category as ADMET (both are drug-property analyses).
2. For medicinal chemistry, also use the dedicated Medicinal Chemistry module (Murcko, MMPA, toxicophores, retrosynthesis) — different category.
3. A compound flagged as PAINS should NOT be advanced without careful validation.
4. Combine with ADMET prediction for complete developability assessment.
