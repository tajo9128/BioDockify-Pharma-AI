### qsar
QSAR modeling: train ML models, predict bioactivity
args: `action` (train, predict, batch_predict, strategies), `smiles`
optional: `smiles_list`, `endpoint`, `model_type`
example:
~~~json
{
  "thoughts": ["I need to predict bioactivity."],
  "headline": "Running QSAR prediction",
  "tool_name": "qsar",
  "tool_args": {
    "action": "predict",
    "smiles": "CC(=O)Oc1ccccc1C(=O)O"
  }
}
~~~
