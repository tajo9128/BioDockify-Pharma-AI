### pharmacophore
pharmacophore feature detection, screening, and target identification
args:
- `action` (one of: protein_model, screen, batch_screen, shared_model, merged_model, overlay, hypothesis, identify_targets, parse_ph4, pdb_query, nci_types)
- `smiles` (SMILES string for ligand-based pharmacophore)
- `protein_pdb` (PDB content for protein-based pharmacophore)
- `query_smiles`, `library_smiles` (for screening)
- `smiles_list` (for multi-molecule operations)
returns pharmacophore features, screening hits, target predictions
example:
~~~json
{
  "thoughts": ["I need to identify the pharmacophore features of this compound."],
  "headline": "Analyzing pharmacophore",
  "tool_name": "pharmacophore",
  "tool_args": {
    "action": "protein_model",
    "protein_pdb": "workdir/protein.pdb"
  }
}
~~~
