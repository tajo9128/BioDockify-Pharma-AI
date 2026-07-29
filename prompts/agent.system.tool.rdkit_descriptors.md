## RDKit Descriptors Calculator

**Purpose:** Calculate 200+ molecular descriptors across 7 categories using RDKit. Single molecule or batch mode. Includes drug-likeness categories (Fragment-like, Lead-like, Drug-like, Non-drug-like). Results auto-store to Knowledge Base.

**When to use:**
- User asks about molecular descriptors, physicochemical properties
- User wants comprehensive molecular characterization
- User needs descriptor matrix for QSAR modeling
- User wants to categorize compounds as Fragment/Lead/Drug-like

### Single Molecule

```python
import sys; sys.path.insert(0, "/a0")
import asyncio
from api.rdkit_descriptors import RdkitDescriptorsHandler

async def calc():
    h = RdkitDescriptorsHandler()
    result = await h.process({
        "action": "calculate",
        "smiles": "CC(=O)Oc1ccccc1C(=O)O",
    }, None)
    print("Descriptors:", len([k for k in result if isinstance(result[k], (int, float))]))
    print("Drug category:", result.get("Drug_category"))
    print("MW:", result.get("MolWt"))
    print("LogP:", result.get("MolLogP"))
    print("TPSA:", result.get("TPSA"))

asyncio.run(calc())
```

### Batch Mode

```python
import sys; sys.path.insert(0, "/a0")
import asyncio
from api.rdkit_descriptors import RdkitDescriptorsHandler

async def batch():
    h = RdkitDescriptorsHandler()
    result = await h.process({
        "action": "batch",
        "smiles_list": ["CCO", "CC(=O)O", "c1ccccc1"],
    }, None)
    print("Molecules:", result["n_molecules"])
    print("Descriptors:", result["n_descriptors"])
    print("Categories:", result.get("drug_categories"))

asyncio.run(batch())
```

### Categories Available

```python
import sys; sys.path.insert(0, "/a0")
import asyncio
from api.rdkit_descriptors import RdkitDescriptorsHandler

async def cats():
    h = RdkitDescriptorsHandler()
    result = await h.process({"action": "categories"}, None)
    for name, info in result["categories"].items():
        print(f"{name}: {info['count']} descriptors")

asyncio.run(cats())
```

**7 Descriptor Categories:**
- basic (24): MolWt, LogP, TPSA, HBD, HBA, RotBonds, FractionCSP3, etc.
- topological (17): Chi0-4, Kappa1-3, HallKierAlpha, BalabanJ, BertzCT
- electronic (8): EState indices, partial charges
- surface (36): SlogP_VSA1-12, SMR_VSA1-10, PEOE_VSA1-14
- bcut (8): BCUT2D_MW/CHG/LOGP/MR
- autocorr (8): Autocorr2D vectors
- fragment (80+): fr_ether, fr_halogen, fr_benzene, fr_sulfone, etc.

**Drug-likeness categories:** Fragment-like, Lead-like, Drug-like, Non-drug-like
