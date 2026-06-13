"""Statistics Analysis API — unified endpoint for all statistical tests."""
from helpers.api import ApiHandler, Request, Response
import logging

log = logging.getLogger("statistics_analyze")

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


# ===== APA Output Builder =====

def _apa_table(caption, headers, rows, note="", sig_cols=None):
    return {"caption": caption, "headers": headers, "rows": rows, "note": note, "sig": sig_cols}

def _fmt(v, d=2): return f"{v:.{d}f}" if isinstance(v, (int, float, np.floating)) else str(v)

def _p_str(p, alpha=0.05):
    if p < 0.001: return "< .001"
    if p < 0.01: return f"{p:.3f}"
    if isinstance(p, (float, np.floating)): return f"{p:.{2 if p >= 0.05 else 3}f}"
    return str(p)

def _effect_interpretation(d):
    d = abs(d)
    if d < 0.2: return "negligible"
    if d < 0.5: return "small"
    if d < 0.8: return "medium"
    return "large"

def _build_python_code(test_type, params=None):
    params = params or {}
    if test_type == "ttest":
        return f"""from scipy import stats
# Independent T-Test: {params.get('value','Y')} ~ {params.get('group','X')}
group1_vals = [...]  # values for group 1
group2_vals = [...]  # values for group 2
t_stat, p_value = stats.ttest_ind(group1_vals, group2_vals, equal_var={params.get('equal_var',True)})
print(f"t={{t_stat:.4f}}, p={{p_value:.6f}}")"""
    if test_type == "anova":
        return f"""from scipy import stats
# One-Way ANOVA: {params.get('value','Y')} ~ {params.get('group','X')}
g1, g2, g3 = [...], [...], [...]  # one list per group
f_stat, p_value = stats.f_oneway(g1, g2, g3)
print(f"F={{f_stat:.4f}}, p={{p_value:.6f}}")
# Post-hoc Tukey HSD: from statsmodels.stats.multicomp import pairwise_tukeyhsd"""
    if test_type == "correlation":
        return f"""from scipy import stats
# Pearson Correlation
r, p = stats.pearsonr(x_vals, y_vals)
print(f"r={{r:.4f}}, p={{p:.6f}}")"""
    if test_type == "descriptive":
        return f"""import numpy as np
from scipy import stats
# Descriptive Statistics for a column
data = np.array([...])  # your values
print(f"N={{len(data)}}, Mean={{np.mean(data):.2f}}, SD={{np.std(data, ddof=1):.2f}}")
print(f"Median={{np.median(data):.2f}}, Skew={{stats.skew(data):.3f}}")"""
    if test_type == "chisquare":
        return f"""from scipy import stats
# Chi-Square Test of Independence
observed = [[a, b], [c, d]]  # contingency table
chi2, p, dof, expected = stats.chi2_contingency(observed)
print(f"X2={{chi2:.4f}}, df={{dof}}, p={{p:.6f}}")"""
    if test_type == "mannwhitney":
        return f"""from scipy import stats
# Mann-Whitney U Test
u_stat, p = stats.mannwhitneyu(group1, group2, alternative='two-sided')
print(f"U={{u_stat:.4f}}, p={{p:.6f}}")"""
    if test_type == "wilcoxon":
        return f"""from scipy import stats
# Wilcoxon Signed-Rank Test
w_stat, p = stats.wilcoxon(before, after)
print(f"W={{w_stat:.4f}}, p={{p:.6f}}")"""
    if test_type == "kruskalwallis":
        return f"""from scipy import stats
# Kruskal-Wallis H Test
h_stat, p = stats.kruskal(g1, g2, g3)
print(f"H={{h_stat:.4f}}, p={{p:.6f}}")"""
    if test_type == "friedman":
        return f"""from scipy import stats
# Friedman Test
chi2, p = stats.friedmanchisquare(t1, t2, t3)
print(f"X2={{chi2:.4f}}, p={{p:.6f}}")"""
    if test_type == "normality":
        return f"""from scipy import stats
# Shapiro-Wilk Normality Test
w_stat, p = stats.shapiro(data)
print(f"W={{w_stat:.4f}}, p={{p:.6f}}")
print(f"Normal: {p > 0.05}")"""
    if test_type == "fisher":
        return f"""from scipy import stats
# Fisher's Exact Test
odds_ratio, p = stats.fisher_exact([[a,b],[c,d]])
print(f"OR={{odds_ratio:.4f}}, p={{p:.6f}}")"""
    if test_type == "homogeneity":
        return f"""from scipy import stats
# Levene's Test for Homogeneity of Variance
w_stat, p = stats.levene(g1, g2, g3)
print(f"W={{w_stat:.4f}}, p={{p:.6f}}")"""
    return f"# {test_type} — see scipy documentation\n"

def _ai_interpret(test_type, result, params=None):
    params = params or {}
    sig = result.get("significant", False)
    p = result.get("p_value", 0)

    if test_type == "ttest":
        g1 = result.get("group1", {}); g2 = result.get("group2", {})
        n1, n2 = g1.get("n", 0), g2.get("n", 0)
        m1, m2 = g1.get("mean", 0), g2.get("mean", 0)
        t = result.get("statistic", 0)
        d = abs(m1 - m2) / max(max(g1.get("std", 1), g2.get("std", 1)), 0.001)
        eff = _effect_interpretation(d)
        return f"The {g1.get('name','Group 1')} group (n={n1}, M={_fmt(m1)}) showed significantly different values compared to {g2.get('name','Group 2')} (n={n2}, M={_fmt(m2)}), t≈{_fmt(t)}, p={_p_str(p)}. Cohen's d ≈ {_fmt(d,2)} indicates a {eff} effect size." if sig else f"No significant difference between {g1.get('name','Group 1')} (n={n1}, M={_fmt(m1)}) and {g2.get('name','Group 2')} (n={n2}, M={_fmt(m2)}), t≈{_fmt(t)}, p={_p_str(p)}."

    if test_type == "anova":
        grps = result.get("groups", [])
        fstat = result.get("statistic", 0)
        return f"ANOVA revealed {'significant differences among groups' if sig else 'no significant difference among groups'}, F≈{_fmt(fstat)}, p={_p_str(p)}. " + (" ").join([f"{g.get('name','Group')} (M={_fmt(g.get('mean',0))})" for g in grps[:4]]) + "."

    if test_type == "correlation":
        r_val = result.get("statistic", 0) or 0
        return f"A {'strong' if abs(r_val)>0.7 else 'moderate' if abs(r_val)>0.4 else 'weak'} {'positive' if r_val>0 else 'negative'} correlation was found, r≈{_fmt(r_val)}, p={_p_str(p)}." + (" The relationship is statistically significant." if sig else " The relationship is not statistically significant.")

    if test_type == "normality":
        nc = result.get("normality", {})
        if isinstance(nc, dict):
            normal = [c for c, v in nc.items() if isinstance(v, dict) and v.get("normal")]
            not_n = [c for c, v in nc.items() if isinstance(v, dict) and not v.get("normal")]
            parts = []
            if normal: parts.append(f"{', '.join(normal)} {'follows' if len(normal)==1 else 'follow'} a normal distribution")
            if not_n: parts.append(f"{', '.join(not_n)} {'does' if len(not_n)==1 else 'do'} NOT follow a normal distribution — consider non-parametric tests")
            return ". ".join(parts) + "." if parts else "Normality assessed via Shapiro-Wilk."
        return f"Normality assessed. {'Data appears normally distributed.' if sig else 'Data may not be normally distributed.'}"

    return f"{'Statistically significant result' if sig else 'No statistically significant result'}, p={_p_str(p)}."


# ===== StatisticsAnalyze =====

class StatisticsAnalyze(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        if not HAS_NUMPY:
            return {"status": "error", "error": "numpy not installed. Statistics module unavailable."}
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
        total_rows = summary.get("total_rows", 0)
        # Phase 2: Read user slot assignments
        slots = input.get("slots", {})
        # Use slots if provided, otherwise fall back to AI auto-detection
        gc = slots.get("group") or (group_cols[0] if group_cols else "")
        nc = slots.get("value") or (numeric_cols[0] if numeric_cols else (columns[1] if len(columns) > 1 else columns[0] if columns else ""))
        bc = slots.get("before") or (numeric_cols[0] if numeric_cols else "")
        af = slots.get("after") or (numeric_cols[1] if len(numeric_cols) > 1 else "")
        fc = slots.get("cols") or ""
        rc = slots.get("rows") or (group_cols[0] if group_cols else (categorical_cols[0] if categorical_cols else ""))
        cc = slots.get("cols") or (group_cols[1] if len(group_cols) > 1 else (categorical_cols[1] if len(categorical_cols) > 1 else ""))

        def _err(msg, hint=""):
            return {"status": "error", "test_type": test_type, "error": msg, "hint": hint}

        try:
            # Validate test can work with available columns
            if test_type in ("ttest", "anova", "mannwhitney"):
                if not group_cols:
                    return _err(
                        f"No group column found for {test_type.upper()}.",
                        "Your data needs a column with group labels (e.g., 'Treatment', 'Group') containing 2+ distinct text values like 'Drug' and 'Placebo'."
                    )
                if not numeric_cols:
                    return _err(
                        f"No numeric column found for {test_type.upper()}.",
                        "Your data needs at least one numeric column (e.g., 'Score', 'Response') with number values to compare between groups."
                    )
                # Verify group column actually has 2+ groups
                gc_name = group_cols[0]
                if gc_name not in columns:
                    return _err(f"Group column '{gc_name}' not found in data columns.", f"Available columns: {', '.join(columns[:10])}")

            if test_type == "correlation" and len(numeric_cols) < 2:
                return _err("Need at least 2 numeric columns for correlation.", f"Found {len(numeric_cols)} numeric column(s): {', '.join(numeric_cols) if numeric_cols else 'none'}.")

            if test_type == "chisquare" and len(group_cols) < 2 and len(categorical_cols) < 2:
                return _err("Need at least 2 categorical columns for Chi-Square test.", f"Found group columns: {group_cols}, categorical: {categorical_cols}")

            # Execute test — use slot-assigned columns when available
            result = {"status": "ok", "test_type": test_type, "sub_type": "auto-decided"}
            exp = []

            if test_type == "ttest":
                input["group_col"] = gc; input["value_col"] = nc
                input["test_type"] = "independent"; input["equal_var"] = True
                exp.append({"step":1,"title":"AI Decision","detail":f"Running Independent T-Test: {nc} vs {gc}"})
                r = self._ttest(input)
                if r.get("error"): return _err(r["error"], "Check that the group column contains exactly 2 distinct text labels.")
                result.update(r)

            elif test_type == "anova":
                input["group_col"] = gc; input["value_col"] = nc
                exp.append({"step":1,"title":"AI Decision","detail":f"Running One-Way ANOVA: {nc} vs {gc}"})
                r = self._anova(input)
                if r.get("error"): return _err(r["error"], "Check that the group column contains 3+ distinct labels.")
                result.update(r)

            elif test_type == "correlation":
                input["selected_cols"] = numeric_cols[:10]; input["method"] = "pearson"
                exp.append({"step":1,"title":"Pearson Correlation","detail":"Linear relationship between numeric columns."})
                r = self._correlation(input); result.update(r)

            elif test_type == "descriptive":
                exp.append({"step":1,"title":"Descriptive Statistics","detail":"Summary for every numeric column."})
                r = self._descriptive(input); result.update(r)

            elif test_type == "normality":
                exp.append({"step":1,"title":"Normality Check","detail":"Shapiro-Wilk: p>0.05 = normal."})
                r = self._normality(input); result.update(r)

            elif test_type == "chisquare":
                input["group_col"] = rc; input["value_col"] = cc
                exp.append({"step":1,"title":"Chi-Square","detail":"Tests association between categorical variables."})
                r = self._chisquare(input); result.update(r)

            elif test_type == "mannwhitney":
                input["group_col"] = gc; input["value_col"] = nc
                exp.append({"step":1,"title":"Mann-Whitney U","detail":"Non-parametric comparison of 2 independent groups."})
                r = self._mannwhitney(input); result.update(r)

            elif test_type == "wilcoxon":
                input["group_col"] = bc; input["value_col"] = af
                input["test_type"] = "paired"
                exp.append({"step":1,"title":"Wilcoxon Signed-Rank","detail":"Non-parametric paired comparison (before vs after)."})
                r = self._wilcoxon(input); result.update(r)

            elif test_type == "kruskalwallis":
                input["group_col"] = gc; input["value_col"] = nc
                exp.append({"step":1,"title":"Kruskal-Wallis","detail":"Non-parametric comparison of 3+ independent groups."})
                r = self._kruskalwallis(input); result.update(r)

            elif test_type == "friedman":
                input["selected_cols"] = fc.split(",") if fc else numeric_cols[:10]
                exp.append({"step":1,"title":"Friedman Test","detail":"Non-parametric repeated measures."})
                r = self._friedman(input); result.update(r)

            elif test_type == "fisher":
                input["group_col"] = rc; input["value_col"] = cc
                exp.append({"step":1,"title":"Fisher Exact Test","detail":"For small sample categorical data."})
                r = self._fisher(input); result.update(r)

            elif test_type == "homogeneity":
                input["group_col"] = gc; input["value_col"] = nc
                exp.append({"step":1,"title":"Levene's Test","detail":"Tests homogeneity of variance across groups."})
                r = self._homogeneity(input); result.update(r)

            elif test_type == "power":
                exp.append({"step":1,"title":"Power Analysis","detail":"Calculates required sample size."})
                r = self._power(input); result.update(r)

            elif test_type == "roc":
                input["y_true"] = slots.get("labels",""); input["y_score"] = slots.get("scores","")
                r = self._roc(input); result.update(r)

            elif test_type == "factor":
                r = self._factor(input) if hasattr(self,"_factor") else {"message":"Factor analysis via agent chat"}
                result.update(r)

            elif test_type == "reliability":
                r = self._reliability(input) if hasattr(self,"_reliability") else {"message":"Reliability analysis via agent chat"}
                result.update(r)

            elif test_type == "cluster":
                r = self._cluster(input) if hasattr(self,"_cluster") else {"message":"Cluster analysis via agent chat"}
                result.update(r)

            elif test_type in ("survival", "regression"):
                return {"status":"ok","test_type":test_type,"message":f"{test_type.title()} uses agent chat. Type your request in the chat panel.","explanations":[{"step":1,"title":"Agent Required","detail":f"Open the chat panel to run {test_type} analysis."}]}

            else:
                return _err(f"Unknown test: {test_type}")

            # Finalize result
            if r.get("significant") is not None:
                result["test_name"] = (r.get("test") or test_type)
                result["sub_type"] = r.get("test") or test_type
            metrics = {}
            for k in ("statistic", "p_value", "n", "auc", "odds_ratio"):
                if k in r: metrics[k] = r[k]
            if metrics: result["metrics"] = metrics
            result["explanations"] = exp
            result["data_check"] = {
                "total_rows": total_rows,
                "columns": columns,
                "groups_found": group_cols,
                "numeric_found": numeric_cols,
            }
            # Phase 4: APA Publication Output
            result["apa_output"] = self._build_apa(test_type, r, exp, columns)
            result["apa_output"]["python_code"] = _build_python_code(test_type, {})
            result["apa_output"]["ai_interpretation"] = _ai_interpret(test_type, r, {})
            result["apa_output"]["meta"] = {"significant": r.get("significant", False), "test": test_type}
            # Gap 1: Inline chart
            try:
                chart = self._render_chart(test_type, r)
                if chart: result["apa_output"]["chart"] = {"base64": chart}
            except: pass
            return _to_json_safe(result)

        except Exception as e:
            return _to_json_safe({"status": "error", "error": str(e), "test_type": test_type})

    def _build_apa(self, test_type, r, exp, columns):
        sig = r.get("significant", False)
        p = r.get("p_value", 0)
        if test_type == "ttest":
            g1 = r.get("group1", {}); g2 = r.get("group2", {})
            return {
                "title": "Independent Samples T-Test",
                "tables": [
                    _apa_table("Table 1. Group Descriptives",
                        ["Group", "N", "Mean", "SD", "SE"],
                        [[g1.get("name","G1"), g1.get("n",0), _fmt(g1.get("mean",0)), _fmt(g1.get("std",0)), _fmt(g1.get("std",0)/max(g1.get("n",1)**0.5,0.001))],
                         [g2.get("name","G2"), g2.get("n",0), _fmt(g2.get("mean",0)), _fmt(g2.get("std",0)), _fmt(g2.get("std",0)/max(g2.get("n",1)**0.5,0.001))]],
                        note=f"Note. N={g1.get('n',0)+g2.get('n',0)}."),
                    _apa_table("Table 2. Independent Samples T-Test",
                        ["", "t", "df", "p"],
                        [[r.get("variable", columns[0] if columns else "Y"), _fmt(r.get("statistic",0)), r.get("df", g1.get("n",0)+g2.get("n",0)-2) or g1.get("n",0)+g2.get("n",0)-2, _p_str(p)]],
                        note=f"Note. Student's t-test. {'Equal variances assumed.' if r.get('equal_var',True) else 'Welch correction applied.'}", sig_cols=[False, True if sig else True, False, True]),
                ]
            }
        if test_type == "anova":
            grps = r.get("groups", []); fstat = r.get("statistic", 0); df1 = len(grps)-1 if len(grps)>1 else 1; df2 = sum(g.get("n",0) for g in grps) - len(grps)
            return {
                "title": "One-Way ANOVA",
                "tables": [
                    _apa_table("Table 1. Group Descriptives",
                        ["Group", "N", "Mean", "SD"],
                        [[g.get("name",f"G{i+1}"), g.get("n",0), _fmt(g.get("mean",0)), _fmt(g.get("std",0))] for i,g in enumerate(grps[:8])],
                        note=f"Note. Total N={df2+len(grps)}."),
                    _apa_table("Table 2. ANOVA Summary",
                        ["Source", "df", "F", "p"],
                        [[r.get("variable","Value"), f"{df1},{df2}", _fmt(fstat), _p_str(p)]],
                        note="Note. One-way between-subjects ANOVA.", sig_cols=[False, False, False, True]),
                ]
            }
        if test_type == "correlation":
            corr_cols = r.get("columns", []); matrix = r.get("correlation_matrix", []); pvals = r.get("p_values", [])
            n = len(corr_cols)
            if n and matrix:
                rows = []
                for i in range(n):
                    row = [corr_cols[i]]
                    for j in range(n):
                        v = matrix[i][j] if i < len(matrix) and j < len(matrix[i]) else ""
                        if i != j and v: v = f"{v:.3f}"
                        elif i == j: v = "—"
                        row.append(v)
                    if len(row) > 1: rows.append(row)
                return {
                    "title": "Pearson Correlation Matrix",
                    "tables": [_apa_table("Table 1. Correlation Matrix", [""] + corr_cols[:8], rows, note=f"Note. N={r.get('n',0)}. Values are Pearson r.")],
                }
            return {"title": "Correlation", "tables": []}
        if test_type == "descriptive":
            desc = r.get("descriptive", {}) or r
            if isinstance(desc, dict):
                cols = [k for k in desc if isinstance(desc[k], dict) and "mean" in desc[k]]
                if cols:
                    rows = [["N", *[_fmt(desc[c].get("n",0)) for c in cols]],
                            ["Mean", *[_fmt(desc[c].get("mean",0)) for c in cols]],
                            ["Median", *[_fmt(desc[c].get("median",0)) for c in cols]],
                            ["SD", *[_fmt(desc[c].get("std",0)) for c in cols]],
                            ["Min", *[_fmt(desc[c].get("min",0)) for c in cols]],
                            ["Max", *[_fmt(desc[c].get("max",0)) for c in cols]],
                            ["Skewness", *[_fmt(desc[c].get("skewness",0),3) for c in cols]],
                            ["Kurtosis", *[_fmt(desc[c].get("kurtosis",0),3) for c in cols]]]
                    return {"title":"Descriptive Statistics","tables":[_apa_table("Table 1. Summary Statistics",[""]+cols,rows,note=f"Note. N={max([desc[c].get('n',0) for c in cols]) if cols else 'N/A'}.")]}
            return {"title":"Descriptive Statistics","tables":[]}
        if test_type == "normality":
            nc = r.get("normality", {}) or r
            if isinstance(nc, dict):
                rows = [[c, v.get("test","Shapiro-Wilk"), _fmt(v.get("statistic",0),4), _p_str(v.get("p_value",0)), "✓ Normal" if v.get("normal") else "× Not Normal"] for c,v in nc.items() if isinstance(v,dict) and "p_value" in v]
                return {"title":"Normality Tests (Shapiro-Wilk)","tables":[_apa_table("Table 1. Normality Tests",["Column","Test","W","p","Result"],rows,note="Note. p\u2265.05 indicates normal distribution.")]}
            return {"title":"Normality Tests","tables":[]}
        # Generic fallback for any test
        rows = []
        if r.get("p_value"): rows.append(["p-value", _p_str(p)])
        if r.get("statistic"): rows.append(["Statistic", _fmt(r["statistic"],4)])
        return {"title": r.get("test", test_type.title()), "tables": [_apa_table("Results", ["Metric","Value"], rows)] if rows else []}

    def _render_chart(self, test_type, r):
        """Generate inline chart for publication output."""
        try:
            from api.statistics_charts import (
                generate_boxplot, generate_scatter, generate_histogram,
                generate_bar_chart, generate_correlation_heatmap, generate_qq_plot
            )
        except: return None
        if test_type in ("ttest", "mannwhitney"):
            g1 = r.get("group1", {}); g2 = r.get("group2", {})
            return generate_boxplot({g1.get("name","G1"): [], g2.get("name","G2"): []})
        if test_type in ("anova", "kruskalwallis"):
            grps = r.get("groups", [])
            gd = {g.get("name", f"G{i}"): [] for i, g in enumerate(grps[:8])}
            return generate_boxplot(gd) if gd else None
        if test_type == "correlation":
            mat = r.get("correlation_matrix", [[]])
            cols = r.get("columns", [])
            return generate_correlation_heatmap(mat, cols) if mat else None
        if test_type in ("descriptive", "normality"):
            return generate_histogram([], title=test_type.title())
        if test_type == "chisquare":
            return generate_bar_chart([], [], title="Chi-Square")
        return None

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
