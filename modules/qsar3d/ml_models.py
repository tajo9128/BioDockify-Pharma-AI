"""
Multi-Model QSAR — trains and compares 10+ ML models for molecular property prediction.

Inspired by Omixium's QSAR_ML_all_models pipeline (Pritam Panda).
Models: PLS, Ridge, Lasso, Elastic Net, KNN, Decision Tree, Random Forest,
        Gradient Boosting, Extra Trees, XGBoost, LightGBM, CatBoost.

Supports: Morgan fingerprints + RDKit descriptors, multi-target prediction,
          model comparison table, feature importance, saved models (.pkl).
"""
import logging
import time
import numpy as np

log = logging.getLogger("qsar.ml_models")

try:
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
    from sklearn.preprocessing import StandardScaler
    from sklearn.cross_decomposition import PLSRegression
    from sklearn.linear_model import Ridge, Lasso, ElasticNet
    from sklearn.neighbors import KNeighborsRegressor
    from sklearn.tree import DecisionTreeRegressor
    from sklearn.ensemble import (RandomForestRegressor, GradientBoostingRegressor,
                                  ExtraTreesRegressor)
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

try:
    import lightgbm as lgb
    HAS_LGBM = True
except ImportError:
    HAS_LGBM = False

try:
    from catboost import CatBoostRegressor
    HAS_CATBOOST = True
except ImportError:
    HAS_CATBOOST = False

try:
    from rdkit import Chem
    from rdkit.Chem import rdFingerprintGenerator, Descriptors, rdMolDescriptors
    HAS_RDKIT = True
except ImportError:
    HAS_RDKIT = False


def generate_morgan_fingerprints(smiles_list, fp_size=2048, radius=2):
    """Generate Morgan fingerprints from SMILES list.

    Returns: (numpy array [n_molecules, fp_size], list of valid indices)
    """
    if not HAS_RDKIT:
        raise ImportError("RDKit not available")

    from rdkit import RDLogger
    RDLogger.DisableLog("rdApp.*")

    gen = rdFingerprintGenerator.GetMorganGenerator(radius=radius, fpSize=fp_size)
    fps = []
    valid_idx = []

    for i, smi in enumerate(smiles_list):
        mol = Chem.MolFromSmiles(str(smi).strip())
        if mol is None:
            continue
        fp = gen.GetFingerprint(mol)
        arr = np.zeros(fp_size, dtype=np.float32)
        for bit in fp.GetOnBits():
            arr[bit] = 1.0
        fps.append(arr)
        valid_idx.append(i)

    return np.array(fps), valid_idx


def calculate_descriptors(smiles_list):
    """Calculate 50+ RDKit molecular descriptors from SMILES list.

    Returns: (numpy array [n_molecules, n_descriptors], list of descriptor names, list of valid indices)
    """
    if not HAS_RDKIT:
        raise ImportError("RDKit not available")

    from rdkit import RDLogger
    RDLogger.DisableLog("rdApp.*")

    descriptor_names = [
        "MolWt", "MolLogP", "TPSA", "NumHDonors", "NumHAcceptors",
        "NumRotatableBonds", "NumAromaticRings", "NumAliphaticRings",
        "NumSaturatedRings", "NumHeteroatoms", "NumHeavyAtoms",
        "FractionCSP3", "RingCount", "NumAmideBonds",
        "LabuteASA", "BalabanJ", "BertzCT", "HallKierAlpha",
        "Kappa1", "Kappa2", "Kappa3", "Chi0", "Chi1", "Chi0n", "Chi1n",
        "Chi0v", "Chi1v", "Chi2v", "Chi3v", "Chi4v",
        "MaxAbsEStateIndex", "MinAbsEStateIndex", "MaxEStateIndex", "MinEStateIndex",
        "qed", "MolMR",
        "NumValenceElectrons", "NumRadicalElectrons",
        "MaxPartialCharge", "MinPartialCharge",
        "MaxAbsPartialCharge", "MinAbsPartialCharge",
        "FpDensityMorgan1", "FpDensityMorgan2", "FpDensityMorgan3",
        "NumNHOHCount", "NumNOCount",
        "NumAliphaticCarbocycles", "NumAliphaticHeterocycles",
        "NumAromaticCarbocycles", "NumAromaticHeterocycles",
    ]

    descriptor_funcs = []
    for name in descriptor_names:
        func = getattr(Descriptors, name, None) or getattr(rdMolDescriptors, name, None)
        if func:
            descriptor_funcs.append((name, func))

    all_desc = []
    valid_idx = []

    for i, smi in enumerate(smiles_list):
        mol = Chem.MolFromSmiles(str(smi).strip())
        if mol is None:
            continue
        row = []
        for name, func in descriptor_funcs:
            try:
                val = func(mol)
                if val is None or np.isnan(val) or np.isinf(val):
                    val = 0.0
                row.append(float(val))
            except Exception:
                row.append(0.0)
        all_desc.append(row)
        valid_idx.append(i)

    names = [n for n, _ in descriptor_funcs]
    return np.array(all_desc), names, valid_idx


def get_all_models():
    """Return dict of all available models with their constructors."""
    models = {}

    # Always available (sklearn)
    if HAS_SKLEARN:
        models["PLS"] = {"class": PLSRegression, "params": {"n_components": 5}, "type": "linear"}
        models["Ridge"] = {"class": Ridge, "params": {"alpha": 1.0}, "type": "linear"}
        models["Lasso"] = {"class": Lasso, "params": {"alpha": 0.01, "max_iter": 10000}, "type": "linear"}
        models["ElasticNet"] = {"class": ElasticNet, "params": {"alpha": 0.01, "l1_ratio": 0.5, "max_iter": 10000}, "type": "linear"}
        models["KNN"] = {"class": KNeighborsRegressor, "params": {"n_neighbors": 5}, "type": "instance"}
        models["DecisionTree"] = {"class": DecisionTreeRegressor, "params": {"max_depth": 10, "random_state": 42}, "type": "tree"}
        models["RandomForest"] = {"class": RandomForestRegressor, "params": {"n_estimators": 200, "max_depth": 15, "random_state": 42, "n_jobs": -1}, "type": "ensemble"}
        models["GradientBoosting"] = {"class": GradientBoostingRegressor, "params": {"n_estimators": 200, "max_depth": 5, "random_state": 42}, "type": "ensemble"}
        models["ExtraTrees"] = {"class": ExtraTreesRegressor, "params": {"n_estimators": 200, "max_depth": 15, "random_state": 42, "n_jobs": -1}, "type": "ensemble"}

    if HAS_XGB:
        models["XGBoost"] = {"class": xgb.XGBRegressor, "params": {"n_estimators": 300, "max_depth": 6, "learning_rate": 0.1, "random_state": 42, "n_jobs": -1}, "type": "boosting"}

    if HAS_LGBM:
        models["LightGBM"] = {"class": lgb.LGBMRegressor, "params": {"n_estimators": 300, "max_depth": 6, "learning_rate": 0.1, "random_state": 42, "n_jobs": -1, "verbose": -1}, "type": "boosting"}

    if HAS_CATBOOST:
        models["CatBoost"] = {"class": CatBoostRegressor, "params": {"iterations": 300, "depth": 6, "learning_rate": 0.1, "random_state": 42, "verbose": 0}, "type": "boosting"}

    return models


def train_and_compare(X, y, target_names=None, test_fraction=0.2, random_state=42):
    """Train all available models and compare performance.

    Args:
        X: feature matrix (n_samples, n_features)
        y: target values (n_samples,) or (n_samples, n_targets)
        target_names: list of target property names
        test_fraction: fraction for test split
        random_state: random seed

    Returns:
        dict with:
          - results: list of {model, model_type, r2, rmse, mae, train_time}
          - best_model: name of best model by R²
          - best_r2: best R² score
          - trained_models: dict of {name: fitted model}
          - predictions: dict of {name: {y_test, y_pred}}
    """
    if not HAS_SKLEARN:
        return {"error": "scikit-learn not available"}

    # Handle multi-target
    if y.ndim == 1:
        y = y.reshape(-1, 1)
    n_targets = y.shape[1]
    if target_names is None:
        target_names = [f"Target_{i+1}" for i in range(n_targets)]

    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=test_fraction, random_state=random_state
    )

    all_models = get_all_models()
    results = []
    trained_models = {}
    predictions = {}

    for model_name, model_info in all_models.items():
        try:
            t0 = time.time()
            model_class = model_info["class"]
            params = model_info["params"]

            # PLS needs special handling (n_components can't exceed min(n_features, n_samples))
            if model_name == "PLS":
                max_comp = min(X_train.shape[0], X_train.shape[1], 10)
                params["n_components"] = min(params["n_components"], max_comp)

            model = model_class(**params)

            # Fit
            if model_name == "PLS":
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)
            else:
                if n_targets == 1:
                    model.fit(X_train, y_train.ravel())
                    y_pred = model.predict(X_test).reshape(-1, 1)
                else:
                    model.fit(X_train, y_train)
                    y_pred = model.predict(X_test)

            train_time = round(time.time() - t0, 2)

            # Metrics per target
            for t_idx in range(n_targets):
                yt = y_test[:, t_idx]
                yp = y_pred[:, t_idx] if y_pred.ndim > 1 else y_pred
                r2 = round(r2_score(yt, yp), 4)
                rmse = round(np.sqrt(mean_squared_error(yt, yp)), 4)
                mae = round(mean_absolute_error(yt, yp), 4)

                results.append({
                    "model": model_name,
                    "model_type": model_info["type"],
                    "target": target_names[t_idx],
                    "r2": r2,
                    "rmse": rmse,
                    "mae": mae,
                    "train_time": train_time,
                })

            trained_models[model_name] = model
            predictions[model_name] = {"y_test": y_test, "y_pred": y_pred}

        except Exception as e:
            log.warning(f"Model {model_name} failed: {e}")
            for t_idx in range(n_targets):
                results.append({
                    "model": model_name,
                    "model_type": model_info["type"],
                    "target": target_names[t_idx],
                    "r2": None, "rmse": None, "mae": None,
                    "train_time": None, "error": str(e)[:100],
                })

    # Find best model per target
    best_per_target = {}
    for t_name in target_names:
        t_results = [r for r in results if r["target"] == t_name and r["r2"] is not None]
        if t_results:
            best = max(t_results, key=lambda r: r["r2"])
            best_per_target[t_name] = {"model": best["model"], "r2": best["r2"], "rmse": best["rmse"]}

    return {
        "results": results,
        "best_per_target": best_per_target,
        "trained_models": trained_models,
        "predictions": predictions,
        "scaler": scaler,
        "n_models_tested": len(all_models),
        "n_targets": n_targets,
        "target_names": target_names,
    }


def get_feature_importance(model, model_name, feature_names=None, top_n=15):
    """Extract feature importance from a trained model.

    Returns list of {feature, importance} sorted by importance descending.
    """
    importance = None

    if model_name in ("RandomForest", "GradientBoosting", "ExtraTrees", "XGBoost", "LightGBM", "CatBoost"):
        importance = model.feature_importances_
    elif model_name in ("Ridge", "Lasso", "ElasticNet"):
        importance = np.abs(model.coef_)
        if importance.ndim > 1:
            importance = importance.mean(axis=0)
    elif model_name == "PLS":
        importance = np.abs(model.coef_)
        if importance.ndim > 1:
            importance = importance.mean(axis=0)
    elif model_name == "DecisionTree":
        importance = model.feature_importances_

    if importance is None:
        return []

    if feature_names is None:
        feature_names = [f"Feature_{i}" for i in range(len(importance))]

    pairs = sorted(zip(feature_names, importance), key=lambda x: x[1], reverse=True)
    return [{"feature": n, "importance": round(float(v), 6)} for n, v in pairs[:top_n]]
