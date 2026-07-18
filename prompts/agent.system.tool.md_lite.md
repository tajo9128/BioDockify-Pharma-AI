## MD Lite Tool (Molecular Dynamics)

**Purpose:** Run OpenMM molecular dynamics simulations to verify ligand-protein complex stability over time. Returns RMSD, RMSF, energy plots, and trajectory analysis. Results auto-store to the Knowledge Base.

**When to use:**
- User has a docked pose and wants to verify stability
- User asks for MD simulation, trajectory analysis, or dynamics
- User wants RMSD/RMSF plots for a publication
- After docking, to confirm binding stability

**How to use:** MD simulations are LONG-RUNNING (hours). Use the job system.

```python
import sys; sys.path.insert(0, "/a0")
import asyncio
from api.md_lite import MDLite

async def run_md():
    h = MDLite()
    # Start simulation
    result = await h.process({
        "action": "start",
        "complex_pdb": "/path/to/docked_complex.pdb",
        "duration_ns": 10,            # simulation length
        "forcefield": "AMBER",        # AMBER | CHARMM
    }, None)
    job_id = result.get("job_id")
    print("Started MD job:", job_id)
    # Poll status periodically
    status = await h.process({"action": "status", "job_id": job_id}, None)
    print("Progress:", status.get("progress_pct"), "%")

asyncio.run(run_md())
```

**Actions:**
- `start` — launch an MD simulation job
- `status` — check job progress
- `results` — retrieve RMSD/RMSF/energy when complete (auto-stores to KB)
- `list` — list all MD jobs

**Critical rules:**
1. MD jobs run for hours. Always return the job_id to the user immediately.
2. When status returns "completed", results auto-store to KB — they appear in the Knowledge Base.
3. After completion, suggest next steps: AI interpretation of RMSD/RMSF, or thesis write-up.
4. Typical setup: 10 ns production run, AMBER forcefield, explicit water.

**Pipeline context:** Docking → **MD Lite** → Knowledge Base → Academic Writer
