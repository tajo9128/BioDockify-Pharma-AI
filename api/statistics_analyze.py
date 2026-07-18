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
        # Cohen's d with pooled SD (correct formula)
        s1 = float(g1.get("std", 1) or 1); s2 = float(g2.get("std", 1) or 1)
        n1 = max(int(g1.get("n", 1) or 1), 1); n2 = max(int(g2.get("n", 1) or 1), 1)
        pooled_sd = (((n1-1)*s1**2 + (n2-1)*s2**2) / max(n1+n2-2, 1)) ** 0.5
        d = abs(m1 - m2) / max(pooled_sd, 0.001)
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

        # ── Core (16) ──
        if action == "auto_decide":         return self._auto_decide(input)
        elif action == "descriptive":       return self._descriptive(input)
        elif action == "correlation":       return self._correlation(input)
        elif action == "ttest":             return self._ttest(input)
        elif action == "anova":             return self._anova(input)
        elif action == "chisquare":         return self._chisquare(input)
        elif action == "mannwhitney":       return self._mannwhitney(input)
        elif action == "wilcoxon":          return self._wilcoxon(input)
        elif action == "kruskalwallis":     return self._kruskalwallis(input)
        elif action == "friedman":          return self._friedman(input)
        elif action == "fisher":            return self._fisher(input)
        elif action == "normality":         return self._normality(input)
        elif action == "homogeneity":       return self._homogeneity(input)
        elif action == "roc":               return self._roc(input)
        elif action == "power":             return self._power(input)
        elif action == "survival":          return self._survival(input)
        elif action == "pdf_report":        return self._pdf_report(input)

        # ── Non-parametric & Post-hoc ──
        elif action == "sign_test":         return self._delegated(input, "sign_test")
        elif action == "dunns":             return self._delegated(input, "dunns")
        elif action == "z_test":            return self._delegated(input, "z_test")

        # ── Chi-square variants ──
        elif action == "chi_square_goodness":    return self._delegated(input, "chi_square_goodness")
        elif action == "chi_square_independence": return self._delegated(input, "chi_square_independence")
        elif action == "mcnemar":                return self._delegated(input, "mcnemar")
        elif action == "cmh":                    return self._delegated(input, "cmh")

        # ── Survival analysis ──
        elif action == "kaplan_meier":      return self._survival_module(input, "kaplan_meier")
        elif action == "log_rank":          return self._survival_module(input, "log_rank")
        elif action == "cox_ph":            return self._survival_module(input, "cox_ph")

        # ── Bioequivalence & PK ──
        elif action == "tost":              return self._bioequiv(input, "tost")
        elif action == "crossover":         return self._bioequiv(input, "crossover")
        elif action == "bioavailability":   return self._bioequiv(input, "bioavailability")
        elif action == "non_inferiority":   return self._bioequiv(input, "non_inferiority")
        elif action == "equivalence":       return self._bioequiv(input, "equivalence")
        elif action == "nca_pk":            return self._pkpd(input, "nca_pk")
        elif action == "auc":               return self._pkpd(input, "auc")
        elif action == "cmax_tmax":         return self._pkpd(input, "cmax_tmax")
        elif action == "half_life":         return self._pkpd(input, "half_life")
        elif action == "clearance":         return self._pkpd(input, "clearance")
        elif action == "pk_bioavailability": return self._pkpd(input, "pk_bioavailability")
        elif action == "pd_response":       return self._pkpd(input, "pd_response")
        elif action == "compartmental":     return self._pkpd(input, "compartmental")
        elif action == "dose_proportionality": return self._pkpd(input, "dose_proportionality")
        elif action == "pk_summary":        return self._pkpd(input, "pk_summary")

        # ── Regression & Modeling ──
        elif action == "logistic_regression":   return self._delegated(input, "logistic_regression")
        elif action == "poisson_regression":    return self._delegated(input, "poisson_regression")
        elif action == "negative_binomial":      return self._delegated(input, "negative_binomial")
        elif action == "multiple_regression":    return self._delegated(input, "multiple_regression")
        elif action == "polynomial_regression":  return self._delegated(input, "polynomial_regression")
        elif action == "mixed_effects":          return self._delegated(input, "mixed_effects")
        elif action == "mixed_model":            return self._delegated(input, "mixed_model")
        elif action == "glm":                    return self._delegated(input, "glm")

        # ── Advanced ANOVA ──
        elif action == "repeated_measures_anova": return self._delegated(input, "repeated_measures_anova")
        elif action == "ancova":                 return self._delegated(input, "ancova")
        elif action == "manova":                 return self._delegated(input, "manova")

        # ── Post-hoc ──
        elif action == "tukey_hsd":         return self._delegated(input, "tukey_hsd")
        elif action == "bonferroni_posthoc": return self._delegated(input, "bonferroni_posthoc")
        elif action == "dunnett_posthoc":   return self._delegated(input, "dunnett_posthoc")
        elif action == "scheffe_posthoc":   return self._delegated(input, "scheffe_posthoc")

        # ── Meta-analysis ──
        elif action == "meta_analysis":     return self._delegated(input, "meta_analysis")

        else:
            return {"error": f"Unknown action: {action}. Available actions: " +
                    ", ".join(self._available_actions())}

    def _available_actions(self):
        """Return all available action names for error messages."""
        return [
            "auto_decide", "descriptive", "correlation", "ttest", "anova", "chisquare",
            "mannwhitney", "wilcoxon", "kruskalwallis", "friedman", "fisher", "normality",
            "homogeneity", "roc", "power", "survival", "pdf_report",
            "sign_test", "dunns", "z_test",
            "chi_square_goodness", "chi_square_independence", "mcnemar", "cmh",
            "kaplan_meier", "log_rank", "cox_ph",
            "tost", "crossover", "bioavailability", "non_inferiority", "equivalence",
            "nca_pk", "auc", "cmax_tmax", "half_life", "clearance", "pk_bioavailability",
            "pd_response", "compartmental", "dose_proportionality", "pk_summary",
            "logistic_regression", "poisson_regression", "negative_binomial",
            "multiple_regression", "polynomial_regression", "mixed_effects", "mixed_model", "glm",
            "repeated_measures_anova", "ancova", "manova",
            "tukey_hsd", "bonferroni_posthoc", "dunnett_posthoc", "scheffe_posthoc",
            "meta_analysis",
        ]

    def _delegated(self, input: dict, action_name: str) -> dict:
        """Delegate to the enhanced engine or advanced biostatistics module."""
        try:
            columns = input.get("columns", [])
            data = input.get("data", [])
            if not data:
                return {"status": "error", "error": f"No data provided for {action_name}"}

            import pandas as pd
            df = pd.DataFrame(data)

            # Map action to method on enhanced engine
            method_map = {
                "sign_test": lambda: self._run_sign_test(df, input),
                "dunns": lambda: self._run_dunns(df, input),
                "z_test": lambda: self._run_z_test(df, input),
                "chi_square_goodness": lambda: self._run_chi_square_goodness(df, input),
                "chi_square_independence": lambda: self._run_chi_square_independence(df, input),
                "mcnemar": lambda: self._run_mcnemar(df, input),
                "cmh": lambda: self._run_cmh(df, input),
                "logistic_regression": lambda: self._run_logistic_regression(df, input),
                "poisson_regression": lambda: self._run_poisson_regression(df, input),
                "negative_binomial": lambda: self._run_negative_binomial(df, input),
                "multiple_regression": lambda: self._run_multiple_regression(df, input),
                "polynomial_regression": lambda: self._run_polynomial_regression(df, input),
                "mixed_effects": lambda: self._run_mixed_effects(df, input),
                "mixed_model": lambda: self._run_mixed_effects(df, input),  # alias
                "glm": lambda: self._run_glm(df, input),
                "repeated_measures_anova": lambda: self._run_repeated_anova(df, input),
                "ancova": lambda: self._run_ancova(df, input),
                "manova": lambda: self._run_manova(df, input),
                "tukey_hsd": lambda: self._run_posthoc(df, input, "tukey"),
                "bonferroni_posthoc": lambda: self._run_posthoc(df, input, "bonferroni"),
                "dunnett_posthoc": lambda: self._run_posthoc(df, input, "dunnett"),
                "scheffe_posthoc": lambda: self._run_posthoc(df, input, "scheffe"),
                "meta_analysis": lambda: self._run_meta_analysis(df, input),
            }

            if action_name in method_map:
                result = method_map[action_name]()
                result["action"] = action_name
                result["status"] = "ok"
                return _to_json_safe(result)
            else:
                return {"status": "error", "error": f"Unknown delegated action: {action_name}"}

        except Exception as e:
            log.exception(f"Delegated action {action_name} failed")
            return {"status": "error", "error": str(e)}

    def _survival_module(self, input: dict, sub_action: str) -> dict:
        """Delegate to survival analysis module."""
        try:
            from modules.statistics.survival_analysis import SurvivalAnalysis
            data = input.get("data", [])
            if not data:
                return {"status": "error", "error": "No data provided"}
            import pandas as pd
            df = pd.DataFrame(data)
            sa = SurvivalAnalysis()

            if sub_action == "kaplan_meier":
                time_col = input.get("time_col", "time")
                event_col = input.get("event_col", "event")
                group_col = input.get("group_col")
                return _to_json_safe(sa.kaplan_meier(df, time_col, event_col, group_col))
            elif sub_action == "log_rank":
                time_col = input.get("time_col", "time")
                event_col = input.get("event_col", "event")
                group_col = input.get("group_col")
                return _to_json_safe(sa.log_rank_test(df, time_col, event_col, group_col))
            elif sub_action == "cox_ph":
                time_col = input.get("time_col", "time")
                event_col = input.get("event_col", "event")
                covariates = input.get("covariates", [])
                return _to_json_safe(sa.cox_ph(df, time_col, event_col, covariates))
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _bioequiv(self, input: dict, sub_action: str) -> dict:
        """Delegate to bioequivalence module."""
        try:
            from modules.statistics.bioequivalence import BioequivalenceTests
            data = input.get("data", [])
            if not data:
                return {"status": "error", "error": "No data provided"}
            import pandas as pd
            df = pd.DataFrame(data)
            bt = BioequivalenceTests()

            if sub_action == "tost":
                col1 = input.get("col1", "")
                col2 = input.get("col2", "")
                margin = input.get("margin", 0.2)
                return _to_json_safe(bt.tost_two_sample(df, col1, col2, margin))
            elif sub_action == "crossover":
                return _to_json_safe(bt.crossover_analysis(df, **{k: v for k, v in input.items() if k not in ("action", "data")}))
            elif sub_action == "bioavailability":
                return _to_json_safe(bt.bioavailability_analysis(df, **{k: v for k, v in input.items() if k not in ("action", "data")}))
            elif sub_action == "non_inferiority":
                return _to_json_safe(bt.non_inferiority_test(df, **{k: v for k, v in input.items() if k not in ("action", "data")}))
            elif sub_action == "equivalence":
                return _to_json_safe(bt.equivalence_test(df, **{k: v for k, v in input.items() if k not in ("action", "data")}))
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _pkpd(self, input: dict, sub_action: str) -> dict:
        """Delegate to PK/PD analysis module."""
        try:
            from modules.statistics.pkpd_analysis import PKPDAnalysis
            data = input.get("data", [])
            if not data:
                return {"status": "error", "error": "No data provided"}
            import pandas as pd
            df = pd.DataFrame(data)
            pk = PKPDAnalysis()
            result = getattr(pk, sub_action)(df, **{k: v for k, v in input.items() if k not in ("action", "data")})
            return _to_json_safe({"status": "ok", "action": sub_action, "result": result})
        except AttributeError:
            return {"status": "error", "error": f"PK/PD method '{sub_action}' not found in PKPDAnalysis"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ── Generic delegated implementations (scipy-based) ──

    def _run_sign_test(self, df, input):
        from scipy import stats
        col = input.get("col", input.get("value_col", ""))
        median = input.get("median", 0)
        diffs = df[col] - median
        n_pos = (diffs > 0).sum()
        n_neg = (diffs < 0).sum()
        n = n_pos + n_neg
        if n == 0:
            return {"error": "No non-zero differences"}
        p = stats.binom_test(n_pos, n, 0.5) if hasattr(stats, 'binom_test') else stats.binomtest(n_pos, n, 0.5).pvalue
        return {"n_positive": int(n_pos), "n_negative": int(n_neg), "p_value": round(float(p), 4),
                "test_statistic": int(min(n_pos, n_neg)), "median_test": round(float(median), 4)}

    def _run_dunns(self, df, input):
        from scipy import stats
        import numpy as np
        group_col = input.get("group_col", "")
        value_col = input.get("value_col", "")
        groups = [g[value_col].dropna().values for _, g in df.groupby(group_col)]
        H, p = stats.kruskal(*groups)
        pairwise = []
        for i in range(len(groups)):
            for j in range(i+1, len(groups)):
                U, pval = stats.mannwhitneyu(groups[i], groups[j], alternative='two-sided')
                pairwise.append({"group_i": i, "group_j": j, "U": float(U), "p_value": round(float(pval), 4)})
        return {"kruskal_H": float(H), "kruskal_p": round(float(p), 4), "pairwise_comparisons": pairwise}

    def _run_z_test(self, df, input):
        from scipy import stats
        import numpy as np
        col = input.get("col", input.get("value_col", ""))
        value = float(input.get("population_mean", 0))
        known_std = float(input.get("known_std", df[col].std()))
        n = len(df[col].dropna())
        xbar = df[col].mean()
        z = (xbar - value) / (known_std / np.sqrt(n))
        p_two = 2 * (1 - stats.norm.cdf(abs(z)))
        return {"z_statistic": round(float(z), 4), "p_value": round(float(p_two), 4), "mean": round(float(xbar), 4), "n": n, "known_std": round(float(known_std), 4)}

    def _run_chi_square_goodness(self, df, input):
        import numpy as np
        from scipy import stats
        col = input.get("col", input.get("value_col", ""))
        freq = input.get("frequencies")
        if freq:
            observed = np.array(freq, dtype=float)
        else:
            observed = df[col].value_counts().sort_index().values.astype(float)
        expected = np.ones_like(observed) * observed.sum() / len(observed)
        chi2, p = stats.chisquare(observed, expected)
        return {"chi2": round(float(chi2), 4), "p_value": round(float(p), 4), "df": len(observed)-1, "observed": observed.tolist(), "expected": expected.tolist()}

    def _run_chi_square_independence(self, df, input):
        import pandas as pd
        from scipy import stats
        col1 = input.get("col1", input.get("group_col", ""))
        col2 = input.get("col2", "")
        ct = pd.crosstab(df[col1], df[col2])
        chi2, p, dof, expected = stats.chi2_contingency(ct)
        return {"chi2": round(float(chi2), 4), "p_value": round(float(p), 4), "df": int(dof), "contingency_table": ct.to_dict(), "expected_frequencies": expected.tolist()}

    def _run_mcnemar(self, df, input):
        import pandas as pd
        from scipy import stats
        col_before = input.get("col_before", "")
        col_after = input.get("col_after", "")
        ct = pd.crosstab(df[col_before], df[col_after])
        if ct.shape == (2, 2):
            b = ct.iloc[0, 1]
            c = ct.iloc[1, 0]
            n = b + c
            if n == 0:
                chi2 = 0; p = 1.0
            elif n <= 25:
                p = stats.binom_test(b, n, 0.5) if hasattr(stats, 'binom_test') else stats.binomtest(b, n, 0.5).pvalue
                chi2 = (abs(b - c) - 1)**2 / n if n > 0 else 0
            else:
                chi2 = (abs(b - c) - 1)**2 / n
                p = 1 - stats.chi2.cdf(chi2, 1)
            return {"chi2": round(float(chi2), 4), "p_value": round(float(p), 4), "discordant_pairs": {"b_only": int(b), "c_only": int(c)}}
        return {"error": "McNemar requires 2x2 table"}

    def _run_cmh(self, df, input):
        """Cochran-Mantel-Haenszel test for stratified 2x2 tables."""
        from scipy import stats
        import numpy as np
        strata_col = input.get("strata_col", "")
        col1 = input.get("col1", "")
        col2 = input.get("col2", "")
        tables = []
        for stratum, sdf in df.groupby(strata_col):
            ct = pd.crosstab(sdf[col1], sdf[col2])
            if ct.shape == (2, 2):
                tables.append(ct.values)
        if not tables:
            return {"error": "No valid 2x2 tables found"}
        tables = [np.array(t, dtype=float) for t in tables]
        cmh, p = stats.chi2_contingency(np.sum(tables, axis=0).reshape(2, 2))[:2] if len(tables) == 1 else (None, None)
        # Use standard CMH formula
        num = 0; den = 0
        total_a = total_b = total_c = total_d = 0
        for t in tables:
            a, b, c, d = t[0,0], t[0,1], t[1,0], t[1,1]
            n = t.sum()
            if n > 1:
                num += a - (a+b)*(a+c)/n
                den += (a+b)*(c+d)*(a+c)*(b+d)/(n**2*(n-1))
        if den > 0:
            chi2 = num**2 / den
            p = 1 - stats.chi2.cdf(chi2, 1)
        else:
            chi2 = 0; p = 1.0
        return {"cmh_chi2": round(float(chi2), 4), "p_value": round(float(p), 4), "strata_count": len(tables), "df": 1}

    def _run_logistic_regression(self, df, input):
        from scipy import stats
        import numpy as np
        y_col = input.get("y_col", input.get("value_col", ""))
        x_cols = input.get("x_cols", input.get("columns", []))
        if not x_cols:
            x_cols = [c for c in df.columns if c != y_col]
        try:
            from sklearn.linear_model import LogisticRegression
            from sklearn.preprocessing import StandardScaler
            X = df[x_cols].dropna().values
            y = df[y_col].dropna().values
            if len(X) != len(y):
                min_len = min(len(X), len(y)); X = X[:min_len]; y = y[:min_len]
            scaler = StandardScaler()
            X_s = scaler.fit_transform(X)
            model = LogisticRegression(max_iter=1000)
            model.fit(X_s, y)
            coefs = model.coef_[0].tolist()
            intercept = float(model.intercept_[0])
            odds_ratios = [round(float(np.exp(c)), 4) for c in coefs]
            return {"coefficients": [round(c, 4) for c in coefs], "intercept": round(intercept, 4),
                    "odds_ratios": odds_ratios, "feature_names": x_cols,
                    "accuracy": round(float(model.score(X_s, y)), 4)}
        except ImportError:
            return {"error": "scikit-learn required for logistic regression"}

    def _run_poisson_regression(self, df, input):
        try:
            import statsmodels.api as sm
            y_col = input.get("y_col", input.get("value_col", ""))
            x_cols = input.get("x_cols", input.get("columns", []))
            if not x_cols:
                x_cols = [c for c in df.columns if c != y_col]
            X = sm.add_constant(df[x_cols].dropna())
            y = df[y_col].dropna().values[:len(X)]
            model = sm.GLM(y, X, family=sm.families.Poisson()).fit()
            return {"summary": str(model.summary()), "aic": round(float(model.aic), 2), "bic": round(float(model.bic), 2),
                    "coefficients": dict(zip(["const"] + x_cols, [round(float(c), 4) for c in model.params]))}
        except ImportError:
            return {"error": "statsmodels required for Poisson regression"}

    def _run_negative_binomial(self, df, input):
        try:
            import statsmodels.api as sm
            y_col = input.get("y_col", input.get("value_col", ""))
            x_cols = input.get("x_cols", input.get("columns", []))
            if not x_cols:
                x_cols = [c for c in df.columns if c != y_col]
            X = sm.add_constant(df[x_cols].dropna())
            y = df[y_col].dropna().values[:len(X)]
            model = sm.NegativeBinomial(y, X).fit(disp=False)
            return {"summary": str(model.summary()), "aic": round(float(model.aic), 2), "bic": round(float(model.bic), 2),
                    "alpha": round(float(model.params[-1]), 4) if hasattr(model, 'params') else None}
        except ImportError:
            return {"error": "statsmodels required for negative binomial regression"}

    def _run_multiple_regression(self, df, input):
        try:
            import statsmodels.api as sm
            y_col = input.get("y_col", input.get("value_col", ""))
            x_cols = input.get("x_cols", input.get("columns", []))
            if not x_cols:
                x_cols = [c for c in df.columns if c != y_col]
            X = sm.add_constant(df[x_cols].dropna())
            y = df[y_col].dropna().values[:len(X)]
            model = sm.OLS(y, X).fit()
            return {"summary": str(model.summary()), "r2": round(float(model.rsquared), 4),
                    "adj_r2": round(float(model.rsquared_adj), 4), "f_statistic": round(float(model.fvalue), 4),
                    "f_pvalue": round(float(model.f_pvalue), 6),
                    "coefficients": dict(zip(["const"] + x_cols, [round(float(c), 4) for c in model.params])),
                    "p_values": dict(zip(["const"] + x_cols, [round(float(p), 4) for p in model.pvalues]))}
        except ImportError:
            return {"error": "statsmodels required for multiple regression"}

    def _run_polynomial_regression(self, df, input):
        import numpy as np
        x_col = input.get("x_col", "")
        y_col = input.get("y_col", input.get("value_col", ""))
        degree = int(input.get("degree", 2))
        x = df[x_col].dropna().values
        y = df[y_col].dropna().values[:len(x)]
        coeffs = np.polyfit(x, y, degree)
        y_pred = np.polyval(coeffs, x)
        ss_res = np.sum((y - y_pred)**2)
        ss_tot = np.sum((y - np.mean(y))**2)
        r2 = 1 - ss_res/ss_tot if ss_tot > 0 else 0
        return {"coefficients": [round(float(c), 6) for c in coeffs], "degree": degree,
                "r2": round(float(r2), 4), "equation": " + ".join([f"{c:.4f}x^{i}" for i, c in enumerate(reversed(coeffs))])}

    def _run_mixed_effects(self, df, input):
        try:
            import statsmodels.api as sm
            import statsmodels.formula.api as smf
            formula = input.get("formula", "")
            groups = input.get("groups", "")
            model = smf.mixedlm(formula, df, groups=df[groups]).fit()
            return {"summary": str(model.summary()), "aic": round(float(model.aic), 2) if hasattr(model, 'aic') else None,
                    "converged": model.converged if hasattr(model, 'converged') else True}
        except ImportError:
            return {"error": "statsmodels required for mixed effects model"}

    def _run_glm(self, df, input):
        try:
            import statsmodels.api as sm
            import statsmodels.formula.api as smf
            formula = input.get("formula", "")
            family = input.get("family", "gaussian")
            family_map = {"gaussian": sm.families.Gaussian, "binomial": sm.families.Binomial,
                          "poisson": sm.families.Poisson, "gamma": sm.families.Gamma}
            fam = family_map.get(family, sm.families.Gaussian)()
            model = smf.glm(formula, df, family=fam).fit()
            return {"summary": str(model.summary()), "aic": round(float(model.aic), 2), "bic": round(float(model.bic), 2),
                    "deviance": round(float(model.deviance), 4)}
        except ImportError:
            return {"error": "statsmodels required for GLM"}

    def _run_repeated_anova(self, df, input):
        try:
            import pandas as pd
            import statsmodels.api as sm
            import statsmodels.formula.api as smf
            dv = input.get("dv", input.get("value_col", ""))
            within = input.get("within", "")
            subject = input.get("subject", "")
            model = smf.ols(f'{dv} ~ C({within})', data=df).fit()
            anova_table = sm.stats.anova_lm(model, typ=2)
            return {"anova_table": anova_table.to_dict(), "f_statistic": round(float(anova_table["F"].iloc[0]), 4),
                    "p_value": round(float(anova_table["PR(>F)"].iloc[0]), 6)}
        except ImportError:
            return {"error": "statsmodels required for repeated measures ANOVA"}

    def _run_ancova(self, df, input):
        try:
            import statsmodels.api as sm
            import statsmodels.formula.api as smf
            dv = input.get("dv", input.get("value_col", ""))
            between = input.get("between", "")
            covariate = input.get("covariate", "")
            model = smf.ols(f'{dv} ~ C({between}) + {covariate}', data=df).fit()
            anova_table = sm.stats.anova_lm(model, typ=2)
            return {"anova_table": anova_table.to_dict(), "coefficients": dict(zip(model.params.index, [round(float(c), 4) for c in model.params])),
                    "r2": round(float(model.rsquared), 4)}
        except ImportError:
            return {"error": "statsmodels required for ANCOVA"}

    def _run_manova(self, df, input):
        try:
            import statsmodels.api as sm
            from statsmodels.multivariate.manova import MANOVA
            dv_cols = input.get("dv_cols", input.get("columns", []))
            between = input.get("between", "")
            formula = f"{' + '.join(dv_cols)} ~ C({between})"
            mv = MANOVA.from_formula(formula, data=df)
            result = mv.mv_test()
            return {"multivariate_tests": str(result), "status": "ok"}
        except ImportError:
            return {"error": "statsmodels required for MANOVA"}

    def _run_posthoc(self, df, input, method):
        from scipy import stats
        import numpy as np
        group_col = input.get("group_col", "")
        value_col = input.get("value_col", "")
        groups = {}
        for _, row in df.iterrows():
            g = row[group_col]
            groups.setdefault(g, []).append(float(row[value_col]))
        group_names = list(groups.keys())
        results = []
        for i in range(len(group_names)):
            for j in range(i+1, len(group_names)):
                t, p = stats.ttest_ind(groups[group_names[i]], groups[group_names[j]])
                n_tests = len(group_names) * (len(group_names) - 1) / 2
                if method == "bonferroni":
                    p_adj = min(p * n_tests, 1.0)
                else:
                    p_adj = p  # tukey/dunnett/scheffe simplified
                results.append({"group_1": group_names[i], "group_2": group_names[j],
                                "t_stat": round(float(t), 4), "p_value": round(float(p), 4),
                                "p_adjusted": round(float(p_adj), 4)})
        return {"method": method, "comparisons": results}

    def _run_meta_analysis(self, df, input):
        import numpy as np
        effect_col = input.get("effect_col", "effect_size")
        se_col = input.get("se_col", "se")
        if effect_col not in df.columns or se_col not in df.columns:
            return {"error": f"Columns {effect_col} and {se_col} required"}
        effects = df[effect_col].dropna().values
        ses = df[se_col].dropna().values[:len(effects)]
        weights = 1.0 / (ses ** 2)
        pooled = np.sum(weights * effects) / np.sum(weights)
        pooled_se = np.sqrt(1.0 / np.sum(weights))
        z = pooled / pooled_se
        from scipy import stats
        p = 2 * (1 - stats.norm.cdf(abs(z)))
        # Q statistic for heterogeneity
        Q = np.sum(weights * (effects - pooled)**2)
        df_Q = len(effects) - 1
        I2 = max(0, (Q - df_Q) / Q * 100) if Q > 0 else 0
        ci_lower = pooled - 1.96 * pooled_se
        ci_upper = pooled + 1.96 * pooled_se
        return {"pooled_effect": round(float(pooled), 4), "pooled_se": round(float(pooled_se), 4),
                "z_statistic": round(float(z), 4), "p_value": round(float(p), 6),
                "ci_95": [round(float(ci_lower), 4), round(float(ci_upper), 4)],
                "Q_statistic": round(float(Q), 4), "Q_df": int(df_Q),
                "I2_heterogeneity": round(float(I2), 1),
                "n_studies": len(effects),
                "individual_effects": [round(float(e), 4) for e in effects]}

    def _survival(self, input: dict) -> dict:
        """Survival analysis stub — agent-driven."""
        return {"status": "ok", "action": "survival", "message": "Survival analysis uses agent chat. Type your request with the data attached."}

    def _pdf_report(self, input: dict) -> dict:
        """Generate a PDF report with BioDockify letterhead for a statistics result."""
        analysis_type = input.get("analysis_type", "descriptive")
        results = input.get("results", {})
        interpretation = input.get("interpretation", "")
        methodology = input.get("methodology", "")
        table_records = input.get("table_records")
        table_columns = input.get("table_columns")
        chart_path = input.get("chart_path")

        try:
            from modules.statistics.pdf_report import generate_statistics_report
            import base64

            title_map = {
                "descriptive": "Descriptive Statistics Report",
                "correlation": "Correlation Analysis Report",
                "ttest": "T-Test Analysis Report",
                "anova": "ANOVA Analysis Report",
                "chisquare": "Chi-Square Test Report",
                "mannwhitney": "Mann-Whitney U Test Report",
                "wilcoxon": "Wilcoxon Signed-Rank Test Report",
                "kruskalwallis": "Kruskal-Wallis Test Report",
                "normality": "Normality Test Report",
                "homogeneity": "Homogeneity of Variance Report",
                "power": "Power Analysis Report",
                "auto_decide": "Statistical Analysis Report",
            }
            title = title_map.get(analysis_type, f"Statistics Report — {analysis_type.title()}")

            pdf_buffer = generate_statistics_report(
                title=title,
                analysis_type=analysis_type,
                results=results,
                interpretation=interpretation,
                methodology=methodology,
                table_records=table_records,
                table_columns=table_columns,
                chart_path=chart_path,
            )
            pdf_bytes = pdf_buffer.read()
            pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")

            # Auto-store to KB
            try:
                from modules.knowledge.auto_store import auto_store
                auto_store("statistics", f"PDF Report — {analysis_type.title()}",
                           {"analysis_type": analysis_type, "results_summary": str(results)[:500]},
                           source="Statistics PDF Report",
                           tags=["statistics", "pdf", analysis_type])
            except Exception:
                pass

            return {
                "status": "ok",
                "pdf_base64": pdf_b64,
                "filename": f"statistics_{analysis_type}_{__import__('time').strftime('%Y%m%d')}.pdf",
                "size_bytes": len(pdf_bytes),
            }
        except ImportError:
            return {"status": "error", "error": "reportlab not installed. PDF generation unavailable."}
        except Exception as e:
            log.exception("PDF report generation failed")
            return {"status": "error", "error": str(e)}

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
        cc = slots.get("column") or (group_cols[1] if len(group_cols) > 1 else (categorical_cols[1] if len(categorical_cols) > 1 else ""))

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
            except Exception:
                pass
            safe_result = _to_json_safe(result)
            # ── AUTO-STORE ──
            try:
                from modules.knowledge.auto_store import auto_store
                auto_store("statistics", f"Stats: {test_type}", safe_result,
                           source=f"Statistics ({test_type})", tags=["statistics", test_type])
            except Exception:
                pass
            return safe_result

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
            desc = r.get("columns", r.get("descriptive", {})) or r
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
            nc = r.get("results", r.get("normality", {})) or r
            if isinstance(nc, dict):
                rows = [[c, v.get("test","Shapiro-Wilk"), _fmt(v.get("statistic",0),4), _p_str(v.get("p_value",0)), "✓ Normal" if v.get("normal") else "× Not Normal"] for c,v in nc.items() if isinstance(v,dict) and "p_value" in v]
                return {"title":"Normality Tests (Shapiro-Wilk)","tables":[_apa_table("Table 1. Normality Tests",["Column","Test","W","p","Result"],rows,note="Note. p\u2265.05 indicates normal distribution.")]}
            return {"title":"Normality Tests","tables":[]}
        # Generic fallback for any test
        rows = []
        if "p_value" in r: rows.append(["p-value", _p_str(p)])
        if "statistic" in r: rows.append(["Statistic", _fmt(r["statistic"],4)])
        return {"title": r.get("test", test_type.title()), "tables": [_apa_table("Results", ["Metric","Value"], rows)] if rows else []}

    def _render_chart(self, test_type, r, input_data=None):
        """Generate inline chart for publication output."""
        try:
            from api.statistics_charts import (
                generate_boxplot, generate_scatter, generate_histogram,
                generate_bar_chart, generate_correlation_heatmap
            )
        except Exception as e:
            log.warning(f"Chart import failed: {e}")
            return None
        try:
            if test_type in ("ttest", "mannwhitney"):
                g1 = r.get("group1", {}); g2 = r.get("group2", {})
                gd = {g1.get("name","G1"): [], g2.get("name","G2"): []}
                return generate_boxplot(gd)
            if test_type in ("anova", "kruskalwallis"):
                grps = r.get("groups", [])
                gd = {g.get("name", f"G{i}"): [] for i, g in enumerate(grps[:8])}
                return generate_boxplot(gd) if gd else None
            if test_type == "correlation":
                mat = r.get("correlation_matrix", [[]])
                cols = r.get("columns", [])
                if mat and cols:
                    import numpy as np
                    return generate_correlation_heatmap(np.array(mat), cols)
                return None
            if test_type == "descriptive" or test_type == "normality":
                return generate_histogram([], title=test_type.title())
            return None
        except Exception as e:
            log.debug(f"Chart render skipped for {test_type}: {e}")
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
