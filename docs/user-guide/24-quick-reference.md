# Chapter 24: Keyboard Shortcuts & Quick Reference

## 24.1 Global Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Send message in chat |
| `Shift+Enter` | New line in input |
| `Escape` | Close modal/popup |
| `F5` | Refresh module state |

---

## 24.2 Module Navigation

| Action | Method |
|--------|--------|
| Open module | Click icon in sidebar |
| Switch tabs | Click tab button |
| Minimize window | Click − button |
| Maximize window | Click □ button |
| Close window | Click × button |

---

## 24.3 SMILES Quick Reference

| Pattern | Meaning |
|---------|---------|
| `C` | Methyl group |
| `c` | Aromatic carbon |
| `O` | Hydroxyl |
| `N` | Amine |
| `S` | Thiol/sulfide |
| `F,Cl,Br,I` | Halogens |
| `( )` | Branch |
| `=, #` | Double, triple bond |
| `@` | Stereochemistry |

### Common Drug SMILES

| Drug | SMILES |
|------|--------|
| Aspirin | `CC(=O)Oc1ccccc1C(=O)O` |
| Ibuprofen | `CC(C)Cc1ccc(cc1)C(C)C(=O)O` |
| Caffeine | `Cn1cnc2c1c(=O)n(c(=O)n2C)C` |
| Paracetamol | `CC(=O)Nc1ccc(O)cc1` |
| Warfarin | `CC(=O)OC(Cc1c(O)c2ccccc2oc1=O)C(c1ccccc1)=O` |

---

## 24.4 Common PDB Codes

| Protein | PDB | Disease |
|---------|-----|---------|
| COX-2 | 3LN1 | Inflammation |
| EGFR | 1M17 | Cancer |
| ABL Kinase | 1IEP | CML |
| HIV Protease | 1HPV | HIV |
| SARS-CoV-2 Mpro | 6LU7 | COVID-19 |
| Acetylcholinesterase | 4EY7 | Alzheimer's |

---

## 24.5 Format Conversion Reference

| From | To | Method |
|------|-----|--------|
| SMILES → PDBQT | Via RDKit + Meeko | Auto in docking |
| PDB → PDBQT | Via OpenBabel/Meeko | Auto in docking |
| SDF → SMILES | Via RDKit | Manual or API |
| SMILES → SVG | Via RDKit Draw | Export button |
| PDB → SDF | Via RDKit | 3D conformer generation |

---

## 24.6 API Endpoint Quick Reference

| Endpoint | Key Actions |
|----------|-------------|
| `/api/drug_properties` | `analyze` |
| `/api/drug_analysis` | `check` |
| `/api/structure_3d` | Generate SDF |
| `/api/qsar` | `train`, `predict`, `predict_batch` |
| `/api/pharmacophore` | `generate`, `screen`, `batch_screen` |
| `/api/journal_finder` | `verify`, `search`, `suggest` |
| `/api/docking_prepare` | Prepare PDBQT |
| `/api/docking_run` | Run Vina + GNINA |
| `/api/docking_analysis` | `deep_analysis`, `plif` |
