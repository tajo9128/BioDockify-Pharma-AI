"""QSAR Modeler API — train ML models on molecular descriptors and predict bioactivity."""
from helpers.api import ApiHandler, Request, Response
import os, json, pickle, uuid, logging, threading, io, csv
from datetime import datetime
from typing import Dict, List, Optional
import numpy as np

log = logging.getLogger("qsar_api")
JOBS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "data", "qsar_models")
os.makedirs(JOBS_DIR, exist_ok=True)

_training_jobs: Dict = {}
_lock = threading.Lock()

DESCRIPTOR_GROUPS = {
    "physicochemical": ["MolWt","ExactMolWt","HeavyAtomMolWt","MolLogP","MolMR","TPSA","NumHDonors","NumHAcceptors","NumRotatableBonds","NumAromaticRings","NumAliphaticRings","NumSaturatedRings","RingCount","NumHeteroatoms","FractionCSP3","HeavyAtomCount"],
    "topological": ["BalabanJ","BertzCT","Chi0","Chi1","Chi2v","Chi3v","Chi4v","Kappa1","Kappa2","Kappa3","LabuteASA"],
    "electronic": ["MaxAbsEStateIndex","MinAbsEStateIndex","MaxEStateIndex","MinEStateIndex"],
    "fragment": ["fr_Al_COO","fr_Al_OH","fr_Ar_N","fr_Ar_NH","fr_Ar_OH","fr_C_O","fr_C_O_noCOO","fr_NH0","fr_NH1","fr_NH2","fr_N_O","fr_Ndealkylation1","fr_amide","fr_aniline","fr_carbonyl","fr_halogen","fr_ketone","fr_methoxy","fr_nitro","fr_phenol","fr_sulfide","fr_sulfonamd"],
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


def _calculate_descriptors(smiles_list, groups=None):
    try:
        from rdkit import Chem
        from rdkit.Chem import Descriptors
    except ImportError:
        return {"error": "RDKit not available", "descriptors": [], "valid_smiles": [], "failed_smiles": []}

    selected = ALL_DESCRIPTORS if not groups or "all" in groups else []
    if not selected:
        for g in groups:
            selected.extend(DESCRIPTOR_GROUPS.get(g, []))

    desc_map = {name: func for name, func in Descriptors.descList}
    results, valid, failed = [], [], []

    for smi in smiles_list:
        try:
            mol = Chem.MolFromSmiles(smi)
            if mol is None:
                failed.append(smi); continue
            row = {}
            for dname in selected:
                row[dname] = _safe_desc(desc_map[dname], mol) if dname in desc_map else 0.0
            results.append(row); valid.append(smi)
        except Exception:
            failed.append(smi)

    return {"success": True, "descriptors": results, "valid_smiles": valid, "failed_smiles": failed, "n_valid": len(valid), "n_failed": len(failed), "feature_names": selected}


def _train_worker(job_id, X, y, feature_names, model_type, model_name, activity_col, desc_groups, cv_folds):
    from sklearn.model_selection import cross_val_score
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.svm import SVR
    from sklearn.cross_decomposition import PLSRegression
    from sklearn.linear_model import Ridge, Lasso
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline

    try:
        with _lock:
            _training_jobs[job_id]["status"] = "running"

        X_arr = np.array(X, dtype=np.float64)
        y_arr = np.array(y, dtype=np.float64)

        models = {
            "RandomForest": RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1),
            "GradientBoosting": GradientBoostingRegressor(n_estimators=100, random_state=42),
            "SVR": SVR(kernel="rbf", C=1.0),
            "PLS": PLSRegression(n_components=min(5, X_arr.shape[1] - 1, 10)),
            "Ridge": Ridge(alpha=1.0),
            "Lasso": Lasso(alpha=0.1),
        }
        model = models.get(model_type, models["RandomForest"])

        if model_type in ("SVR", "Ridge", "Lasso"):
            pipeline = Pipeline([("scaler", StandardScaler()), ("model", model)])
        else:
            pipeline = model

        cv_r2 = cross_val_score(pipeline, X_arr, y_arr, cv=cv_folds, scoring="r2", n_jobs=-1)
        cv_rmse = np.sqrt(-cross_val_score(pipeline, X_arr, y_arr, cv=cv_folds, scoring="neg_mean_squared_error", n_jobs=-1))

        pipeline.fit(X_arr, y_arr)
        y_pred = pipeline.predict(X_arr)
        if hasattr(y_pred, "ravel"):
            y_pred = y_pred.ravel()
        train_r2 = 1 - np.sum((y_arr - y_pred)**2) / np.sum((y_arr - y_arr.mean())**2) if np.sum((y_arr - y_arr.mean())**2) > 0 else 0.0

        model_id = str(uuid.uuid4())[:8]
        model_path = os.path.join(JOBS_DIR, f"{model_id}.pkl")
        meta_path = os.path.join(JOBS_DIR, f"{model_id}.json")

        with open(model_path, "wb") as f:
            pickle.dump(pipeline, f)

        X_mean = np.mean(X_arr, axis=0)
        X_centered = X_arr - X_mean
        try:
            XtX_inv = np.linalg.pinv(X_centered.T @ X_centered)
        except Exception:
            XtX_inv = None

        meta = {
            "model_id": model_id, "name": model_name, "model_type": model_type,
            "feature_names": feature_names, "n_features": len(feature_names),
            "metrics": {"cv_r2": float(np.mean(cv_r2)), "cv_rmse": float(np.mean(cv_rmse)), "train_r2": float(train_r2), "cv_std": float(np.std(cv_r2))},
            "activity_column": activity_col, "descriptor_groups": desc_groups,
            "created_at": datetime.now().isoformat(), "ad_h_star": float(3 * len(feature_names) / len(y_arr)),
            "ad_x_mean": X_mean.tolist(), "ad_xtx_inv": XtX_inv.tolist() if XtX_inv is not None else None,
        }
        with open(meta_path, "w") as f:
            json.dump(meta, f)

        with _lock:
            _training_jobs[job_id] = {"status": "completed", "result": meta, "updated_at": datetime.now().isoformat()}
        log.info(f"QSAR training done: {model_id} cv_r2={meta['metrics']['cv_r2']:.4f}")
    except Exception as e:
        log.error(f"QSAR training failed: {e}")
        with _lock:
            _training_jobs[job_id] = {"status": "failed", "error": str(e), "updated_at": datetime.now().isoformat()}


class QsarHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "descriptors")

        if action == "descriptors":
            return {"groups": list(DESCRIPTOR_GROUPS.keys()), "descriptors": DESCRIPTOR_GROUPS, "all_count": len(ALL_DESCRIPTORS)}

        if action == "calculate":
            smiles = input.get("smiles_list", [])
            if isinstance(smiles, str):
                smiles = [s.strip() for s in smiles.split("\n") if s.strip()]
            groups = input.get("groups", ["all"])
            return _calculate_descriptors(smiles, groups)

        if action == "process_dataset":
            content = input.get("content", "")
            smiles_col = input.get("smiles_col", "smiles")
            activity_col = input.get("activity_col", "activity")
            groups = input.get("groups", "all")

            if isinstance(content, str):
                content = content.encode("utf-8")

            try:
                reader = csv.DictReader(io.StringIO(content.decode("utf-8", errors="replace")))
                rows = list(reader)
                if not rows:
                    return {"error": "Empty CSV"}
                if smiles_col not in rows[0]:
                    return {"error": f"Column '{smiles_col}' not found. Available: {list(rows[0].keys())}"}
                if activity_col not in rows[0]:
                    return {"error": f"Column '{activity_col}' not found. Available: {list(rows[0].keys())}"}

                smiles_list, y_raw = [], []
                for row in rows:
                    smi = row.get(smiles_col, "").strip()
                    act = row.get(activity_col, "").strip()
                    if smi and act:
                        try:
                            y_raw.append(float(act))
                            smiles_list.append(smi)
                        except ValueError:
                            continue
                if not smiles_list:
                    return {"error": "No valid SMILES/activity pairs"}

                group_list = [g.strip() for g in groups.split(",")] if isinstance(groups, str) else groups
                desc = _calculate_descriptors(smiles_list, group_list)
                if "error" in desc:
                    return desc

                valid_idx = [smiles_list.index(s) for s in desc["valid_smiles"]]
                y_valid = [y_raw[i] for i in valid_idx]
                feature_names = desc["feature_names"]
                X = [[row.get(f, 0.0) for f in feature_names] for row in desc["descriptors"]]
                X_arr = np.nan_to_num(np.array(X, dtype=np.float32))

                return {"X": X_arr.tolist(), "y": y_valid, "feature_names": feature_names, "n_compounds": len(y_valid), "n_features": len(feature_names), "failed_count": len(desc["failed_smiles"])}
            except Exception as e:
                return {"error": str(e)}

        if action == "train":
            X = input.get("X", [])
            y = input.get("y", [])
            feature_names = input.get("feature_names", [])
            if not X or not y or not feature_names:
                return {"error": "X, y, and feature_names required"}
            job_id = str(uuid.uuid4())[:12]
            with _lock:
                _training_jobs[job_id] = {"status": "pending"}
            t = threading.Thread(target=_train_worker, args=(job_id, X, y, feature_names, input.get("model_type", "RandomForest"), input.get("model_name", "QSAR Model"), input.get("activity_column", "activity"), input.get("descriptor_groups", ["all"]), input.get("cv_folds", 5)), daemon=True)
            t.start()
            return {"job_id": job_id, "status": "pending"}

        if action == "training_status":
            jid = input.get("job_id", "")
            with _lock:
                return dict(_training_jobs.get(jid, {"status": "not_found"}))

        if action == "predict":
            model_id = input.get("model_id", "")
            smiles = input.get("smiles", "")
            model_path = os.path.join(JOBS_DIR, f"{model_id}.pkl")
            meta_path = os.path.join(JOBS_DIR, f"{model_id}.json")
            if not os.path.exists(model_path):
                return {"error": f"Model {model_id} not found", "success": False}
            try:
                with open(model_path, "rb") as f:
                    model = pickle.load(f)
                with open(meta_path) as f:
                    meta = json.load(f)
                desc = _calculate_descriptors([smiles], meta.get("descriptor_groups", ["all"]))
                if not desc.get("valid_smiles"):
                    return {"error": "Invalid SMILES", "success": False}
                row = desc["descriptors"][0]
                x_vec = np.array([[row.get(f, 0.0) for f in meta["feature_names"]]], dtype=np.float64)
                y_pred = model.predict(x_vec)
                if hasattr(y_pred, "ravel"):
                    y_pred = y_pred.ravel()
                predicted = float(y_pred[0])

                ad_status = "unknown"
                h = None
                h_star = meta.get("ad_h_star")
                x_mean = meta.get("ad_x_mean")
                xtx_inv = meta.get("ad_xtx_inv")
                if h_star and x_mean and xtx_inv:
                    diff = x_vec[0] - np.array(x_mean, dtype=np.float64)
                    h = float(diff @ np.array(xtx_inv, dtype=np.float64) @ diff)
                    ad_status = "in_domain" if h <= h_star * 0.5 else ("warning" if h <= h_star else "out_of_domain")

                return {"success": True, "smiles": smiles, "predicted_activity": predicted, "ad_status": ad_status, "ad_leverage": h}
            except Exception as e:
                return {"error": str(e), "success": False}

        if action == "predict_batch":
            return {"error": "Batch prediction not yet implemented", "success": False}

        if action == "models":
            models = []
            for fname in os.listdir(JOBS_DIR):
                if fname.endswith(".json"):
                    try:
                        with open(os.path.join(JOBS_DIR, fname)) as f:
                            m = json.load(f)
                        models.append({"model_id": m["model_id"], "name": m["name"], "model_type": m["model_type"], "metrics": m["metrics"], "n_features": m["n_features"], "activity_column": m.get("activity_column", "activity"), "created_at": m["created_at"]})
                    except Exception:
                        continue
            return {"models": sorted(models, key=lambda m: m["created_at"], reverse=True)}

        if action == "delete_model":
            mid = input.get("model_id", "")
            deleted = False
            for ext in [".pkl", ".json"]:
                p = os.path.join(JOBS_DIR, f"{mid}{ext}")
                if os.path.exists(p):
                    os.remove(p); deleted = True
            return {"deleted": deleted}

        return {"error": f"Unknown action: {action}"}
