# Chapter 3: Molecule Editor

## 3.1 Overview

The Molecule Editor is BioDockify's molecular workbench — a 4-tab module for drawing, viewing, profiling, filtering, and optimizing molecules. It integrates JSME (2D drawing), 3Dmol.js (3D visualization), RDKit (chemistry), and PubChem (database lookup).

### Access Path
**All Tools → Molecule Editor** (or click the ✏️ icon in the toolbar)

### What It Does

| Tab | Function |
|-----|----------|
| **3D View** | Render molecules in 3D with 7 styles, measure distances, view PDB proteins |
| **Properties** | Calculate MW, LogP, TPSA, hERG, AMES, pKa, BBB, melting point, druglikeness |
| **Filters** | Check PAINS, Brenk, NIH structural alerts for assay interference |
| **Optimize** | Generate bioisosteric replacements for lead optimization |

---

## 3.2 Tab 1: 3D View

### Drawing Molecules

1. **JSME Canvas**: Draw molecules using the interactive 2D editor
   - Click atoms (C, N, O, S, P, F, Cl, Br) from the toolbar
   - Click bonds (single, double, triple, aromatic) to modify
   - Use ring templates (3-8 membered, aromatic)
   - Undo/Redo with Ctrl+Z / Ctrl+Y

2. **SMILES Input**: Type or paste a SMILES string
   - Bidirectional sync: drawing updates SMILES, SMILES updates drawing
   - Press Enter to validate

3. **PubChem Search**: Enter a drug name (e.g., "aspirin", "caffeine")
   - Searches PubChem database
   - Loads structure automatically

4. **Quick Load**: Click preset drug buttons (Aspirin, Caffeine, Ibuprofen, etc.)

### 3D Rendering Styles

| Style | Description |
|-------|-------------|
| **Stick** | Thin cylinders for bonds |
| **Ball+Stick** | Spheres at atoms + sticks for bonds |
| **CPK** | Space-filling spheres (van der Waals radii) |
| **Sphere** | Large opaque spheres |
| **Chain** | Cartoon backbone (proteins only) |
| **Surface** | Transparent molecular surface |
| **Charge** | Electrostatic coloring |

### Protein PDB Viewer

Upload a PDB file to view protein structures:
- **Chain coloring**: Different colors per chain
- **Distance measurement**: Click "Measure" → click 2 atoms → yellow cylinder + Å label
- **Residue sequence**: Clickable residue list — click to zoom to residue
- **Background toggle**: Dark (#1a1a2e) / Light (#ffffff)
- **Snapshot**: PNG download of current view

### Controls

| Button | Action |
|--------|--------|
| **Stick/Ball+Stick/CPK/Sphere/Chain/Surface/Charge** | Change rendering style |
| **Measure** | Toggle distance measurement mode |
| **BG** | Toggle dark/light background |
| **Snap** | Download PNG snapshot |
| **Clear Canvas** | Reset drawing and 3D view |

---

## 3.3 Tab 2: Properties

Displays comprehensive drug properties calculated by RDKit:

### Core Properties

| Property | Description | Typical Range |
|----------|-------------|---------------|
| **Formula** | Molecular formula | e.g., C₉H₈O₄ |
| **MW** | Molecular weight (Da) | 150-500 for drugs |
| **LogP** | Lipophilicity (octanol/water) | -2 to 5 for drugs |
| **TPSA** | Topological polar surface area (Å²) | 20-140 for oral drugs |
| **HBD** | H-bond donors | ≤5 (Lipinski) |
| **HBA** | H-bond acceptors | ≤10 (Lipinski) |
| **Rot Bonds** | Rotatable bonds | ≤10 (Veber) |
| **Melting Point** | Joback group contribution (°C) | Varies |

### Drug-Likeness Score (0-1)

Composite score combining 6 filters + fragment penalties:

| Score | Label |
|-------|-------|
| ≥0.9 | Excellent |
| ≥0.7 | Good |
| ≥0.5 | Moderate |
| <0.5 | Poor |

### Toxicity Alerts

| Alert | What It Checks | Alerts |
|-------|---------------|--------|
| **hERG** | Cardiotoxicity (QT prolongation) | 10 SMARTS patterns |
| **AMES** | Mutagenicity | 15 Kazius-Hansen patterns |

Risk levels: Low risk ✅ / Moderate risk ⚠️ / High risk ❌

### Pharmacokinetics

| Property | Method | Description |
|----------|--------|-------------|
| **BBB Score** | Clark's model (0-1) | Blood-brain barrier permeability |
| **pKa Acidic** | Substructure matching | Strongest acidic group |
| **pKa Basic** | Substructure matching | Strongest basic group |

---

## 3.4 Tab 3: Filters

Checks molecules against structural alert databases used in drug safety:

### PAINS (Pan-Assay Interference Compounds)

8 filters that detect molecules likely to give false positives in high-throughput screens:
- Michael acceptors
- Redox cyclers
- Fluorescent compounds
- Metal chelators
- Aggregators

### Brenk (Medicinal Chemistry Filters)

10 filters for undesirable functional groups:
- Alkyl halides
- Azides
- Boronic acids
- Epoxides
- Peroxides
- Phosphor-amidates
- Sulfonyl halides
- Thiols
- Triflates
- Diazo compounds

### NIH (NIH Molecular Libraries)

8 filters for problematic substructures:
- Acylhydrazides
- Alkyl nitrites
- Amino-oxy compounds
- Boronic acids
- Diazo compounds
- Enones
- Hydroxamic acids
- Quinones

### Results Display

Each filter shows:
- **PASS** (green) — no alerts found
- **FAIL** (red) — alerts triggered, with details

---

## 3.5 Tab 4: Optimize

Generates bioisosteric replacements for lead optimization:

### How It Works

1. Enter a SMILES string
2. Select a strategy from the dropdown:
   - Carboxyl → Tetrazole
   - Amide → Sulfonamide
   - Phenyl → Pyridine
   - Ether → Thioether
   - And more...
3. Click **Generate Mutants**
4. View generated analogues with their properties

### Mutant Actions

Each generated mutant has two buttons:
- **Load in Editor** — replaces current molecule in the editor
- **Send to Docking** — transfers SMILES to Molecular Toolkit for docking

---

## 3.6 Export Options

| Format | Description |
|--------|-------------|
| **PNG** | 2D structure image (600×400) |
| **SVG** | Scalable vector graphics |
| **MOL** | MDL MOL file (2D coordinates) |
| **SDF** | Structure Data File (3D coordinates) |

---

## 3.7 Example Workflow: Profiling Aspirin

1. Open Molecule Editor
2. Type `CC(=O)Oc1ccccc1C(=O)O` in SMILES field
3. **3D View**: See 3D structure rendered
4. **Properties**: MW=180.16, LogP=1.2, TPSA=63.6, hERG=Low risk, AMES=Non-mutagenic
5. **Filters**: PAINS=PASS, Brenk=PASS, NIH=PASS
6. **Optimize**: Generate bioisosteric replacements (e.g., tetrazole for carboxyl)
7. **Export**: Download as PNG for publication
