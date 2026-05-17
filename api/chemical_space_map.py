from helpers.api import ApiHandler, Request
import base64
import io


class ChemicalSpace(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        smiles_list = input.get("smiles_list", [])
        if not smiles_list or len(smiles_list) < 2:
            return {"error": "At least 2 SMILES required"}

        try:
            from rdkit import Chem, DataStructs
            from rdkit.Chem import AllChem, Descriptors
            import numpy as np
            from sklearn.decomposition import PCA

            fps_list = []
            mols = []
            valid_smiles = []

            for s in smiles_list:
                mol = Chem.MolFromSmiles(s.strip())
                if mol is None:
                    continue
                mols.append(mol)
                valid_smiles.append(s.strip())
                fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, 2048)
                arr = np.zeros((1, 2048), dtype=np.int8)
                DataStructs.ConvertToNumpyArray(fp, arr[0])
                fps_list.append(arr[0])

            if len(fps_list) < 2:
                return {"error": "Need at least 2 valid molecules"}

            X = np.array(fps_list)
            pca = PCA(n_components=2)
            coords = pca.fit_transform(X)

            # Compute MW for coloring
            mws = [Descriptors.MolWt(m) for m in mols]

            # Build plot
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(8, 6))
            fig.patch.set_facecolor("#0f0f23")
            ax.set_facecolor("#0f0f23")

            scatter = ax.scatter(coords[:, 0], coords[:, 1], c=mws, cmap="viridis",
                               s=60, alpha=0.8, edgecolors="#00d4aa", linewidth=0.5)

            for i, s in enumerate(valid_smiles):
                ax.annotate(s[:20], (coords[i, 0], coords[i, 1]),
                           fontsize=5, alpha=0.7, color="#a0a0b0")

            ax.set_title("Chemical Space (PCA on Morgan Fingerprints)", color="#ffffff", fontsize=10)
            ax.tick_params(colors="#a0a0b0", labelsize=7)
            cbar = plt.colorbar(scatter, ax=ax)
            cbar.set_label("Molecular Weight", color="#a0a0b0")
            for t in cbar.ax.get_yticklabels():
                t.set_color("#a0a0b0")

            buf = io.BytesIO()
            plt.savefig(buf, format="png", dpi=120, bbox_inches="tight")
            plt.close()
            buf.seek(0)
            plot_b64 = base64.b64encode(buf.read()).decode()

            return {
                "plot_base64": plot_b64,
                "num_molecules": len(valid_smiles),
                "variance_explained": [round(float(v), 2) for v in pca.explained_variance_ratio_],
                "molecules": [
                    {"smiles": s, "x": round(float(coords[i, 0]), 2), "y": round(float(coords[i, 1]), 2), "mw": round(float(mws[i]), 1)}
                    for i, s in enumerate(valid_smiles)
                ],
            }

        except ImportError as e:
            return {"error": f"Missing dependency: {e}"}
        except Exception as e:
            return {"error": str(e)}
