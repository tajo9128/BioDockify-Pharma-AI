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


def _to_json_safe(obj):
    """Recursively convert numpy types to native Python types for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_json_safe(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return _to_json_safe(obj.tolist())
    if isinstance(obj, float):
        return float(obj)
    if isinstance(obj, bool):
        return bool(obj)
    if isinstance(obj, int):
        return int(obj)
    return obj


class StatisticsAuto(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "")

        if action == "health":
            return self._health()
        elif action == "analyze":
            return self._analyze(input)
        elif action == "auto_analyze":
            return self._auto_analyze(input)

        return {"actions": ["health", "analyze"], "hint": "Upload with action=analyze for AI column detection"}

    def _analyze(self, input: dict):
        """Step 2: AI analyzes file — classifies columns, recommends best test."""
        content = input.get("content", "")
        filename = input.get("filename", "data.csv")
        if not content:
            return {"status": "error", "error": "No file content provided"}

        rows, cols, err = _parse_content(content, filename)
        if err:
            return {"status": "error", "error": err}
        if not rows or not cols:
            return {"status": "error", "error": "No data parsed"}

        n_rows = len(rows)
        numeric, categorical, group_candidates = _classify_columns(rows, cols)

        # Check normality for recommendation
        normal_cols = []
        not_normal = []
        if HAS_SCIPY:
            for col in numeric:
                arr = _col_values(rows, col, cols)
                if len(arr) >= 8:
                    arr = arr[~np.isnan(arr)]
                    if len(arr) >= 8:
                        stat, p = scipy_stats.shapiro(arr[:min(5000, len(arr))])
                        if bool(p > 0.05): normal_cols.append(col)
                        else: not_normal.append(col)

        # AI decides best test
        recommended = "descriptive"
        rec_text = ""

        if group_candidates:
            group_col = group_candidates[0]
            gvals = set()
            for r in rows:
                v = str(r.get(group_col) or "").strip()
                if v: gvals.add(v)
            n_groups = len(gvals)

            # Detect paired
            id_col = None
            for c in categorical:
                if c not in group_candidates:
                    ids = set(str(r.get(c) or "") for r in rows if str(r.get(c) or "").strip())
                    if len(ids) > n_rows * 0.4:
                        id_col = c
                        break
            paired = False
            if id_col:
                gids = {}
                for r in rows:
                    g = str(r.get(group_col) or "")
                    pid = str(r.get(id_col) or "")
                    if g and pid: gids.setdefault(g, set()).add(pid)
                if len(gids) >= 2:
                    sets = list(gids.values())
                    common = sets[0]
                    for s in sets[1:]: common = common & s
                    paired = len(common) > min(len(s) for s in sets) * 0.6

            all_n = all(c in normal_cols for c in numeric if c != group_col)

            if paired:
                if n_groups == 2:
                    recommended = "ttest"
                    rec_text = f"AI detected PAIRED data (same subjects in both groups). 2 groups found in '{group_col}'. Recommend Paired T-Test. {'Data is normal — parametric test appropriate.' if all_n else 'Data may not be normal — consider Wilcoxon Signed Rank instead.'}"
                else:
                    recommended = "anova"
                    rec_text = f"AI detected PAIRED/REPEATED data with {n_groups} groups in '{group_col}'. Recommend Repeated Measures ANOVA. {'Data is normal.' if all_n else 'Consider Friedman test (non-parametric).'}"
            elif n_groups == 2:
                recommended = "ttest"
                rec_text = f"AI detected 2 independent groups in '{group_col}' ({', '.join(sorted(gvals))}). Recommend Independent T-Test. {'Data is normal — parametric test appropriate.' if all_n else 'Data may not be normal — consider Mann-Whitney U instead.'}"
            elif n_groups >= 3:
                recommended = "anova"
                rec_text = f"AI detected {n_groups} independent groups in '{group_col}'. Recommend One-Way ANOVA. {'Data is normal.' if all_n else 'Consider Kruskal-Wallis (non-parametric).'}"
        elif len(numeric) >= 2:
            recommended = "correlation"
            rec_text = f"AI detected {len(numeric)} numeric columns with no group variable. Recommend Correlation Analysis."
        elif len(numeric) == 1:
            recommended = "descriptive"
            rec_text = f"AI detected 1 numeric column ({numeric[0]}). Recommend Descriptive Statistics."
        elif categorical:
            recommended = "chisquare"
            rec_text = f"AI detected categorical data. Recommend Chi-Square test for association."

        return _to_json_safe({
            "status": "ok",
            "action": "analyze",
            "filename": filename,
            "data_summary": {
                "total_rows": n_rows,
                "total_columns": len(cols),
                "column_names": cols,
                "numeric_columns": numeric,
                "categorical_columns": categorical,
                "group_columns": group_candidates,
            },
            "recommended_test": recommended,
            "recommendation_text": rec_text,
            "normality": {c: (c in normal_cols) for c in numeric},
        })

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
            return _to_json_safe(report)

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

        # 4. Group comparisons — auto-detect test sub-type (paired, independent, two-way)
        paired = False
        two_way = False
        n_groups = 0
        if group_candidates and numeric:
            try:
                group_col = group_candidates[0]
                # Detect paired data: check if an ID column has overlapping IDs across groups
                id_col = None
                for c in categorical:
                    if c not in group_candidates:
                        raw = [str(r.get(c) or "") for r in rows]
                        unique_ids = len(set(v for v in raw if v.strip()))
                        if unique_ids > n_rows * 0.4:
                            id_col = c
                            break

                paired = False
                if id_col:
                    group_ids = {}
                    for r in rows:
                        g = str(r.get(group_col) or "")
                        pid = str(r.get(id_col) or "")
                        if g and pid:
                            group_ids.setdefault(g, set()).add(pid)
                    if len(group_ids) >= 2:
                        id_sets = list(group_ids.values())
                        common = id_sets[0]
                        for s in id_sets[1:]:
                            common = common & s
                        if id_sets and len(common) > min(len(s) for s in id_sets) * 0.6:
                            paired = True

                # Detect two-way possibility
                two_way = len(group_candidates) >= 2

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
                    n_groups = len(gnames)

                    if paired and n_groups == 2 and len(arrays[0]) == len(arrays[1]):
                        stat, p = scipy_stats.ttest_rel(arrays[0], arrays[1])
                        test_name = "Paired T-Test 🔗"
                        test_desc = f"Same subjects measured in both groups ({', '.join(gnames)}). Paired design detected — using Paired T-Test (ttest_rel) because measurements come from matched subjects (before/after or crossover)."
                        sub_type = "paired"
                    elif n_groups == 2:
                        stat, p = scipy_stats.ttest_ind(arrays[0], arrays[1])
                        test_name = "Independent T-Test"
                        test_desc = f"Compares '{value_col}' between 2 independent groups ({', '.join(gnames)}). Different subjects in each group — using Independent T-Test (ttest_ind)."
                        sub_type = "independent"
                    else:
                        stat, p = scipy_stats.f_oneway(*arrays)
                        if two_way and len(group_candidates) >= 2:
                            test_name = "One-Way ANOVA ⚠ Two-Way Possible"
                            test_desc = f"Running One-Way ANOVA on '{group_col}' ({n_groups} groups). Note: a second group column '{group_candidates[1]}' was detected. For Two-Way ANOVA (testing both factors simultaneously), use the Manual Test tab."
                            sub_type = "one_way_two_way_possible"
                        else:
                            test_name = "One-Way ANOVA"
                            test_desc = f"Compares '{value_col}' across {n_groups} independent groups. F-test determines if at least one group mean differs."
                            sub_type = "one_way"

                    gdesc = "; ".join(f"{g} (n={len(groups[g])}, x\u0304={round(np.mean(groups[g]),3)})" for g in gnames)
                    report["group_tests"][f"{value_col} ~ {group_col}"] = {
                        "test": test_name,
                        "statistic": round(float(stat), 4),
                        "p_value": round(float(p), 6),
                        "groups": {g: {"n": len(groups[g]), "mean": round(np.mean(groups[g]), 4)} for g in gnames},
                        "significant": bool(p < 0.05),
                        "paired": paired,
                        "sub_type": sub_type,
                    }
                    sig = bool(p < 0.05)
                    report["explanations"].append({
                        "step": 6, "title": test_name,
                        "detail": test_desc + f"\n\nStatistic={stat:.4f}, p={p:.6f}. " + ("SIGNIFICANT (p<0.05) \u2014 the difference between groups is statistically meaningful." if sig else "NOT significant (p\u22650.05) \u2014 no evidence of difference between groups.") + f"\n\nGroup summary: {gdesc}",
                        "significant": sig,
                        "findings": [gdesc],
                        "test_sub_type": sub_type
                    })
                    break
            except Exception as e:
                report["group_tests"]["_error"] = str(e)
        elif not group_candidates:
            report["explanations"].append({
                "step": 6, "title": "Group Comparison Skipped",
                "detail": "No group column detected (need 2-20 unique text/label values). If your data has groups (e.g., Drug vs Placebo), ensure the group column contains text labels, not numbers."
            })

        # 5. Generate recommendations
        recs = []
        if numeric:
            recs.append(f"Your dataset has {len(numeric)} numeric column(s): {', '.join(numeric)}.")
        if len(numeric) >= 2:
            recs.append(f"Correlation analysis available between {len(numeric)} columns. Check the correlation matrix.")
        if group_candidates:
            recs.append(f"Group column '{group_candidates[0]}' detected.")
            if paired:
                recs.append("Matching IDs across groups \u2014 paired/crossover design. Use Paired T-Test (2 groups) or Repeated Measures ANOVA (3+ groups).")
            elif n_groups == 2:
                recs.append(f"{n_groups} groups with independent subjects \u2014 Independent T-Test used.")
            else:
                recs.append(f"{n_groups} groups \u2014 One-Way ANOVA used.")
            if two_way and len(group_candidates) >= 2:
                recs.append(f"Two grouping columns detected: '{group_candidates[0]}' and '{group_candidates[1]}'. Use Two-Way ANOVA from Manual Test to analyze both simultaneously.")
        for col, n_test in report.get("normality", {}).items():
            if isinstance(n_test, dict) and not n_test.get("is_normal", True):
                recs.append(f"'{col}' is NOT normal \u2014 use non-parametric: Mann-Whitney U (2 groups), Kruskal-Wallis (3+), Spearman correlation.")
        all_normal = all(v.get("is_normal", False) for v in report.get("normality", {}).values() if isinstance(v, dict))
        if all_normal and numeric and group_candidates:
            if paired:
                recs.append("All data is normal and paired \u2714 Use Paired T-Test / Repeated Measures ANOVA.")
            else:
                recs.append("All data is normally distributed \u2714 Parametric tests (t-test, ANOVA, Pearson) are appropriate.")
        if not recs:
            recs.append("Data imported. Use the Manual Test tab to select a specific analysis.")
        report["recommendations"] = recs

        report["explanations"].append({
            "step": 7, "title": "Summary & Recommendations",
            "detail": "Based on the analysis above, here is what you should do next:",
            "findings": recs
        })

        return _to_json_safe(report)
