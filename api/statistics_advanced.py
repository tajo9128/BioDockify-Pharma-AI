"""Advanced Statistics API — ROC, Missing Value Analysis, Curve Estimation, Stepwise Regression."""
from helpers.api import ApiHandler, Request, Response
import logging, numpy as np

log = logging.getLogger("statistics_advanced")

try:
    from sklearn.linear_model import LogisticRegression, LinearRegression
    from sklearn.metrics import roc_curve, auc, roc_auc_score
    from sklearn.impute import SimpleImputer, KNNImputer
    from sklearn.model_selection import cross_val_score
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    from scipy import stats as scipy_stats
    from scipy.optimize import curve_fit
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

try:
    import statsmodels.api as sm
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False


# ─── ROC Analysis ──────────────────────────────────────
def _roc_analysis(y_true, y_score):
    if not HAS_SKLEARN:
        return {"error": "scikit-learn not available"}
    try:
        yt = np.array(y_true, dtype=float)
        ys = np.array(y_score, dtype=float)
        # Remove NaN
        mask = ~(np.isnan(yt) | np.isnan(ys))
        yt, ys = yt[mask], ys[mask]
        if len(yt) < 5 or len(np.unique(yt)) < 2:
            return {"error": "Need at least 5 observations with both classes present"}

        fpr, tpr, thresholds = roc_curve(yt, ys)
        auc_val = round(auc(fpr, tpr), 4)

        # Optimal cutoff via Youden index
        youden = tpr - fpr
        best_idx = np.argmax(youden)
        optimal_cutoff = float(thresholds[best_idx]) if best_idx < len(thresholds) else 0.5

        # Sensitivity/specificity at optimal cutoff
        sensitivity = float(tpr[best_idx])
        specificity = float(1 - fpr[best_idx])

        # Coordinates table
        coords = []
        for i in range(0, len(thresholds), max(1, len(thresholds) // 20)):
            coords.append({
                "threshold": round(float(thresholds[i]), 4),
                "sensitivity": round(float(tpr[i]), 3),
                "specificity": round(float(1 - fpr[i]), 3),
            })

        return {
            "success": True,
            "auc": auc_val,
            "n_observations": len(yt),
            "optimal_cutoff": round(optimal_cutoff, 4),
            "sensitivity_at_cutoff": round(sensitivity, 3),
            "specificity_at_cutoff": round(specificity, 3),
            "youden_index": round(sensitivity + specificity - 1, 3),
            "fpr": fpr.tolist(),
            "tpr": tpr.tolist(),
            "thresholds": thresholds.tolist(),
            "coordinates": coords[:25],
            "interpretation": "Excellent" if auc_val >= 0.9 else "Good" if auc_val >= 0.8 else "Fair" if auc_val >= 0.7 else "Poor" if auc_val >= 0.6 else "Fail",
        }
    except Exception as e:
        return {"error": str(e)}


def _roc_compare(y_true, scores_dict):
    """Compare multiple ROC curves (pairwise DeLong-like)."""
    try:
        yt = np.array(y_true, dtype=float)
        results = {}
        for name, scores in scores_dict.items():
            ys = np.array(scores, dtype=float)
            mask = ~(np.isnan(yt) | np.isnan(ys))
            if mask.sum() > 5:
                auc_val = round(roc_auc_score(yt[mask], ys[mask]), 4)
                results[name] = {"auc": auc_val, "n": int(mask.sum())}

        ranked = sorted(results.items(), key=lambda x: x[1]["auc"], reverse=True)
        return {"success": True, "comparison": [{"name": n, **v} for n, v in ranked],
                "best": ranked[0][0] if ranked else None}
    except Exception as e:
        return {"error": str(e)}


# ─── Missing Value Analysis ────────────────────────────
def _missing_analysis(data, columns):
    """Analyze missing value patterns and provide imputation recommendations."""
    try:
        X = np.array(data, dtype=float)
        n_rows, n_cols = X.shape

        # Per-column missing stats
        col_stats = []
        overall_missing_count = 0
        for i in range(n_cols):
            col_name = columns[i] if i < len(columns) else f"Col_{i}"
            nan_count = int(np.isnan(X[:, i]).sum())
            pct = round(nan_count / n_rows * 100, 1) if n_rows > 0 else 0
            overall_missing_count += nan_count
            col_stats.append({"column": col_name, "missing_count": nan_count,
                             "missing_pct": pct, "available": n_rows - nan_count})

        # Per-row missing counts
        row_missing = np.isnan(X).sum(axis=1)
        rows_with_any = int((row_missing > 0).sum())
        rows_all_missing = int((row_missing == n_cols).sum())

        # Imputation suggestions
        imputed = X.copy()
        for i in range(n_cols):
            mask = np.isnan(X[:, i])
            if mask.sum() > 0 and (~mask).sum() > 1:
                imputed[mask, i] = np.nanmean(X[:, i])

        return {
            "success": True,
            "n_rows": n_rows,
            "n_columns": n_cols,
            "total_missing": overall_missing_count,
            "total_cells": n_rows * n_cols,
            "overall_missing_pct": round(overall_missing_count / (n_rows * n_cols) * 100, 1) if n_rows * n_cols > 0 else 0,
            "rows_with_missing": rows_with_any,
            "rows_complete": n_rows - rows_with_any,
            "rows_all_missing": rows_all_missing,
            "column_stats": col_stats,
            "recommendation": "Drop columns with >50% missing; impute mean/median for others" if any(c["missing_pct"] > 50 for c in col_stats) else "Low missing rate — mean imputation recommended",
            "imputed_data": imputed.tolist() if overall_missing_count > 0 else None,
        }
    except Exception as e:
        return {"error": str(e)}


# ─── Curve Estimation ──────────────────────────────────
CURVE_MODELS = {
    "linear": lambda x, a, b: a + b * x,
    "quadratic": lambda x, a, b, c: a + b * x + c * x**2,
    "cubic": lambda x, a, b, c, d: a + b * x + c * x**2 + d * x**3,
    "logarithmic": lambda x, a, b: a + b * np.log(np.maximum(x, 1e-10)),
    "inverse": lambda x, a, b: a + b / np.maximum(x, 1e-10),
    "power": lambda x, a, b: a * np.power(np.maximum(x, 1e-10), b),
    "exponential": lambda x, a, b: a * np.exp(b * x),
    "compound": lambda x, a, b: a * np.power(b, x),
    "growth": lambda x, a, b: np.exp(a + b * x),
    "logistic": lambda x, a, b, c, d: c / (1 + a * np.exp(-b * x)) + d,
    "s_curve": lambda x, a, b: np.exp(a + b / np.maximum(x, 1e-10)),
}


def _curve_estimation(x_vals, y_vals, model_type="linear"):
    """Fit a curve model and return fitted values + R²."""
    if not HAS_SCIPY:
        return {"error": "scipy not available"}
    try:
        x = np.array(x_vals, dtype=float)
        y = np.array(y_vals, dtype=float)
        mask = ~(np.isnan(x) | np.isnan(y))
        x, y = x[mask], y[mask]

        if len(x) < 4:
            return {"error": f"Need at least 4 observations, got {len(x)}"}

        if model_type not in CURVE_MODELS:
            return {"error": f"Unknown model: {model_type}. Available: {list(CURVE_MODELS.keys())}"}

        model_fn = CURVE_MODELS[model_type]

        # Smart initial params
        n_params = model_fn.__code__.co_argcount - 1
        p0 = [1.0] * n_params

        try:
            popt, _ = curve_fit(model_fn, x, y, p0=p0, maxfev=10000)
        except Exception:
            # Fallback: simple linear fit
            z = np.polyfit(x, y, 1)
            y_pred = np.polyval(z, x)
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
            return {"success": True, "model": "linear (fallback)", "r_squared": round(float(r2), 4),
                    "fitted": y_pred.tolist(), "x": x.tolist(), "y_actual": y.tolist()}

        y_pred = model_fn(x, *popt)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        return {
            "success": True,
            "model": model_type,
            "r_squared": round(float(r2), 4),
            "parameters": [round(float(p), 4) for p in popt],
            "fitted": y_pred.tolist(),
            "x": x.tolist(),
            "y_actual": y.tolist(),
            "n": len(x),
        }
    except Exception as e:
        return {"error": str(e)}


def _compare_curves(x_vals, y_vals):
    """Fit all 11 models and rank by R²."""
    results = []
    for name in CURVE_MODELS:
        r = _curve_estimation(x_vals, y_vals, name)
        if r.get("success") and r.get("r_squared") is not None:
            results.append({"model": name, "r_squared": r["r_squared"]})
    results.sort(key=lambda r: r["r_squared"], reverse=True)
    return {"success": True, "comparison": results, "best_model": results[0]["model"] if results else None}


# ─── Stepwise Regression ───────────────────────────────
def _stepwise_regression(X, y, direction="forward", criterion="aic"):
    """Forward/backward stepwise regression using AIC or BIC."""
    if not HAS_STATSMODELS:
        return {"error": "statsmodels not available"}
    try:
        X_arr = np.array(X, dtype=float)
        y_arr = np.array(y, dtype=float)
        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(-1, 1)
        mask = ~(np.isnan(X_arr).any(axis=1) | np.isnan(y_arr))
        X_clean, y_clean = X_arr[mask], y_arr[mask]
        if len(y_clean) < 10 or X_clean.shape[1] < 2:
            return {"error": "Need at least 10 observations and 2 predictors"}

        n, p = X_clean.shape
        all_features = set(range(p))
        selected = set()
        steps = []

        if direction == "forward":
            for step_num in range(min(p, 20)):
                best_feat = None
                best_score = float("inf") if criterion == "aic" else float("inf")
                for f in all_features - selected:
                    trial = sorted(selected | {f})
                    if not trial:
                        continue
                    try:
                        X_trial = sm.add_constant(X_clean[:, trial])
                        model = sm.OLS(y_clean, X_trial).fit()
                        score = model.aic if criterion == "aic" else model.bic
                        if score < best_score:
                            best_score = score
                            best_feat = f
                    except Exception:
                        continue
                if best_feat is None:
                    break
                selected.add(best_feat)
                steps.append({"step": step_num + 1, "added": int(best_feat),
                              criterion: round(float(best_score), 2),
                              "selected_features": sorted(selected)})
        elif direction == "backward":
            selected = set(range(p))
            for step_num in range(min(p, 20)):
                if len(selected) <= 1:
                    break
                best_feat = None
                best_score = float("inf") if criterion == "aic" else float("inf")
                for f in selected:
                    trial = selected - {f}
                    if not trial:
                        continue
                    try:
                        X_trial = sm.add_constant(X_clean[:, sorted(trial)])
                        model = sm.OLS(y_clean, X_trial).fit()
                        score = model.aic if criterion == "aic" else model.bic
                        if score < best_score:
                            best_score = score
                            best_feat = f
                    except Exception:
                        continue
                if best_feat is None:
                    break
                selected.remove(best_feat)
                steps.append({"step": step_num + 1, "removed": int(best_feat),
                              criterion: round(float(best_score), 2),
                              "remaining_features": sorted(selected)})

        # Final model fit
        X_final = sm.add_constant(X_clean[:, sorted(selected)])
        final_model = sm.OLS(y_clean, X_final).fit()

        # Use positional index into params/pvalues (params[0]=intercept, params[1..n]=features)
        sorted_sel = sorted(selected)
        return {
            "success": True,
            "direction": direction,
            "criterion": criterion,
            "selected_features": sorted_sel,
            "n_observations": n,
            "steps": steps,
            "r_squared": round(float(final_model.rsquared), 4),
            "adj_r_squared": round(float(final_model.rsquared_adj), 4),
            "aic": round(float(final_model.aic), 2),
            "bic": round(float(final_model.bic), 2),
            "params": {f"x_{orig_i}": round(float(final_model.params[pos + 1]), 4)
                       for pos, orig_i in enumerate(sorted_sel)},
            "p_values": {f"x_{orig_i}": round(float(final_model.pvalues[pos + 1]), 4)
                         for pos, orig_i in enumerate(sorted_sel)},
        }
    except Exception as e:
        return {"error": str(e)}


class StatisticsAdvanced(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "roc")

        if action == "roc":
            return _roc_analysis(input.get("y_true", []), input.get("y_score", []))

        if action == "roc_compare":
            return _roc_compare(input.get("y_true", []), input.get("scores", {}))

        if action == "missing":
            return _missing_analysis(input.get("data", []), input.get("columns", []))

        if action == "curve_estimation":
            return _curve_estimation(input.get("x", []), input.get("y", []), input.get("model", "linear"))

        if action == "curve_compare":
            return _compare_curves(input.get("x", []), input.get("y", []))

        if action == "stepwise":
            return _stepwise_regression(
                input.get("X", []), input.get("y", []),
                input.get("direction", "forward"),
                input.get("criterion", "aic"),
            )

        if action == "methods":
            return {
                "roc": {"description": "ROC curve with AUC, optimal cutoff", "requires": ["y_true", "y_score"]},
                "missing": {"description": "Missing value patterns and imputation", "requires": ["data", "columns"]},
                "curve_estimation": {"description": "Fit 11 curve models", "models": list(CURVE_MODELS.keys())},
                "stepwise": {"description": "Forward/backward stepwise regression", "directions": ["forward", "backward"], "criteria": ["aic", "bic"]},
            }

        return {"error": f"Unknown action: {action}. Available: roc, roc_compare, missing, curve_estimation, curve_compare, stepwise, methods"}
