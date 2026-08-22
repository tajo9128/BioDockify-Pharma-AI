## Bioactivity Predictor Tool

**Purpose:** Predict bioactivity (IC50/pIC50) of small molecules against major target classes using pre-trained ML models (Random Forest on ECFP4 fingerprints). Also finds similar known actives and detects activity cliffs (SAR analysis). Bridges the gap between molecule generation/docking and experimental validation prioritization.

**When to use:**
- User asks "will this compound be active against kinases/GPCRs/proteases?"
- User wants a predicted IC50 or pIC50 for a molecule before synthesis or docking
- User has a batch of molecules (e.g. from Molecule Designer) and wants them ranked by predicted activity
- User asks for compounds similar to a known active
- User wants SAR / activity cliff analysis on a compound series (small structural change, big potency change)
- After target identification, to check what target class a ligand is likely active against

**How to use:** Call via `code_execution_tool`.

```python
import sys; sys.path.insert(0, "/a0")
import asyncio
from api.bioactivity_predictor import BioactivityPredictorHandler

async def predict():
    h = BioactivityPredictorHandler()
    result = await h.process({
        "action": "predict",
        "smiles": "CC(=O)Oc1ccccc1C(=O)O",   # aspirin
        "target_class": "general",             # or kinase/gpcr/protease/...
    }, None)
    print(result)  # predicted pIC50, confidence, model used

asyncio.run(predict())
```

**Actions:**
- `predict` — single molecule: predicted pIC50 + activity class for a target class
- `batch_predict` — rank a list of molecules (`smiles_list`)
- `target_classes` — available target classes: kinase, gpcr, protease, nuclear_receptor, ion_channel, transporter, epigenetic, general
- `similar` — find known actives similar to a query molecule (`threshold` Tanimoto, default 0.3)
- `activity_cliffs` — SAR analysis: pairs with high similarity but large potency difference (`smiles_list` + `activities` pIC50 values)

**Critical rules:**
1. Use `target_classes` first if unsure which target class applies.
2. When no pre-trained model exists for a class, the module falls back to similarity-based prediction — report this to the user (lower confidence).
3. Predictions are approximate ML estimates, not experimental data — always label them as predicted values.
4. Works well combined with other modules: Molecule Designer (rank generated molecules), QSAR (compare models), Docking (structural validation).

**Pipeline context:** Target ID → Molecule Designer → Bioactivity Predictor → Docking → MM-GBSA → MD Lite
