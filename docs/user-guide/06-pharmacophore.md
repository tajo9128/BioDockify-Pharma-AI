# Chapter 6: Pharmacophore Modeling

## 6.1 Overview
Pharmacophore modeling identifies the spatial arrangement of chemical features responsible for biological activity. BioDockify's pharmacophore module provides 13 actions covering the complete pharmacophore workflow.

### Access Path
**All Tools → Pharmacophore** (or click 🎯 icon)

### Tabs: Ligand · Protein · Screen · Batch · Models · Target · Hypothesis · Import · NCI

---

## 6.2 Ligand-Based Pharmacophore
Enter SMILES → **Generate** → view features:
- **Donor** (blue) — H-bond donors
- **Acceptor** (red) — H-bond acceptors
- **Hydrophobic** (gold) — hydrophobic regions
- **Aromatic** (purple) — aromatic rings
- **Cation** (green) — positive ionizable
- **Anion** (orange) — negative ionizable
- **Halogen** (cyan) — halogen bond donors

---

## 6.3 Protein-Based Pharmacophore
Paste PDB content → **Model** → extracts features from binding site residues:
- Maps residues to pharmacophore types (ALA→Hydrophobic, PHE→Aromatic, etc.)
- Backbone N→Donor, O→Acceptor
- Configurable center + cutoff distance
- Export as .pm file

---

## 6.4 Virtual Screening
**Query SMILES** + **Library SMILES** (one per line) → weighted screening:
- PharmacoNet weights: Cation/Anion=8, Aromatic/Halogen/HBA/HBD=4, Hydrophobic=1
- Jaccard-like weighted intersection/union scoring
- Hits sorted by score

---

## 6.5 ZINCPharmer Batch Screen
Pre-filter library before pharmacophore matching:
| Filter | Description |
|--------|-------------|
| MW min/max | Molecular weight range |
| LogP min/max | Lipophilicity range |
| Rot max | Maximum rotatable bonds |
| TPSA max | Polar surface area limit |
| HBA/HBD max | H-bond acceptors/donors |

Results: pre-filtered count + hits + hit rate

---

## 6.6 Shared & Merged Models
- **Shared (∩)**: Features present in ALL input molecules
- **Merged (∪)**: Features from ANY input molecule (deduplicated by 1.5Å clustering)
- Coverage statistics per feature type

---

## 6.7 Target Identification
PharmMapper-style multi-conformer profiling:
1. Generate N conformers (default 10)
2. Extract features per conformer
3. Compute consensus feature profile
4. Rank conformers by richness + consensus score

---

## 6.8 Example: CDK2 Inhibitor Discovery
1. Generate pharmacophore from 15 known CDK2 inhibitors → 6 shared features
2. Screen ZINC database with batch pre-filter (MW<500, LogP<5, RotBonds<10)
3. View hits with weighted scores
4. Load top hit into Molecule Editor for 3D viewing
