### mol_optimizer
molecular optimization: bioisostere mutagenesis for lead optimization
args:
- `action` (one of: strategies, mutate)
- `smiles` (SMILES string of the molecule to optimize)
- `strategy` (optional: optimization strategy ID)
returns mutant SMILES with improved properties (MW, LogP, HBD, HBA)
example:
~~~json
{
  "thoughts": ["I need to optimize this lead compound."],
  "headline": "Generating molecular mutants",
  "tool_name": "mol_optimizer",
  "tool_args": {
    "action": "mutate",
    "smiles": "CC(=O)Oc1ccccc1C(=O)O"
  }
}
~~~
