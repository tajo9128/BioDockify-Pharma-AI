### molecular_docking
run AutoDock Vina molecular docking
args: `receptor_pdb` (path), `ligand_smiles` (SMILES string)
optional: `center_x/y/z`, `size_x/y/z`, `exhaustiveness`
example:
~~~json
{
  "thoughts": ["I need to dock this ligand to the protein."],
  "headline": "Running molecular docking",
  "tool_name": "molecular_docking",
  "tool_args": {
    "receptor_pdb": "workdir/protein.pdb",
    "ligand_smiles": "CC(=O)Oc1ccccc1C(=O)O"
  }
}
~~~
