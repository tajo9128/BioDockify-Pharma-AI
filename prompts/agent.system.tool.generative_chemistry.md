## Molecule Designer Tool (Generative Chemistry)

**Purpose:** De novo molecule generation and lead optimization — 3 pure-RDKit methods (no ML training): BRICS fragment recombination, genetic algorithm (mutate SMILES → score → evolve), scaffold enumeration. Multi-objective scoring: QED drug-likeness, SA synthetic accessibility, Lipinski compliance, ADMET quick screen, diversity (Tanimoto), novelty vs seeds. Also Murcko scaffold analysis, scaffold hopping, R-group analysis, and docking-result ranking. Results auto-store to the Knowledge Base (category=drug_design).

**When to use:**
- User wants novel molecules "like this one" / idea generation from seed actives
- User wants to optimize a lead toward property targets (MW, LogP, TPSA windows)
- User asks for scaffold hopping — same activity, different core
- User wants Murcko scaffolds, R-group analysis, or fragment libraries from a set
- User has docking results and wants them re-ranked by drug-likeness (rank_docking)
- After Target ID / Bioactivity prediction → generate candidates → score → Retrosynthesis check

**How to use:** Call via `code_execution_tool`.

```python
import sys; sys.path.insert(0, "/a0")
import asyncio
from api.generative_chemistry import GenerativeChemistryHandler

async def generate():
    h = GenerativeChemistryHandler()
    r = await h.process({
        "action": "generate",
        "smiles": ["CC(=O)Oc1ccccc1C(=O)O"],   # seed molecule(s)
        "method": "brics",                       # brics | genetic | scaffold
        "n_candidates": 50,
        "constraints": {"max_mw": 500, "max_logp": 5},
    }, None)
    print(r)  # ranked candidates with QED/SA/Lipinski/diversity scores

asyncio.run(generate())
```

**Actions:**
- `generate` — novel molecules from seeds (`smiles[]`, `method` brics/genetic/scaffold, `n_candidates`, `constraints` dict)
- `optimize` — genetic optimization of one seed toward property targets
- `score` — score one molecule (`smiles` string): QED, SA, Lipinski, ADMET quick screen
- `scaffold_hop` — bioisosteric ring replacements keeping peripheral groups
- `scaffolds` — Murcko scaffold extraction + frequency from a library
- `r_groups` — R-group decomposition and classification
- `fragments` — fragment library building from seeds (BRICS)
- `rank_docking` — re-rank docking poses/ligands with drug-likeness consensus score

**Critical rules:**
1. Generated molecules are suggestions — always check with `score` and verify makeability via Retrosynthesis before recommending synthesis.
2. Results auto-store to KB (category=drug_design) — mention this to the user.
3. Combine methods: generate → score → scaffold_hop on the best → rank_docking after docking.

**Pipeline context:** Target ID → Bioactivity Predictor → Molecule Designer → score → Retrosynthesis (makeability) → Docking → MD Lite
