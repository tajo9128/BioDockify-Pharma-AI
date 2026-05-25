"""QSAR Modeler API v2 — train ML models (regression + classification), predict bioactivity,
batch screen, feature importance, PLS VIP, Williams Plot, read-across, feature selection.

Inspired by QSAR-Co (classification with conditions), Cloud 3D-QSAR (field-based visualization),
OECD QSAR Toolbox (read-across, AD, profiling)."""
from helpers.api import ApiHandler, Request, Response
import os, json, pickle, uuid, logging, threading, io, csv, shutil
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

REGRESSION_MODELS = ["RandomForest", "GradientBoosting", "SVR", "PLS", "Ridge", "Lasso"]
CLASSIFICATION_MODELS = ["RandomForestClassifier", "SVC", "LogisticRegression"]


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
        return {"error": "RDKit not available"}

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
                if dname in desc_map:
                    row[dname] = _safe_desc(desc_map[dname], mol)
                else:
                    row[dname] = 0.0
            results.append(row); valid.append(smi)
        except Exception:
            failed.append(smi)
    return {"success": True, "descriptors": results, "valid_smiles": valid, "failed_smiles": failed,
            "n_valid": len(valid), "n_failed": len(failed), "feature_names": selected}


def _train_worker(job_id, X, y, feature_names, model_type, model_name, activity_col,
                  desc_groups, cv_folds, test_split, model_task):
    import sklearn
    try:
        with _lock:
            _training_jobs[job_id]["status"] = "running"

        X_arr = np.array(X, dtype=np.float64)
        y_arr = np.array(y, dtype=np.float64)
        n_samples = len(y_arr)

        # ── Train/Test Split ──
        test_X, test_y = None, None
        test_metrics = {}
        if test_split and test_split > 0 and test_split < 1:
            from sklearn.model_selection import train_test_split
            X_arr, test_X, y_arr, test_y = train_test_split(X_arr, y_arr, test_size=test_split, random_state=42)
        n_train = len(y_arr)

        from sklearn.preprocessing import StandardScaler
        needs_scaling = model_type in ("SVR", "SVC", "Ridge", "Lasso", "LogisticRegression")

        # ── Build model ──
        if model_task == "classification":
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.svm import SVC
            from sklearn.linear_model import LogisticRegression as LR
            clf_map = {
                "RandomForestClassifier": RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1),
                "SVC": SVC(kernel="rbf", C=1.0, probability=True, random_state=42),
                "LogisticRegression": LR(max_iter=1000, random_state=42, n_jobs=-1),
            }
            model = clf_map.get(model_type, clf_map["RandomForestClassifier"])
            if needs_scaling:
                pipeline = sklearn.pipeline.make_pipeline(StandardScaler(), model)
            else:
                pipeline = model

            from sklearn.model_selection import cross_val_score, StratifiedKFold
            skf = StratifiedKFold(n_splits=min(cv_folds, min(np.bincount(y_arr.astype(int)))),
                                  shuffle=True, random_state=42)
            cv_acc = cross_val_score(pipeline, X_arr, y_arr, cv=skf, scoring="accuracy", n_jobs=-1)
            cv_auc = cross_val_score(pipeline, X_arr, y_arr, cv=skf, scoring="roc_auc", n_jobs=-1) if len(set(y_arr)) == 2 else np.array([0])
        else:
            from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
            from sklearn.svm import SVR
            from sklearn.cross_decomposition import PLSRegression
            from sklearn.linear_model import Ridge, Lasso
            reg_map = {
                "RandomForest": RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1),
                "GradientBoosting": GradientBoostingRegressor(n_estimators=100, random_state=42),
                "SVR": SVR(kernel="rbf", C=1.0),
                "PLS": PLSRegression(n_components=min(5, X_arr.shape[1] - 1, 10, n_train - 1)),
                "Ridge": Ridge(alpha=1.0),
                "Lasso": Lasso(alpha=0.1),
            }
            model = reg_map.get(model_type, reg_map["RandomForest"])
            if needs_scaling:
                pipeline = sklearn.pipeline.make_pipeline(StandardScaler(), model)
            else:
                pipeline = model
            from sklearn.model_selection import cross_val_score
            cv_r2 = cross_val_score(pipeline, X_arr, y_arr, cv=min(cv_folds, n_train), scoring="r2", n_jobs=-1)
            cv_rmse = np.sqrt(-cross_val_score(pipeline, X_arr, y_arr, cv=min(cv_folds, n_train),
                                               scoring="neg_mean_squared_error", n_jobs=-1))

        # Fit final model
        pipeline.fit(X_arr, y_arr)

        # ── Train metrics ──
        y_pred = pipeline.predict(X_arr)
        if hasattr(y_pred, "ravel"):
            y_pred = y_pred.ravel()

        if model_task == "classification":
            from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
            y_pred_class = y_pred if y_pred.dtype in (np.int32, np.int64, int) else np.round(y_pred).astype(int)
            train_acc = accuracy_score(y_arr.astype(int), y_pred_class)
            train_prec = precision_score(y_arr.astype(int), y_pred_class, average="weighted", zero_division=0)
            train_rec = recall_score(y_arr.astype(int), y_pred_class, average="weighted", zero_division=0)
            train_f1 = f1_score(y_arr.astype(int), y_pred_class, average="weighted", zero_division=0)
            metrics = {
                "cv_accuracy": float(np.mean(cv_acc)), "cv_auc": float(np.mean(cv_auc)),
                "cv_std": float(np.std(cv_acc)), "train_accuracy": float(train_acc),
                "train_precision": float(train_prec), "train_recall": float(train_rec), "train_f1": float(train_f1),
            }
        else:
            train_r2 = 1 - np.sum((y_arr - y_pred)**2) / np.sum((y_arr - y_arr.mean())**2) if np.sum((y_arr - y_arr.mean())**2) > 0 else 0.0
            metrics = {
                "cv_r2": float(np.mean(cv_r2)), "cv_rmse": float(np.mean(cv_rmse)),
                "cv_std": float(np.std(cv_r2)), "train_r2": float(train_r2),
            }

        # ── Test metrics ──
        if test_X is not None and test_y is not None and len(test_y) > 0:
            y_test_pred = pipeline.predict(test_X)
            if hasattr(y_test_pred, "ravel"):
                y_test_pred = y_test_pred.ravel()
            if model_task == "classification":
                y_tc = y_test_pred if y_test_pred.dtype in (np.int32, np.int64, int) else np.round(y_test_pred).astype(int)
                test_metrics = {
                    "test_accuracy": float(accuracy_score(test_y.astype(int), y_tc)),
                    "test_precision": float(precision_score(test_y.astype(int), y_tc, average="weighted", zero_division=0)),
                    "test_recall": float(recall_score(test_y.astype(int), y_tc, average="weighted", zero_division=0)),
                    "test_f1": float(f1_score(test_y.astype(int), y_tc, average="weighted", zero_division=0)),
                    "test_n": int(len(test_y)),
                }
            else:
                test_r2 = 1 - np.sum((test_y - y_test_pred)**2) / np.sum((test_y - test_y.mean())**2) if np.sum((test_y - test_y.mean())**2) > 0 else 0.0
                test_rmse = float(np.sqrt(np.mean((test_y - y_test_pred)**2)))
                test_metrics = {"test_r2": float(test_r2), "test_rmse": test_rmse, "test_n": int(len(test_y))}
        metrics.update(test_metrics)

        # ── Feature Importance ──
        feat_importance = None
        pls_vip = None
        if model_type in ("RandomForest", "RandomForestClassifier", "GradientBoosting"):
            est = pipeline.named_steps["model"] if isinstance(pipeline, sklearn.pipeline.Pipeline) else pipeline
            if hasattr(est, "feature_importances_"):
                fi = est.feature_importances_
                feat_importance = {feature_names[i]: round(float(fi[i]), 4) for i in range(len(feature_names))}
                feat_importance = dict(sorted(feat_importance.items(), key=lambda x: x[1], reverse=True))
        elif model_type == "PLS":
            est = pipeline.named_steps["model"] if isinstance(pipeline, sklearn.pipeline.Pipeline) else pipeline
            if hasattr(est, "x_weights_"):
                w = est.x_weights_[:, 0] if est.x_weights_.ndim == 2 else est.x_weights_
                ssx = np.sum(est.x_scores_**2, axis=0) if hasattr(est, "x_scores_") else np.ones(len(w))
                vip = np.sqrt(len(feature_names) * np.sum(ssx * (w**2) * np.sign(w), axis=1) / np.sum(ssx)) if w.ndim == 2 else np.abs(w)
                pls_vip = {feature_names[i]: round(float(vip[i]), 4) for i in range(min(len(feature_names), len(vip)))}
                pls_vip = dict(sorted(pls_vip.items(), key=lambda x: x[1], reverse=True))

        # ── Save model ──
        model_id = str(uuid.uuid4())[:8]
        model_path = os.path.join(JOBS_DIR, f"{model_id}.pkl")
        meta_path = os.path.join(JOBS_DIR, f"{model_id}.json")
        with open(model_path, "wb") as f:
            pickle.dump(pipeline, f)

        # Move training smiles data to model_id if available
        with _lock:
            job_meta = _training_jobs.get(job_id, {})
        train_smi_src = job_meta.get("_train_data_file")
        if train_smi_src and os.path.exists(train_smi_src):
            import shutil
            dst = os.path.join(JOBS_DIR, f"{model_id}_train.json")
            shutil.copy(train_smi_src, dst)

        X_all = np.vstack([X_arr, test_X]) if test_X is not None else X_arr
        X_mean = np.mean(X_all, axis=0)
        X_centered = X_all - X_mean
        try:
            XtX_inv = np.linalg.pinv(X_centered.T @ X_centered)
        except Exception:
            XtX_inv = None

        meta = {
            "model_id": model_id, "name": model_name, "model_type": model_type,
            "model_task": model_task, "feature_names": feature_names,
            "n_features": len(feature_names),
            "metrics": metrics, "activity_column": activity_col,
            "descriptor_groups": desc_groups, "n_train": n_train, "n_test": len(test_y) if test_y is not None else 0,
            "created_at": datetime.now().isoformat(),
            "ad_h_star": float(3 * len(feature_names) / n_samples),
            "ad_x_mean": X_mean.tolist(), "ad_xtx_inv": XtX_inv.tolist() if XtX_inv is not None else None,
            "feature_importance": feat_importance,
            "pls_vip": pls_vip,
            "train_y_mean": float(np.mean(y_arr)),
        }
        with open(meta_path, "w") as f:
            json.dump(meta, f, default=str)

        with _lock:
            _training_jobs[job_id] = {"status": "completed", "result": meta, "updated_at": datetime.now().isoformat()}
        log.info(f"QSAR training done: {model_id} model={model_type} task={model_task}")
    except Exception as e:
        log.error(f"QSAR training failed: {e}")
        with _lock:
            _training_jobs[job_id] = {"status": "failed", "error": str(e), "updated_at": datetime.now().isoformat()}


def _generate_williams_svg(train_y, pred_y, leverage, h_star, smi_labels):
    """Generate a Williams Plot SVG (leverage vs standardized residuals)."""
    import math
    y_arr = np.array(train_y)
    p_arr = np.array(pred_y)
    residuals = y_arr - p_arr
    std_r = residuals / (np.std(residuals) + 1e-10)

    w, h = 480, 400
    m = 50
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">',
           f'<rect width="{w}" height="{h}" fill="#fafafa" rx="6"/>',
           f'<text x="{w/2}" y="18" text-anchor="middle" font-size="11" font-weight="bold" fill="#333">Williams Plot — Applicability Domain</text>']

    max_h = max(h_star * 2, max(leverage) * 1.2) if leverage else 0.1
    max_sr = max(abs(min(std_r)), abs(max(std_r))) * 1.2 if len(std_r) > 0 else 3

    def sx(hv):
        return m + (hv / max_h) * (w - 2 * m) if max_h > 0 else m
    def sy(sr):
        return h / 2 - (sr / max_sr) * (h / 2 - m) if max_sr > 0 else h / 2

    # Axes
    svg.append(f'<line x1="{m}" y1="{h-m}" x2="{w-m}" y2="{h-m}" stroke="#ccc" stroke-width="1"/>')
    svg.append(f'<line x1="{m}" y1="{m}" x2="{m}" y2="{h-m}" stroke="#ccc" stroke-width="1"/>')
    svg.append(f'<text x="{w-m+4}" y="{h-m+10}" font-size="9" fill="#666">Hat h</text>')
    svg.append(f'<text x="{m-30}" y="{m-4}" font-size="9" fill="#666">Std. Res.</text>')

    # h* threshold line
    hsx = sx(h_star)
    svg.append(f'<line x1="{hsx}" y1="{m}" x2="{hsx}" y2="{h-m}" stroke="#ff6b6b" stroke-width="1.5" stroke-dasharray="5,3"/>')
    svg.append(f'<text x="{hsx+2}" y="{h-m-5}" font-size="8" fill="#ff6b6b">h*={h_star:.4f}</text>')

    # ±3 std residuals
    for sr_val, label in [(-3, "-3σ"), (3, "+3σ")]:
        ys = sy(sr_val)
        svg.append(f'<line x1="{m}" y1="{ys}" x2="{w-m}" y2="{ys}" stroke="#aaa" stroke-width="0.5" stroke-dasharray="3,3"/>')

    # Points
    for i in range(len(leverage)):
        if i < len(std_r):
            xp, yp = sx(leverage[i]), sy(std_r[i])
            color = "#22c55e" if leverage[i] <= h_star else "#ff6b6b"
            svg.append(f'<circle cx="{xp}" cy="{yp}" r="3.5" fill="{color}" opacity="0.7"/>')

    svg.append('</svg>')
    return "".join(svg)


def _find_analogues(query_smiles, train_smiles, train_activities, ad_mean, ad_xtx_inv,
                    ad_h_star, feature_names, desc_groups, top_k=10):
    """Read-across: find training compounds most similar to the query (Tanimoto on ECFP4)."""
    from rdkit import Chem
    from rdkit.Chem import AllChem, DataStructs
    mol = Chem.MolFromSmiles(query_smiles)
    if mol is None:
        return []
    query_fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)

    analogues = []
    for i, smi in enumerate(train_smiles):
        try:
            tm = Chem.MolFromSmiles(smi)
            if tm is None:
                continue
            t_fp = AllChem.GetMorganFingerprintAsBitVect(tm, 2, nBits=2048)
            sim = DataStructs.TanimotoSimilarity(query_fp, t_fp)
            if sim >= 0.3:
                analogues.append({"smiles": smi, "activity": train_activities[i], "similarity": round(sim, 3)})
        except Exception:
            continue

    analogues.sort(key=lambda a: a["similarity"], reverse=True)
    return analogues[:top_k]


def _feature_selection(X, y, feature_names, method="mutual_info", k=20):
    """Select top-k features by mutual information or ANOVA F-test."""
    X_arr = np.array(X, dtype=np.float64)
    y_arr = np.array(y, dtype=np.float64)

    if method == "mutual_info":
        from sklearn.feature_selection import mutual_info_regression
        scores = mutual_info_regression(X_arr, y_arr, random_state=42)
    else:
        from sklearn.feature_selection import f_regression
        scores, _ = f_regression(X_arr, y_arr)

    ranked = sorted(zip(feature_names, scores), key=lambda x: x[1], reverse=True)
    top = [{"feature": f, "score": round(float(s), 4)} for f, s in ranked[:k]]
    return {"top_features": top, "method": method, "n_selected": len(top)}


class QsarHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "descriptors")

        if action == "descriptors":
            return {"groups": list(DESCRIPTOR_GROUPS.keys()), "descriptors": DESCRIPTOR_GROUPS,
                    "all_count": len(ALL_DESCRIPTORS),
                    "model_types": {"regression": REGRESSION_MODELS, "classification": CLASSIFICATION_MODELS}}

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
            task = input.get("task", "regression")
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

                smiles_list, y_raw, class_labels = [], [], {}
                for row in rows:
                    smi = row.get(smiles_col, "").strip()
                    act = row.get(activity_col, "").strip()
                    if smi and act:
                        try:
                            if task == "classification":
                                if act not in class_labels:
                                    class_labels[act] = len(class_labels)
                                y_raw.append(class_labels[act])
                            else:
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
                all_smi = [smiles_list[i] for i in valid_idx]
                feature_names = desc["feature_names"]
                X = [[row.get(f, 0.0) for f in feature_names] for row in desc["descriptors"]]
                X_arr = np.nan_to_num(np.array(X, dtype=np.float32))

                return {
                    "X": X_arr.tolist(), "y": y_valid, "feature_names": feature_names,
                    "n_compounds": len(y_valid), "n_features": len(feature_names),
                    "failed_count": len(desc["failed_smiles"]), "task": task,
                    "class_mapping": class_labels if task == "classification" else None,
                    "_smiles": all_smi,
                }
            except Exception as e:
                return {"error": str(e)}

        if action == "train":
            X = input.get("X", [])
            y = input.get("y", [])
            feature_names = input.get("feature_names", [])
            task = input.get("task", "regression")
            train_smiles = input.get("_smiles", [])
            if not X or not y or not feature_names:
                return {"error": "X, y, and feature_names required"}
            job_id = str(uuid.uuid4())[:12]
            model_type = input.get("model_type", "RandomForest")
            # Store training data for read-across + Williams plot
            if train_smiles:
                tpath = os.path.join(JOBS_DIR, f"{job_id}_smiles.json")
                try:
                    with open(tpath, "w") as f:
                        json.dump({"smiles": train_smiles, "activities": y}, f)
                except Exception:
                    pass
            with _lock:
                _training_jobs[job_id] = {"status": "pending", "_train_data_file": os.path.join(JOBS_DIR, f"{job_id}_smiles.json") if train_smiles else None}
            t = threading.Thread(target=_train_worker, args=(
                job_id, X, y, feature_names, model_type,
                input.get("model_name", "QSAR Model"),
                input.get("activity_column", "activity"),
                input.get("descriptor_groups", ["all"]),
                input.get("cv_folds", 5),
                input.get("test_split", 0),
                task,
            ), daemon=True)
            t.start()
            return {"job_id": job_id, "status": "pending", "task": task}

        if action == "training_status":
            jid = input.get("job_id", "")
            with _lock:
                j = dict(_training_jobs.get(jid, {"status": "not_found"}))
            if j.get("status") == "completed" and j.get("result"):
                j["model_id"] = j["result"].get("model_id")
            return j

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

                # AD
                ad_status, h = "unknown", None
                h_star = meta.get("ad_h_star")
                x_mean = meta.get("ad_x_mean")
                xtx_inv = meta.get("ad_xtx_inv")
                if h_star and x_mean and xtx_inv:
                    diff = x_vec[0] - np.array(x_mean, dtype=np.float64)
                    h = float(diff @ np.array(xtx_inv, dtype=np.float64) @ diff)
                    ad_status = "in_domain" if h <= h_star * 0.5 else ("warning" if h <= h_star else "out_of_domain")

                result = {"success": True, "smiles": smiles, "predicted_activity": predicted,
                          "ad_status": ad_status, "ad_leverage": h, "model_task": meta.get("model_task", "regression")}

                if meta.get("model_task") == "classification":
                    result["predicted_class"] = str(int(round(predicted)))
                    if hasattr(model, "predict_proba"):
                        result["probabilities"] = [round(float(p), 4) for p in model.predict_proba(x_vec)[0]]

                return result
            except Exception as e:
                return {"error": str(e), "success": False}

        if action == "predict_batch":
            model_id = input.get("model_id", "")
            smiles_list = input.get("smiles_list", [])
            if isinstance(smiles_list, str):
                smiles_list = [s.strip() for s in smiles_list.split("\n") if s.strip()]
            if not smiles_list:
                return {"error": "smiles_list required"}

            model_path = os.path.join(JOBS_DIR, f"{model_id}.pkl")
            meta_path = os.path.join(JOBS_DIR, f"{model_id}.json")
            if not os.path.exists(model_path):
                return {"error": f"Model {model_id} not found"}
            try:
                with open(model_path, "rb") as f:
                    model = pickle.load(f)
                with open(meta_path) as f:
                    meta = json.load(f)
                desc = _calculate_descriptors(smiles_list, meta.get("descriptor_groups", ["all"]))
                results, failed = [], desc.get("failed_smiles", [])
                for i, row in enumerate(desc.get("descriptors", [])):
                    smi = desc["valid_smiles"][i]
                    x_vec = np.array([[row.get(f, 0.0) for f in meta["feature_names"]]], dtype=np.float64)
                    y_pred = model.predict(x_vec)
                    if hasattr(y_pred, "ravel"):
                        y_pred = y_pred.ravel()
                    r = {"smiles": smi, "predicted": float(y_pred[0])}
                    # AD
                    h_star = meta.get("ad_h_star")
                    x_mean = meta.get("ad_x_mean")
                    xtx_inv = meta.get("ad_xtx_inv")
                    if h_star and x_mean and xtx_inv:
                        diff = x_vec[0] - np.array(x_mean, dtype=np.float64)
                        h = float(diff @ np.array(xtx_inv, dtype=np.float64) @ diff)
                        r["ad_status"] = "in_domain" if h <= h_star * 0.5 else ("warning" if h <= h_star else "out_of_domain")
                    results.append(r)
                return {"success": True, "predictions": results, "failed": failed, "total": len(smiles_list),
                        "n_predictions": len(results), "model_task": meta.get("model_task", "regression")}
            except Exception as e:
                return {"error": str(e)}

        if action == "read_across":
            model_id = input.get("model_id", "")
            smiles = input.get("smiles", "")
            meta_path = os.path.join(JOBS_DIR, f"{model_id}.json")
            train_data_key = f"_train_smiles_{model_id}"
            if not os.path.exists(meta_path):
                return {"error": f"Model {model_id} not found"}
            try:
                with open(meta_path) as f:
                    meta = json.load(f)
                # Read-across needs training data — stored in a separate file from process_dataset
                train_path = os.path.join(JOBS_DIR, f"{model_id}_train.json")
                if not os.path.exists(train_path):
                    return {"error": "Training data not cached for this model. Re-train with read-across enabled."}

                with open(train_path) as f:
                    tdata = json.load(f)
                analogues = _find_analogues(smiles, tdata["smiles"], tdata["activities"],
                                            meta.get("ad_x_mean"), meta.get("ad_xtx_inv"),
                                            meta.get("ad_h_star"), meta.get("feature_names", []),
                                            meta.get("descriptor_groups", ["all"]))
                return {"success": True, "query_smiles": smiles, "analogues": analogues, "n_analogues": len(analogues)}
            except Exception as e:
                return {"error": str(e)}

        if action == "williams_plot":
            model_id = input.get("model_id", "")
            meta_path = os.path.join(JOBS_DIR, f"{model_id}.json")
            if not os.path.exists(meta_path):
                return {"error": f"Model {model_id} not found"}
            try:
                with open(meta_path) as f:
                    meta = json.load(f)
                # Need training data
                train_path = os.path.join(JOBS_DIR, f"{model_id}_train.json")
                if not os.path.exists(train_path):
                    return {"error": "Training data not cached for this model"}

                with open(train_path) as f:
                    tdata = json.load(f)
                model_path = os.path.join(JOBS_DIR, f"{model_id}.pkl")
                with open(model_path, "rb") as f:
                    model = pickle.load(f)

                # Recompute predictions + leverage for train set
                desc = _calculate_descriptors(tdata["smiles"], meta.get("descriptor_groups", ["all"]))
                Xr = []
                for row in desc.get("descriptors", []):
                    Xr.append([row.get(fn, 0.0) for fn in meta["feature_names"]])
                X_arr = np.array(Xr, dtype=np.float64)
                y_pred = model.predict(X_arr)
                if hasattr(y_pred, "ravel"):
                    y_pred = y_pred.ravel()

                leverage = []
                x_mean = np.array(meta.get("ad_x_mean", []), dtype=np.float64)
                xtx_inv = np.array(meta.get("ad_xtx_inv", []), dtype=np.float64) if meta.get("ad_xtx_inv") else None
                h_star = meta.get("ad_h_star", 0.1)
                if xtx_inv is not None and xtx_inv.size > 0:
                    for x in X_arr:
                        diff = x - x_mean
                        leverage.append(float(diff @ xtx_inv @ diff))
                else:
                    leverage = [0.0] * len(X_arr)

                svg = _generate_williams_svg(np.array(tdata["activities"]), y_pred, leverage, h_star, tdata["smiles"])
                return {"success": True, "svg": svg, "h_star": h_star, "n_points": len(leverage)}
            except Exception as e:
                return {"error": str(e)}

        if action == "feature_selection":
            X = input.get("X", [])
            y = input.get("y", [])
            feature_names = input.get("feature_names", [])
            method = input.get("method", "mutual_info")
            k = input.get("k", 20)
            if not X or not y or not feature_names:
                return {"error": "X, y, and feature_names required"}
            try:
                return {"success": True, **_feature_selection(X, y, feature_names, method, k)}
            except Exception as e:
                return {"error": str(e)}

        if action == "models":
            models = []
            for fname in os.listdir(JOBS_DIR):
                if fname.endswith(".json") and not fname.endswith("_train.json"):
                    try:
                        with open(os.path.join(JOBS_DIR, fname)) as f:
                            m = json.load(f)
                        models.append({
                            "model_id": m["model_id"], "name": m["name"], "model_type": m["model_type"],
                            "model_task": m.get("model_task", "regression"),
                            "metrics": m["metrics"], "n_features": m["n_features"],
                            "activity_column": m.get("activity_column", "activity"),
                            "created_at": m["created_at"],
                        })
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
            tp = os.path.join(JOBS_DIR, f"{mid}_train.json")
            if os.path.exists(tp):
                os.remove(tp); deleted = True
            return {"deleted": deleted}

        return {"error": f"Unknown action: {action}"}
