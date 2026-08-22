## EnviroTox Tool (Environmental Fate & Ecotoxicity)

**Purpose:** Screening-level environmental risk assessment — bioconcentration (BCF, Meylan 1999), soil adsorption (Koc, Karickhoff 1981), fish 96h LC50 (Könemann 1981 baseline narcosis + reactivity flags), ready-biodegradability (BIOWIN-like heuristics), and PBT/vPvB screening per REACH Annex XIII. Covers agrochemical/environmental research gaps — green-chemistry flags for halogens, metals, hydrophobicity.

**When to use:**
- User asks about environmental impact / fate of a compound → `assess`
- User asks about bioaccumulation, BCF, persistence, biodegradability → `assess`
- User asks about ecotoxicity — fish toxicity, LC50, daphnia → `assess` (fish)
- User screens a compound library / agrochemical candidates for environmental safety → `batch`
- User mentions REACH, PBT, vPvB, green chemistry, regulatory environmental assessment
- Complements ADMET (human) — this is the environmental side

**How to use:** Call via `code_execution_tool`.

```python
import sys; sys.path.insert(0, "/a0")
import asyncio
from api.envirotox import EnviroToxHandler

async def main():
    h = EnviroToxHandler()
    r = await h.process({"action": "assess", "smiles": "Clc1ccc(C(c2ccc(Cl)cc2)Cl)cc1"}, None)  # DDT
    print(r["overall_concern"], r["pbt_screen"]["classification"], r["bioconcentration"]["bcf_l_kg"])

asyncio.run(main())
```

**Actions:**
- `assess` — full panel for one SMILES: descriptors, BCF (B/vB flags), Koc + mobility, fish LC50 (T flag) with mode-of-action, biodegradability verdict + reasons, PBT/vPvB screen, green-chemistry flags, overall concern (low/moderate/high)
- `batch` — condensed screen for a SMILES list, sorted high-concern first

**Critical rules:**
1. These are SCREENING-LEVEL descriptor QSAR estimates — always say so; NOT a substitute for OECD 301/305/203 studies or regulatory submissions.
2. Models assume non-ionics; ionized species (salts, zwitterions) are approximate.
3. Overall concern drives triage: high → deprioritize or redesign (fewer halogens, lower logP); link to Molecule Designer for greener analogs.
4. Excellent for teaching environmental chemistry and prioritizing before expensive studies.

**Pipeline context:** Drug/Agro candidate → EnviroTox (screen) → redesign (Molecule Designer) → re-screen; Regulatory → PBT flags → eCTD context
