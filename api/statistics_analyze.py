"""Statistics Analysis API — unified endpoint for all statistical tests."""
from helpers.api import ApiHandler, Request, Response
import logging, numpy as np

log = logging.getLogger("statistics_analyze")

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


def _to_json_safe(obj):
    """Recursively convert numpy types to native Python types."""
    if isinstance(obj, dict):
        return {k: _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, np.ndarray)):
        return [_to_json_safe(v) for v in obj]
    if isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj


class StatisticsAnalyze(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        result = await self._dispatch(input)
        return _to_json_safe(result)

    async def _dispatch(self, input: dict) -> dict:
        action = input.get("action", "")

        if action == "auto_decide":
            return self._auto_decide(input)
        elif action == "descriptive":
            return self._descriptive(input)
        elif action == "correlation":
            return self._correlation(input)
        elif action == "ttest":
            return self._ttest(input)
        elif action == "anova":
            return self._anova(input)
        elif action == "chisquare":
            return self._chisquare(input)
        elif action == "mannwhitney":
            return self._mannwhitney(input)
        elif action == "wilcoxon":
            return self._wilcoxon(input)
        elif action == "kruskalwallis":
            return self._kruskalwallis(input)
        elif action == "friedman":
            return self._friedman(input)
        elif action == "fisher":
            return self._fisher(input)
        elif action == "normality":
            return self._normality(input)
        elif action == "homogeneity":
            return self._homogeneity(input)
        elif action == "roc":
            return self._roc(input)
        elif action == "power":
            return self._power(input)
        elif action == "survival":
            return self._survival(input)
        return {"error": f"Unknown action: {action}"}

    def _auto_decide(self, input: dict):
        """Step 3-6: AI decides sub-type, runs test, returns results with explanations."""
        test_type = input.get("test_type", "descriptive")
        columns = input.get("columns", [])
        summary = input.get("summary", {})
        group_cols = summary.get("group_columns", [])
        numeric_cols = summary.get("numeric_columns", [])
        categorical_cols = summary.get("categorical_columns", [])

        result = {"status": "ok", "test_type": test_type, "sub_type": "auto-decided"}
        exp = []

        try:
            if test_type == "ttest":
                gc = group_cols[0] if group_cols else ""
                nc = numeric_cols[0] if numeric_cols else columns[0] if len(columns) > 1 else ""
                input["group_col"] = gc
                input["value_col"] = nc
                input["test_type"] = "independent"
                input["equal_var"] = True
                exp.append({"step": 1, "title": "AI Decision", "detail": f"Running Independent T-Test: {nc} ~ {gc}", "findings": ["Comparing 2 independent groups. If data is paired (same subjects measured twice), results may differ."]})
                exp.append({"step": 2, "title": "Running Test", "detail": "Performing statistical computation..."})
                r = self._ttest(input)
                result.update(r)
                sig = r.get("significant", False)
                exp.append({"step": 3, "title": "Interpretation", "detail": f"p={r.get('p_value',0):.4f} — {'SIGNIFICANT — the groups differ' if sig else 'NOT significant — no evidence of difference between groups'}."})

            elif test_type == "anova":
                gc = group_cols[0] if group_cols else ""
                nc = numeric_cols[0] if numeric_cols else columns[0] if len(columns) > 1 else ""
                input["group_col"] = gc
                input["value_col"] = nc
                exp.append({"step": 1, "title": "AI Decision", "detail": f"Running One-Way ANOVA: {nc} ~ {gc}", "findings": [f"Comparing means across groups in '{gc}'."]})
                r = self._anova(input)
                result.update(r)
                sig = r.get("significant", False)
                exp.append({"step": 2, "title": "Interpretation", "detail": f"p={r.get('p_value',0):.4f} — {'SIGNIFICANT — at least one group differs' if sig else 'NOT significant — no group differences'}."})

            elif test_type == "correlation":
                input["selected_cols"] = numeric_cols[:10]
                input["method"] = "pearson"
                exp.append({"step": 1, "title": "Pearson Correlation", "detail": "Measures linear relationship between numeric columns. r ranges from -1 to +1."})
                r = self._correlation(input)
                result.update(r)
                if r.get("correlation_matrix"):
                    n = len(r.get("columns", []))
                    strong = []
                    for i in range(n):
                        for j in range(i+1, n):
                            if abs(r["correlation_matrix"][i][j]) > 0.7:
                                strong.append(f"{r['columns'][i]} vs {r['columns'][j]}: r={r['correlation_matrix'][i][j]:.3f}")
                    exp.append({"step": 2, "title": "Findings", "findings": strong if strong else ["No strong correlations (|r|>0.7) found."]})

            elif test_type == "descriptive":
                exp.append({"step": 1, "title": "Descriptive Statistics", "detail": "Summary statistics for numeric columns. Mean=average, Median=middle value, Std=spread."})
                r = self._descriptive(input)
                result.update(r)

            elif test_type == "normality":
                exp.append({"step": 1, "title": "Shapiro-Wilk Normality", "detail": "Tests if data follows normal distribution. p>0.05 = normal (use parametric tests). p<0.05 = not normal (use non-parametric tests)."})
                r = self._normality(input)
                result.update(r)

            elif test_type == "chisquare":
                gc = group_cols[0] if group_cols else ""
                vc = group_cols[1] if len(group_cols) > 1 else (categorical_cols[0] if categorical_cols else "")
                input["group_col"] = gc
                input["value_col"] = vc
                if not gc or not vc:
                    return {"status": "error", "error": "Need 2 categorical columns for Chi-Square"}
                exp.append({"step": 1, "title": "Chi-Square", "detail": "Tests association between categorical variables."})
                r = self._chisquare(input)
                result.update(r)
                sig = r.get("significant", False)
                exp.append({"step": 2, "title": "Interpretation", "detail": f"p={r.get('p_value',0):.4f} — {'SIGNIFICANT association' if sig else 'No significant association'}."})

            elif test_type == "mannwhitney":
                gc = group_cols[0] if group_cols else ""
                nc = numeric_cols[0] if numeric_cols else ""
                input["group_col"] = gc
                input["value_col"] = nc
                exp.append({"step": 1, "title": "Mann-Whitney U", "detail": "Non-parametric comparison of 2 groups. Use when data is not normally distributed."})
                r = self._mannwhitney(input)
                result.update(r)
                sig = r.get("significant", False)
                exp.append({"step": 2, "title": "Interpretation", "detail": f"p={r.get('p_value',0):.4f} — {'SIGNIFICANT difference' if sig else 'No significant difference'}."})

            elif test_type == "survival":
                exp.append({"step": 1, "title": "Survival Analysis", "detail": "Agent-driven — use chat to analyze survival data."})
                result["message"] = "Survival analysis requires agent chat. Type your request with the data attached."

            elif test_type == "regression":
                exp.append({"step": 1, "title": "Regression Analysis", "detail": "Agent-driven — use chat to run regression."})
                result["message"] = "Regression analysis requires agent chat. Type your request with the data attached."

            elif test_type == "roc":
                exp.append({"step": 1, "title": "ROC/AUC Analysis", "detail": "Agent-driven — use chat for ROC analysis."})
                result["message"] = "ROC analysis requires agent chat. Type your request with the data attached."

            elif test_type in ("factor", "cluster"):
                exp.append({"step": 1, "title": test_type.title() + " Analysis", "detail": "Agent-driven — use chat for this analysis."})
                result["message"] = f"{test_type.title()} analysis requires agent chat."

            else:
                return {"status": "error", "error": f"Test '{test_type}' not available"}

            if r.get("significant") is not None:
                result["test_name"] = (r.get("test") or test_type).replace("Independent T-Test", "T-Test").replace("One-Way ANOVA", "ANOVA")
                result["sub_type"] = r.get("test") or test_type

            # Merge metrics for display
            metrics = {}
            for k in ("statistic", "p_value", "n", "required_n", "auc", "odds_ratio"):
                if k in r: metrics[k] = r[k]
            if metrics: result["metrics"] = metrics

            result["explanations"] = exp
            return _to_json_safe(result)
        except Exception as e:
            return _to_json_safe({"status": "error", "error": str(e), "test_type": test_type})

    def _descriptive(self, input: dict) -> dict:
        data = input.get("data", [])
        columns = input.get("columns", [])
        if not data:
            return {"status": "error", "error": "No data loaded"}
        try:
            result = {}
            for ci, col in enumerate(columns):
                vals = [float(row[ci]) for row in data if ci < len(row) and isinstance(row[ci], (int, float)) or (ci < len(row) and str(row[ci]).replace('.','',1).replace('-','',1).isdigit())]
                if not vals:
                    continue
                arr = np.array(vals, dtype=float)
                arr = arr[~np.isnan(arr)]
                if len(arr) == 0:
                    continue
                from scipy import stats as scipy_stats
                result[col] = {
                    "n": int(len(arr)),
                    "mean": round(float(np.mean(arr)), 4),
                    "median": round(float(np.median(arr)), 4),
                    "std": round(float(np.std(arr, ddof=1)), 4),
                    "variance": round(float(np.var(arr, ddof=1)), 4),
                    "min": round(float(np.min(arr)), 4),
                    "max": round(float(np.max(arr)), 4),
                    "q25": round(float(np.percentile(arr, 25)), 4),
                    "q75": round(float(np.percentile(arr, 75)), 4),
                    "iqr": round(float(np.percentile(arr, 75) - np.percentile(arr, 25)), 4),
                    "skewness": round(float(scipy_stats.skew(arr)), 4),
                    "kurtosis": round(float(scipy_stats.kurtosis(arr)), 4),
                }
            return {"status": "ok", "action": "descriptive", "columns": result}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _correlation(self, input: dict) -> dict:
        data = input.get("data", [])
        columns = input.get("columns", [])
        method = input.get("method", "pearson")
        if len(columns) < 2:
            return {"status": "error", "error": "Select at least 2 columns"}
        try:
            from scipy import stats as scipy_stats
            # Extract columns as arrays
            col_arrays = []
            for ci in range(len(columns)):
                vals = []
                for row in data:
                    if ci < len(row) and isinstance(row[ci], (int, float)):
                        vals.append(float(row[ci]))
                col_arrays.append(np.array(vals, dtype=float))

            # Remove rows with NaN
            min_len = min(len(a) for a in col_arrays)
            col_arrays = [a[:min_len] for a in col_arrays]

            n_cols = len(columns)
            corr_matrix = np.zeros((n_cols, n_cols))
            p_matrix = np.zeros((n_cols, n_cols))

            for i in range(n_cols):
                for j in range(n_cols):
                    if i == j:
                        corr_matrix[i, j] = 1.0
                        p_matrix[i, j] = 0.0
                    else:
                        if method == "spearman":
                            corr, p = scipy_stats.spearmanr(col_arrays[i], col_arrays[j])
                        else:
                            corr, p = scipy_stats.pearsonr(col_arrays[i], col_arrays[j])
                        corr_matrix[i, j] = round(float(corr), 4)
                        p_matrix[i, j] = round(float(p), 4)

            return {
                "status": "ok", "action": "correlation",
                "columns": columns, "method": method,
                "correlation_matrix": corr_matrix.tolist(),
                "p_value_matrix": p_matrix.tolist(),
                "n_samples": min_len,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _ttest(self, input: dict) -> dict:
        group_col = input.get("group_col", "")
        value_col = input.get("value_col", "")
        test_type = input.get("test_type", "independent")
        equal_var = input.get("equal_var", True)
        data = input.get("data", [])
        columns = input.get("columns", [])
        if not group_col or not value_col:
            return {"status": "error", "error": "Select Group and Value columns"}
        try:
            from scipy import stats as scipy_stats
            group_idx = columns.index(group_col)
            val_idx = columns.index(value_col)
            groups = {}
            for row in data:
                g = str(row[group_idx]) if group_idx < len(row) else ""
                try:
                    v = float(row[val_idx])
                except (ValueError, TypeError):
                    continue
                if g:
                    groups.setdefault(g, []).append(v)

            group_names = sorted(groups.keys())
            if len(group_names) < 2:
                return {"status": "error", "error": "Need at least 2 groups"}

            if test_type == "independent":
                if len(group_names) == 2:
                    g1, g2 = groups[group_names[0]], groups[group_names[1]]
                    stat, p = scipy_stats.ttest_ind(g1, g2, equal_var=equal_var)
                    return {
                        "status": "ok", "action": "ttest_independent",
                        "test": "Independent T-Test", "statistic": round(float(stat), 4), "p_value": round(float(p), 6),
                        "group1": {"name": group_names[0], "n": len(g1), "mean": round(np.mean(g1), 4), "std": round(np.std(g1, ddof=1), 4)},
                        "group2": {"name": group_names[1], "n": len(g2), "mean": round(np.mean(g2), 4), "std": round(np.std(g2, ddof=1), 4)},
                        "significant": bool(p < 0.05),
                    }
                else:
                    # Multi-group → one-way ANOVA
                    arrays = [groups[g] for g in group_names]
                    stat, p = scipy_stats.f_oneway(*arrays)
                    return {"status": "ok", "action": "anova_one", "test": "One-way ANOVA (independent)", "statistic": round(float(stat), 4), "p_value": round(float(p), 6), "groups": [{"name": g, "n": len(groups[g]), "mean": round(np.mean(groups[g]), 4)} for g in group_names], "significant": bool(p < 0.05)}
            else:  # paired
                if len(group_names) != 2:
                    return {"status": "error", "error": "Paired test requires exactly 2 groups"}
                g1, g2 = groups[group_names[0]], groups[group_names[1]]
                if len(g1) != len(g2):
                    return {"status": "error", "error": "Paired test requires equal number of observations in each group"}
                stat, p = scipy_stats.ttest_rel(g1, g2)
                return {
                    "status": "ok", "action": "ttest_paired", "test": "Paired T-Test",
                    "statistic": round(float(stat), 4), "p_value": round(float(p), 6),
                    "group1": {"name": group_names[0], "n": len(g1), "mean": round(np.mean(g1), 4), "std": round(np.std(g1, ddof=1), 4)},
                    "group2": {"name": group_names[1], "n": len(g2), "mean": round(np.mean(g2), 4), "std": round(np.std(g2, ddof=1), 4)},
                    "significant": bool(p < 0.05),
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _anova(self, input: dict) -> dict:
        group_col = input.get("group_col", "")
        value_col = input.get("value_col", "")
        post_hoc = input.get("post_hoc", True)
        data = input.get("data", [])
        columns = input.get("columns", [])
        if not group_col or not value_col:
            return {"status": "error", "error": "Select Group and Value columns"}
        try:
            from scipy import stats as scipy_stats
            group_idx = columns.index(group_col)
            val_idx = columns.index(value_col)
            groups = {}
            for row in data:
                g = str(row[group_idx]) if group_idx < len(row) else ""
                try:
                    v = float(row[val_idx])
                except (ValueError, TypeError):
                    continue
                if g:
                    groups.setdefault(g, []).append(v)

            group_names = sorted(groups.keys())
            if len(group_names) < 2:
                return {"status": "error", "error": "Need at least 2 groups"}

            arrays = [groups[g] for g in group_names]
            stat, p = scipy_stats.f_oneway(*arrays)

            result = {
                "status": "ok", "action": "anova",
                "test": "One-way ANOVA",
                "statistic": round(float(stat), 4), "p_value": round(float(p), 6),
                "groups": [{"name": g, "n": len(groups[g]), "mean": round(np.mean(groups[g]), 4), "std": round(np.std(groups[g], ddof=1), 4)} for g in group_names],
                "significant": bool(p < 0.05),
            }

            if post_hoc and p < 0.05 and len(group_names) >= 2:
                # Tukey HSD post-hoc
                try:
                    from itertools import combinations
                    post_hoc_results = []
                    for i, j in combinations(range(len(group_names)), 2):
                        g1, g2 = arrays[i], arrays[j]
                        stat_t, p_t = scipy_stats.ttest_ind(g1, g2)
                        post_hoc_results.append({
                            "group1": group_names[i], "group2": group_names[j],
                            "statistic": round(float(stat_t), 4), "p_value": round(float(p_t), 6),
                            "significant": p_t < 0.05,
                        })
                    result["post_hoc"] = post_hoc_results
                except Exception:
                    pass

            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _chisquare(self, input: dict) -> dict:
        group_col = input.get("group_col", "")
        value_col = input.get("value_col", "")
        data = input.get("data", [])
        columns = input.get("columns", [])
        if not group_col or not value_col:
            return {"status": "error", "error": "Select Group and Value columns"}
        try:
            from scipy import stats as scipy_stats
            group_idx = columns.index(group_col)
            val_idx = columns.index(value_col)
            contingency = {}
            for row in data:
                g = str(row[group_idx]) if group_idx < len(row) else ""
                v = str(row[val_idx]) if val_idx < len(row) else ""
                if g and v:
                    contingency.setdefault(g, {})[v] = contingency.get(g, {}).get(v, 0) + 1

            row_labels = sorted(contingency.keys())
            col_labels = sorted(set(v for d in contingency.values() for v in d))
            table = [[contingency[r].get(c, 0) for c in col_labels] for r in row_labels]

            chi2, p, dof, expected = scipy_stats.chi2_contingency(table)
            return {
                "status": "ok", "action": "chisquare",
                "test": "Chi-Square Independence",
                "statistic": round(float(chi2), 4), "p_value": round(float(p), 6),
                "degrees_of_freedom": int(dof),
                "observed": table, "expected": expected.tolist(),
                "row_labels": row_labels, "col_labels": col_labels,
                "significant": bool(p < 0.05),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _mannwhitney(self, input: dict) -> dict:
        group_col = input.get("group_col", "")
        value_col = input.get("value_col", "")
        data = input.get("data", [])
        columns = input.get("columns", [])
        if not group_col or not value_col:
            return {"status": "error", "error": "Select Group and Value columns"}
        try:
            from scipy import stats as scipy_stats
            group_idx = columns.index(group_col)
            val_idx = columns.index(value_col)
            groups = {}
            for row in data:
                g = str(row[group_idx]) if group_idx < len(row) else ""
                try: v = float(row[val_idx])
                except: continue
                if g: groups.setdefault(g, []).append(v)
            names = sorted(groups.keys())
            if len(names) != 2:
                return {"status": "error", "error": "Mann-Whitney U requires exactly 2 groups"}
            stat, p = scipy_stats.mannwhitneyu(groups[names[0]], groups[names[1]], alternative='two-sided')
            return {"status": "ok", "action": "mannwhitney", "test": "Mann-Whitney U", "statistic": round(float(stat), 4), "p_value": round(float(p), 6), "group1": {"name": names[0], "n": len(groups[names[0]])}, "group2": {"name": names[1], "n": len(groups[names[1]])}, "significant": bool(p < 0.05)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _wilcoxon(self, input: dict) -> dict:
        group_col = input.get("group_col", "")
        value_col = input.get("value_col", "")
        data = input.get("data", [])
        columns = input.get("columns", [])
        if not group_col or not value_col:
            return {"status": "error", "error": "Select Group and Value columns"}
        try:
            from scipy import stats as scipy_stats
            group_idx = columns.index(group_col)
            val_idx = columns.index(value_col)
            groups = {}
            for row in data:
                g = str(row[group_idx]) if group_idx < len(row) else ""
                try: v = float(row[val_idx])
                except: continue
                if g: groups.setdefault(g, []).append(v)
            names = sorted(groups.keys())
            if len(names) != 2:
                return {"status": "error", "error": "Wilcoxon requires exactly 2 paired groups"}
            g1, g2 = groups[names[0]], groups[names[1]]
            if len(g1) != len(g2):
                return {"status": "error", "error": "Wilcoxon requires equal observations in each group"}
            stat, p = scipy_stats.wilcoxon(g1, g2)
            return {"status": "ok", "action": "wilcoxon", "test": "Wilcoxon Signed Rank", "statistic": round(float(stat), 4), "p_value": round(float(p), 6), "n": len(g1), "significant": bool(p < 0.05)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _kruskalwallis(self, input: dict) -> dict:
        group_col = input.get("group_col", "")
        value_col = input.get("value_col", "")
        data = input.get("data", [])
        columns = input.get("columns", [])
        if not group_col or not value_col:
            return {"status": "error", "error": "Select Group and Value columns"}
        try:
            from scipy import stats as scipy_stats
            group_idx = columns.index(group_col)
            val_idx = columns.index(value_col)
            groups = {}
            for row in data:
                g = str(row[group_idx]) if group_idx < len(row) else ""
                try: v = float(row[val_idx])
                except: continue
                if g: groups.setdefault(g, []).append(v)
            names = sorted(groups.keys())
            arrays = [groups[g] for g in names]
            stat, p = scipy_stats.kruskal(*arrays)
            return {"status": "ok", "action": "kruskalwallis", "test": "Kruskal-Wallis", "statistic": round(float(stat), 4), "p_value": round(float(p), 6), "groups": [{"name": g, "n": len(groups[g])} for g in names], "significant": bool(p < 0.05)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _friedman(self, input: dict) -> dict:
        data = input.get("data", [])
        columns = input.get("columns", [])
        if len(columns) < 3:
            return {"status": "error", "error": "Friedman requires at least 3 numeric columns"}
        try:
            from scipy import stats as scipy_stats
            arrays = []
            for ci in range(min(len(columns), 10)):
                vals = [float(row[ci]) for row in data if ci < len(row) and isinstance(row[ci], (int, float))]
                if len(vals) > 0:
                    arrays.append(vals[:200])
            if len(arrays) < 3:
                return {"status": "error", "error": "Need at least 3 columns with numeric data"}
            arrays = [np.array(a[:min(len(x) for x in arrays)]) for a in arrays]
            stat, p = scipy_stats.friedmanchisquare(*arrays)
            return {"status": "ok", "action": "friedman", "test": "Friedman", "statistic": round(float(stat), 4), "p_value": round(float(p), 6), "n_samples": len(arrays[0]), "significant": bool(p < 0.05)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _fisher(self, input: dict) -> dict:
        data = input.get("data", [])
        columns = input.get("columns", [])
        try:
            from scipy import stats as scipy_stats
            if len(columns) < 2:
                return {"status": "error", "error": "Need 2 categorical columns"}
            c1, c2 = 0, 1
            contingency = {}
            for row in data:
                a, b = str(row[c1]), str(row[c2])
                contingency.setdefault(a, {})[b] = contingency.get(a, {}).get(b, 0) + 1
            labels_r = sorted(contingency.keys())
            labels_c = sorted(set(v for d in contingency.values() for v in d))
            table = [[contingency[r].get(c, 0) for c in labels_c] for r in labels_r]
            if len(labels_r) == 2 and len(labels_c) == 2:
                oddsr, p = scipy_stats.fisher_exact(table)
                return {"status": "ok", "action": "fisher_exact", "test": "Fisher Exact", "odds_ratio": round(float(oddsr), 4), "p_value": round(float(p), 6), "table": table, "row_labels": labels_r, "col_labels": labels_c, "significant": bool(p < 0.05)}
            else:
                chi2, p, dof, expected = scipy_stats.chi2_contingency(table)
                return {"status": "ok", "action": "chi_square", "test": "Chi-Square (Fisher fallback)", "statistic": round(float(chi2), 4), "p_value": round(float(p), 6), "significant": bool(p < 0.05)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _normality(self, input: dict) -> dict:
        data = input.get("data", [])
        columns = input.get("columns", [])
        try:
            from scipy import stats as scipy_stats
            results = {}
            for ci, col in enumerate(columns):
                vals = [float(row[ci]) for row in data if ci < len(row) and isinstance(row[ci], (int, float))]
                if len(vals) < 8:
                    continue
                arr = np.array(vals)
                if len(arr) > 5000:
                    stat, p = scipy_stats.kstest(arr, 'norm', args=(arr.mean(), arr.std()))
                    test = "Kolmogorov-Smirnov"
                else:
                    stat, p = scipy_stats.shapiro(arr[:5000])
                    test = "Shapiro-Wilk"
                results[col] = {"test": test, "statistic": round(float(stat), 4), "p_value": round(float(p), 6), "normal": bool(p > 0.05), "n": len(arr)}
            return {"status": "ok", "action": "normality", "results": results}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _homogeneity(self, input: dict) -> dict:
        group_col = input.get("group_col", "")
        value_col = input.get("value_col", "")
        data = input.get("data", [])
        columns = input.get("columns", [])
        if not group_col or not value_col:
            return {"status": "error", "error": "Select Group and Value columns"}
        try:
            from scipy import stats as scipy_stats
            group_idx = columns.index(group_col)
            val_idx = columns.index(value_col)
            groups = {}
            for row in data:
                g = str(row[group_idx]) if group_idx < len(row) else ""
                try: v = float(row[val_idx])
                except: continue
                if g: groups.setdefault(g, []).append(v)
            arrays = [groups[g] for g in sorted(groups.keys())]
            stat, p = scipy_stats.levene(*arrays)
            return {"status": "ok", "action": "homogeneity", "test": "Levene", "statistic": round(float(stat), 4), "p_value": round(float(p), 6), "homogeneous": bool(p > 0.05), "n_groups": len(arrays)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _roc(self, input: dict) -> dict:
        y_true = input.get("y_true", [])
        y_score = input.get("y_score", [])
        if not y_true or not y_score:
            return {"status": "error", "error": "Provide y_true and y_score arrays"}
        try:
            from sklearn.metrics import roc_curve, auc
            yt = np.array(y_true, dtype=float)
            ys = np.array(y_score, dtype=float)
            mask = ~(np.isnan(yt) | np.isnan(ys))
            yt, ys = yt[mask], ys[mask]
            if len(yt) < 5 or len(np.unique(yt)) < 2:
                return {"status": "error", "error": "Need at least 5 observations with both classes present"}
            fpr, tpr, thresholds = roc_curve(yt, ys)
            auc_val = round(float(auc(fpr, tpr)), 4)
            youden = tpr - fpr
            best_idx = int(np.argmax(youden))
            return {"status": "ok", "action": "roc", "auc": auc_val, "optimal_cutoff": round(float(thresholds[best_idx]), 4), "fpr": [round(float(x), 4) for x in fpr[:100]], "tpr": [round(float(x), 4) for x in tpr[:100]], "n_pos": int(np.sum(yt == 1)), "n_neg": int(np.sum(yt == 0))}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _power(self, input: dict) -> dict:
        effect_size = float(input.get("effect_size", 0.5))
        alpha = float(input.get("alpha", 0.05))
        power = float(input.get("power", 0.80))
        test_type = input.get("test_type", "ttest_ind")
        try:
            from statsmodels.stats.power import TTestIndPower
            power_analysis = TTestIndPower()
            n = power_analysis.solve_power(effect_size=effect_size, alpha=alpha, power=power, alternative='two-sided')
            return {"status": "ok", "action": "power", "test": test_type, "effect_size": effect_size, "alpha": alpha, "power": power, "required_n": int(np.ceil(n))}
        except Exception as e:
            return {"status": "error", "error": str(e)}
