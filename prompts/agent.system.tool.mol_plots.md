## Interactive Molecular Plots

**Purpose:** Generate interactive Plotly dashboards for molecular properties. Includes property distributions, correlation heatmap, chemical space PCA, drug-likeness analysis, 3D chemical space, parallel coordinates, and scatter matrix.

**When to use:**
- User wants to visualize molecular property distributions
- User needs chemical space visualization (PCA)
- User wants interactive drug-likeness plots
- User needs pairwise property correlation analysis

### Generate All Plots

```python
import sys; sys.path.insert(0, "/a0")
import asyncio
from api.mol_plots import MolPlotsHandler

async def plots():
    h = MolPlotsHandler()
    result = await h.process({
        "action": "generate",
        "smiles_list": [
            "CC(=O)Oc1ccccc1C(=O)O",  # aspirin
            "CC(C)Cc1ccc(cc1)C(C)C(=O)O",  # ibuprofen
            "CC(=O)Nc1ccc(O)cc1",  # paracetamol
            "CC12CCC3C(C1CCC2O)CCC4=CC(=O)CCC34C",  # testosterone
        ],
        "names": ["Aspirin", "Ibuprofen", "Paracetamol", "Testosterone"],
    }, None)
    # Returns plotly HTML strings for each plot type
    print("Distributions:", "OK" if result.get("distributions_html") else "N/A")
    print("Correlation:", "OK" if result.get("correlation_html") else "N/A")
    print("Chemical Space PCA:", "OK" if result.get("chemical_space_html") else "N/A")
    print("Drug-likeness:", "OK" if result.get("druglikeness_html") else "N/A")
    print("3D Space:", "OK" if result.get("chemical_space_3d_html") else "N/A")
    print("Parallel Coords:", "OK" if result.get("parallel_coordinates_html") else "N/A")
    print("Scatter Matrix:", "OK" if result.get("scatter_matrix_html") else "N/A")

asyncio.run(plots())
```

**8 Plot Types:**
1. Property Distributions (MW, LogP, TPSA, HBD, HBA, QED)
2. Correlation Heatmap (8 properties)
3. Chemical Space PCA (2D, colored by QED)
4. Drug-likeness Analysis (MW vs LogP + TPSA vs LogP)
5. 3D Chemical Space (LogP vs MW vs TPSA, colored by category)
6. Parallel Coordinates (multi-property comparison)
7. Scatter Matrix (pairwise property relationships)
8. Summary Table (per-compound data)

All plots are interactive Plotly HTML — zoom, hover, pan.
