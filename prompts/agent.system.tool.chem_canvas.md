## ChemCanvas Structure Studio Tool

**Purpose:** Chemical structure drawing and file pipeline — the ChemCanvas-style drawing studio. In-browser editors (Ketcher 3 canvas + JSME quick-draw) with an RDKit engine behind them: validation, conversion, PubChem lookup, depiction, 2D cleanup, structure library (`usr/structures/`), and an optional bridge that launches the ChemCanvas desktop app with a library file. This is where hand-drawn molecules enter the platform.

**When to use:**
- User wants to draw / sketch a molecule (point them to the Structure Draw module window)
- User has a structure name ("aspirin") and needs the structure → `pubchem_lookup`
- User needs format conversion: SMILES ↔ MOL ↔ InChI/InChIKey (`convert`, accepts molblock too)
- User asks to check a structure: valence errors, implicit hydrogens, stereo centers (`validate`)
- User drew a molecule in ChemCanvas desktop and saved it → `files` + `import_file` from the shared `usr/structures/` folder
- User wants a 2D SVG depiction of a molecule for reports/KB (`depict`)
- User wants clean 2D coordinates recomputed (`clean2d`)
- Before docking/ADMET/QSAR when the input is a drawn or imported structure

**How to use:** Call via `code_execution_tool`.

```python
import sys; sys.path.insert(0, "/a0")
import asyncio
from api.chem_canvas import ChemCanvasHandler

async def lookup():
    h = ChemCanvasHandler()
    r = await h.process({"action": "pubchem_lookup", "name": "paracetamol"}, None)
    print(r["smiles"], r["formula"])   # CC(=O)NC1=CC=C(C=C1)O  C8H9NO2
    # then: convert, validate, or export_file to save into usr/structures/

asyncio.run(lookup())
```

**Actions:**
- `status` — ChemCanvas desktop app detection (installed? launcher? in_docker?)
- `launch` — start ChemCanvas desktop (optional `file` from library); GUI host only
- `files` — list structure library `usr/structures/` (mol/sdf/smi/smiles/cdxml/rxn/mrv/ccdx/svg)
- `import_file` — parse a library file → SMILES + molblock + SVG + descriptors
- `export_file` — SMILES → `.mol` (2D coords) or `.smi` saved into the library
- `depict` — RDKit 2D SVG depiction of any SMILES
- `pubchem_lookup` — compound name → canonical SMILES + IUPAC + formula + MW (live PubChem REST)
- `clean2d` — recompute 2D coordinates (coordGen when available) → molblock
- `convert` — SMILES or molblock → canonical SMILES, InChI, InChIKey, formula, MW, molblock
- `validate` — SketChem-style check: valence/sanitization errors, implicit H, stereo centers
- `save_to_kb` — store structure (SMILES + depiction + basics) into the Knowledge Base

**Critical rules:**
1. The library folder `usr/structures/` is the exchange medium with the ChemCanvas desktop app — all file actions stay inside it.
2. `pubchem_lookup` needs internet; everything else is fully offline (RDKit).
3. Ketcher (in-browser) needs no server; the desktop bridge is a convenience, never required.
4. After importing/drawing, hand off naturally: Docking, ADMET, QSAR, Molecule Designer, Bioactivity Predictor, Retrosynthesis.

**Pipeline context:** ChemCanvas Studio → (properties/validate) → Send-To: Docking / ADMET / QSAR / Designer / Bioactivity / Retrosynthesis → KB
