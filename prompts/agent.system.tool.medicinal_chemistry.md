## Medicinal Chemistry Tool

**Purpose:** Synthetic & analytical medicinal chemistry tools — Murcko scaffold extraction, Matched Molecular Pair Analysis (MMPA), Butina clustering + diversity picking, SMARTS substructure search, synthetic accessibility (SA) scoring, single-step retrosynthesis, named reactions database, protecting groups database, toxicophore scan, and stereochemistry analysis. Fills the synthetic-chemistry gap (docking/QSAR/pharmacophore/MD/PAINS are in other modules). Note: `api/synthesize.py` is TTS, NOT chemistry.

**When to use:**
- User wants to identify privileged scaffolds across a compound library (Murcko)
- User asks about Matched Molecular Pair Analysis — what small transformation changes a property
- User needs to cluster a library by similarity or pick a diverse screening subset (Butina + maximin)
- User wants to find a substructure across a library using a SMARTS pattern
- User asks how synthetically accessible a molecule is (SA score 1-10)
- User asks for retrosynthetic analysis — how to make a target molecule
- User references a named reaction (Suzuki, Heck, Diels-Alder, Wittig, Mitsunobu, etc.)
- User asks about protecting groups for amines/alcohols/carboxyls (Boc, Fmoc, TBS, Bn)
- User wants to check a molecule for toxicophores (anilines, nitroaromatics, Michael acceptors)
- User asks about stereochemistry — chiral centers, R/S assignment, E/Z bonds

**Actions:**
- `murcko_scaffold` — Murcko framework extraction + scaffold frequency + privileged scaffold detection
- `mmpa` — Matched Molecular Pair Analysis; group transformations, report Δproperty
- `butina_cluster` — Butina clustering (Tanimoto) + maximin diversity picking
- `smarts_search` — arbitrary SMARTS pattern matching with atom indices + match rate
- `sa_score` — Synthetic Accessibility score (Ertl 2009 descriptor approximation)
- `retrosynthesis` — single-step disconnection via ~10 curated reaction motifs
- `named_reactions` — 30+ named reactions with conditions, substrates, advantages
- `protecting_groups` — 20+ protecting groups with install/remove conditions, stability
- `toxicophore_scan` — 15 toxicity structural alerts (distinct from PAINS/hERG)
- `stereo_analysis` — chiral centers, R/S, E/Z, stereoisomer count, canonical SMILES

**API endpoint:** `POST /api/medicinal_chemistry`
