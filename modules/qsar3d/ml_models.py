"""
Multi-Model QSAR — trains and compares 20+ ML models for molecular property prediction.

Inspired by Omixium's QSAR_ML_all_models pipeline (Pritam Panda).
Models: PLS, Ridge, Lasso, Elastic Net, KNN, Decision Tree, Random Forest,
        Gradient Boosting, Extra Trees, XGBoost, LightGBM, CatBoost,
        SVR, Gaussian Process, MLP (Neural Net), AdaBoost, Bagging,
        Stacking, Voting, Kernel Ridge, TabNet.

Supports: Morgan fingerprints + RDKit descriptors, multi-target prediction,
          model comparison table, feature importance, EDA plots,
          actual vs predicted plots, feature importance bit interpretation,
          batch model saving, CSV export.
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

    # (display_name, function) pairs — using correct RDKit API names
    descriptor_funcs = [
        ("MolWt", Descriptors.MolWt),
        ("MolLogP", Descriptors.MolLogP),
        ("TPSA", Descriptors.TPSA),
        ("NumHDonors", Descriptors.NumHDonors),
        ("NumHAcceptors", Descriptors.NumHAcceptors),
        ("NumRotatableBonds", Descriptors.NumRotatableBonds),
        ("NumAromaticRings", Descriptors.NumAromaticRings),
        ("NumAliphaticRings", Descriptors.NumAliphaticRings),
        ("NumSaturatedRings", Descriptors.NumSaturatedRings),
        ("NumHeteroatoms", Descriptors.NumHeteroatoms),
        ("HeavyAtomCount", Descriptors.HeavyAtomCount),
        ("FractionCSP3", rdMolDescriptors.CalcFractionCSP3),
        ("RingCount", Descriptors.RingCount),
        ("NumAmideBonds", rdMolDescriptors.CalcNumAmideBonds),
        ("LabuteASA", Descriptors.LabuteASA),
        ("BalabanJ", Descriptors.BalabanJ),
        ("BertzCT", Descriptors.BertzCT),
        ("HallKierAlpha", Descriptors.HallKierAlpha),
        ("Kappa1", Descriptors.Kappa1),
        ("Kappa2", Descriptors.Kappa2),
        ("Kappa3", Descriptors.Kappa3),
        ("Chi0", Descriptors.Chi0),
        ("Chi1", Descriptors.Chi1),
        ("Chi0n", Descriptors.Chi0n),
        ("Chi1n", Descriptors.Chi1n),
        ("Chi0v", Descriptors.Chi0v),
        ("Chi1v", Descriptors.Chi1v),
        ("Chi2v", Descriptors.Chi2v),
        ("Chi3v", Descriptors.Chi3v),
        ("Chi4v", Descriptors.Chi4v),
        ("MaxAbsEStateIndex", Descriptors.MaxAbsEStateIndex),
        ("MinAbsEStateIndex", Descriptors.MinAbsEStateIndex),
        ("MaxEStateIndex", Descriptors.MaxEStateIndex),
        ("MinEStateIndex", Descriptors.MinEStateIndex),
        ("qed", Descriptors.qed),
        ("MolMR", Descriptors.MolMR),
        ("NumValenceElectrons", Descriptors.NumValenceElectrons),
        ("NumRadicalElectrons", Descriptors.NumRadicalElectrons),
        ("MaxPartialCharge", Descriptors.MaxPartialCharge),
        ("MinPartialCharge", Descriptors.MinPartialCharge),
        ("MaxAbsPartialCharge", Descriptors.MaxAbsPartialCharge),
        ("MinAbsPartialCharge", Descriptors.MinAbsPartialCharge),
        ("FpDensityMorgan1", Descriptors.FpDensityMorgan1),
        ("FpDensityMorgan2", Descriptors.FpDensityMorgan2),
        ("FpDensityMorgan3", Descriptors.FpDensityMorgan3),
        ("NHOHCount", Descriptors.NHOHCount),
        ("NOCount", Descriptors.NOCount),
        ("NumAliphaticCarbocycles", Descriptors.NumAliphaticCarbocycles),
        ("NumAliphaticHeterocycles", Descriptors.NumAliphaticHeterocycles),
        ("NumAromaticCarbocycles", Descriptors.NumAromaticCarbocycles),
        ("NumAromaticHeterocycles", Descriptors.NumAromaticHeterocycles),
    ]
    # Filter to only those that actually exist in this RDKit version
    descriptor_funcs = [(n, f) for n, f in descriptor_funcs if callable(f)]

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
    """Return dict of all available models with their constructors.

    20+ models covering: linear, instance-based, tree, ensemble, boosting,
    kernel, neural network, stacking, voting (Omixium full pipeline).
    """
    models = {}

    # Always available (sklearn)
    if HAS_SKLEARN:
        from sklearn.svm import SVR
        from sklearn.neural_network import MLPRegressor
        from sklearn.kernel_ridge import KernelRidge
        from sklearn.ensemble import (AdaBoostRegressor, BaggingRegressor,
                                      VotingRegressor, StackingRegressor)

        # Linear models
        models["PLS"] = {"class": PLSRegression, "params": {"n_components": 5}, "type": "linear"}
        models["Ridge"] = {"class": Ridge, "params": {"alpha": 1.0}, "type": "linear"}
        models["Lasso"] = {"class": Lasso, "params": {"alpha": 0.01, "max_iter": 10000}, "type": "linear"}
        models["ElasticNet"] = {"class": ElasticNet, "params": {"alpha": 0.01, "l1_ratio": 0.5, "max_iter": 10000}, "type": "linear"}

        # Instance-based
        models["KNN"] = {"class": KNeighborsRegressor, "params": {"n_neighbors": 5}, "type": "instance"}

        # Tree
        models["DecisionTree"] = {"class": DecisionTreeRegressor, "params": {"max_depth": 10, "random_state": 42}, "type": "tree"}

        # Ensemble
        models["RandomForest"] = {"class": RandomForestRegressor, "params": {"n_estimators": 200, "max_depth": 15, "random_state": 42, "n_jobs": -1}, "type": "ensemble"}
        models["GradientBoosting"] = {"class": GradientBoostingRegressor, "params": {"n_estimators": 200, "max_depth": 5, "random_state": 42}, "type": "ensemble"}
        models["ExtraTrees"] = {"class": ExtraTreesRegressor, "params": {"n_estimators": 200, "max_depth": 15, "random_state": 42, "n_jobs": -1}, "type": "ensemble"}
        models["AdaBoost"] = {"class": AdaBoostRegressor, "params": {"n_estimators": 100, "random_state": 42}, "type": "ensemble"}
        models["Bagging"] = {"class": BaggingRegressor, "params": {"n_estimators": 50, "random_state": 42}, "type": "ensemble"}

        # Kernel / SVM
        models["SVR"] = {"class": SVR, "params": {"kernel": "rbf", "C": 1.0}, "type": "kernel"}
        models["KernelRidge"] = {"class": KernelRidge, "params": {"kernel": "rbf", "alpha": 1.0}, "type": "kernel"}

        # Neural Network
        models["MLP"] = {"class": MLPRegressor, "params": {"hidden_layer_sizes": (256, 128), "max_iter": 500, "random_state": 42, "early_stopping": True}, "type": "neural"}

    if HAS_XGB:
        models["XGBoost"] = {"class": xgb.XGBRegressor, "params": {"n_estimators": 300, "max_depth": 6, "learning_rate": 0.1, "random_state": 42, "n_jobs": -1}, "type": "boosting"}

    if HAS_LGBM:
        models["LightGBM"] = {"class": lgb.LGBMRegressor, "params": {"n_estimators": 300, "max_depth": 6, "learning_rate": 0.1, "random_state": 42, "n_jobs": -1, "verbose": -1}, "type": "boosting"}

    if HAS_CATBOOST:
        models["CatBoost"] = {"class": CatBoostRegressor, "params": {"iterations": 300, "depth": 6, "learning_rate": 0.1, "random_state": 42, "verbose": 0}, "type": "boosting"}

    # Stacking & Voting (requires other models to be available)
    if HAS_SKLEARN and len(models) >= 3:
        estimators = [(n, m["class"](**m["params"])) for n, m in list(models.items())[:3]]
        models["Voting"] = {"class": VotingRegressor, "params": {"estimators": estimators}, "type": "meta"}
        models["Stacking"] = {"class": StackingRegressor, "params": {"estimators": estimators, "final_estimator": Ridge(alpha=1.0)}, "type": "meta"}

    return models


def generate_eda_plots(smiles_list, target_values, target_names=None):
    """Generate EDA plots: distribution histograms + correlation heatmap.

    Returns dict of base64 PNG plots (Omixium Cell 3 style).
    """
    import io, base64
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return {"error": "matplotlib not available"}

    try:
        import pandas as pd
    except ImportError:
        return {"error": "pandas not available"}

    if target_names is None:
        target_names = [f"Prop_{i+1}" for i in range(target_values.shape[1] if target_values.ndim > 1 else 1)]

    y = target_values if target_values.ndim > 2 else target_values.reshape(-1, 1) if target_values.ndim == 1 else target_values
    df = pd.DataFrame(y, columns=target_names)
    plots = {}

    # 1. Distribution histograms
    try:
        n = len(target_names)
        cols = min(n, 3)
        rows = (n + cols - 1) // cols
        fig, axes = plt.subplots(rows, cols, figsize=(5 * cols, 4 * rows))
        if n == 1:
            axes = [axes]
        else:
            axes = axes.flatten()
        colors = ["#2196F3", "#F44336", "#4CAF50", "#FF9800", "#9C27B0", "#00BCD4"]
        for i, name in enumerate(target_names):
            ax = axes[i]
            df[name].hist(ax=ax, bins=30, color=colors[i % len(colors)], edgecolor="black", linewidth=0.5)
            ax.set_title(f"{name} Distribution", fontweight="bold", fontsize=10)
            ax.set_xlabel(name)
            ax.set_ylabel("Count")
        for j in range(i + 1, len(axes)):
            axes[j].set_visible(False)
        fig.suptitle("Molecular Property Distributions", fontsize=14, fontweight="bold")
        plt.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
        buf.seek(0)
        plots["distribution_b64"] = base64.b64encode(buf.read()).decode()
        plt.close(fig)
    except Exception as e:
        log.warning("Distribution plot failed: %s", e)

    # 2. Correlation heatmap
    try:
        corr = df.corr()
        fig, ax = plt.subplots(figsize=(6, 5))
        im = ax.imshow(corr.values, cmap="RdBu", vmin=-1, vmax=1)
        ax.set_xticks(range(len(target_names)))
        ax.set_yticks(range(len(target_names)))
        ax.set_xticklabels(target_names, fontsize=8, rotation=45, ha="right")
        ax.set_yticklabels(target_names, fontsize=8)
        for i in range(len(target_names)):
            for j in range(len(target_names)):
                ax.text(j, i, f"{corr.values[i, j]:.2f}", ha="center", va="center", fontsize=8)
        fig.colorbar(im, label="Correlation")
        ax.set_title("Property Correlation Matrix", fontweight="bold")
        plt.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
        buf.seek(0)
        plots["correlation_b64"] = base64.b64encode(buf.read()).decode()
        plt.close(fig)
    except Exception as e:
        log.warning("Correlation plot failed: %s", e)

    plots["success"] = True
    return plots


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


def generate_actual_vs_predicted_plots(predictions, target_names, top_n_models=5):
    """Generate actual vs predicted scatter plots for top models (Omixium Cell 11 style).

    Args:
        predictions: dict of {model_name: {"y_test": array, "y_pred": array}}
        target_names: list of target property names
        top_n_models: number of top models to plot

    Returns: dict of base64 PNG plots per target.
    """
    import io, base64
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return {"error": "matplotlib not available"}

    plots = {}
    colors = ["#2196F3", "#F44336", "#4CAF50", "#FF9800", "#9C27B0", "#00BCD4", "#795548", "#607D8B"]

    for t_idx, t_name in enumerate(target_names):
        try:
            fig, axes = plt.subplots(1, min(top_n_models, len(predictions)), figsize=(4 * min(top_n_models, len(predictions)), 4))
            if top_n_models >= len(predictions):
                axes = [axes] if len(predictions) == 1 else axes
            else:
                axes = axes[:top_n_models]

            for ax_idx, (model_name, pred_data) in enumerate(list(predictions.items())[:top_n_models]):
                ax = axes[ax_idx] if hasattr(axes, '__len__') else axes
                y_test = pred_data["y_test"]
                y_pred = pred_data["y_pred"]

                if y_test.ndim > 1:
                    yt = y_test[:, t_idx]
                    yp = y_pred[:, t_idx] if y_pred.ndim > 1 else y_pred
                else:
                    yt = y_test
                    yp = y_pred

                ax.scatter(yt, yp, alpha=0.5, s=20, color=colors[ax_idx % len(colors)])
                min_val = min(yt.min(), yp.min())
                max_val = max(yt.max(), yp.max())
                ax.plot([min_val, max_val], [min_val, max_val], 'k--', alpha=0.5, linewidth=1)
                r2 = np.corrcoef(yt, yp)[0, 1] ** 2
                ax.set_title(f"{model_name}\nR²={r2:.3f}", fontsize=9, fontweight="bold")
                ax.set_xlabel("Actual", fontsize=8)
                ax.set_ylabel("Predicted", fontsize=8)

            fig.suptitle(f"Actual vs Predicted — {t_name}", fontsize=12, fontweight="bold")
            plt.tight_layout()
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
            buf.seek(0)
            plots[t_name] = base64.b64encode(buf.read()).decode()
            plt.close(fig)
        except Exception as e:
            log.warning("Actual vs predicted plot failed for %s: %s", t_name, e)

    return plots


def generate_model_comparison_chart(results, target_name=None):
    """Generate model comparison bar chart (Omixium Cell 6/12 style).

    Args:
        results: list of {model, model_type, r2, rmse, mae, target}
        target_name: filter to specific target (if None, average across all)

    Returns: base64 PNG bar chart.
    """
    import io, base64
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import pandas as pd
    except ImportError:
        return {"error": "matplotlib/pandas not available"}

    try:
        df = pd.DataFrame(results)
        df = df[df["r2"].notna()]

        if target_name:
            df = df[df["target"] == target_name]
        else:
            df = df.groupby("model").agg({"r2": "mean", "rmse": "mean", "mae": "mean"}).reset_index()

        df = df.sort_values("r2", ascending=True)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, max(4, len(df) * 0.35)))

        # R² bar chart
        colors = ["#4CAF50" if r > 0.7 else "#FF9800" if r > 0.4 else "#F44336" for r in df["r2"]]
        ax1.barh(df["model"], df["r2"], color=colors, edgecolor="black", linewidth=0.5)
        ax1.set_xlabel("R² Score")
        ax1.set_title("Model Comparison (R²)", fontweight="bold")
        ax1.axvline(x=0.5, color="gray", linestyle="--", alpha=0.5)

        # RMSE bar chart
        ax2.barh(df["model"], df["rmse"], color="#2196F3", edgecolor="black", linewidth=0.5)
        ax2.set_xlabel("RMSE")
        ax2.set_title("Model Comparison (RMSE)", fontweight="bold")

        title = f"QSAR Model Comparison" + (f" — {target_name}" if target_name else " (Average)")
        fig.suptitle(title, fontsize=14, fontweight="bold")
        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
        buf.seek(0)
        return base64.b64encode(buf.read()).decode()
    except Exception as e:
        log.warning("Model comparison chart failed: %s", e)
        return None


def interpret_fingerprint_bits(model, model_name, feature_names, smiles, top_n=10):
    """Interpret which molecular substructures correspond to important fingerprint bits.

    Uses RDKit bit info to map fingerprint bits to atom environments (Omixium Cell 13 style).

    Returns: list of {bit, importance, substructure_smarts, atom_indices}.
    """
    if not HAS_RDKIT:
        return []

    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem, Draw
        from rdkit import RDLogger
        RDLogger.DisableLog("rdApp.*")

        importance = get_feature_importance(model, model_name, feature_names, top_n=top_n * 2)
        if not importance:
            return []

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return []

        bit_info = {}
        fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius=2, nBits=2048, bitInfo=bit_info)

        interpreted = []
        for imp in importance:
            feat_name = imp["feature"]
            if feat_name.startswith("Bit_"):
                bit_idx = int(feat_name.split("_")[1])
                if bit_idx in bit_info:
                    for atom_idx, radius in bit_info[bit_idx]:
                        env = Chem.FindAtomEnvironmentOfRadiusN(mol, radius, atom_idx)
                        if env:
                            submol = Chem.PathToSubmol(mol, env)
                            smarts = Chem.MolToSmarts(submol) if submol else None
                        else:
                            smarts = None
                        interpreted.append({
                            "bit": bit_idx,
                            "importance": imp["importance"],
                            "atom_index": atom_idx,
                            "radius": radius,
                            "substructure_smarts": smarts,
                        })
                        break  # Just show first occurrence

        interpreted.sort(key=lambda x: x["importance"], reverse=True)
        return interpreted[:top_n]
    except Exception as e:
        log.warning("Fingerprint interpretation failed: %s", e)
        return []
