"""Statistics Auto-Analyze API — upload file, auto-detect columns, run all applicable tests.
No user input required beyond uploading a file."""
from helpers.api import ApiHandler, Request, Response
import logging, io, csv, json, base64, traceback

log = logging.getLogger("statistics_auto")

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None

try:
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

try:
    import statsmodels.api as sm
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False

try:
    import sklearn
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


def _safe_float(v):
    try: return float(v)
    except: return None


def _parse_content(content, filename):
    """Parse file content into list-of-dicts rows + column names. Handles CSV, JSON, XLSX."""
    rows = []
    cols = []
    ext = (filename or "").lower()

    if ext.endswith(".json"):
        obj = json.loads(content)
        items = obj if isinstance(obj, list) else (obj.get("data", []) or list(obj.values())[0] if isinstance(obj, dict) else [])
        if items:
            cols = list(items[0].keys())
            rows = items

    elif ext.endswith((".xlsx", ".xls")):
        if HAS_PANDAS:
            try:
                df = pd.read_excel(io.BytesIO(base64.b64decode(content)))
            except:
                df = pd.read_excel(io.BytesIO(content.encode("latin1") if isinstance(content, str) else content))
            cols = list(df.columns)
            rows = df.to_dict("records")
        else:
            return None, None, "pandas not installed — cannot read Excel files"

    else:
        # CSV
        rows = [r for r in csv.DictReader(io.StringIO(content))]
        if rows:
            cols = list(rows[0].keys())
        else:
            return None, None, "No data rows found"

    return rows, cols, None


def _classify_columns(rows, cols):
    """Classify each column as numeric, categorical, or group."""
    numeric = []
    categorical = []
    group_candidates = []  # dichotomous or few unique values
    n = len(rows)

    for ci, col in enumerate(cols):
        vals = [_safe_float(r.get(col)) if isinstance(r, dict) else _safe_float(r[ci]) for r in rows]
        numeric_count = sum(1 for v in vals if v is not None)
        unique_vals = set(v for v in vals if v is not None)

        if numeric_count > n * 0.7 and len(unique_vals) > 2:
            numeric.append(col)
        elif len(unique_vals) <= 20 and len(unique_vals) >= 1:
            if len(unique_vals) == 2:
                group_candidates.append(col)
            categorical.append(col)
        elif numeric_count > 0:
            numeric.append(col)
        else:
            categorical.append(col)

    return numeric, categorical, group_candidates


def _col_values(rows, col, cols):
    """Extract numeric values for a column."""
    ci = cols.index(col) if col in cols else None
    if ci is None:
        return []
    vals = []
    for r in rows:
        v = r.get(col) if isinstance(r, dict) else r[ci]
        n = _safe_float(v)
        if n is not None:
            vals.append(n)
    return np.array(vals, dtype=float)


class StatisticsAuto(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "")

        if action == "health":
            return self._health()
        elif action == "auto_analyze":
            return self._auto_analyze(input)

        return {"actions": ["health", "auto_analyze"], "hint": "Upload a file with action=auto_analyze"}

    def _health(self):
        return {
            "status": "ok",
            "health": {
                "scipy": HAS_SCIPY,
                "statsmodels": HAS_STATSMODELS,
                "sklearn": HAS_SKLEARN,
                "pandas": HAS_PANDAS,
                "numpy": True,
            },
            "missing": [p for p, ok in [("scipy", HAS_SCIPY), ("statsmodels", HAS_STATSMODELS), ("sklearn", HAS_SKLEARN), ("pandas", HAS_PANDAS)] if not ok],
            "ready": all([HAS_SCIPY, HAS_STATSMODELS, HAS_SKLEARN, HAS_PANDAS]),
        }

    def _auto_analyze(self, input: dict):
        if not HAS_NUMPY:
            return {"status": "error", "error": "numpy not installed. Run: pip install numpy scipy pandas"}
        content = input.get("content", "")
        filename = input.get("filename", "data.csv")
        if not content:
            return {"status": "error", "error": "No file content provided"}

        # Parse
        rows, cols, err = _parse_content(content, filename)
        if err:
            return {"status": "error", "error": err}
        if not rows or not cols:
            return {"status": "error", "error": "No data parsed from file"}

        n_rows = len(rows)

        # Classify columns
        numeric, categorical, group_candidates = _classify_columns(rows, cols)

        report = {
            "status": "ok",
            "action": "auto_analyze",
            "filename": filename,
            "data_summary": {
                "total_rows": n_rows,
                "total_columns": len(cols),
                "column_names": cols,
                "numeric_columns": numeric,
                "categorical_columns": categorical,
                "group_columns": group_candidates,
            },
            "descriptive": {},
            "correlation": {},
            "normality": {},
            "group_tests": {},
            "recommendations": [],
            "diagnostics": {
                "scipy": HAS_SCIPY,
                "statsmodels": HAS_STATSMODELS,
                "sklearn": HAS_SKLEARN,
                "pandas": HAS_PANDAS,
            },
        }

        if not HAS_SCIPY:
            report["error"] = "scipy not installed. Run: pip install scipy"
            return report

        # 1. Descriptive stats for all numeric columns
        try:
            for col in numeric:
                arr = _col_values(rows, col, cols)
                if len(arr) < 2:
                    continue
                arr = arr[~np.isnan(arr)]
                if len(arr) < 2:
                    continue
                report["descriptive"][col] = {
                    "n": int(len(arr)),
                    "mean": round(float(np.mean(arr)), 4),
                    "median": round(float(np.median(arr)), 4),
                    "std": round(float(np.std(arr, ddof=1)), 4),
                    "min": round(float(np.min(arr)), 4),
                    "max": round(float(np.max(arr)), 4),
                    "q25": round(float(np.percentile(arr, 25)), 4),
                    "q75": round(float(np.percentile(arr, 75)), 4),
                    "skewness": round(float(scipy_stats.skew(arr)), 4),
                    "kurtosis": round(float(scipy_stats.kurtosis(arr)), 4),
                }
        except Exception as e:
            report["descriptive"]["_error"] = str(e)

        # 2. Correlation matrix (all numeric columns)
        if len(numeric) >= 2:
            try:
                arrs = []
                valid_cols = []
                for col in numeric:
                    a = _col_values(rows, col, cols)
                    a = a[~np.isnan(a)]
                    if len(a) > 2:
                        arrs.append(a)
                        valid_cols.append(col)
                min_len = min(len(a) for a in arrs) if arrs else 0
                if min_len > 2:
                    arrs = [a[:min_len] for a in arrs]
                    n = len(valid_cols)
                    corr = np.zeros((n, n))
                    pvals = np.zeros((n, n))
                    for i in range(n):
                        for j in range(n):
                            if i == j:
                                corr[i, j] = 1.0
                                pvals[i, j] = 0.0
                            else:
                                c, p = scipy_stats.pearsonr(arrs[i], arrs[j])
                                corr[i, j] = round(float(c), 4)
                                pvals[i, j] = round(float(p), 6)
                    report["correlation"] = {
                        "method": "pearson",
                        "columns": valid_cols,
                        "matrix": corr.tolist(),
                        "p_values": pvals.tolist(),
                    }
            except Exception as e:
                report["correlation"]["_error"] = str(e)

        # 3. Normality tests
        try:
            for col in numeric:
                arr = _col_values(rows, col, cols)
                arr = arr[~np.isnan(arr)]
                if len(arr) < 8:
                    continue
                if len(arr) > 5000:
                    arr = arr[:5000]
                stat, p = scipy_stats.shapiro(arr[:(min(5000, len(arr)))])
                report["normality"][col] = {
                    "test": "Shapiro-Wilk",
                    "statistic": round(float(stat), 4),
                    "p_value": round(float(p), 6),
                    "is_normal": p > 0.05,
                    "n": len(arr),
                }
        except Exception as e:
            report["normality"]["_error"] = str(e)

        # 4. Group comparisons (auto-detect T-Test / ANOVA)
        if group_candidates and numeric:
            try:
                group_col = group_candidates[0]
                for value_col in numeric:
                    if value_col == group_col:
                        continue
                    groups = {}
                    for r in rows:
                        g = str(r.get(group_col) if isinstance(r, dict) else r[cols.index(group_col)])
                        v = _safe_float(r.get(value_col) if isinstance(r, dict) else r[cols.index(value_col)])
                        if v is not None and g:
                            groups.setdefault(g, []).append(v)
                    if len(groups) < 2:
                        continue
                    gnames = sorted(groups.keys())
                    arrays = [groups[g] for g in gnames]
                    if len(gnames) == 2:
                        stat, p = scipy_stats.ttest_ind(arrays[0], arrays[1])
                        report["group_tests"][f"{value_col} ~ {group_col}"] = {
                            "test": "Independent T-Test",
                            "statistic": round(float(stat), 4),
                            "p_value": round(float(p), 6),
                            "groups": {g: {"n": len(groups[g]), "mean": round(np.mean(groups[g]), 4)} for g in gnames},
                            "significant": p < 0.05,
                        }
                    else:
                        stat, p = scipy_stats.f_oneway(*arrays)
                        report["group_tests"][f"{value_col} ~ {group_col}"] = {
                            "test": "One-Way ANOVA",
                            "statistic": round(float(stat), 4),
                            "p_value": round(float(p), 6),
                            "groups": {g: {"n": len(groups[g]), "mean": round(np.mean(groups[g]), 4)} for g in gnames},
                            "significant": p < 0.05,
                        }
                    break  # one group test is sufficient
            except Exception as e:
                report["group_tests"]["_error"] = str(e)

        # 5. Generate recommendations
        recs = []
        if numeric:
            recs.append(f"Descriptive statistics computed for {len(numeric)} numeric columns")
        if len(numeric) >= 2:
            recs.append(f"Pearson correlation available for {len(numeric)} columns")
        if group_candidates:
            recs.append(f"Group comparison possible with: {', '.join(group_candidates[:3])}")
        for col, n_test in report.get("normality", {}).items():
            if isinstance(n_test, dict) and not n_test.get("is_normal", True):
                recs.append(f"'{col}' is not normally distributed — consider non-parametric tests (Mann-Whitney, Kruskal-Wallis)")
        if not recs:
            recs.append("Data imported successfully. Run a specific test for detailed results.")
        report["recommendations"] = recs

        return report
