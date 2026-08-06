## Docking Tool

**Purpose:** Run AutoDock Vina molecular docking — predicts how a small molecule (ligand) binds to a protein target. Returns binding energies, poses, and key interactions. Results auto-store to the Knowledge Base for later analysis (MM-GBSA, MD simulations, thesis writing).

**When to use:**
- User wants to dock a ligand against a protein target
- User asks "will this compound bind to X receptor"
- User is doing structure-based drug design
- User asks for binding energy, pose prediction, or binding affinity
- After docking, user may want AI interpretation, MD simulation, or thesis write-up

**How to use:** Docking is a longer-running task. Call via `code_execution_tool`.

```python
import sys; sys.path.insert(0, "/a0")
import asyncio
from api.docking_run import DockingRun

async def dock():
    h = DockingRun()
    result = await h.process({
        "action": "dock",
        "receptor": "/path/to/protein.pdb",      # or PDB ID
        "ligand": "CC(=O)Oc1ccccc1C(=O)O",        # SMILES or .pdbqt path
        "center_x": 0, "center_y": 0, "center_z": 0,
        "size_x": 20, "size_y": 20, "size_z": 20,
        "exhaustiveness": 64,                      # higher = better, slower
    }, None)
    print("Status:", result.get("status"))
    print("Best affinity:", result.get("best_affinity"), "kcal/mol")
    # Results auto-store to KB as category=docking

asyncio.run(dock())
```

**Actions:**
- `dock` — run a docking job (auto-stores results to KB)
- `status` — check progress of a running job
- `results` — retrieve completed job results

**Critical rules:**
1. Docking results auto-store to KB — they appear in the Knowledge Base UI under "Docking Results".
2. After docking, suggest next steps: Docking Analysis (interactions), MD Simulation (stability), or AI Interpretation.
3. Use exhaustiveness=64 for publication quality (default 8 is too low).
4. For batch docking (multiple ligands), call multiple times or use the docking_analysis module.

**Pipeline context:** Docking → Docking Analysis → Knowledge Base → Academic Writer
