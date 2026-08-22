## Reaction Lab Tool

**Purpose:** Synthetic chemistry execution — run named forward reactions (12 templates: amide coupling, Suzuki, reductive amination, Buchwald, SNAr...), combinatorial library enumeration, reactant→product atom mapping (MCS), impurity/degradation prediction (ICH Q1A stress rules: hydrolysis, oxidation, photolysis), and reaction condition recommendation. The synthetic-chemistry workbench complement to the Retrosynthesis planner.

**When to use:**
- User asks "what happens if I react X with Y" or wants a forward synthesis executed → `forward`
- User wants a combinatorial library from building blocks → `enumerate`
- User asks which atoms survive a reaction / atom correspondence → `atom_map`
- User asks about degradation products, stress testing, ICH Q1A impurities, stability → `impurities`
- User asks how to run a reaction — reagents, solvents, temperature → `conditions`
- After Molecule Designer generates candidates → check synthetic accessibility + conditions
- After Retrosynthesis proposes a route → execute each step forward to validate it

**How to use:** Call via `code_execution_tool`.

```python
import sys; sys.path.insert(0, "/a0")
import asyncio
from api.reaction_lab import ReactionLabHandler

async def main():
    h = ReactionLabHandler()
    r = await h.process({
        "action": "forward",
        "reaction": "Amide Coupling",
        "reactants": ["CC(=O)O", "CCN"],
    }, None)
    print(r["products"][0]["smiles"])  # CCNC(C)=O
    imp = await h.process({"action": "impurities", "smiles": "CC(=O)Oc1ccccc1C(=O)O"}, None)
    print(imp["risk_level"], [f["impurity"] for f in imp["findings"]])

asyncio.run(main())
```

**Actions:**
- `reactions` — list the 12 named reaction templates (reagents + conditions included)
- `forward` — run a named reaction or custom `reaction_smarts` on `reactants` (SMILES list); returns products + reagents + conditions
- `enumerate` — combinatorial products from `building_block_sets` (one SMILES list per slot)
- `atom_map` — MCS-based conserved-atom correspondence reactants→product
- `impurities` — ICH Q1A stress-degradation risks with predicted degradant structures; optional `conditions` filter (e.g. ["oxidative", "acid"])
- `conditions` — recommended reagent systems for the detected functional groups

**Critical rules:**
1. Products are template/SMARTS outputs — verify valence/sanity and recommend literature confirmation.
2. Impurity prediction is screening-level; real impurity profiling needs forced-degradation experiments (HPLC/LC-MS).
3. Impurity SMARTS transforms need explicit hydrogens internally — already handled; do not re-implement.
4. Chain with Retrosynthesis: plan (retro) → validate steps forward (this tool) → conditions → Wet Lab module.

**Pipeline context:** Molecule Designer → Retrosynthesis → Reaction Lab (forward validation) → Wet Lab; Drug candidate → Reaction Lab (impurities) → Stability/Regulatory
