## QSAR3D Tool

**Purpose:** Build and predict using 3D-QSAR and 2D-QSAR models based on Open3DQSAR + Py-CoMFA engine.

**When to use:**
- User wants to build a QSAR model from molecular data
- User wants to predict biological activity of new molecules
- User wants to list or manage QSAR models
- User asks about 3D-QSAR, CoMFA, or molecular interaction fields

**Actions:**
- `build` — Build a QSAR model from SMILES + activity data
- `predict` — Predict activity for new molecules using a trained model
- `models` — List available QSAR models
- `delete` — Delete a QSAR model
- `info` — Get QSAR engine information

**Parameters:**
- `smiles` (required for build/predict): List of SMILES strings
- `activity` (required for build): List of activity values (same length as smiles)
- `model_id` (required for predict/delete): ID of the model to use
- `name` (optional): Name for the model
- `mode` (optional): "3d" (MIF-based) or "2d" (descriptor-based), default "3d"
- `test_fraction` (optional): Fraction of data for testing, default 0.2
- `grid_spacing` (optional): Grid spacing for 3D-QSAR, default 2.0
- `grid_margin` (optional): Grid margin for 3D-QSAR, default 5.0
- `field_types` (optional): List of field types, default ["steric", "electrostatic"]

**Example usage:**
```
Tool: qsar3d
Action: build
smiles: ["CC(=O)OC1=CC=CC=C1C(=O)O", "CC12CCC3C(CCC4CC(=O)CCC34C)C1CCC2O", ...]
activity: [7.2, 8.5, 6.1, ...]
mode: 3d
name: "My QSAR Model"
```

**Engine capabilities:**
- 3D-QSAR: Molecular Interaction Fields (steric + electrostatic)
- 2D-QSAR: 50+ molecular descriptors (replaces PaDEL-Java)
- Structure standardization (OPERA-style curation)
- PLS regression with optimal component search
- Leave-One-Out cross-validation
- Leave-5-Out cross-validation (100 iterations)
- Y-scrambling for chance correlation check
- Applicability domain with confidence scoring
- MCS-based molecular alignment
- Descriptor importance ranking
- 3D contour plot data export
