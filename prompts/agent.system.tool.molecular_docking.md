### molecular_docking
run AutoDock Vina molecular docking to predict protein-ligand binding
args:
- `receptor_pdb` (path to protein PDB file)
- `ligand_smiles` (SMILES string of the ligand)
- `center_x`, `center_y`, `center_z` (grid center coordinates, optional — auto-detected from protein)
- `size_x`, `size_y`, `size_z` (grid size in Angstroms, optional — default 20)
- `exhaustiveness` (search exhaustiveness, optional — default 8)
returns binding energies for each pose (kcal/mol), downloadable PDBQT/SDF files
example:
~~~json
{
  "thoughts": ["I need to dock this ligand to the protein to predict binding."],
  "headline": "Running molecular docking",
  "tool_name": "molecular_docking",
  "tool_args": {
    "receptor_pdb": "workdir/protein.pdb",
    "ligand_smiles": "CC(=O)Oc1ccccc1C(=O)O"
  }
}
~~~
