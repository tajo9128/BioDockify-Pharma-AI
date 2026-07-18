## ADMET Prediction Tool

**Purpose:** Predict Absorption, Distribution, Metabolism, Excretion, and Toxicity properties of a small molecule from its SMILES. Uses science-based models (BOILED-Egg for BBB, pkCSM-inspired hERG, Valko PPB, SwissADME bioavailability, CYP450 SMARTS soft spots). Results auto-store to the Knowledge Base under the `drug_analysis` category.

**When to use:**
- User asks about ADMET, PK properties, or drug-likeness of a compound
- User wants to know if a compound will cross the BBB, bind hERG, or be metabolized by CYP450
- User is screening a lead compound for developability
- User needs Lipinski/Veber/Golden Triangle rule checks
- Before recommending a compound for in-vivo testing

**How to use:** Call via `code_execution_tool`.

```python
import sys; sys.path.insert(0, "/a0")
import asyncio
from api.admet_predict import AdmetPredict

async def predict():
    h = AdmetPredict()
    result = await h.process({
        "smiles": "CC(=O)Oc1ccccc1C(=O)O",   # aspirin
    }, None)
    print("MW:", result.get("molecular_weight"))
    print("LogP:", result.get("logp"))
    print("BBB:", result.get("bbb_permeability"))
    print("hERG risk:", result.get("herg_risk"))
    print("Bioavailability:", result.get("bioavailability_score"))
    # Results auto-store to KB as category=drug_analysis

asyncio.run(predict())
```

**Properties predicted:**
- Physicochemical: MW, LogP, TPSA, HBD, HBA, rotatable bonds, aromatic rings, QED
- Absorption: Caco-2 proxy, GI absorption
- Distribution: BBB (BOILED-Egg), plasma protein binding (Valko)
- Metabolism: CYP1A2/2C9/2C19/2D6/3A4 inhibition (SMARTS)
- Toxicity: hERG risk (pkCSM-inspired)
- Drug-likeness: Lipinski, Veber, Golden Triangle, bioavailability

**Critical rules:**
1. Results auto-store to KB under `drug_analysis` — separate from docking, literature, etc.
2. Always report confidence — these are in-silico predictions, not experimental.
3. For thorough safety screening, also use the Drug Analysis tool (PAINS, Brenk alerts).
