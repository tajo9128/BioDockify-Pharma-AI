## HOMO-LUMO Calculator

**Purpose:** Calculate frontier molecular orbital energies (HOMO, LUMO, gap) and chemical reactivity descriptors. Uses RDKit empirical correlations for fast estimation. For DFT-grade calculations, PySCF would be needed (optional). Results auto-store to Knowledge Base.

**When to use:**
- User asks about HOMO-LUMO gap, chemical reactivity, or orbital energies
- User wants to assess electrophilicity, nucleophilicity, or stability
- User needs ionization potential or electron affinity estimates
- Comparing reactivity of multiple compounds

### Single Molecule

```python
import sys; sys.path.insert(0, "/a0")
import asyncio
from api.homo_lumo import HomoLumoHandler

async def calc():
    h = HomoLumoHandler()
    result = await h.process({
        "action": "calculate",
        "smiles": "CC(=O)Oc1ccccc1C(=O)O",
        "name": "Aspirin",
    }, None)
    print("HOMO:", result.get("homo_ev"), "eV")
    print("LUMO:", result.get("lumo_ev"), "eV")
    print("Gap:", result.get("gap_ev"), "eV")
    print("Reactivity:", result.get("reactivity"))
    print("Drug-like gap:", result.get("drug_like_gap"))
    print("Energy diagram:", "YES" if result.get("energy_diagram_b64") else "NO")

asyncio.run(calc())
```

### Batch Mode

```python
import sys; sys.path.insert(0, "/a0")
import asyncio
from api.homo_lumo import HomoLumoHandler

async def batch():
    h = HomoLumoHandler()
    result = await h.process({
        "action": "batch",
        "smiles_list": ["CCO", "CC(=O)O", "c1ccccc1"],
        "names": ["Ethanol", "Acetic acid", "Benzene"],
    }, None)
    print("Avg gap:", result["summary"]["avg_gap"], "eV")
    print("Drug-like count:", result["summary"]["drug_like_count"])

asyncio.run(batch())
```

**Properties returned:**
- HOMO, LUMO, gap (eV)
- Chemical hardness, softness, electronegativity, electrophilicity index
- Ionization potential, electron affinity
- Reactivity level (High/Moderate/Low)
- Drug-like gap range (5-9 eV)
- Energy level diagram (base64 PNG)
