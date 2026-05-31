### mol_optimizer
molecular optimization: bioisostere mutagenesis
args: `action` (strategies, mutate), `smiles`
optional: `strategy`
example:
~~~json
{
  "thoughts": ["I need to optimize this compound."],
  "headline": "Generating mutants",
  "tool_name": "mol_optimizer",
  "tool_args": {
    "action": "mutate",
    "smiles": "CC(=O)Oc1ccccc1C(=O)O"
  }
}
~~~
