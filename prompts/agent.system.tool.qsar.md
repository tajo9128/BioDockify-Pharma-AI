### qsar
QSAR modeling: train ML models on molecular descriptors, predict bioactivity, batch screening
args:
- `action` (one of: train, predict, batch_predict, strategies)
- `smiles` (SMILES string for single prediction)
- `smiles_list` (newline-separated SMILES for batch prediction)
- `endpoint` (property to predict, e.g. "activity", "toxicity")
- `model_type` (optional: rf, gbr, svr, pls, ridge, lasso)
returns trained model metrics (R², RMSE, MAE), predictions, applicability domain
example:
~~~json
{
  "thoughts": ["I need to predict bioactivity for these compounds."],
  "headline": "Running QSAR prediction",
  "tool_name": "qsar",
  "tool_args": {
    "action": "predict",
    "smiles": "CC(=O)Oc1ccccc1C(=O)O"
  }
}
~~~
