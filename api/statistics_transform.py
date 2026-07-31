"""Data Transformation API — compute, recode, rank, normalize, handle missing values."""
from helpers.api import ApiHandler, Request, Response
import logging, io, base64, numpy as np

log = logging.getLogger("statistics_transform")

try:
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


def _safe_numeric(values):
    """Extract numeric values from mixed data."""
    result = []
    for v in values:
        try:
            result.append(float(v) if v is not None and str(v).strip() else np.nan)
        except (ValueError, TypeError):
            result.append(np.nan)
    return np.array(result, dtype=float)


def _compute_variable(data, formula, columns):
    """Compute a new variable from an expression like 'col_a + col_b * 2'.

    Uses a safe evaluator — only arithmetic on column arrays is allowed.
    No imports, no attribute access, no function calls beyond np.*.
    """
    try:
        env = {}
        for i, col in enumerate(columns):
            if i < data.shape[1]:
                env[col] = data[:, i]
        for i in range(data.shape[1]):
            env[f"col_{i}"] = data[:, i]
        # Allow only safe numpy operations
        safe_np = {
            "abs": np.abs, "log": np.log, "log10": np.log10, "sqrt": np.sqrt,
            "sin": np.sin, "cos": np.cos, "tan": np.tan, "exp": np.exp,
            "where": np.where, "clip": np.clip, "nan": np.nan,
            "mean": np.mean, "std": np.std, "min": np.min, "max": np.max,
        }
        env.update(safe_np)
        # Use compile+eval with restricted builtins — no imports, no getattr
        code = compile(formula, "<formula>", "eval")
        # Disallow attribute access (prevents np.__class__.__bases__ etc.)
        for node in __import__('ast').walk(code):
            if isinstance(node, __import__('ast').Attribute):
                return {"error": "Attribute access not allowed in formulas. Use column names and numpy functions (abs, log, sqrt, etc.)."}
        result = eval(code, {"__builtins__": {}}, env)
        return np.asarray(result, dtype=float).tolist()
    except Exception as e:
        return {"error": f"Formula evaluation failed: {e}"}


def _recode_variable(values, mapping, default=None):
    """Recode values: mapping = [{"from": 1, "to": 10}, {"from": [2,3], "to": 20}], or {"old": "new"}."""
    result = []
    vals = _safe_numeric(values)
    for v in vals:
        if np.isnan(v):
            result.append(default)
            continue
        found = False
        for rule in (mapping if isinstance(mapping, list) else [mapping]):
            fr = rule.get("from")
            to = rule.get("to")
            if isinstance(fr, list):
                if v in fr:
                    result.append(to); found = True; break
            elif fr is not None and v == fr:
                result.append(to); found = True; break
        if not found:
            result.append(default if default is not None else v)
    return result


def _rank_cases(values, method="average"):
    """Rank values. Methods: average, min, max, dense, ordinal."""
    vals = _safe_numeric(values)
    mask = ~np.isnan(vals)
    ranks = np.full(len(vals), np.nan)
    if HAS_SCIPY and np.any(mask):
        ranks[mask] = scipy_stats.rankdata(vals[mask], method=method)
    else:
        # Simple ordinal ranking
        order = np.argsort(vals[mask])
        ranks[np.where(mask)[0][order]] = np.arange(1, mask.sum() + 1)
    return ranks.tolist()


def _replace_missing(values, method="mean"):
    """Replace missing (NaN) values with mean/median/mode/interpolate."""
    vals = _safe_numeric(values)
    mask = np.isnan(vals)
    if not np.any(mask):
        return vals.tolist()

    filled = vals.copy()
    if method == "mean":
        filled[mask] = np.nanmean(vals)
    elif method == "median":
        filled[mask] = np.nanmedian(vals)
    elif method == "mode":
        from scipy import stats as sp_stats
        mode_result = sp_stats.mode(vals[~mask], keepdims=True)
        filled[mask] = mode_result.mode[0]
    elif method == "min":
        filled[mask] = np.nanmin(vals)
    elif method == "max":
        filled[mask] = np.nanmax(vals)
    elif method == "interpolate":
        # Linear interpolation
        idx = np.arange(len(vals))
        filled = np.interp(idx, idx[~mask], vals[~mask])
    elif method == "zero":
        filled[mask] = 0.0
    elif method == "drop":
        return vals[~mask].tolist()
    return filled.tolist()


def _standardize(values, method="zscore"):
    """Standardize/normalize values: zscore, minmax, robust."""
    vals = _safe_numeric(values)
    mask = ~np.isnan(vals)
    result = np.full(len(vals), np.nan)
    clean = vals[mask]
    if len(clean) < 2:
        return vals.tolist()

    if method == "zscore":
        result[mask] = (clean - np.mean(clean)) / np.std(clean, ddof=1)
    elif method == "minmax":
        mn, mx = np.min(clean), np.max(clean)
        if mx > mn:
            result[mask] = (clean - mn) / (mx - mn)
        else:
            result[mask] = 0.0
    elif method == "robust":
        med = np.median(clean)
        iqr = np.percentile(clean, 75) - np.percentile(clean, 25)
        if iqr > 0:
            result[mask] = (clean - med) / iqr
        else:
            result[mask] = 0.0
    elif method == "center":
        result[mask] = clean - np.mean(clean)
    return result.tolist()


def _select_cases(data, condition, columns):
    """Filter rows matching a condition like 'col_a > 5'."""
    try:
        env = {}
        for i, col in enumerate(columns):
            if i < data.shape[1]:
                env[col] = data[:, i]
        for i in range(data.shape[1]):
            env[f"col_{i}"] = data[:, i]
        env["np"] = np
        mask = eval(condition, {"__builtins__": {}}, {**env, "np": np})
        mask_arr = np.asarray(mask, dtype=bool)
        selected = data[mask_arr]
        return {
            "rows_before": int(data.shape[0]),
            "rows_after": int(selected.shape[0]),
            "rows_removed": int(data.shape[0] - selected.shape[0]),
            "data": selected.tolist(),
        }
    except Exception as e:
        return {"error": f"Condition evaluation failed: {e}"}


class StatisticsTransform(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "compute")

        values = input.get("values", [])
        columns = input.get("columns", [])
        data_arr = np.array(input.get("data", []), dtype=float) if input.get("data") else None

        if action == "compute":
            if data_arr is None:
                return {"error": "data array required (2D: rows × columns)"}
            result = _compute_variable(data_arr, input.get("formula", ""), columns)
            if isinstance(result, dict):
                return result
            return {"success": True, "action": "compute", "result": result, "formula": input.get("formula", "")}

        if action == "recode":
            result = _recode_variable(values, input.get("mapping", {}), input.get("default"))
            return {"success": True, "action": "recode", "result": result}

        if action == "rank":
            result = _rank_cases(values, input.get("method", "average"))
            return {"success": True, "action": "rank", "result": result, "method": input.get("method", "average")}

        if action == "fill_missing":
            result = _replace_missing(values, input.get("method", "mean"))
            return {"success": True, "action": "fill_missing", "result": result, "method": input.get("method", "mean"), "original_nan_count": int(np.isnan(_safe_numeric(values)).sum()) if values else 0}

        if action == "standardize":
            result = _standardize(values, input.get("method", "zscore"))
            return {"success": True, "action": "standardize", "result": result, "method": input.get("method", "zscore")}

        if action == "select_cases":
            if data_arr is None:
                return {"error": "data array required (2D: rows × columns)"}
            result = _select_cases(data_arr, input.get("condition", ""), columns)
            return {"success": True, "action": "select_cases", **result} if "error" not in result else result

        if action == "methods":
            return {
                "compute": {"description": "Create new variable from formula", "example": "col_0 + col_1 * 2"},
                "recode": {"description": "Map old values to new values", "example": '[{"from": 1, "to": 10}]'},
                "rank": {"description": "Rank values", "methods": ["average", "min", "max", "dense", "ordinal"]},
                "fill_missing": {"description": "Replace missing values", "methods": ["mean", "median", "mode", "min", "max", "interpolate", "zero", "drop"]},
                "standardize": {"description": "Normalize/standardize values", "methods": ["zscore", "minmax", "robust", "center"]},
                "select_cases": {"description": "Filter rows by condition", "example": "col_0 > 5"},
            }

        return {"error": f"Unknown action: {action}. Available: compute, recode, rank, fill_missing, standardize, select_cases, methods"}
