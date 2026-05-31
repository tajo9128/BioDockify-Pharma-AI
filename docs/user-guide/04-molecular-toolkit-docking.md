# Chapter 4: Molecular Toolkit & Docking

## 4.1 Overview

The Molecular Toolkit is BioDockify's integrated chemistry and docking platform. It combines ADMET prediction, molecular similarity, chemical space visualization, and a full AutoDock Vina + GNINA CNN docking pipeline with inline 3D analysis.

### Access Path
**All Tools → Molecular Toolkit** (or click the 🔬 icon in the toolbar)

### Tabs

| Tab | Function |
|-----|----------|
| **ADMET** | SwissADME-style 6-section results + BOILED-Egg plot + Bioavailability Radar |
| **Similarity** | Tanimoto similarity between two molecules |
| **Chem Space** | PCA visualization of molecular libraries |
| **Docking** | AutoDock Vina + GNINA CNN docking with 3D analysis |
| **Analysis** | Post-docking deep analysis (auto-opened after docking) |

---

## 4.2 ADMET Tab

### SwissADME Analysis

Enter a SMILES string and click **🇨🇭 SwissADME** for comprehensive ADME prediction:

**Section 1: Physicochemical Properties**
- Molecular Weight, Heavy Atoms, Aromatic Heavy Atoms
- Fraction Csp3, Rotatable Bonds, HBA, HBD
- Molar Refractivity, TPSA

**Section 2: Lipophilicity** (5 models)
| Model | Type |
|-------|------|
| iLOGP | Physics-based atom-type |
| XLOGP3 | Crippen-based corrected |
| WLOGP | Wildman-Crippen |
| MLOGP | Moriguchi |
| SILICOS-IT | Fragment-based |
| **Consensus** | Average of 5 models |

**Section 3: Water Solubility** (3 models)
| Model | Output |
|-------|--------|
| ESOL | LogS + Solubility class |
| Ali | LogS + Solubility class |
| SILICOS-IT | LogS + Solubility class |

Classes: Highly soluble → Very soluble → Soluble → Moderately soluble → Poorly soluble → Insoluble

**Section 4: Pharmacokinetics**
- GI Absorption (High/Low)
- BBB Permeant (Yes/No)
- P-gp Substrate (Yes/No)
- Log Kp (skin permeation)
- CYP450 Inhibition: CYP1A2, CYP2C19, CYP2C9, CYP2D6, CYP3A4

**Section 5: Druglikeness** (6 filters)
- Lipinski (Pfizer), Ghose (Amgen), Veber (GSK), Egan (Pharmacia), Muegge (Bayer)
- Bioavailability Score

**Section 6: Medicinal Chemistry**
- Leadlikeness
- Synthetic Accessibility (1=easy, 10=difficult)

**Section 7: BOILED-Egg Plot**
- WLOGP × TPSA scatter plot
- White zone: GI absorption
- Yellow zone: BBB permeation
- Red dots: P-gp+ compounds
- Blue dots: P-gp- compounds

**Section 8: Bioavailability Radar**
- 6-axis spider chart: LIPO, SIZE, POLAR, INSOLU, INSATU, FLEX
- Green zone: optimal oral drug-likeness

---

## 4.3 Molecular Docking

### Step 1: Prepare Input

**Protein (Receptor):**
- Paste PDB content or upload `.pdb`, `.pdbqt`, `.cif`, `.mol2` file
- Supported formats: PDB, PDBQT, CIF, MOL2, ENT
- Auto-detected by file extension

**Ligand:**
- Enter SMILES string or upload `.sdf`, `.mol`, `.pdb`, `.mol2`, `.smi` file
- Auto-converted to PDBQT via Meeko (pure Python) or OpenBabel

### Step 2: Run Docking

Click **Run Docking** — the pipeline executes:

1. **Prepare** — Format detection, protein standardization (remove waters, add hydrogens), PDB→PDBQT conversion, grid box auto-detection
2. **Ligand** — 3D conformer generation with fixed seed (ETKDGv3, seed=42) for reproducible results
3. **Vina** — AutoDock Vina docking with fixed seed (--seed 42) for deterministic search
4. **GNINA** — CNN deep-learning rescoring (when available in Docker)
5. **Consensus** — Z-score normalized combination of Vina + GNINA scores

**Reproducibility**: Same protein + ligand + parameters always produces identical poses (same seed, same standardized protein).

### Step 3: View Results

**Pose Energy Grid:**
- Shows all docked poses ranked by binding energy
- Best pose highlighted with green border
- Energy in kcal/mol (lower = stronger binding)

**Download Options:**
| File | Description |
|------|-------------|
| PDBQT | All docked poses |
| SDF | 3D structure file |
| Best Pose (3D) | Single PDB file of best pose |
| Log | Vina docking log |

**Continue with Docking Analysis** — opens inline analysis tab

---

## 4.4 Docking Analysis (Inline)

After docking completes, the **Analysis** tab provides:

### 3D View
- Receptor rendered as cartoon (spectrum-colored by chain)
- Best ligand pose rendered as stick (green)
- H-bond visualization: yellow dashed cylinders with Å distances
- Molecular surface toggle (VDW, white carbon)
- Style controls: Cartoon / Stick / Sphere for protein
- Snapshot PNG download

### Overview
- Best binding affinity score
- Pose count
- Interaction summary: H-bonds, hydrophobic contacts, salt bridges, pi-stacking
- Cluster count
- Binding site residue badges

### Interactions
- H-bond table with atom pairs and distances
- Hydrophobic contact list
- Salt bridge details
- Pi-stacking pairs

### Residue Energy
- Per-residue energy decomposition bar chart
- Top 20 residues by energy contribution
- Green = favorable, red = unfavorable

### Clusters
- RMSD-based pose clustering
- Cluster ID, size, average energy

### Torsion
- Dihedral angle analysis for best pose

### 2D Diagram
- RDKit-generated interaction diagram
- Shows H-bond, hydrophobic, and pi-stacking interactions
- Falls back to text legend if SVG unavailable

---

## 4.4 Health Badges

The header shows real-time status:

| Badge | Color | Meaning |
|-------|-------|---------|
| **Vina** | 🟢 Green | AutoDock Vina installed |
| **CNN** | 🟢 Green / 🟡 Yellow | GNINA available / Docker required |
| **RDKit** | 🟢 Green | RDKit chemistry library available |

Hover any badge for details.

---

## 4.5 Example: Docking Aspirin Against COX-2

1. Open Molecular Toolkit → Docking tab
2. Paste COX-2 PDB (e.g., PDB: 3LN1) in Protein card
3. Type `CC(=O)Oc1ccccc1C(=O)O` (aspirin) in Ligard card
4. Click **Run Docking**
5. View poses in the grid — best pose highlighted
6. Click **Continue with Docking Analysis**
7. Switch to **3D View** — see aspirin bound in COX-2 active site
8. Check **Interactions** tab — identify key H-bonds with Arg120, Tyr355
9. Download **Best Pose (3D)** for publication figure
