## Pharmacophore Tool

**Purpose:** Pharmacophore modeling, screening, and analysis with OpenPharmaco + Pharmer capabilities.

**When to use:**
- User wants to generate pharmacophore features from molecules
- User wants to extract pharmacophore from protein binding sites
- User wants to screen compound libraries against pharmacophore queries
- User wants to generate pharmacophore hypotheses from active compounds
- User wants to calculate pharmacophore fingerprints
- User wants to compare molecular shapes
- User asks about pharmacophore modeling, NCI types, or feature detection

**Actions:**
- `generate` — Generate ligand-based pharmacophore from SMILES
- `protein_model` — Extract pharmacophore features from protein binding site
- `screen` — Screen compound library against pharmacophore query
- `hypothesis` — Generate pharmacophore hypothesis from multiple active molecules
- `nci_types` — Return NCI type reference data
- `enhanced_detect` — Detect pharmacophore features with functional-group SMARTS (OpenPharmaco)
- `enhanced_interactions` — Extract protein-ligand interaction pharmacophore (Pharmer-style)
- `enhanced_screen` — Screen compound library with multi-conformer matching (Pharmer-style)
- `enhanced_model` — Build consensus pharmacophore model (OpenPharmaco + Pharmer)
- `enhanced_fingerprint` — Generate pharmacophore fingerprint (Pharmer-style 256-bit)
- `enhanced_shape` — Calculate shape similarity between two molecules
- `enhanced_protein_features` — Extract per-residue protein features (OpenPharmaco-style)

**Parameters:**
- `smiles` (required for generate/enhanced_detect/enhanced_fingerprint): SMILES string
- `protein_pdb` (required for protein_model/enhanced_interactions/enhanced_protein_features): PDB content
- `query_smiles` (required for screen/enhanced_screen/enhanced_shape): Query SMILES
- `library_smiles` (required for screen/enhanced_screen): List of SMILES for screening
- `active_smiles` (required for hypothesis/enhanced_model): List of active SMILES
- `ligand_smiles` (required for enhanced_interactions): Ligand SMILES
- `target_smiles` (required for enhanced_shape): Target SMILES
- `cutoff` (optional): Distance cutoff, default 5.0-8.0 Å
- `min_coverage` (optional): Minimum feature coverage, default 0.6
- `num_conformers` (optional): Number of conformers for screening, default 3
- `threshold` (optional): Similarity threshold, default 0.5
- `excluded_volume` (optional): Add excluded volumes to model, default false

**Example usage:**
```
Tool: pharmacophore
Action: generate
smiles: "CC(=O)OC1=CC=CC=C1C(=O)O"
```

**Engine capabilities:**
- 7 pharmacophore feature types: Hydrophobic, Aromatic, HBond_donor, HBond_acceptor, Cation, Anion, Halogen
- Functional-group SMARTS detection (guanidinium, carboxylate, phosphate, sulfonate)
- Feature clustering (merge multi-atom groups into single pharmacophore points)
- Priority-ordered matching (charged/aromatic first)
- Multi-conformer screening with triangle-based matching (Pharmer)
- Excluded volumes with post-alignment checking
- Radius-weighted RMSD scoring
- Interaction pharmacophores (protein-ligand proximity-based)
- Pharmacophore fingerprint (256-bit with chirality)
- Shape similarity calculation
- Consensus model building from multiple actives with excluded volumes
- NCI type mapping (10 PLIP interactions → 7 pharmacophore types)
- Residue → pharmacophore type mapping (20 amino acid types)
