"""QSAR Tool — agent predicts molecular properties from SMILES."""
from helpers.tool import Tool, Response
import os, json, pickle, numpy as np

JOBS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "data", "qsar_models")

DESCRIPTOR_GROUPS = {
    "physicochemical": ["MolWt","ExactMolWt","HeavyAtomMolWt","MolLogP","MolMR","TPSA","NumHDonors","NumHAcceptors","NumRotatableBonds","NumAromaticRings","NumAliphaticRings","NumSaturatedRings","RingCount","NumHeteroatoms","FractionCSP3","HeavyAtomCount"],
}
ALL_DESCRIPTORS = [d for g in DESCRIPTOR_GROUPS.values() for d in g]

def _safe_desc(func, mol, default=0.0):
    try:
        v = func(mol)
        if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
            return default
        return float(v)
    except Exception:
        return default

class QsarTool(Tool):
    async def execute(self, action: str = "predict", **kwargs):
        if action == "descriptors":
            smiles = kwargs.get("smiles", "")
            if not smiles:
                return Response(message="Please provide a SMILES string.", break_loop=False)
            try:
                from rdkit import Chem
                from rdkit.Chem import Descriptors
                mol = Chem.MolFromSmiles(smiles)
                if not mol:
                    return Response(message=f"Invalid SMILES: {smiles}", break_loop=False)
                desc_map = {name: func for name, func in Descriptors.descList}
                lines = [f"Molecular Descriptors for: {smiles}"]
                lines.append("-" * 40)
                for dname in ALL_DESCRIPTORS:
                    if dname in desc_map:
                        lines.append(f"  {dname}: {_safe_desc(desc_map[dname], mol):.3f}")
                return Response(message="\n".join(lines), break_loop=False)
            except ImportError:
                return Response(message="RDKit not available for descriptor calculation.", break_loop=False)

        if action == "predict":
            model_id = kwargs.get("model_id", "")
            smiles = kwargs.get("smiles", "")
            if not model_id:
                return Response(message="Available QSAR models:\n" + self._list_models(), break_loop=False)
            if not smiles:
                return Response(message="Please provide a SMILES string and model_id.", break_loop=False)

            model_path = os.path.join(JOBS_DIR, f"{model_id}.pkl")
            meta_path = os.path.join(JOBS_DIR, f"{model_id}.json")
            if not os.path.exists(model_path):
                return Response(message=f"Model {model_id} not found.\n" + self._list_models(), break_loop=False)

            try:
                with open(model_path, "rb") as f:
                    model = pickle.load(f)
                with open(meta_path) as f:
                    meta = json.load(f)

                from rdkit import Chem
                from rdkit.Chem import Descriptors
                mol = Chem.MolFromSmiles(smiles)
                if not mol:
                    return Response(message=f"Invalid SMILES: {smiles}", break_loop=False)

                desc_map = {name: func for name, func in Descriptors.descList}
                row = {}
                for f in meta["feature_names"]:
                    row[f] = _safe_desc(desc_map[f], mol) if f in desc_map else 0.0

                x_vec = np.array([[row.get(f, 0.0) for f in meta["feature_names"]]], dtype=np.float64)
                y_pred = model.predict(x_vec)
                if hasattr(y_pred, "ravel"):
                    y_pred = y_pred.ravel()
                predicted = float(y_pred[0])

                lines = [f"QSAR Prediction: {meta['name']}"]
                lines.append(f"  Model: {meta['model_type']} | CV R²: {meta['metrics']['cv_r2']:.3f}")
                lines.append(f"  SMILES: {smiles}")
                lines.append(f"  Predicted {meta.get('activity_column', 'activity')}: {predicted:.4f}")
                return Response(message="\n".join(lines), break_loop=False)
            except Exception as e:
                return Response(message=f"Prediction failed: {str(e)}", break_loop=False)

        if action == "models":
            return Response(message=self._list_models(), break_loop=False)

        return Response(message="QSAR actions: descriptors, predict, models. Use: QSAR action=predict model_id=ID smiles=SMILES", break_loop=False)

    def _list_models(self):
        lines = ["Saved QSAR Models:", "-" * 40]
        try:
            for fname in sorted(os.listdir(JOBS_DIR), reverse=True):
                if fname.endswith(".json"):
                    with open(os.path.join(JOBS_DIR, fname)) as f:
                        m = json.load(f)
                    lines.append(f"  {m['model_id']}: {m['name']} ({m['model_type']}) R²={m['metrics']['cv_r2']:.3f}")
        except Exception:
            pass
        if len(lines) == 2:
            lines.append("  (no models trained yet)")
        return "\n".join(lines)
