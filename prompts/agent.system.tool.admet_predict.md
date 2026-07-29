## ADMET Prediction Tool

**Purpose:** Comprehensive ADMET profiling with SwissADME-grade analysis. Single molecule or batch mode (thousands of compounds). Uses peer-reviewed models: BOILED-Egg (Daina 2016), PAINS/Brenk (RDKit FilterCatalog, 480+ filters), CYP450 SMARTS, hERG (pkCSM), Valko PPB, Ghose/Muegge/Egan drug-likeness filters. Results auto-store to Knowledge Base.

**When to use:**
- User asks about ADMET, PK properties, or drug-likeness
- User wants BOILED-Egg plot, PAINS/Brenk structural alerts
- User is screening compounds for developability
- User needs Lipinski/Veber/Ghose/Muegge/Egan filter checks
- User wants batch analysis of multiple compounds at once
- Before recommending a compound for in-vivo testing

### Single Molecule Analysis

```python
import sys; sys.path.insert(0, "/a0")
import asyncio
from api.admet_predict import AdmetPredict

async def predict():
    h = AdmetPredict()
    result = await h.process({
        "smiles": "CC(=O)Oc1ccccc1C(=O)O",  # aspirin
    }, None)
    print("MW:", result.get("mw"))
    print("LogP:", result.get("logp"))
    print("Lipinski:", result.get("lipinski"))
    print("GI Absorption:", result.get("gi_absorption"))
    print("BBB:", result.get("bbb_pass"))
    print("hERG:", result.get("herg_risk"))
    print("PAINS hits:", result.get("pains", {}).get("hits"))
    print("Brenk hits:", result.get("brenk", {}).get("hits"))
    print("Bioavailability:", result.get("bioavailability_score"))
    print("BOILED-Egg plot:", "YES" if result.get("boiled_egg", {}).get("plot_b64") else "NO")

asyncio.run(predict())
```

### Batch Analysis (thousands of compounds)

```python
import sys; sys.path.insert(0, "/a0")
import asyncio
from api.admet_predict import AdmetPredict

async def batch():
    h = AdmetPredict()
    result = await h.process({
        "smiles_list": [
            "CC(=O)Oc1ccccc1C(=O)O",  # aspirin
            "CC(C)Cc1ccc(cc1)C(C)C(=O)O",  # ibuprofen
            "CC(=O)Nc1ccc(O)cc1",  # paracetamol
        ],
        "names": ["Aspirin", "Ibuprofen", "Paracetamol"],
    }, None)
    print("Analyzed:", result["summary"]["successful"])
    print("Lipinski pass:", result["summary"]["lipinski_pass_rate"])
    print("GI High:", result["summary"]["gi_absorption_high"])
    # Results include: distribution plot (base64 PNG), CSV data

asyncio.run(batch())
```

### Properties Predicted (7 filters + full ADMET)

**Drug-likeness filters (7):**
- Lipinski Ro5 (2001) — with verbose violations
- Veber (2002) — TPSA + rotatable bonds
- Egan (2000) — absorption upper bounds
- Ghose (1999) — qualifying range
- Muegge (2001) — pharmacophore filter
- Golden Triangle (2009) — MW + LogP optimal
- QED (Bickerton 2012) — quantitative drug-likeness

**Pharmacokinetics:**
- GI Absorption (Caco-2 proxy)
- BBB Penetration (BOILED-Egg ellipse model, Daina 2016)
- Plasma Protein Binding (Valko 2001)
- CYP450 Inhibition (1A2, 2C9, 2C19, 2D6, 3A4)
- P-glycoprotein substrate

**Toxicity:**
- hERG Cardiotoxicity (pkCSM-inspired)
- PAINS Alerts (480+ RDKit FilterCatalog filters, Baell 2010)
- Brenk Structural Alerts (toxic/reactive fragments, Brenk 2008)
- Ames Mutagenicity (Benigni-Bossa)
- Bioaccumulation (BCF, Dimitrov 2005)

**Visualizations:**
- BOILED-Egg plot (base64 PNG) with compound plotted
- Batch distribution plots (MW, LogP, Lipinski pie, GI bar)

**Critical rules:**
1. Results auto-store to KB under `drug_analysis` — separate from docking, literature, etc.
2. Always report confidence — these are in-silico predictions, not experimental.
3. For batch mode, use `smiles_list` input — processes thousands efficiently.
4. PAINS/Brenk use RDKit FilterCatalog (480+ curated filters), not hand-written SMARTS.
