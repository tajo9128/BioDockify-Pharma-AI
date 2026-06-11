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
    group_candidates = []
    n = len(rows)

    for ci, col in enumerate(cols):
        raw_vals = [str(r.get(col)) if isinstance(r, dict) else str(r[ci]) if r[ci] is not None else "" for r in rows]
        float_vals = [_safe_float(v) for v in raw_vals]
        numeric_count = sum(1 for v in float_vals if v is not None)
        raw_unique = set(v for v in raw_vals if v and v.strip() and v != "nan")
        float_unique = set(v for v in float_vals if v is not None)
        n_unique = len(raw_unique) if raw_unique else len(float_unique)

        if numeric_count > n * 0.7 and len(float_unique) > 2:
            numeric.append(col)
        elif n_unique <= 20 and n_unique >= 2:
            group_candidates.append(col)
            categorical.append(col)
        elif numeric_count > 0:
            numeric.append(col)
        else:
            categorical.append(col)

    return numeric, categorical, group_candidates


def _col_values(rows, col, cols):
    """Extract numeric values for a column."""
    if not HAS_NUMPY:
        return []
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
                "numpy": HAS_NUMPY,
                "scipy": HAS_SCIPY,
                "statsmodels": HAS_STATSMODELS,
                "sklearn": HAS_SKLEARN,
                "pandas": HAS_PANDAS,
            },
            "missing": [p for p, ok in [("numpy", HAS_NUMPY), ("scipy", HAS_SCIPY), ("statsmodels", HAS_STATSMODELS), ("sklearn", HAS_SKLEARN), ("pandas", HAS_PANDAS)] if not ok],
            "ready": all([HAS_NUMPY, HAS_SCIPY, HAS_STATSMODELS, HAS_SKLEARN, HAS_PANDAS]),
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
            "explanations": [],
            "diagnostics": {
                "scipy": HAS_SCIPY,
                "statsmodels": HAS_STATSMODELS,
                "sklearn": HAS_SKLEARN,
                "pandas": HAS_PANDAS,
            },
        }

        # Step-by-step explanations for students and researchers
        report["explanations"].append({
            "step": 1, "title": "File Parsed",
            "detail": f"Successfully read {n_rows} rows and {len(cols)} columns from '{filename}'. Columns detected: {', '.join(cols)}."
        })
        report["explanations"].append({
            "step": 2, "title": "Column Classification",
            "detail": f"Numeric columns ({len(numeric)}): {', '.join(numeric) if numeric else 'none'}. Categorical columns ({len(categorical)}): {', '.join(categorical) if categorical else 'none'}. Potential group columns: {', '.join(group_candidates) if group_candidates else 'none detected'}."
        })

        if not HAS_SCIPY:
            report["error"] = "scipy not installed. Run: pip install scipy"
            return report

        # 1. Descriptive stats for all numeric columns
        desc_findings = []
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
                m = round(float(np.mean(arr)), 4)
                s = round(float(np.std(arr, ddof=1)), 4)
                sk = round(float(scipy_stats.skew(arr)), 4)
                desc_findings.append(f"'{col}': mean={m}, SD={s}, range [{round(float(np.min(arr)),4)}–{round(float(np.max(arr)),4)}], skew={sk}" + (" (normal)" if abs(sk)<1 else " (skewed)" if abs(sk)<2 else " (highly skewed)"))
        except Exception as e:
            report["descriptive"]["_error"] = str(e)

        report["explanations"].append({
            "step": 3, "title": "Descriptive Statistics",
            "detail": "Computed for all numeric columns. Key metrics explained: Mean = average value. Median = middle value (50th percentile, less affected by outliers). Std = standard deviation (spread of data—smaller means values are close together). Skewness = symmetry (0 = perfectly symmetric; >1 or <-1 suggests skew). Kurtosis = tail heaviness. Q25/Q75 = 25th and 75th percentiles (interquartile range).",
            "findings": desc_findings
        })

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
                    strong = []
                    for i in range(n):
                        for j in range(i+1, n):
                            if abs(corr[i,j]) > 0.7:
                                strong.append(f"{valid_cols[i]} vs {valid_cols[j]}: r={corr[i,j]:.3f} (p={pvals[i,j]:.4f})")
                    report["explanations"].append({
                        "step": 4, "title": "Pearson Correlation Matrix",
                        "detail": "Measures linear relationship between numeric columns. r ranges from -1 (perfect negative) to +1 (perfect positive). |r|>0.7 = strong, 0.4<|r|<0.7 = moderate, |r|<0.4 = weak. P-value <0.05 means the correlation is statistically significant (unlikely due to chance).",
                        "findings": strong if strong else ["No strong correlations found (|r|>0.7)"]
                    })
            except Exception as e:
                report["correlation"]["_error"] = str(e)
        else:
            report["explanations"].append({
                "step": 4, "title": "Correlation Skipped",
                "detail": "Need at least 2 numeric columns for correlation analysis."
            })

        # 3. Normality tests
        norm_findings = []
        try:
            for col in numeric:
                arr = _col_values(rows, col, cols)
                arr = arr[~np.isnan(arr)]
                if len(arr) < 8:
                    continue
                if len(arr) > 5000:
                    arr = arr[:5000]
                stat, p = scipy_stats.shapiro(arr[:(min(5000, len(arr)))])
                is_n = bool(p > 0.05)
                report["normality"][col] = {
                    "test": "Shapiro-Wilk",
                    "statistic": round(float(stat), 4),
                    "p_value": round(float(p), 6),
                    "is_normal": is_n,
                    "n": len(arr),
                }
                norm_findings.append(f"'{col}': Shapiro-Wilk p={p:.4f} → {'NORMAL ✓ (use parametric tests)' if is_n else 'NOT NORMAL ⚠ (consider non-parametric tests)'}")
        except Exception as e:
            report["normality"]["_error"] = str(e)

        report["explanations"].append({
            "step": 5, "title": "Normality Test (Shapiro-Wilk)",
            "detail": "Tests whether data follows a normal (bell-curve) distribution. Null hypothesis: data IS normally distributed. If p>0.05 → data is normal → use parametric tests (t-test, ANOVA, Pearson). If p≤0.05 → data is NOT normal → use non-parametric tests (Mann-Whitney, Kruskal-Wallis, Spearman). This is the most important check before choosing a statistical test.",
            "findings": norm_findings if norm_findings else ["Not enough data points (minimum 8 required per column)"]
        })

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
                            "significant": bool(p < 0.05),
                        }
                        gdesc = "; ".join(f"{g} (n={len(groups[g])}, mean={round(np.mean(groups[g]),4)})" for g in gnames)
                        report["explanations"].append({
                            "step": 6, "title": "Independent T-Test",
                            "detail": f"Compares means of '{value_col}' between 2 groups ({', '.join(gnames)}). Null hypothesis: there is NO difference between groups. T-statistic={stat:.4f}, p={p:.6f}. If p<0.05 → the groups ARE significantly different. If p≥0.05 → no evidence of difference. Group summary: {gdesc}. Note: T-test assumes normal distribution. Check Step 5 results to verify this assumption.",
                            "significant": bool(p < 0.05)
                        })
                    else:
                        stat, p = scipy_stats.f_oneway(*arrays)
                        report["group_tests"][f"{value_col} ~ {group_col}"] = {
                            "test": "One-Way ANOVA",
                            "statistic": round(float(stat), 4),
                            "p_value": round(float(p), 6),
                            "groups": {g: {"n": len(groups[g]), "mean": round(np.mean(groups[g]), 4)} for g in gnames},
                            "significant": bool(p < 0.05),
                        }
                        gdesc = "; ".join(f"{g} (n={len(groups[g])}, mean={round(np.mean(groups[g]),4)})" for g in gnames[:6])
                        report["explanations"].append({
                            "step": 6, "title": "One-Way ANOVA",
                            "detail": f"Compares means of '{value_col}' across {len(gnames)} groups. Null hypothesis: ALL group means are equal. F-statistic={stat:.4f}, p={p:.6f}. If p<0.05 → at least one group is significantly different from others. If p≥0.05 → no evidence of differences. Group summary: {gdesc}. Note: ANOVA assumes normality and equal variance. Check Step 5 for normality results.",
                            "significant": bool(p < 0.05)
                        })
                    break  # one group test is sufficient
            except Exception as e:
                report["group_tests"]["_error"] = str(e)
        elif not group_candidates:
            report["explanations"].append({
                "step": 6, "title": "Group Comparison Skipped",
                "detail": "No group/grouping column detected (need 2-20 unique text/label values). If your data has groups (e.g., Drug vs Placebo), ensure the group column contains text labels, not numbers."
            })

        # 5. Generate recommendations
        recs = []
        if numeric:
            recs.append(f"Your dataset has {len(numeric)} numeric column(s): {', '.join(numeric)}. Use these for parametric tests.")
        if len(numeric) >= 2:
            recs.append(f"Correlation analysis is available between {len(numeric)} numeric columns. Check the correlation matrix for relationships.")
        if group_candidates:
            recs.append(f"Group column '{group_candidates[0]}' detected with {len(set(str(r.get(group_candidates[0])) for r in rows if r.get(group_candidates[0]) and str(r.get(group_candidates[0])).strip()))} group(s). Run the appropriate test based on group count and normality.")
        for col, n_test in report.get("normality", {}).items():
            if isinstance(n_test, dict) and not n_test.get("is_normal", True):
                recs.append(f"'{col}' is NOT normally distributed. Use non-parametric alternatives: Mann-Whitney U (2 groups), Kruskal-Wallis (3+ groups), or Spearman correlation instead of Pearson.")
        all_normal = all(v.get("is_normal", False) for v in report.get("normality", {}).values() if isinstance(v, dict))
        if all_normal and numeric and group_candidates:
            recs.append("All numeric columns are normally distributed. Safe to use parametric tests (t-test for 2 groups, ANOVA for 3+ groups, Pearson correlation).")
        if not recs:
            recs.append("Data imported successfully. Use the Manual Test option to select a specific analysis.")
        report["recommendations"] = recs

        report["explanations"].append({
            "step": 7, "title": "Summary & Recommendations",
            "detail": "Based on the analysis above, here is what you should do next:",
            "findings": recs
        })

        return report
