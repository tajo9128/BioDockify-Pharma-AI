### pharmacophore
pharmacophore feature detection and screening
args: `action` (protein_model, screen, batch_screen, shared_model, merged_model, overlay, hypothesis, identify_targets, parse_ph4, pdb_query, nci_types)
optional: `smiles`, `protein_pdb`, `query_smiles`, `library_smiles`, `smiles_list`
example:
~~~json
{
  "thoughts": ["I need to identify pharmacophore features."],
  "headline": "Analyzing pharmacophore",
  "tool_name": "pharmacophore",
  "tool_args": {
    "action": "protein_model",
    "protein_pdb": "workdir/protein.pdb"
  }
}
~~~
