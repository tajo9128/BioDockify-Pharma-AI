# Appendix D: Data Formats

## Molecular Formats

| Format | Extension | Description | Use In BioDockify |
|--------|----------|-------------|-------------------|
| **SMILES** | .smi | Text-based molecular notation | All modules |
| **PDB** | .pdb | Protein Data Bank coordinate file | Docking, Molecule Editor |
| **PDBQT** | .pdbqt | AutoDock format (PDB + charges + types) | Docking |
| **SDF** | .sdf | Structure Data File (3D coordinates) | Docking results, export |
| **MOL** | .mol | MDL MOL file (single molecule) | Molecule Editor |
| **MOL2** | .mol2 | Tripos MOL2 format | Pharmacophore |
| **CSV** | .csv | Comma-separated values | QSAR datasets |

## CSV Format for QSAR

Required columns:
```csv
smiles,activity
CC(=O)Oc1ccccc1C(=O)O,1
CC(C)Cc1ccc(cc1)C(C)C(=O)O,0
Cn1cnc2c1c(=O)n(c(=O)n2C)C,1
```

- **smiles**: Valid SMILES string
- **activity**: Numeric value (regression) or 0/1 (classification)

## Pharmacophore .pm Format

```
# Pharmacophore Model
# num_features=6
Hydrophobic 1.5 2.3 0.8 0.5 Hydrophobic
Aromatic 3.2 1.1 -0.5 0.4 PiStacking_P
HBond_donor 0.8 2.9 1.2 0.3 HBond_pdon
```

Format: `type x y z score nci_type`

## PDB Format

```
ATOM      1  N   ALA A   1       0.000   0.000   0.000  1.00 20.00           N
ATOM      2  CA  ALA A   1       1.458   0.000   0.000  1.00 20.00           C
HETATM  100  C1  LIG A   0       5.000   3.000   2.000  1.00 20.00           C
```

## Download Formats

| Button | Format | Content |
|--------|--------|---------|
| PDBQT | chemical/x-pdbqt | All docked poses |
| SDF | chemical/x-sdf | 3D structures |
| Best Pose (3D) | chemical/x-pdb | Single best pose |
| Log | text/plain | Vina docking log |
| PNG | image/png | 2D structure image |
| SVG | image/svg+xml | Scalable vector |
