# Chapter 16: Computational Methods Reference

## 16.1 Docking Scoring Functions

### AutoDock Vina Score
Empirical scoring with weighted terms:
- Gauss (steric repulsion)
- Repulsion (close contacts)
- Hydrophobic (non-polar contacts)
- Hydrogen bonding
- Torsional penalty

### GNINA CNN Score
Deep-learning rescoring:
- CNN processes protein-ligand complex
- Outputs binding affinity prediction (0-1)
- Trained on PDBbind dataset

### Consensus Z-Score
```
Z_final = 0.6 × Z_vina + 0.4 × Z_gnina
```
Normalized across all poses in a docking run.

---

## 16.2 QSAR Descriptors

### RDKit Descriptor Groups

| Group | Count | Examples |
|-------|-------|---------|
| Physicochemical | 16 | MolWt, LogP, TPSA, HBA, HBD |
| Topological | 11 | BalabanJ, BertzCT, Chi0-4, Kappa1-3 |
| Electronic | 4 | MaxEStateIndex, MinEStateIndex |
| Fragment | 21 | fr_Al_COO, fr_Ar_N, fr_amide, fr_halogen |

### ECFP4 Fingerprints
Extended-Connectivity Fingerprints (radius 4):
- 2048-bit binary vectors
- Captures local atomic environments
- Used for similarity and read-across

---

## 16.3 Pharmacophore Feature Types

| NCI Type | Description | Weight |
|----------|-------------|--------|
| Hydrophobic | Non-polar contacts | 1 |
| PiStacking_P | Parallel pi-stacking | 4 |
| PiStacking_T | T-shaped pi-stacking | 4 |
| PiCation_lring | Protein cation + ligand aromatic | 8 |
| PiCation_pring | Protein aromatic + ligand cation | 8 |
| SaltBridge_pneg | Protein anion + ligand cation | 8 |
| SaltBridge_lneg | Protein cation + ligand anion | 8 |
| XBond | Halogen bond | 4 |
| HBond_pdon | Protein donor + ligand acceptor | 4 |
| HBond_ldon | Protein acceptor + ligand donor | 4 |

---

## 16.4 Drug Properties v2 Algorithms

### hERG Cardiotoxicity
10 SMARTS structural alerts:
- Tertiary amine pharmacophore
- Aromatic ring + halogen
- Sulfonamide
- Alkoxy benzene
- Fluoro alkane
- Tetrazole
- Nitrile
- Imidazole basic
- Piperazine
- Diphenylmethane

### AMES Mutagenicity
15 Kazius-Hansen SMARTS patterns:
- Nitro group
- Nitroso
- Aromatic amine
- Epoxide
- Alkyl halide
- Aziridine
- N-nitroso
- Hydrazine
- Polycyclic aromatic
- Acyl halide
- Sulfonate ester
- Quinone
- Diazo
- Hydroxylamine
- Mustard

### pKa Prediction
Substructure matching with empirical pKa values:
- **Acidic**: Carboxylic acid (4.2), Sulfonic acid (-2.0), Phenol (9.9), Tetrazole (4.9)
- **Basic**: Aliphatic amine (10.5), Aniline (4.6), Pyridine (5.2), Imidazole (7.0), Guanidine (13.0)

### BBB Permeability (Clark's Model)
Score components:
- LogP contribution (0.3 if 1-4)
- TPSA contribution (0.3 if <60)
- MW contribution (0.2 if <400)
- HBD penalty (-0.1 if >1)
- HBA penalty (-0.05 if >6)
- Rot bond penalty (-0.05 if >5)
- Nitrogen count penalty (-0.2 if >3)

### Melting Point (Joback Method)
Group contribution method:
- Base: 122.5°C
- Ring: +5.0 per ring
- Methyl: -5.10 per CH3
- Hydroxyl: +44.45 per OH
- Carbonyl: +61.20 per C=O
- Carboxyl: +155.50 per COOH
- Amino primary: +66.85 per NH2
- Rotatable bond penalty: +2.0 per rot bond

### Drug-Likeness Score
Composite score (0-1):
```
Score = 1.0
- 0.15 if MW outside 200-650
- 0.12 if LogP outside -2 to 6
- 0.10 if HBD > 6
- 0.10 if HBA > 12
- 0.08 if TPSA > 160
- 0.08 if RotBonds > 12
- 0.08 if aromatic atoms > 18
- 0.05 if halogen atoms > 4
```

---

## 16.5 Interaction Analysis

### Interaction Detection Thresholds

| Interaction | Distance Cutoff | Geometry |
|-------------|----------------|----------|
| H-bond | 3.5 Å | D-H···A angle > 120° |
| Hydrophobic | 4.0 Å | C-C or C-S contacts |
| Salt bridge | 4.5 Å | Positive-negative charge |
| Pi-stacking | 5.5 Å | Ring centroid distance |
| Binding site | 5.0 Å | Any protein atom near ligand |

### PLIF Bitmask Encoding
```
Bit 0 (1):  H-bond donor
Bit 1 (2):  H-bond acceptor
Bit 2 (4):  Hydrophobic
Bit 3 (8):  Aromatic (pi-stacking)
Bit 4 (16): Ionic (salt bridge)
Bit 5 (32): Halogen bond
```

---

## 16.6 Statistical Methods

### Model Validation

| Metric | Formula | Use |
|--------|---------|-----|
| R² | 1 - SS_res/SS_tot | Regression fit |
| Q² | 1 - PRESS/SS_tot | Cross-validation |
| RMSE | √(Σ(y-ŷ)²/n) | Error magnitude |
| MCC | (TP·TN-FP·FN)/√((TP+FP)(TP+FN)(TN+FP)(TN+FN)) | Binary classification |
| AUC | Area under ROC curve | Diagnostic performance |

### Applicability Domain
Leverage method:
```
h_i = x_i^T (X^T X)^{-1} x_i
h* = 3p/n
```
Where p = number of descriptors, n = number of training compounds.
