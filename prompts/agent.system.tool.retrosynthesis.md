## Retrosynthesis Planning Tool

**Purpose:** Plan synthesis routes for a target molecule — iterative retrosynthetic disconnection using BRICS bond analysis + curated reaction templates, down to commercially available building blocks. Outputs route trees with steps, reagents, and conditions. Use this for MULTI-STEP route planning; for single-step disconnections and named-reaction lookups the Medicinal Chemistry module also has a lighter `retrosynthesis` action.

**When to use:**
- User asks "how do I synthesize this molecule?" or "what's the synthesis route for X?"
- User wants disconnection analysis — where to break the molecule
- User asks about synthetic complexity of a molecule (before committing to synthesis)
- User needs purchasable building blocks for a target
- After Molecule Designer / scaffold hopping generates a novel structure and the user asks if it's makeable
- User wants to see available reaction templates

**How to use:** Call via `code_execution_tool`.

```python
import sys; sys.path.insert(0, "/a0")
import asyncio
from api.retrosynthesis import RetrosynthesisHandler

async def plan():
    h = RetrosynthesisHandler()
    result = await h.process({
        "action": "plan",
        "smiles": "CC(=O)Oc1ccccc1C(=O)O",   # target molecule
        "max_depth": 4,                        # disconnection depth
        "max_routes": 5,                       # number of routes to return
    }, None)
    print(result)  # route tree: steps, precursors, reagents, conditions

asyncio.run(plan())
```

**Actions:**
- `plan` — full route tree from target down to building blocks (`smiles`, `max_depth`, `max_routes`)
- `disconnect` — single-level disconnection analysis (BRICS bonds + template matches)
- `complexity` — synthetic complexity estimate (rings, stereocenters, bridging)
- `building_blocks` — purchasable starting materials for the target
- `templates` — list of available reaction templates with transforms

**Critical rules:**
1. Routes are template-based suggestions — verify feasibility against literature before recommending to a wet lab.
2. Always report route depth and number of steps; fewer steps is generally better.
3. Combine with `complexity` to advise the user whether a target is practically synthesizable.
4. Reagents/conditions come from curated templates — when a template is uncertain, say so.

**Pipeline context:** Molecule Designer → Retrosynthesis (makeability check) → Building Blocks → Wet Lab / Notes
