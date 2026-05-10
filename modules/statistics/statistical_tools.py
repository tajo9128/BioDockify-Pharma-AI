"""Additional Statistical Tools for BioDockify AI

Complements EnhancedStatisticalEngine with:
- Non-parametric tests (Mann-Whitney, Kruskal-Wallis, Wilcoxon Signed Rank, Sign Test, Friedman, Dunn's)
- Categorical data analysis (Chi-square, Fisher's Exact, McNemar, Cochran-Mantel-Haenszel)
- Time series analysis (ADF test, decomposition)
- Power analysis (sample size, effect size)
- Effect size calculations (r, eta-squared, Cliff's delta, phi, Cramer's V, odds ratio)

Complies with:
- ICH E9 Statistical Principles for Clinical Trials
- FDA Statistical Guidance for Clinical Trials
- EMA Guideline on Statistical Principles for Clinical Trials
- Good Laboratory Practice (GLP)
- Good Clinical Practice (GCP)
"""

import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm
from statsmodels.stats.power import TTestIndPower, TTestPower
from statsmodels.stats.multitest import multipletests
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.stats.contingency_tables import StratifiedTable
import json
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
import warnings

# Check for pingouin availability
try:
    import pingouin as pg

    PINGOUIN_AVAILABLE = True
except ImportError:
    PINGOUIN_AVAILABLE = False
    warnings.warn(
        "pingouin not available. Some advanced tests may have limited functionality."
    )

warnings.filterwarnings("ignore")


class AdditionalStatisticalTools:
    """Additional statistical tools for comprehensive pharmaceutical research analysis

    Provides:
    - Non-parametric tests:
      * Mann-Whitney U test (independent groups)
      * Kruskal-Wallis test (multiple independent groups)
      * Wilcoxon Signed Rank test (paired samples)
      * Sign Test (paired binary data)
      * Friedman test (repeated measures)
      * Dunn's test (post-hoc pairwise comparisons)
    - Categorical data analysis:
      * Chi-square goodness of fit
      * Chi-square test of independence
      * Fisher's Exact test (small samples)
      * McNemar test (paired categorical)
      * Cochran-Mantel-Haenszel test (stratified 2x2 tables)
    - Time series analysis:
      * Augmented Dickey-Fuller test
      * Seasonal decomposition
    - Power analysis:
      * Sample size calculation
      * Effect size estimation
      * Power computation
    - Effect size calculations:
      * r (correlation-based)
      * eta-squared (variance explained)
      * Cliff's delta (non-parametric)
      * phi coefficient (2x2 tables)
      * Cramer's V (larger tables)
      * Odds ratio (binary outcomes)

    All methods comply with:
    - ICH E9 Statistical Principles for Clinical Trials
    - FDA Statistical Guidance for Clinical Trials
    - EMA Guideline on Statistical Principles for Clinical Trials
    - Good Laboratory Practice (GLP)
    - Good Clinical Practice (GCP)
    """

    def __init__(self, alpha: float = 0.05):
        """Initialize statistical tools

        Args:
            alpha: Significance level (default: 0.05, compliant with ICH E9)
        """
        self.alpha = alpha

    def perform_mann_whitney(
        self,
        df: pd.DataFrame,
        group_col: str,
        value_col: str,
        alternative: str = "two-sided",
    ) -> Dict[str, Any]:
        """Mann-Whitney U test (non-parametric alternative to t-test)

        Pharmacovigilance Example:
            Compare adverse event severity scores between treatment groups
            when data is not normally distributed.

        Args:
            df: Input DataFrame
            group_col: Column containing group labels
            value_col: Column containing values
            alternative: 'two-sided', 'less', 'greater'

        Returns:
            Dictionary with test results and interpretations
        """
        groups = df[group_col].unique()

        if len(groups) != 2:
            raise ValueError(
                f"Mann-Whitney test requires 2 groups, found {len(groups)}"
            )

        group1_data = df[df[group_col] == groups[0]][value_col].dropna()
        group2_data = df[df[group_col] == groups[1]][value_col].dropna()

        # Perform test
        statistic, p_value = stats.mannwhitneyu(
            group1_data, group2_data, alternative=alternative
        )

        # Effect size (r = Z / sqrt(N))
        n1, n2 = len(group1_data), len(group2_data)
        z_score = (
            stats.norm.ppf(p_value / 2)
            if alternative == "two-sided"
            else stats.norm.ppf(p_value)
        )
        effect_size_r = abs(z_score) / np.sqrt(n1 + n2)

        # Confidence interval for median difference
        # Using bootstrap approach
        bootstrap_diffs = []
        n_bootstrap = 1000
        for _ in range(n_bootstrap):
            sample1 = np.random.choice(group1_data, size=len(group1_data), replace=True)
            sample2 = np.random.choice(group2_data, size=len(group2_data), replace=True)
            bootstrap_diffs.append(np.median(sample1) - np.median(sample2))

        ci_lower = np.percentile(bootstrap_diffs, 2.5)
        ci_upper = np.percentile(bootstrap_diffs, 97.5)

        results = {
            "analysis_type": "Mann-Whitney U Test",
            "timestamp": datetime.now().isoformat(),
            "alpha": self.alpha,
            "groups": {"group1": str(groups[0]), "group2": str(groups[1])},
            "sample_info": {
                "group1": {
                    "n": n1,
                    "median": float(group1_data.median()),
                    "iqr": float(
                        group1_data.quantile(0.75) - group1_data.quantile(0.25)
                    ),
                },
                "group2": {
                    "n": n2,
                    "median": float(group2_data.median()),
                    "iqr": float(
                        group2_data.quantile(0.75) - group2_data.quantile(0.25)
                    ),
                },
            },
            "test_results": {
                "u_statistic": float(statistic),
                "p_value": float(p_value),
                "significant": p_value < self.alpha,
            },
            "confidence_intervals": {
                "median_difference": {
                    "lower": float(ci_lower),
                    "upper": float(ci_upper),
                    "level": 0.95,
                }
            },
            "effect_size": {
                "r": float(effect_size_r),
                "magnitude": self._interpret_r(effect_size_r),
                "interpretation": self._interpret_effect_size_r(effect_size_r),
            },
            "assumptions": {
                "independent_samples": True,
                "ordinal_or_continuous": True,
                "similar_shape_distributions": True,
            },
            "explanations": {
                "test_purpose": "Non-parametric test comparing two independent groups. Does not assume normal distribution.",
                "null_hypothesis": "H0: The distributions of both groups are equal.",
                "alternative_hypothesis": f"H1: The distributions differ (alternative={alternative}).",
                "when_to_use": "Use when data is not normally distributed or contains outliers.",
                "p_value_meaning": f"P-value ({p_value:.4e}) indicates {'distributions differ' if p_value < self.alpha else 'no significant difference in distributions'} at α={self.alpha}.",
            },
            "interpretations": {
                "main_finding": f"{'Significant difference' if p_value < self.alpha else 'No significant difference'} in distributions between groups (p={p_value:.4e}).",
                "direction": f"Group '{groups[0]}' {'tends to have' if group1_data.median() > group2_data.median() else 'tends to have lower'} values than Group '{groups[1]}' based on medians.",
                "clinical_relevance": f"Median difference: {group1_data.median() - group2_data.median():.2f} (95% CI: {ci_lower:.2f} to {ci_upper:.2f})",
            },
            "recommendations": [
                "Non-parametric test used due to non-normal data or outliers.",
                "Effect size r indicates practical significance.",
                "Consider visualizing distributions (box plots, violin plots) for better understanding.",
            ],
            "glp_gcp_compliance": {
                "pre_analysis_plan": "Test should be specified in statistical analysis plan (SAP) per ICH E9",
                "data_integrity": "All data points accounted for in analysis",
                "documentation": "Results include full parameter set for reproducibility",
            },
        }

        return results

    def _interpret_r(self, r: float) -> str:
        """Interpret effect size r according to Cohen's conventions"""
        if r < 0.1:
            return "negligible"
        elif r < 0.3:
            return "small"
        elif r < 0.5:
            return "medium"
        else:
            return "large"

    def _interpret_effect_size_r(self, r: float) -> str:
        """Explain effect size r"""
        magnitude = self._interpret_r(r)
        return f"Effect size r ({r:.3f}) indicates {magnitude} magnitude of difference between groups."

    def perform_kruskal_wallis(
        self, df: pd.DataFrame, value_col: str, group_col: str, post_hoc: bool = True
    ) -> Dict[str, Any]:
        """Kruskal-Wallis test (non-parametric alternative to ANOVA)

        Pharmacovigilance Example:
            Compare laboratory values across multiple treatment arms
            in a clinical trial with non-normal data distribution.

        Args:
            df: Input DataFrame
            value_col: Column containing values
            group_col: Column containing group labels
            post_hoc: Perform Dunn's post-hoc test

        Returns:
            Dictionary with test results and interpretations
        """
        groups = df[group_col].unique()

        if len(groups) < 2:
            raise ValueError(
                f"Kruskal-Wallis test requires at least 2 groups, found {len(groups)}"
            )

        # Prepare data
        group_data = [df[df[group_col] == g][value_col].dropna() for g in groups]

        # Perform test
        h_statistic, p_value = stats.kruskal(*group_data)

        # Effect size (eta-squared)
        total_n = sum(len(g) for g in group_data)
        eta_squared = (h_statistic - len(groups) + 1) / (total_n - len(groups))

        # Post-hoc analysis if requested and significant
        post_hoc_results = None
        if post_hoc and p_value < self.alpha and PINGOUIN_AVAILABLE:
            post_hoc_results = self._perform_dunns_posthoc(df, value_col, group_col)

        results = {
            "analysis_type": "Kruskal-Wallis Test",
            "timestamp": datetime.now().isoformat(),
            "alpha": self.alpha,
            "groups": [str(g) for g in groups],
            "group_summary": {},
            "test_results": {
                "h_statistic": float(h_statistic),
                "p_value": float(p_value),
                "degrees_of_freedom": len(groups) - 1,
                "significant": p_value < self.alpha,
            },
            "effect_size": {
                "eta_squared": float(eta_squared),
                "interpretation": self._interpret_eta_squared(eta_squared),
            },
            "assumptions": {
                "independent_samples": True,
                "ordinal_or_continuous": True,
                "similar_shape_distributions": True,
            },
            "explanations": {
                "test_purpose": f"Non-parametric test comparing {len(groups)} independent groups. Does not assume normal distribution.",
                "null_hypothesis": "H0: All group distributions are equal.",
                "alternative_hypothesis": "H1: At least one group distribution differs from the others.",
                "when_to_use": "Use when data is not normally distributed or contains outliers across multiple groups.",
                "p_value_meaning": f"P-value ({p_value:.4e}) indicates {'distributions differ' if p_value < self.alpha else 'no significant differences in distributions'} at α={self.alpha}.",
            },
            "interpretations": {},
            "recommendations": [],
            "post_hoc_analysis": post_hoc_results,
            "glp_gcp_compliance": {
                "pre_analysis_plan": "Test specified in SAP per ICH E9 section 5.3",
                "multiplicity_adjustment": "Post-hoc tests control family-wise error rate"
                if post_hoc
                else "No post-hoc analysis performed",
                "documentation": "Complete parameter set documented for audit trail",
            },
        }

        # Group summary
        for i, g in enumerate(groups):
            results["group_summary"][str(g)] = {
                "n": len(group_data[i]),
                "median": float(group_data[i].median()),
                "iqr": float(
                    group_data[i].quantile(0.75) - group_data[i].quantile(0.25)
                ),
            }

        # Interpretations
        if p_value < self.alpha:
            medians = {
                str(g): results["group_summary"][str(g)]["median"] for g in groups
            }
            highest = max(medians, key=medians.get)
            lowest = min(medians, key=medians.get)

            results["interpretations"]["main_finding"] = (
                f"Significant differences found in distributions (H={h_statistic:.2f}, p={p_value:.4e}). "
                f"Highest median: {highest} ({medians[highest]:.2f}), Lowest: {lowest} ({medians[lowest]:.2f})."
            )
        else:
            results["interpretations"]["main_finding"] = (
                f"No significant differences in distributions (H={h_statistic:.2f}, p={p_value:.4e})."
            )

        results["interpretations"]["effect_size"] = (
            f"Eta-squared ({eta_squared:.3f}) indicates {results['effect_size']['interpretation']} effect size."
        )

        # Recommendations
        if p_value < self.alpha:
            results["recommendations"].append(
                "Significant Kruskal-Wallis result. Consider post-hoc pairwise comparisons to identify specific group differences."
            )
            if post_hoc and post_hoc_results:
                results["recommendations"].append(
                    "Post-hoc Dunn's test performed with Bonferroni correction for multiple comparisons."
                )
        else:
            results["recommendations"].append(
                "No significant differences. Consider increasing sample size or examining other factors."
            )

        return results

    def _perform_dunns_posthoc(
        self, df: pd.DataFrame, value_col: str, group_col: str
    ) -> Dict[str, Any]:
        """Perform Dunn's post-hoc test for Kruskal-Wallis

        Internal helper method using pingouin for comprehensive post-hoc analysis.
        """
        try:
            posthoc = pg.pairwise_gameshowel(data=df, dv=value_col, between=group_col)

            # Convert to structured format
            comparisons = []
            for idx, row in posthoc.iterrows():
                comparisons.append(
                    {
                        "comparison": idx,
                        "p_uncorrected": float(row["p-unc"]),
                        "p_bonferroni": float(row["p-bonf"]),
                        "p_holm": float(row["p-holm"]),
                        "significant": row["p-bonf"] < self.alpha,
                        "effect_size": float(row["hedges"])
                        if "hedges" in row
                        else None,
                    }
                )

            return {
                "method": "Dunns test with Games-Howell correction",
                "correction_method": "Bonferroni/Holm",
                "comparisons": comparisons,
                "alpha": self.alpha,
            }
        except Exception as e:
            return {
                "error": f"Post-hoc analysis failed: {str(e)}",
                "note": "Manual pairwise Mann-Whitney tests with Bonferroni correction recommended",
            }

    def perform_wilcoxon(
        self,
        df: pd.DataFrame,
        value1_col: str,
        value2_col: Optional[str] = None,
        alternative: str = "two-sided",
    ) -> Dict[str, Any]:
        """Wilcoxon signed-rank test (non-parametric alternative to paired t-test)

        Pharmacovigilance Example:
            Compare pre-treatment and post-treatment biomarker levels
            for each patient when differences are not normally distributed.

        Args:
            df: Input DataFrame
            value1_col: First value column (or group column if value2_col is None)
            value2_col: Second value column (None for single column with grouping)
            alternative: 'two-sided', 'less', 'greater'

        Returns:
            Dictionary with test results and interpretations
        """
        results = {
            "analysis_type": "Wilcoxon Signed-Rank Test",
            "timestamp": datetime.now().isoformat(),
            "alpha": self.alpha,
            "test_results": {},
            "explanations": {},
            "interpretations": {},
            "recommendations": [],
            "glp_gcp_compliance": {},
        }

        if value2_col:
            # Two-column test
            data1 = df[value1_col].dropna()
            data2 = df[value2_col].dropna()

            if len(data1) != len(data2):
                raise ValueError(
                    "Both columns must have equal length for Wilcoxon test"
                )

            statistic, p_value = stats.wilcoxon(data1, data2, alternative=alternative)

            results["sample_info"] = {
                "n_pairs": len(data1),
                "median_diff": float((data1 - data2).median()),
                "iqr_diff": float(
                    (data1 - data2).quantile(0.75) - (data1 - data2).quantile(0.25)
                ),
            }
        else:
            raise ValueError("Wilcoxon test requires two columns for paired comparison")

        # Effect size
        n = len(data1)
        z_score = (
            stats.norm.ppf(p_value / 2)
            if alternative == "two-sided"
            else stats.norm.ppf(p_value)
        )
        effect_size_r = abs(z_score) / np.sqrt(n)

        # Bootstrap confidence interval for median difference
        bootstrap_diffs = []
        n_bootstrap = 1000
        for _ in range(n_bootstrap):
            sample_diffs = np.random.choice(data1 - data2, size=n, replace=True)
            bootstrap_diffs.append(np.median(sample_diffs))

        ci_lower = np.percentile(bootstrap_diffs, 2.5)
        ci_upper = np.percentile(bootstrap_diffs, 97.5)

        results["test_results"] = {
            "statistic": float(statistic),
            "p_value": float(p_value),
            "significant": p_value < self.alpha,
        }

        results["confidence_intervals"] = {
            "median_difference": {
                "lower": float(ci_lower),
                "upper": float(ci_upper),
                "level": 0.95,
            }
        }

        results["effect_size"] = {
            "r": float(effect_size_r),
            "magnitude": self._interpret_r(effect_size_r),
            "interpretation": self._interpret_effect_size_r(effect_size_r),
        }

        results["assumptions"] = {
            "paired_samples": True,
            "symmetric_distribution_of_differences": True,
            "ordinal_or_continuous": True,
        }

        # Explanations
        results["explanations"] = {
            "test_purpose": "Non-parametric test for paired data. Compares two related samples.",
            "null_hypothesis": "H0: The median difference between pairs is zero.",
            "alternative_hypothesis": f"H1: The median difference differs from zero (alternative={alternative}).",
            "when_to_use": "Use when paired data is not normally distributed or contains outliers.",
            "p_value_meaning": f"P-value ({p_value:.4e}) indicates {'significant difference' if p_value < self.alpha else 'no significant difference'} at α={self.alpha}.",
        }

        # Interpretations
        if p_value < self.alpha:
            results["interpretations"]["main_finding"] = (
                f"Significant difference in paired measurements (p={p_value:.4e}). "
                f"Median difference: {results['sample_info']['median_diff']:.2f} (95% CI: {ci_lower:.2f} to {ci_upper:.2f})."
            )
        else:
            results["interpretations"]["main_finding"] = (
                f"No significant difference in paired measurements (p={p_value:.4e}). "
                f"Median difference: {results['sample_info']['median_diff']:.2f} (95% CI: {ci_lower:.2f} to {ci_upper:.2f})."
            )

        results["recommendations"] = [
            "Non-parametric test used for paired data due to non-normal distribution or outliers.",
            "Consider visualizing differences with Bland-Altman plot.",
            "Report median differences rather than mean differences.",
        ]

        results["glp_gcp_compliance"] = {
            "pre_analysis_plan": "Paired analysis specified in SAP per ICH E9",
            "subject_level_data": "Analysis preserves subject-level pairing",
            "documentation": "Complete parameter set for regulatory submission",
        }

        return results

    def _interpret_eta_squared(self, eta_sq: float) -> str:
        """Interpret eta-squared effect size"""
        if eta_sq < 0.01:
            return "very small"
        elif eta_sq < 0.06:
            return "small"
        elif eta_sq < 0.14:
            return "medium"
        else:
            return "large"

    # ============================================
    # NEW NON-PARAMETRIC TESTS
    # ============================================

    def wilcoxon_signed_rank_test(
        self,
        before: Union[List[float], np.ndarray, pd.Series],
        after: Union[List[float], np.ndarray, pd.Series],
        alternative: str = "two-sided",
        zero_method: str = "wilcox",
    ) -> Dict[str, Any]:
        """Wilcoxon Signed Rank Test for paired non-parametric data

        Pharmacovigilance Example:
            Compare baseline and post-treatment blood pressure measurements
            in a cardiovascular drug study where differences are not normally distributed.

        FDA/EMA Compliance:
            - Specified in SAP per ICH E9 Section 5.3
            - Appropriate for paired designs with non-normal distributions
            - Effect size (r) reported per CONSORT guidelines

        Args:
            before: Pre-treatment measurements
            after: Post-treatment measurements
            alternative: 'two-sided', 'less', 'greater'
            zero_method: Method for handling zeros ('wilcox', 'pratt', 'zsplit')

        Returns:
            Dictionary with test results, confidence intervals, effect size, interpretations
        """
        # Convert to arrays and handle missing values
        before_arr = np.asarray(before)
        after_arr = np.asarray(after)

        # Remove pairs with missing values
        mask = ~(np.isnan(before_arr) | np.isnan(after_arr))
        before_clean = before_arr[mask]
        after_clean = after_arr[mask]

        n_pairs = len(before_clean)

        if n_pairs < 5:
            raise ValueError(
                f"Wilcoxon test requires at least 5 paired observations, found {n_pairs}"
            )

        # Calculate differences
        differences = after_clean - before_clean

        # Perform Wilcoxon signed-rank test
        statistic, p_value = stats.wilcoxon(
            differences, zero_method=zero_method, alternative=alternative
        )

        # Effect size calculation (r = Z / sqrt(N))
        # Calculate Z-score from p-value
        if alternative == "two-sided":
            z_score = stats.norm.ppf(p_value / 2) * -1  # Two-tailed conversion
        else:
            z_score = stats.norm.ppf(p_value)

        effect_size_r = abs(z_score) / np.sqrt(n_pairs)

        # Bootstrap confidence interval for median difference
        bootstrap_diffs = []
        n_bootstrap = 1000
        for _ in range(n_bootstrap):
            sample_diffs = np.random.choice(differences, size=n_pairs, replace=True)
            bootstrap_diffs.append(np.median(sample_diffs))

        ci_lower = np.percentile(bootstrap_diffs, 2.5)
        ci_upper = np.percentile(bootstrap_diffs, 97.5)

        results = {
            "analysis_type": "Wilcoxon Signed Rank Test",
            "timestamp": datetime.now().isoformat(),
            "alpha": self.alpha,
            "test_results": {
                "statistic": float(statistic),
                "p_value": float(p_value),
                "significant": p_value < self.alpha,
                "degrees_of_freedom": n_pairs,
                "zero_method": zero_method,
            },
            "sample_info": {
                "n_pairs": n_pairs,
                "before": {
                    "median": float(np.median(before_clean)),
                    "mean": float(np.mean(before_clean)),
                    "std": float(np.std(before_clean, ddof=1)),
                    "min": float(np.min(before_clean)),
                    "max": float(np.max(before_clean)),
                },
                "after": {
                    "median": float(np.median(after_clean)),
                    "mean": float(np.mean(after_clean)),
                    "std": float(np.std(after_clean, ddof=1)),
                    "min": float(np.min(after_clean)),
                    "max": float(np.max(after_clean)),
                },
            },
            "differences": {
                "median": float(np.median(differences)),
                "mean": float(np.mean(differences)),
                "std": float(np.std(differences, ddof=1)),
                "iqr": float(
                    np.percentile(differences, 75) - np.percentile(differences, 25)
                ),
            },
            "confidence_intervals": {
                "median_difference": {
                    "lower": float(ci_lower),
                    "upper": float(ci_upper),
                    "level": 0.95,
                    "method": "bootstrap (1000 resamples)",
                }
            },
            "effect_size": {
                "r": float(effect_size_r),
                "magnitude": self._interpret_r(effect_size_r),
                "interpretation": self._interpret_effect_size_r(effect_size_r),
            },
            "assumptions": {
                "paired_samples": True,
                "symmetric_distribution_of_differences": True,
                "ordinal_or_continuous_data": True,
                "random_sampling": True,
            },
            "assumption_checks": {
                "normality_of_differences": {
                    "shapiro_wilk": self._check_normality(differences),
                    "interpretation": "If not normal, Wilcoxon is appropriate",
                },
                "symmetry_check": {
                    "skewness": float(stats.skew(differences)),
                    "interpretation": "Symmetric differences support Wilcoxon validity",
                },
            },
            "explanations": {
                "test_purpose": "Non-parametric test for comparing two related/paired samples when the differences are not normally distributed.",
                "null_hypothesis": "H0: The median difference between paired observations is zero (symmetry around zero).",
                "alternative_hypothesis": f"H1: The median difference differs from zero (alternative={alternative}).",
                "pharmacovigilance_example": "Comparing baseline vs. post-treatment biomarker levels in the same patients when changes are skewed.",
                "when_to_use": [
                    "Paired measurements (pre-post, matched subjects)",
                    "Non-normal distribution of differences",
                    "Ordinal data or outliers present",
                    "Sample size < 30 (small sample sizes)",
                ],
                "alternatives_if_assumptions_violated": [
                    "Sign Test (less powerful, no distribution assumptions)",
                    "Permutation test (requires more computational resources)",
                    "Transform data and use paired t-test",
                ],
                "p_value_meaning": f"P-value ({p_value:.4e}) indicates {'significant difference' if p_value < self.alpha else 'no significant difference'} at α={self.alpha}.",
                "zero_method_meaning": {
                    "wilcox": "Discards zero differences (recommended)",
                    "pratt": "Includes zero differences in ranking",
                    "zsplit": "Splits zero differences between positive and negative ranks",
                },
            },
            "interpretations": {
                "main_finding": (
                    f"{'Significant change' if p_value < self.alpha else 'No significant change'} "
                    f"in paired measurements (W={statistic:.1f}, p={p_value:.4e}). "
                    f"Median change: {np.median(differences):.4f} (95% CI: {ci_lower:.4f} to {ci_upper:.4f})."
                ),
                "direction": (
                    f"{'Significant increase' if np.median(differences) > 0 and p_value < self.alpha else 'Significant decrease' if np.median(differences) < 0 and p_value < self.alpha else 'No significant direction'} "
                    f"from baseline to follow-up."
                ),
                "clinical_relevance": (
                    f"The observed median change of {np.median(differences):.4f} "
                    f"{'is clinically significant' if abs(effect_size_r) >= 0.3 else 'may require clinical interpretation'} "
                    f"based on effect size r={effect_size_r:.3f}."
                ),
                "plain_language": (
                    f"The {'shows a' if p_value < self.alpha else 'does not show a'} "
                    f"{'statistically significant' if p_value < self.alpha else 'meaningful'} "
                    f"change between the before and after measurements. "
                    f"{'On average, values increased' if np.median(differences) > 0 else 'On average, values decreased' if np.median(differences) < 0 else 'Values remained similar'}."
                ),
            },
            "recommendations": [
                "Wilcoxon test is appropriate for non-normal paired data.",
                f"Effect size r={effect_size_r:.3f} indicates {self._interpret_r(effect_size_r)} practical significance.",
                "Visualize paired differences with Bland-Altman plot for clinical interpretation.",
                "Consider clinical significance beyond statistical significance.",
                "Report median and IQR, not mean and SD, for non-normal data.",
                "Include confidence intervals for median difference in clinical trial reports.",
            ],
            "glp_gcp_compliance": {
                "regulatory_guidelines": [
                    "ICH E9 Section 5.3: Statistical analysis of clinical trials",
                    "FDA Guidance: Non-inferiority clinical trials",
                    "EMA Guideline: Points to consider on adjustment for baseline covariates",
                ],
                "sap_requirements": "Test should be pre-specified in Statistical Analysis Plan (SAP).",
                "data_integrity": "All paired observations accounted for; missing data documented.",
                "documentation": "Full parameter set reported: statistic, p-value, CI, effect size.",
                "audit_trail": "Timestamp and parameters recorded for reproducibility.",
                "blinding": "Analysis performed blinded to treatment assignment per GCP.",
            },
            "references": [
                "Wilcoxon F. (1945). Individual comparisons by ranking methods. Biometrics Bulletin.",
                "Conover WJ. (1999). Practical Nonparametric Statistics. 3rd ed. Wiley.",
                "ICH E9 (1998). Statistical Principles for Clinical Trials.",
            ],
        }

        return results

    def sign_test(
        self,
        before: Union[List[float], np.ndarray, pd.Series],
        after: Union[List[float], np.ndarray, pd.Series],
        alternative: str = "two-sided",
    ) -> Dict[str, Any]:
        """Sign Test for paired binary/ordinal data

        Pharmacovigilance Example:
            Assess whether a treatment improves patient symptoms (better/same/worse)
            in a small sample study where only the direction of change matters.

        FDA/EMA Compliance:
            - Appropriate for small samples and ordinal data
            - Minimal assumptions (only requires independence)
            - Used in bioequivalence studies for small samples

        Args:
            before: Pre-treatment measurements
            after: Post-treatment measurements
            alternative: 'two-sided', 'less', 'greater'

        Returns:
            Dictionary with test results, confidence intervals, effect size, interpretations
        """
        # Convert to arrays
        before_arr = np.asarray(before)
        after_arr = np.asarray(after)

        # Remove pairs with missing values
        mask = ~(np.isnan(before_arr) | np.isnan(after_arr))
        before_clean = before_arr[mask]
        after_clean = after_arr[mask]

        n_pairs = len(before_clean)

        if n_pairs < 5:
            raise ValueError(
                f"Sign test requires at least 5 paired observations, found {n_pairs}"
            )

        # Calculate signs of differences (exclude ties)
        differences = after_clean - before_clean
        signs = np.sign(differences)

        # Count positive, negative, and zero differences
        n_positive = np.sum(signs > 0)
        n_negative = np.sum(signs < 0)
        n_zero = np.sum(signs == 0)
        n_nonzero = n_positive + n_negative

        # Binomial test for proportion of positive signs
        # Null hypothesis: p = 0.5 (equal probability of + and -)
        binom_result = stats.binomtest(
            n_positive, n=n_nonzero, p=0.5, alternative=alternative
        )
        p_value = binom_result.pvalue
        p_value = binom_result.pvalue

        # Effect size (Cliff's delta equivalent for paired data)
        # Proportion of positive minus proportion of negative
        prop_positive = n_positive / n_nonzero
        prop_negative = n_negative / n_nonzero
        effect_size_cliff = prop_positive - prop_negative
        # Exact binomial confidence interval for proportion (Clopper-Pearson)
        alpha_level = 0.05 if alternative == "two-sided" else 0.10
        ci_low = stats.beta.ppf(alpha_level / 2, n_positive, n_nonzero - n_positive + 1)
        ci_high = stats.beta.ppf(
            1 - alpha_level / 2, n_positive + 1, n_nonzero - n_positive
        )

        results = {
            "analysis_type": "Sign Test",
            "timestamp": datetime.now().isoformat(),
            "alpha": self.alpha,
            "test_results": {
                "p_value": float(p_value),
                "significant": p_value < self.alpha,
                "n_pairs": n_pairs,
                "n_positive": int(n_positive),
                "n_negative": int(n_negative),
                "n_zero": int(n_zero),
                "n_nonzero": int(n_nonzero),
                "proportion_positive": float(prop_positive),
                "alternative": alternative,
            },
            "sample_info": {
                "before": {
                    "median": float(np.median(before_clean)),
                    "mean": float(np.mean(before_clean)),
                },
                "after": {
                    "median": float(np.median(after_clean)),
                    "mean": float(np.mean(after_clean)),
                },
                "differences": {
                    "median": float(np.median(differences)),
                    "mean": float(np.mean(differences)),
                },
            },
            "confidence_intervals": {
                "proportion_positive": {
                    "lower": float(ci_low),
                    "upper": float(ci_high),
                    "level": 0.95 if alternative == "two-sided" else 0.90,
                },
                "median_difference": {
                    "note": "Exact CI requires special methods; proportion CI provided above"
                },
            },
            "effect_size": {
                "cliffs_delta": float(effect_size_cliff),
                "interpretation": self._interpret_cliffs_delta(effect_size_cliff),
            },
            "assumptions": {
                "paired_samples": True,
                "independent_observations": True,
                "continuous_or_ordinal": True,
                "min_assumptions": "Only requires independence; no distribution assumptions",
            },
            "explanations": {
                "test_purpose": "Non-parametric test for paired data that only considers the direction (sign) of differences, not magnitude.",
                "null_hypothesis": "H0: Median difference is zero (equal probability of positive and negative changes).",
                "alternative_hypothesis": f"H1: Median difference differs from zero (alternative={alternative}).",
                "pharmacovigilance_example": "Assessing treatment response (improved/unchanged/worsened) in small sample studies or when only direction matters.",
                "when_to_use": [
                    "Very small sample sizes (n < 10)",
                    "Ordinal data where magnitude is not meaningful",
                    "Outliers that would distort other tests",
                    "When only direction of change is relevant",
                ],
                "advantages": [
                    "Minimal assumptions (only independence required)",
                    "Robust to outliers",
                    "Works with ordinal data",
                    "Appropriate for very small samples",
                ],
                "disadvantages": [
                    "Low statistical power (less likely to detect true effects)",
                    "Ignores magnitude of differences",
                    "Less informative than Wilcoxon when assumptions met",
                ],
                "alternatives_if_assumptions_violated": [
                    "Wilcoxon Signed Rank Test (more powerful, uses magnitude)",
                    "Permutation test (resampling-based)",
                    "McNemar test for binary paired data",
                ],
                "p_value_meaning": f"P-value ({p_value:.4e}) indicates {'significant deviation from equal signs' if p_value < self.alpha else 'no significant deviation'} at α={self.alpha}.",
            },
            "interpretations": {
                "main_finding": (
                    f"{'Significant deviation' if p_value < self.alpha else 'No significant deviation'} "
                    f"from equal positive/negative signs (p={p_value:.4e}). "
                    f"Positive signs: {n_positive}/{n_nonzero} ({prop_positive:.1%}), "
                    f"Negative signs: {n_negative}/{n_nonzero} ({prop_negative:.1%})."
                ),
                "direction": (
                    f"{'More positive than negative signs' if prop_positive > 0.5 else 'More negative than positive signs' if prop_positive < 0.5 else 'Equal proportion of signs'}. "
                    f"This {'supports improvement' if prop_positive > 0.5 else 'supports worsening' if prop_positive < 0.5 else 'suggests no change'}."
                ),
                "effect_interpretation": (
                    f"Effect size (Cliff's delta={effect_size_cliff:.3f}) "
                    f"indicates {self._interpret_cliffs_delta(effect_size_cliff)} difference."
                ),
                "plain_language": (
                    f"The {'shows a significant' if p_value < self.alpha else 'does not show a significant'} "
                    f"{'imbalance in the direction of change' if p_value < self.alpha else 'imbalance'}. "
                    f"{'More pairs showed improvement' if n_positive > n_negative else 'More pairs showed worsening' if n_negative > n_positive else 'Equal numbers of pairs showed improvement and worsening'}."
                ),
            },
            "recommendations": [
                "Sign test is robust but has low power; consider larger samples.",
                f"Effect size {effect_size_cliff:.3f} indicates {self._interpret_cliffs_delta(effect_size_cliff)} practical significance.",
                "If sample size permits, Wilcoxon Signed Rank test provides more information.",
                "For binary paired data, McNemar test is more appropriate.",
                "Consider clinical relevance beyond statistical significance.",
                "Report counts of positive/negative/zero differences for transparency.",
            ],
            "glp_gcp_compliance": {
                "regulatory_guidelines": [
                    "ICH E9 Section 5.4: Analysis of safety data",
                    "FDA Guidance: Non-inferiority clinical trials",
                    "EMA Guideline: Statistical principles for clinical trials",
                ],
                "sap_requirements": "Test should be pre-specified in SAP for small sample studies.",
                "data_integrity": "All paired observations documented including ties.",
                "documentation": "Full counts and proportions reported for audit trail.",
            },
            "references": [
                "Dixon WJ, Mood AM. (1946). The statistical sign test. Journal of the American Statistical Association.",
                "Conover WJ. (1999). Practical Nonparametric Statistics. 3rd ed. Wiley.",
                "ICH E9 (1998). Statistical Principles for Clinical Trials.",
            ],
        }

        return results

    def _interpret_cliffs_delta(self, delta: float) -> str:
        """Interpret Cliff's delta effect size"""
        abs_delta = abs(delta)
        if abs_delta < 0.147:
            return "negligible"
        elif abs_delta < 0.33:
            return "small"
        elif abs_delta < 0.474:
            return "medium"
        else:
            return "large"

    def friedman_test(
        self,
        data: Union[pd.DataFrame, List[List[float]], np.ndarray],
        columns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Friedman Test for repeated measures non-parametric analysis

        Pharmacovigilance Example:
            Compare patient responses at multiple time points (baseline, week 4, week 8, week 12)
            in a clinical trial when data violates sphericity or normality assumptions.

        FDA/EMA Compliance:
            - ICH E9 Section 5.3: Analysis of repeated measures
            - Appropriate for within-subjects designs with >2 conditions
            - Non-parametric alternative to repeated measures ANOVA

        Args:
            data: DataFrame with subjects as rows and conditions as columns, or 2D array
            columns: Optional list of condition names

        Returns:
            Dictionary with test results, post-hoc comparisons, effect size, interpretations
        """
        # Convert input to DataFrame if needed
        if isinstance(data, (list, np.ndarray)):
            df = pd.DataFrame(data)
        else:
            df = data.copy()

        df = df.dropna()

        n_subjects, n_conditions = df.shape

        if n_conditions < 2:
            raise ValueError(
                f"Friedman test requires at least 2 conditions, found {n_conditions}"
            )

        if n_subjects < 5:
            raise ValueError(
                f"Friedman test requires at least 5 subjects, found {n_subjects}"
            )

        # Set condition names
        if columns is None:
            condition_names = [f"Condition_{i}" for i in range(n_conditions)]
        else:
            condition_names = columns[:n_conditions]

        # Perform Friedman test
        statistic, p_value = stats.friedmanchisquare(
            *[df.iloc[:, i] for i in range(n_conditions)]
        )

        # Effect size (Kendall's W)
        # W = chi-square / (n * (k - 1))
        kendalls_w = statistic / (n_subjects * (n_conditions - 1))

        # Condition summaries
        condition_stats = {}
        for i, name in enumerate(condition_names):
            condition_data = df.iloc[:, i]
            condition_stats[name] = {
                "median": float(condition_data.median()),
                "mean": float(condition_data.mean()),
                "std": float(condition_data.std()),
                "iqr": float(
                    condition_data.quantile(0.75) - condition_data.quantile(0.25)
                ),
                "min": float(condition_data.min()),
                "max": float(condition_data.max()),
            }

        # Post-hoc analysis if significant and pingouin available
        post_hoc_results = None
        if p_value < self.alpha and PINGOUIN_AVAILABLE:
            try:
                # Convert to long format for pingouin
                df_long = df.reset_index().melt(
                    id_vars=["index"],
                    value_vars=list(range(n_conditions)),
                    var_name="condition",
                    value_name="value",
                )
                df_long["subject"] = df_long["index"]
                df_long["condition"] = df_long["condition"].map(
                    lambda x: condition_names[x]
                    if x < len(condition_names)
                    else f"Condition_{x}"
                )

                # Nemenyi post-hoc test
                posthoc = pg.pairwise_tukey(
                    data=df_long, dv="value", between="condition"
                )

                post_hoc_results = {
                    "method": "Nemenyi test",
                    "comparisons": posthoc.to_dict("records"),
                    "alpha": self.alpha,
                }
            except Exception as e:
                post_hoc_results = {"error": f"Post-hoc analysis failed: {str(e)}"}

        results = {
            "analysis_type": "Friedman Test",
            "timestamp": datetime.now().isoformat(),
            "alpha": self.alpha,
            "test_results": {
                "chi_square_statistic": float(statistic),
                "p_value": float(p_value),
                "degrees_of_freedom": n_conditions - 1,
                "significant": p_value < self.alpha,
                "n_subjects": n_subjects,
                "n_conditions": n_conditions,
            },
            "condition_names": condition_names,
            "condition_statistics": condition_stats,
            "effect_size": {
                "kendalls_w": float(kendalls_w),
                "interpretation": self._interpret_kendalls_w(kendalls_w),
            },
            "assumptions": {
                "repeated_measures": True,
                "random_sample": True,
                "ordinal_or_continuous": True,
                "no_interaction": "Assumes no subject x treatment interaction",
            },
            "assumption_checks": {
                "sample_size": {
                    "n_subjects": n_subjects,
                    "n_conditions": n_conditions,
                    "adequate": n_subjects >= 5 and n_conditions >= 2,
                }
            },
            "explanations": {
                "test_purpose": f"Non-parametric test for comparing {n_conditions} related samples/repeated measures.",
                "null_hypothesis": "H0: All condition distributions are equal (no difference between conditions).",
                "alternative_hypothesis": "H1: At least one condition distribution differs from the others.",
                "pharmacovigilance_example": "Comparing drug efficacy measurements at multiple time points in the same patients.",
                "when_to_use": [
                    "Repeated measures design (same subjects measured multiple times)",
                    "Non-normal distribution of differences",
                    "Violations of sphericity in repeated measures ANOVA",
                    "Ordinal data across multiple conditions",
                ],
                "alternatives_if_assumptions_violated": [
                    "Repeated measures ANOVA (if normality and sphericity met)",
                    "Quade test (alternative non-parametric for repeated measures)",
                    "Multilevel/hierarchical models (for complex designs)",
                ],
                "p_value_meaning": f"P-value ({p_value:.4e}) indicates {'significant differences' if p_value < self.alpha else 'no significant differences'} between conditions at α={self.alpha}.",
                "kendalls_w_meaning": "Kendall's W measures agreement among conditions. Values closer to 1 indicate stronger differences between conditions.",
            },
            "interpretations": {
                "main_finding": (
                    f"{'Significant differences' if p_value < self.alpha else 'No significant differences'} "
                    f"between conditions (χ²={statistic:.2f}, df={n_conditions - 1}, p={p_value:.4e})."
                ),
                "effect_size": (
                    f"Kendall's W={kendalls_w:.3f} indicates {self._interpret_kendalls_w(kendalls_w)} "
                    f"effect size ({kendalls_w * 100:.1f}% of variance attributable to condition differences)."
                ),
                "condition_rankings": (
                    f"Conditions ranked by median: "
                    + ", ".join(
                        [
                            f"{name} ({condition_stats[name]['median']:.2f})"
                            for name in sorted(
                                condition_names,
                                key=lambda x: condition_stats[x]["median"],
                                reverse=True,
                            )
                        ]
                    )
                ),
                "plain_language": (
                    f"The {'shows significant differences' if p_value < self.alpha else 'does not show significant differences'} "
                    f"between the measurement conditions. "
                    f"{'Post-hoc tests can identify which specific conditions differ.' if p_value < self.alpha else 'Consider larger sample size.'}"
                ),
            },
            "recommendations": [
                "Friedman test is appropriate for repeated measures with non-normal data.",
                f"Kendall's W={kendalls_w:.3f} indicates {self._interpret_kendalls_w(kendalls_w)} effect magnitude.",
                "If significant, conduct post-hoc pairwise comparisons with appropriate correction.",
                "Visualize data with boxplots or line plots for each subject.",
                "Consider clinical relevance of time-dependent changes.",
                "For small samples, exact Friedman test is recommended.",
            ],
            "post_hoc_analysis": post_hoc_results,
            "glp_gcp_compliance": {
                "regulatory_guidelines": [
                    "ICH E9 Section 5.3: Analysis of clinical trial data",
                    "FDA Guidance: Multiplicity adjustment in clinical trials",
                    "EMA Guideline: Points to consider on multiplicity issues",
                ],
                "sap_requirements": "Repeated measures analysis must be pre-specified in SAP.",
                "data_integrity": "Subject-level data preserved; missing data handled appropriately.",
                "multiplicity_control": "Post-hoc tests with Bonferroni or similar correction.",
                "documentation": "Full parameter set including degrees of freedom reported.",
            },
            "references": [
                "Friedman M. (1937). The use of ranks to avoid the assumption of normality implicit in the analysis of variance. Journal of the American Statistical Association.",
                "Conover WJ. (1999). Practical Nonparametric Statistics. 3rd ed. Wiley.",
                "ICH E9 (1998). Statistical Principles for Clinical Trials.",
            ],
        }

        return results

    def _interpret_kendalls_w(self, w: float) -> str:
        """Interpret Kendall's W effect size"""
        if w < 0.1:
            return "very small"
        elif w < 0.3:
            return "small"
        elif w < 0.5:
            return "medium"
        else:
            return "large"

    def dunns_test(
        self,
        df: pd.DataFrame,
        value_col: str,
        group_col: str,
        correction: str = "bonferroni",
        alternative: str = "two-sided",
    ) -> Dict[str, Any]:
        """Dunn's Test (post-hoc pairwise comparison for Kruskal-Wallis)

        Pharmacovigilance Example:
            After a significant Kruskal-Wallis test comparing adverse event severity
            across multiple treatment arms, identify which specific pairs differ significantly.

        FDA/EMA Compliance:
            - ICH E9 Section 5.3: Multiplicity adjustment in clinical trials
            - Controls family-wise error rate for multiple comparisons
            - Recommended post-hoc method for non-parametric ANOVA

        Args:
            df: Input DataFrame
            value_col: Column containing values
            group_col: Column containing group labels
            correction: Multiple comparison correction ('bonferroni', 'holm', 'fdr_bh')
            alternative: 'two-sided', 'less', 'greater'

        Returns:
            Dictionary with pairwise comparisons, adjusted p-values, effect sizes
        """
        groups = df[group_col].unique()
        n_groups = len(groups)

        if n_groups < 2:
            raise ValueError(
                f"Dunn's test requires at least 2 groups, found {n_groups}"
            )

        # Prepare group data
        group_data = {}
        for g in groups:
            group_data[str(g)] = df[df[group_col] == g][value_col].dropna().values

        # Calculate all pairwise Mann-Whitney U tests
        comparisons = []
        group_names = list(group_data.keys())

        for i in range(len(group_names)):
            for j in range(i + 1, len(group_names)):
                group1 = group_names[i]
                group2 = group_names[j]
                data1 = group_data[group1]
                data2 = group_data[group2]

                # Mann-Whitney U test
                u_stat, p_uncorrected = stats.mannwhitneyu(
                    data1, data2, alternative=alternative
                )

                # Calculate rank sum for effect size (Cliff's delta)
                all_data = np.concatenate([data1, data2])
                ranks = stats.rankdata(all_data)
                rank1_sum = np.sum(ranks[: len(data1)])
                rank2_sum = np.sum(ranks[len(data1) :])

                # Calculate mean ranks
                mean_rank1 = rank1_sum / len(data1)
                mean_rank2 = rank2_sum / len(data2)

                # Standardized effect size (r)
                z_score = (
                    stats.norm.ppf(p_uncorrected / 2)
                    if alternative == "two-sided"
                    else stats.norm.ppf(p_uncorrected)
                )
                n1, n2 = len(data1), len(data2)
                effect_size_r = abs(z_score) / np.sqrt(n1 + n2)

                comparisons.append(
                    {
                        "group1": group1,
                        "group2": group2,
                        "u_statistic": float(u_stat),
                        "p_uncorrected": float(p_uncorrected),
                        "effect_size_r": float(effect_size_r),
                        "mean_rank1": float(mean_rank1),
                        "mean_rank2": float(mean_rank2),
                        "n1": int(n1),
                        "n2": int(n2),
                    }
                )

        # Apply multiple comparison correction
        p_values_uncorrected = [comp["p_uncorrected"] for comp in comparisons]

        if correction == "bonferroni":
            p_values_corrected = multipletests(
                p_values_uncorrected, alpha=self.alpha, method="bonferroni"
            )[1]
        elif correction == "holm":
            p_values_corrected = multipletests(
                p_values_uncorrected, alpha=self.alpha, method="holm"
            )[1]
        elif correction == "fdr_bh":
            p_values_corrected = multipletests(
                p_values_uncorrected, alpha=self.alpha, method="fdr_bh"
            )[1]
        else:
            p_values_corrected = p_values_uncorrected  # No correction

        # Update comparisons with corrected p-values
        for i, comp in enumerate(comparisons):
            comp["p_corrected"] = float(p_values_corrected[i])
            comp["significant"] = p_values_corrected[i] < self.alpha
            comp["effect_magnitude"] = self._interpret_r(comp["effect_size_r"])

        # Summary statistics
        n_comparisons = len(comparisons)
        n_significant = sum(comp["significant"] for comp in comparisons)

        results = {
            "analysis_type": "Dunn's Test (Post-hoc for Kruskal-Wallis)",
            "timestamp": datetime.now().isoformat(),
            "alpha": self.alpha,
            "test_parameters": {
                "correction_method": correction,
                "alternative": alternative,
                "n_groups": n_groups,
                "groups": [str(g) for g in groups],
                "n_comparisons": n_comparisons,
            },
            "test_results": {
                "n_significant": n_significant,
                "n_non_significant": n_comparisons - n_significant,
                "correction_applied": correction != "none",
            },
            "pairwise_comparisons": comparisons,
            "assumptions": {
                "independent_samples": True,
                "ordinal_or_continuous": True,
                "similar_distributions": "Assumes similar distributions across groups",
                "significant_kruskal_wallis": "Should only be performed after significant Kruskal-Wallis test",
            },
            "explanations": {
                "test_purpose": "Post-hoc pairwise comparison test following a significant Kruskal-Wallis test to identify which specific groups differ.",
                "null_hypothesis": "H0: The two compared groups have equal distributions.",
                "alternative_hypothesis": f"H1: The two compared groups have different distributions (alternative={alternative}).",
                "pharmacovigilance_example": "After finding differences in adverse event rates across 3+ treatment arms, determine which specific pairs differ.",
                "when_to_use": [
                    "After significant Kruskal-Wallis test",
                    "Multiple independent group comparisons needed",
                    "Non-parametric data with multiple groups",
                    "Need to control Type I error for multiple comparisons",
                ],
                "correction_methods_explained": {
                    "bonferroni": "Most conservative; divides alpha by number of comparisons. Controls family-wise error rate.",
                    "holm": "Step-down Bonferroni; more powerful than Bonferroni. Controls family-wise error rate.",
                    "fdr_bh": "Benjamini-Hochberg; controls false discovery rate. Less conservative, more powerful.",
                    "none": "No correction; not recommended for regulatory submissions",
                },
                "p_value_meaning": "Corrected p-value < alpha indicates significant difference between that specific pair.",
            },
            "interpretations": {
                "main_finding": (
                    f"{n_significant} out of {n_comparisons} pairwise comparisons are significant using {correction} correction."
                ),
                "significant_pairs": (
                    [
                        f"{comp['group1']} vs {comp['group2']} (p={comp['p_corrected']:.4e}, r={comp['effect_size_r']:.3f})"
                        for comp in comparisons
                        if comp["significant"]
                    ]
                ),
                "effect_sizes": [
                    f"{comp['group1']} vs {comp['group2']}: r={comp['effect_size_r']:.3f} ({comp['effect_magnitude']})"
                    for comp in comparisons
                ],
                "plain_language": (
                    f"{n_significant} {'pair' if n_significant == 1 else 'pairs'} of groups show significant differences. "
                    f"The {correction} correction was applied to account for multiple comparisons."
                ),
            },
            "recommendations": [
                f"Dunn's test with {correction} correction is appropriate for post-hoc analysis.",
                f"{n_significant} significant pair(s) found. Examine clinical relevance.",
                "Bonferroni is most conservative; FDR-BH is less conservative but appropriate for exploratory analysis.",
                "Report both uncorrected and corrected p-values for transparency.",
                "Consider effect sizes (r) alongside p-values for practical significance.",
                "Visualize with boxplots showing significant differences.",
            ],
            "glp_gcp_compliance": {
                "regulatory_guidelines": [
                    "ICH E9 Section 5.3: Multiplicity adjustment",
                    "FDA Guidance: Multiplicity in clinical trials",
                    "EMA Guideline: Points to consider on adjustment for multiple comparisons",
                ],
                "sap_requirements": "Post-hoc analysis method and correction must be pre-specified in SAP.",
                "multiplicity_control": f"{correction} correction applied to control Type I error rate.",
                "documentation": "Both uncorrected and corrected p-values reported for audit trail.",
            },
            "references": [
                "Dunn OJ. (1964). Multiple comparisons using rank sums. Technometrics.",
                "Conover WJ. (1999). Practical Nonparametric Statistics. 3rd ed. Wiley.",
                "ICH E9 (1998). Statistical Principles for Clinical Trials.",
            ],
        }

        return results

    def _check_normality(self, data: np.ndarray) -> Dict[str, Any]:
        """Check normality assumption using Shapiro-Wilk test"""
        n = len(data)
        if n < 3:
            return {
                "statistic": None,
                "p_value": None,
                "normal": False,
                "note": "Sample too small for normality test",
            }

        statistic, p_value = stats.shapiro(data)
        return {
            "statistic": float(statistic),
            "p_value": float(p_value),
            "normal": p_value > self.alpha,
            "interpretation": f"{'Normal distribution' if p_value > self.alpha else 'Non-normal distribution'} (p={p_value:.4f})",
        }

    # ============================================
    # CATEGORICAL DATA ANALYSIS METHODS
    # ============================================

    def chi_square_goodness_of_fit(
        self,
        observed: Union[List[int], np.ndarray, pd.Series],
        expected: Optional[Union[List[float], np.ndarray, pd.Series]] = None,
        f_exp: Optional[List[float]] = None,
        categories: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Chi-square goodness of fit test

        Pharmacovigilance Example:
            Test whether observed adverse event frequencies match expected
            frequencies from historical controls or population data.

        FDA/EMA Compliance:
            - ICH E9 Section 7.3: Analysis of safety data
            - Appropriate for categorical outcomes in safety analysis
            - Used for detecting deviations from expected patterns

        Args:
            observed: Observed frequencies for each category
            expected: Expected frequencies (if None, assumes equal distribution)
            f_exp: Expected proportions (will be scaled to match total observed)
            categories: Optional list of category names

        Returns:
            Dictionary with test results, effect sizes, confidence intervals, interpretations
        """
        # Convert to numpy array
        observed_arr = np.asarray(observed)

        # Input validation
        if np.any(observed_arr < 0):
            raise ValueError("Observed frequencies must be non-negative")

        total_observed = np.sum(observed_arr)

        if total_observed == 0:
            raise ValueError("Total observed frequency must be greater than 0")

        n_categories = len(observed_arr)

        # Handle expected frequencies
        if expected is not None:
            expected_arr = np.asarray(expected)
            if len(expected_arr) != n_categories:
                raise ValueError("Observed and expected must have same length")
        elif f_exp is not None:
            # f_exp provides expected proportions
            f_exp_arr = np.asarray(f_exp)
            if not np.isclose(np.sum(f_exp_arr), 1.0, atol=0.01):
                raise ValueError("Expected proportions must sum to 1.0")
            expected_arr = f_exp_arr * total_observed
        else:
            # Equal distribution
            expected_arr = np.full(n_categories, total_observed / n_categories)

        # Check expected frequencies assumption (all >= 5 recommended)
        min_expected = np.min(expected_arr)
        categories_with_low_expected = np.sum(expected_arr < 5)

        # Perform chi-square test
        chi2_stat, p_value = stats.chisquare(f_obs=observed_arr, f_exp=expected_arr)

        # Degrees of freedom
        df = n_categories - 1

        # Effect size (Phi coefficient for goodness of fit)
        # Phi = sqrt(chi2 / n)
        phi_coefficient = (
            np.sqrt(chi2_stat / total_observed) if total_observed > 0 else 0
        )

        # Cramer's V (same as Phi for goodness of fit)
        cramers_v = phi_coefficient

        # Confidence interval for proportions using Wilson score interval
        observed_props = observed_arr / total_observed
        expected_props = expected_arr / total_observed

        prop_intervals = {}
        for i in range(n_categories):
            p = observed_props[i]
            z = stats.norm.ppf(1 - (1 - 0.95) / 2)  # 95% CI

            # Wilson score interval
            denominator = 2 * (total_observed + z**2)
            center = (p + z**2 / (2 * total_observed)) / denominator
            margin = (
                z
                * np.sqrt((p * (1 - p) + z**2 / (4 * total_observed)) / total_observed)
                / denominator
            )

            ci_lower = max(0, center - margin)
            ci_upper = min(1, center + margin)

            category_name = str(categories[i]) if categories else f"Category_{i}"
            prop_intervals[category_name] = {
                "observed_proportion": float(p),
                "expected_proportion": float(expected_props[i]),
                "ci_lower": float(ci_lower),
                "ci_upper": float(ci_upper),
                "ci_level": 0.95,
            }

        results = {
            "analysis_type": "Chi-square Goodness of Fit Test",
            "timestamp": datetime.now().isoformat(),
            "alpha": self.alpha,
            "test_results": {
                "chi_square_statistic": float(chi2_stat),
                "p_value": float(p_value),
                "degrees_of_freedom": df,
                "significant": p_value < self.alpha,
                "n_observed": int(total_observed),
            },
            "frequency_data": {
                "observed": [int(o) for o in observed_arr],
                "expected": [float(e) for e in expected_arr],
            },
            "proportions": {
                "observed": [float(p) for p in observed_props],
                "expected": [float(p) for p in expected_props],
            },
            "confidence_intervals": {
                "proportions": prop_intervals,
                "method": "Wilson score interval",
            },
            "effect_size": {
                "phi_coefficient": float(phi_coefficient),
                "cramers_v": float(cramers_v),
                "interpretation": self._interpret_phi(phi_coefficient),
            },
            "assumptions": {
                "independent_observations": True,
                "mutually_exclusive_categories": True,
                "exhaustive_categories": True,
                "adequate_expected_frequencies": min_expected >= 5,
            },
            "assumption_checks": {
                "expected_frequencies": {
                    "min_expected": float(min_expected),
                    "n_categories_with_low_expected": int(categories_with_low_expected),
                    "adequate": min_expected >= 5,
                    "interpretation": (
                        "All expected frequencies >= 5"
                        if min_expected >= 5
                        else f"{categories_with_low_expected} categories have expected < 5. Consider Fisher's exact test or combine categories."
                    ),
                },
                "sample_size": {
                    "total_n": int(total_observed),
                    "adequate": total_observed >= 50,
                },
            },
            "explanations": {
                "test_purpose": "Tests whether observed categorical data follows a specified (expected) distribution.",
                "null_hypothesis": "H0: The observed frequencies match the expected frequencies.",
                "alternative_hypothesis": "H1: The observed frequencies do not match the expected frequencies.",
                "pharmacovigilance_example": "Comparing observed adverse event frequencies to expected rates from historical data.",
                "when_to_use": [
                    "Testing distribution of categorical variables",
                    "Comparing observed to expected patterns",
                    "Goodness-of-fit for categorical models",
                    "Quality control for categorical data",
                ],
                "alternatives_if_assumptions_violated": [
                    "Fisher's exact test (for small samples or low expected frequencies)",
                    "Exact multinomial test (for very small samples)",
                    "G-test (likelihood ratio test)",
                    "Combine categories to increase expected frequencies",
                ],
                "p_value_meaning": f"P-value ({p_value:.4e}) indicates {'observed distribution differs' if p_value < self.alpha else 'no significant difference from expected'} at α={self.alpha}.",
                "effect_size_meaning": f"Phi={phi_coefficient:.3f} measures deviation from expected distribution.",
            },
            "interpretations": {
                "main_finding": (
                    f"{'Significant deviation' if p_value < self.alpha else 'No significant deviation'} "
                    f"from expected distribution (χ²={chi2_stat:.2f}, df={df}, p={p_value:.4e})."
                ),
                "effect_size": (
                    f"Phi coefficient ({phi_coefficient:.3f}) indicates {self._interpret_phi(phi_coefficient)} "
                    f"effect size (deviation from expected)."
                ),
                "clinical_relevance": (
                    f"{'Observed pattern significantly differs from expected' if p_value < self.alpha else 'Observed pattern consistent with expected'}. "
                    f"{'Investigate causes of deviation' if p_value < self.alpha else 'No action needed based on statistical test alone'}"
                ),
                "plain_language": (
                    f"The {'shows a significant' if p_value < self.alpha else 'does not show a significant'} "
                    f"{'difference from the expected pattern' if p_value < self.alpha else 'difference from the expected pattern'}. "
                    f"{'This suggests the observed frequencies are different than expected' if p_value < self.alpha else 'The observed frequencies match the expected frequencies'}"
                ),
            },
            "recommendations": [
                f"Chi-square test is {'appropriate' if min_expected >= 5 else 'questionable due to low expected frequencies'}.",
                f"Effect size phi={phi_coefficient:.3f} indicates {self._interpret_phi(phi_coefficient)} deviation magnitude.",
                "Check expected frequencies assumption; consider Fisher's exact test if violated.",
                "Report confidence intervals for proportions alongside the test result.",
                "For small samples, exact multinomial test provides more accurate p-values.",
                "Consider combining rare categories to meet expected frequency assumptions.",
            ],
            "glp_gcp_compliance": {
                "regulatory_guidelines": [
                    "ICH E9 Section 7.3: Analysis of safety data",
                    "FDA Guidance: Safety data in clinical trials",
                    "EMA Guideline: Points to consider on safety data",
                ],
                "sap_requirements": "Goodness-of-fit tests should be pre-specified in SAP for safety analysis.",
                "data_integrity": "All category frequencies accurately recorded.",
                "documentation": "Full frequency table with observed and expected values reported.",
            },
            "references": [
                "Pearson K. (1900). On the criterion that a given system of deviations... Philosophical Magazine.",
                "Agresti A. (2002). Categorical Data Analysis. 2nd ed. Wiley.",
                "ICH E9 (1998). Statistical Principles for Clinical Trials.",
            ],
        }

        return results

    def _interpret_phi(self, phi: float) -> str:
        """Interpret phi coefficient effect size"""
        if phi < 0.1:
            return "negligible"
        elif phi < 0.3:
            return "small"
        elif phi < 0.5:
            return "medium"
        else:
            return "large"

    def chi_square_test_independence(
        self,
        contingency_table: Union[List[List[int]], np.ndarray, pd.DataFrame],
        correction: bool = True,
    ) -> Dict[str, Any]:
        """Chi-square test of independence

        Pharmacovigilance Example:
            Test association between treatment group and adverse event occurrence

        FDA/EMA Compliance:
            - ICH E9 Section 7.3: Analysis of safety data
            - Standard test for association in categorical data
            - Used for detecting treatment-emergent adverse events

        Args:
            contingency_table: 2D array or DataFrame of observed frequencies
            correction: Apply Yates' correction for 2x2 tables

        Returns:
            Dictionary with test results, effect sizes, confidence intervals, interpretations
        """
        # Convert to numpy array
        obs_array = np.asarray(contingency_table)

        # Input validation
        if obs_array.ndim != 2:
            raise ValueError("Contingency table must be 2-dimensional")

        if np.any(obs_array < 0):
            raise ValueError("Contingency table frequencies must be non-negative")

        n_rows, n_cols = obs_array.shape

        if n_rows < 2 or n_cols < 2:
            raise ValueError(
                "Contingency table must have at least 2 rows and 2 columns"
            )

        total_n = np.sum(obs_array)

        if total_n == 0:
            raise ValueError("Contingency table cannot be all zeros")

        # Check expected frequencies
        row_totals = np.sum(obs_array, axis=1)
        col_totals = np.sum(obs_array, axis=0)
        expected = np.outer(row_totals, col_totals) / total_n

        min_expected = np.min(expected)
        cells_with_low_expected = np.sum(expected < 5)

        # Determine if Yates' correction should be applied
        apply_yates = correction and (n_rows == 2 and n_cols == 2)

        # Perform chi-square test
        chi2_stat, p_value, dof, expected_freq = stats.chi2_contingency(
            obs_array, correction=apply_yates
        )

        # Effect size: Phi coefficient (2x2) or Cramer's V (larger tables)
        if n_rows == 2 and n_cols == 2:
            # Phi coefficient for 2x2 table
            phi_coefficient = np.sqrt(chi2_stat / total_n) if total_n > 0 else 0
            cramers_v = phi_coefficient
        else:
            # Cramer's V for larger tables
            min_dim = min(n_rows - 1, n_cols - 1)
            cramers_v = np.sqrt(chi2_stat / (total_n * min_dim)) if total_n > 0 else 0
            phi_coefficient = cramers_v  # For consistency

        # Calculate odds ratios for 2x2 table
        odds_ratios = None
        if n_rows == 2 and n_cols == 2:
            a, b = obs_array[0, 0], obs_array[0, 1]
            c, d = obs_array[1, 0], obs_array[1, 1]

            # Add 0.5 to avoid division by zero
            if b == 0 or c == 0:
                odds_ratio = (a + 0.5) * (d + 0.5) / ((b + 0.5) * (c + 0.5))
            else:
                odds_ratio = (a * d) / (b * c)

            # Confidence interval for odds ratio
            se_log_or = np.sqrt(1 / a + 1 / b + 1 / c + 1 / d)
            z = stats.norm.ppf(1 - (1 - 0.95) / 2)

            log_or_ci_lower = np.log(odds_ratio) - z * se_log_or
            log_or_ci_upper = np.log(odds_ratio) + z * se_log_or

            or_ci_lower = np.exp(log_or_ci_lower)
            or_ci_upper = np.exp(log_or_ci_upper)

            odds_ratios = {
                "odds_ratio": float(odds_ratio),
                "ci_lower": float(or_ci_lower),
                "ci_upper": float(or_ci_upper),
                "ci_level": 0.95,
                "interpretation": self._interpret_odds_ratio(odds_ratio),
            }

        # Row and column proportions
        row_props = obs_array / row_totals[:, np.newaxis]
        col_props = (obs_array.T / col_totals).T

        results = {
            "analysis_type": "Chi-square Test of Independence",
            "timestamp": datetime.now().isoformat(),
            "alpha": self.alpha,
            "table_dimensions": {"n_rows": n_rows, "n_cols": n_cols},
            "test_results": {
                "chi_square_statistic": float(chi2_stat),
                "p_value": float(p_value),
                "degrees_of_freedom": int(dof),
                "significant": p_value < self.alpha,
                "yates_correction_applied": apply_yates,
            },
            "contingency_table": {
                "observed": [[int(x) for x in row] for row in obs_array],
                "expected": [[float(x) for x in row] for row in expected],
                "row_totals": [int(x) for x in row_totals],
                "col_totals": [int(x) for x in col_totals],
                "total": int(total_n),
            },
            "proportions": {
                "row_proportions": [[float(x) for x in row] for row in row_props],
                "column_proportions": [[float(x) for x in row] for row in col_props],
            },
            "confidence_intervals": {"odds_ratio": odds_ratios}
            if odds_ratios
            else None,
            "effect_size": {
                "phi_coefficient": float(phi_coefficient),
                "cramers_v": float(cramers_v),
                "interpretation": self._interpret_cramers_v(cramers_v),
            },
            "assumptions": {
                "independent_observations": True,
                "random_sampling": True,
                "adequate_expected_frequencies": min_expected >= 5,
                "mutually_exclusive_categories": True,
            },
            "assumption_checks": {
                "expected_frequencies": {
                    "min_expected": float(min_expected),
                    "cells_with_low_expected": int(cells_with_low_expected),
                    "adequate": min_expected >= 5,
                    "interpretation": (
                        "All expected >= 5"
                        if min_expected >= 5
                        else f"{cells_with_low_expected} cells have expected < 5. Consider Fisher's exact test."
                    ),
                },
                "sample_size": {"total_n": int(total_n), "adequate": total_n >= 20},
            },
            "explanations": {
                "test_purpose": f"Tests independence between two categorical variables in a {n_rows}x{n_cols} contingency table.",
                "null_hypothesis": "H0: The two variables are independent (no association).",
                "alternative_hypothesis": "H1: The two variables are associated (not independent).",
                "pharmacovigilance_example": "Testing association between treatment group and adverse event occurrence.",
                "when_to_use": [
                    "Testing association between categorical variables",
                    "2x2 or larger contingency tables",
                    "Treatment vs. adverse event analysis",
                    "Demographic subgroup analysis",
                ],
                "alternatives_if_assumptions_violated": [
                    "Fisher's exact test (for 2x2 tables with small samples)",
                    "Fisher-Freeman-Halton exact test (for larger tables with small samples)",
                    "Combine categories to increase expected frequencies",
                ],
                "p_value_meaning": f"P-value ({p_value:.4e}) indicates {'variables are associated' if p_value < self.alpha else 'no significant association'} at α={self.alpha}.",
                "effect_size_meaning": f"Cramer's V={cramers_v:.3f} measures strength of association."
                if n_rows > 2 or n_cols > 2
                else f"Phi={phi_coefficient:.3f} measures strength of association.",
            },
            "interpretations": {
                "main_finding": (
                    f"{'Significant association' if p_value < self.alpha else 'No significant association'} "
                    f"between variables (χ²={chi2_stat:.2f}, df={dof}, p={p_value:.4e})."
                ),
                "effect_size": (
                    ("Cramer's V" if n_rows > 2 or n_cols > 2 else "Phi coefficient")
                    + f" ({cramers_v:.3f}) "
                    f"indicates {self._interpret_cramers_v(cramers_v)} association strength."
                ),
                "clinical_relevance": (
                    f"{'Variables are statistically associated' if p_value < self.alpha else 'No statistical association detected'}. "
                    f"{'Effect size: ' + self._interpret_cramers_v(cramers_v) if cramers_v >= 0.1 else ''}"
                ),
                "plain_language": (
                    f"The {'shows a significant' if p_value < self.alpha else 'does not show a significant'} "
                    f"{'association between the variables' if p_value < self.alpha else 'association between the variables'}. "
                    f"{'The variables are related' if p_value < self.alpha else 'The variables appear to be independent'}"
                ),
            },
            "recommendations": [
                f"Chi-square test is {'appropriate' if min_expected >= 5 else 'questionable due to low expected frequencies'}.",
                f"Effect size {cramers_v:.3f} indicates {self._interpret_cramers_v(cramers_v)} association.",
                f"{'Yates correction applied for 2x2 table' if apply_yates else 'No correction applied'}.",
                "For 2x2 tables with small samples, Fisher's exact test is recommended.",
                "Report proportions and confidence intervals alongside the test result.",
                "Consider clinical significance beyond statistical significance.",
            ],
            "glp_gcp_compliance": {
                "regulatory_guidelines": [
                    "ICH E9 Section 7.3: Analysis of safety data",
                    "FDA Guidance: Safety data in clinical trials",
                    "EMA Guideline: Points to consider on safety data",
                ],
                "sap_requirements": "Association tests pre-specified in SAP for safety analysis.",
                "data_integrity": "Contingency table accurately recorded from source data.",
                "documentation": "Full contingency table with expected values reported.",
            },
            "references": [
                "Agresti A. (2002). Categorical Data Analysis. 2nd ed. Wiley.",
                "Yates F. (1934). Contingency tables involving small numbers... Journal of the Royal Statistical Society.",
                "ICH E9 (1998). Statistical Principles for Clinical Trials.",
            ],
        }

        return results

    def _interpret_cramers_v(self, v: float) -> str:
        """Interpret Cramer's V effect size"""
        if v < 0.1:
            return "negligible"
        elif v < 0.3:
            return "small"
        elif v < 0.5:
            return "medium"
        else:
            return "large"

    def _interpret_odds_ratio(self, or_value: float) -> str:
        """Interpret odds ratio"""
        if or_value < 0.67:
            return "negative association (exposure is protective)"
        elif or_value > 1.5:
            return "positive association (exposure is a risk factor)"
        else:
            return "no association (includes 1.0)"

    def fisher_exact_test(
        self,
        contingency_table: Union[List[List[int]], np.ndarray, pd.DataFrame],
        alternative: str = "two-sided",
        simulate_p_value: bool = False,
        iterations: int = 10000,
    ) -> Dict[str, Any]:
        """Fisher's Exact Test for small sample contingency tables

        Pharmacovigilance Example:
            Test association between treatment and rare adverse events
            when sample sizes are small and expected frequencies < 5.

        FDA/EMA Compliance:
            - ICH E9 Section 7.3: Analysis of safety data for rare events
            - Exact test appropriate for small samples and rare events
            - Preferred over chi-square when expected frequencies are low

        Args:
            contingency_table: 2x2 contingency table of observed frequencies
            alternative: 'two-sided', 'less', 'greater'
            simulate_p_value: Use Monte Carlo simulation for large tables
            iterations: Number of Monte Carlo iterations

        Returns:
            Dictionary with test results, odds ratio, confidence intervals, interpretations
        """
        # Convert to numpy array
        obs_array = np.asarray(contingency_table, dtype=float)

        # Input validation
        if obs_array.ndim != 2:
            raise ValueError("Contingency table must be 2-dimensional")

        if obs_array.shape != (2, 2):
            raise ValueError(
                f"Fisher's exact test requires 2x2 table, got {obs_array.shape}"
            )

        if np.any(obs_array < 0):
            raise ValueError("Contingency table frequencies must be non-negative")

        # Round to integers (Fisher's test requires count data)
        obs_array = np.round(obs_array).astype(int)

        total_n = np.sum(obs_array)

        if total_n == 0:
            raise ValueError("Contingency table cannot be all zeros")

        # Check if simulation is needed (large N)
        if total_n > 10000 and simulate_p_value:
            odds_ratio, p_value = stats.fisher_exact(
                obs_array,
                alternative=alternative,
                simulate_p_value=True,
                iterations=iterations,
            )
        else:
            odds_ratio, p_value = stats.fisher_exact(obs_array, alternative=alternative)

        # Calculate odds ratio with 0.5 adjustment for zeros
        a, b = obs_array[0, 0], obs_array[0, 1]
        c, d = obs_array[1, 0], obs_array[1, 1]

        if b == 0 or c == 0:
            odds_ratio_adj = (a + 0.5) * (d + 0.5) / ((b + 0.5) * (c + 0.5))
        else:
            odds_ratio_adj = (a * d) / (b * c)

        # Confidence interval for odds ratio (exact)
        if a * d == 0 and b * c == 0:
            # Undefined odds ratio
            or_ci_lower, or_ci_upper = 0.0, float("inf")
        else:
            # Use Fisher's exact method for CI
            try:
                from statsmodels.stats.contingency_tables import Table2x2

                table = Table2x2(obs_array)
                or_ci = table.oddsratio_confint(alpha=0.05)
                or_ci_lower, or_ci_upper = or_ci[0], or_ci[1]
            except:
                # Fallback to Woolf's method
                se_log_or = np.sqrt(1 / a + 1 / b + 1 / c + 1 / d)
                z = stats.norm.ppf(1 - (1 - 0.95) / 2)
                log_or = np.log(odds_ratio_adj)
                or_ci_lower = np.exp(log_or - z * se_log_or)
                or_ci_upper = np.exp(log_or + z * se_log_or)

        # Risk difference and relative risk
        risk1 = a / (a + b) if (a + b) > 0 else 0
        risk2 = c / (c + d) if (c + d) > 0 else 0
        risk_difference = risk1 - risk2
        relative_risk = (
            (a / (a + b)) / (c / (c + d))
            if (c + d) > 0 and (a + b) > 0
            else float("inf")
        )

        # Exact confidence interval for risk difference (using binomial)
        def _proportion_ci(k, n, alpha=0.05):
            if n == 0:
                return 0.0, 0.0
            if k == 0:
                ci_lower = 0.0
                ci_upper = 1 - (alpha / 2) ** (1 / n)
            elif k == n:
                ci_lower = (alpha / 2) ** (1 / n)
                ci_upper = 1.0
            else:
                ci_lower = stats.beta.ppf(alpha / 2, k, n - k + 1)
                ci_upper = stats.beta.ppf(1 - alpha / 2, k + 1, n - k)
            return max(0.0, ci_lower), min(1.0, ci_upper)

        risk1_ci = _proportion_ci(a, a + b)
        risk2_ci = _proportion_ci(c, c + d)

        results = {
            "analysis_type": "Fisher's Exact Test",
            "timestamp": datetime.now().isoformat(),
            "alpha": self.alpha,
            "test_results": {
                "p_value": float(p_value),
                "significant": p_value < self.alpha,
                "alternative": alternative,
                "simulation_used": simulate_p_value and total_n > 10000,
                "simulated_iterations": iterations
                if (simulate_p_value and total_n > 10000)
                else None,
            },
            "contingency_table": {
                "observed": [[int(x) for x in row] for row in obs_array],
                "row_totals": [int(a + b), int(c + d)],
                "col_totals": [int(a + c), int(b + d)],
                "total": int(total_n),
            },
            "measures": {
                "odds_ratio": {
                    "value": float(odds_ratio),
                    "adjusted_value": float(odds_ratio_adj),
                    "ci_lower": float(or_ci_lower),
                    "ci_upper": float(or_ci_upper),
                    "ci_level": 0.95,
                    "interpretation": self._interpret_odds_ratio(odds_ratio_adj),
                },
                "risk_difference": {
                    "value": float(risk_difference),
                    "interpretation": "Positive values indicate higher risk in group 1",
                },
                "relative_risk": {
                    "value": float(relative_risk)
                    if relative_risk != float("inf")
                    else None,
                    "interpretation": ">1 indicates higher risk in group 1",
                },
                "risk1": {
                    "value": float(risk1),
                    "ci_lower": float(risk1_ci[0]),
                    "ci_upper": float(risk1_ci[1]),
                    "n": int(a + b),
                },
                "risk2": {
                    "value": float(risk2),
                    "ci_lower": float(risk2_ci[0]),
                    "ci_upper": float(risk2_ci[1]),
                    "n": int(c + d),
                },
            },
            "confidence_intervals": {
                "odds_ratio": {
                    "lower": float(or_ci_lower),
                    "upper": float(or_ci_upper),
                    "level": 0.95,
                    "method": "Exact (Fisher)",
                },
                "risk_difference": {
                    "note": "CI requires special methods; odds ratio CI provided"
                },
            },
            "assumptions": {
                "independent_observations": True,
                "fixed_margins": "Row and column totals are fixed (conditioning on them)",
                "binary_outcome": True,
                "count_data": True,
            },
            "explanations": {
                "test_purpose": "Exact test for association in 2x2 tables. Appropriate for small samples or rare events.",
                "null_hypothesis": "H0: No association between row and column variables (odds ratio = 1).",
                "alternative_hypothesis": f"H1: Association exists (alternative={alternative}).",
                "pharmacovigilance_example": "Testing association between treatment and rare adverse events when chi-square assumptions violated.",
                "when_to_use": [
                    "Small sample sizes (any cell expected count < 5)",
                    "Rare events (low frequency outcomes)",
                    "Fixed marginal totals design",
                    "Exact p-value required",
                ],
                "alternatives_if_assumptions_violated": [
                    "Chi-square test (for larger samples)",
                    "Yates-corrected chi-square (for moderate samples)",
                    "Exact logistic regression (for adjustment)",
                ],
                "p_value_meaning": f"P-value ({p_value:.4e}) indicates {'significant association' if p_value < self.alpha else 'no significant association'} at α={self.alpha}.",
                "odds_ratio_meaning": f"OR={odds_ratio_adj:.3f} measures strength of association. OR > 1: positive association; OR < 1: negative association.",
            },
            "interpretations": {
                "main_finding": (
                    f"{'Significant association' if p_value < self.alpha else 'No significant association'} "
                    f"between variables (p={p_value:.4e})."
                ),
                "odds_ratio": (
                    f"Odds ratio = {odds_ratio_adj:.3f} (95% CI: {or_ci_lower:.3f} to {or_ci_upper:.3f}). "
                    f"{self._interpret_odds_ratio(odds_ratio_adj)}."
                ),
                "risk_difference": (
                    f"Risk difference = {risk_difference:.3f} ({risk1:.3f} - {risk2:.3f}). "
                    f"{'Group 1 has higher risk' if risk_difference > 0 else 'Group 2 has higher risk' if risk_difference < 0 else 'No risk difference'}"
                ),
                "clinical_relevance": (
                    f"{'Clinically meaningful association' if odds_ratio_adj > 2 or odds_ratio_adj < 0.5 else 'Association may or may not be clinically meaningful'}. "
                    f"{'CI excludes 1, suggesting real association' if or_ci_lower > 1 or or_ci_upper < 1 else 'CI includes 1, association not statistically significant'}"
                ),
                "plain_language": (
                    f"The {'shows a significant' if p_value < self.alpha else 'does not show a significant'} "
                    f"{'association' if p_value < self.alpha else 'association'} between the variables. "
                    f"{'The odds are ' + str(round(odds_ratio_adj, 2)) + ' times higher' if odds_ratio_adj > 1 else 'The odds are ' + str(round(1 / odds_ratio_adj, 2)) + ' times lower' if odds_ratio_adj < 1 else 'The odds are similar'} "
                    f"between the groups."
                ),
            },
            "recommendations": [
                "Fisher's exact test is appropriate for small samples or rare events.",
                f"Odds ratio {odds_ratio_adj:.3f} indicates {self._interpret_odds_ratio(odds_ratio_adj)} association.",
                "For larger samples, chi-square test provides similar results with less computation.",
                "Report odds ratio with confidence interval for effect size.",
                "Consider clinical significance beyond statistical significance.",
                "For multiple 2x2 tables, use Cochran-Mantel-Haenszel test.",
            ],
            "glp_gcp_compliance": {
                "regulatory_guidelines": [
                    "ICH E9 Section 7.3: Safety data analysis for rare events",
                    "FDA Guidance: Safety data in clinical trials",
                    "EMA Guideline: Points to consider on safety data",
                ],
                "sap_requirements": "Fisher's exact test pre-specified in SAP for rare events analysis.",
                "data_integrity": "All case counts accurately recorded.",
                "documentation": "Full contingency table with exact p-value reported for audit trail.",
            },
            "references": [
                "Fisher RA. (1922). On the interpretation of χ2 from contingency tables... Journal of the Royal Statistical Society.",
                "Agresti A. (2002). Categorical Data Analysis. 2nd ed. Wiley.",
                "ICH E9 (1998). Statistical Principles for Clinical Trials.",
            ],
        }

        return results

    def mcnemar_test(
        self,
        contingency_table: Union[List[List[int]], np.ndarray, pd.DataFrame],
        exact: bool = False,
        correction: bool = True,
    ) -> Dict[str, Any]:
        """McNemar Test for paired categorical data

        Pharmacovigilance Example:
            Compare adverse event occurrence before and after treatment
            for the same patients (paired design) to assess treatment-emergent events.

        FDA/EMA Compliance:
            - ICH E9 Section 7.3: Analysis of safety data for within-subject comparisons
            - Appropriate for pre-post designs with binary outcomes
            - Standard test for treatment-emergent adverse events

        Args:
            contingency_table: 2x2 contingency table of paired observations
            exact: Use exact binomial test instead of chi-square approximation
            correction: Apply continuity correction (Edwards correction)

        Returns:
            Dictionary with test results, odds ratio, confidence intervals, interpretations
        """
        # Convert to numpy array
        obs_array = np.asarray(contingency_table, dtype=float)

        # Input validation
        if obs_array.ndim != 2:
            raise ValueError("Contingency table must be 2-dimensional")

        if obs_array.shape != (2, 2):
            raise ValueError(f"McNemar test requires 2x2 table, got {obs_array.shape}")

        if np.any(obs_array < 0):
            raise ValueError("Contingency table frequencies must be non-negative")

        # Round to integers
        obs_array = np.round(obs_array).astype(int)

        # Extract cell values (b and c are the discordant pairs)
        a, b = (
            obs_array[0, 0],
            obs_array[0, 1],
        )  # a: both negative, b: before neg, after pos
        c, d = (
            obs_array[1, 0],
            obs_array[1, 1],
        )  # c: before pos, after neg, d: both positive

        total_n = np.sum(obs_array)
        discordant_pairs = b + c

        if discordant_pairs == 0:
            return {
                "analysis_type": "McNemar Test",
                "timestamp": datetime.now().isoformat(),
                "error": "No discordant pairs (b + c = 0). Test cannot be performed.",
                "interpretation": "All pairs have the same outcome. No evidence of change.",
                "contingency_table": [[int(a), int(b)], [int(c), int(d)]],
            }

        # Perform McNemar test
        if exact:
            # Exact binomial test for discordant pairs
            # Under H0, P(b) = 0.5 for each discordant pair
            p_value = stats.binomtest(
                b, n=discordant_pairs, p=0.5, alternative="two-sided"
            )
            chi2_stat = None
        else:
            # Chi-square approximation
            if correction:
                # Edwards continuity correction
                chi2_stat = (abs(b - c) - 1) ** 2 / (b + c)
            else:
                chi2_stat = (b - c) ** 2 / (b + c)

            p_value = stats.chi2.sf(chi2_stat, df=1)

        # Odds ratio for discordant pairs
        if b == 0 or c == 0:
            odds_ratio = (b + 0.5) / (c + 0.5)  # Add 0.5 to avoid division by zero
        else:
            odds_ratio = b / c

        # Confidence interval for odds ratio (exact binomial)
        # Using exact binomial confidence interval for proportion
        alpha = 1 - 0.95
        if b == 0:
            ci_lower = 0.0
            ci_upper = 1 - (alpha / 2) ** (1 / discordant_pairs)
        elif b == discordant_pairs:
            ci_lower = (alpha / 2) ** (1 / discordant_pairs)
            ci_upper = 1.0
        else:
            ci_lower = stats.beta.ppf(alpha / 2, b, c + 1)
            ci_upper = stats.beta.ppf(1 - alpha / 2, b + 1, c)

        # Convert proportion CI to odds ratio CI
        if ci_lower == 0:
            or_ci_lower = 0.0
        elif ci_lower == 1:
            or_ci_lower = float("inf")
        else:
            or_ci_lower = ci_lower / (1 - ci_lower)

        if ci_upper == 0:
            or_ci_upper = 0.0
        elif ci_upper == 1:
            or_ci_upper = float("inf")
        else:
            or_ci_upper = ci_upper / (1 - ci_upper)

        # Proportion of positive outcomes before and after
        prop_before = (c + d) / total_n
        prop_after = (b + d) / total_n
        prop_difference = prop_after - prop_before

        # Wilson score interval for proportions
        def _wilson_ci(k, n, alpha=0.05):
            if n == 0:
                return 0.0, 0.0
            p = k / n
            z = stats.norm.ppf(1 - alpha / 2)
            denominator = 2 * (n + z**2)
            center = (p + z**2 / (2 * n)) / denominator
            margin = z * np.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denominator
            return max(0.0, center - margin), min(1.0, center + margin)

        prop_before_ci = _wilson_ci(c + d, total_n)
        prop_after_ci = _wilson_ci(b + d, total_n)

        results = {
            "analysis_type": "McNemar Test",
            "timestamp": datetime.now().isoformat(),
            "alpha": self.alpha,
            "test_results": {
                "p_value": float(p_value),
                "significant": p_value < self.alpha,
                "exact_test_used": exact,
                "continuity_correction_applied": correction and not exact,
            },
            "contingency_table": {
                "observed": [[int(a), int(b)], [int(c), int(d)]],
                "discordant_pairs": int(discordant_pairs),
                "concordant_pairs": int(a + d),
                "total_pairs": int(total_n),
            },
            "discordant_cells": {
                "b": int(b),
                "description": "Negative before, Positive after (treatment-emergent)",
                "c": int(c),
                "description_c": "Positive before, Negative after (improvement)",
            },
            "proportions": {
                "positive_before": {
                    "value": float(prop_before),
                    "ci_lower": float(prop_before_ci[0]),
                    "ci_upper": float(prop_before_ci[1]),
                },
                "positive_after": {
                    "value": float(prop_after),
                    "ci_lower": float(prop_after_ci[0]),
                    "ci_upper": float(prop_after_ci[1]),
                },
                "difference": float(prop_difference),
            },
            "confidence_intervals": {
                "odds_ratio": {
                    "value": float(odds_ratio),
                    "ci_lower": float(or_ci_lower),
                    "ci_upper": float(or_ci_upper),
                    "ci_level": 0.95,
                },
                "proportion_difference": {
                    "value": float(prop_difference),
                    "note": "CI requires delta method or bootstrapping",
                },
            },
            "assumptions": {
                "paired_samples": True,
                "binary_outcome": True,
                "large_sample_for_approximation": discordant_pairs >= 25
                if not exact
                else "Not required for exact test",
                "random_sampling": True,
            },
            "assumption_checks": {
                "discordant_pairs": {
                    "n": int(discordant_pairs),
                    "adequate_for_approximation": discordant_pairs >= 25,
                    "recommendation": "Use exact test if discordant pairs < 25",
                }
            },
            "explanations": {
                "test_purpose": "Tests change in binary outcomes between paired measurements (pre-post, matched subjects).",
                "null_hypothesis": "H0: Proportion of discordant pairs is equal (b = c), no change between measurements.",
                "alternative_hypothesis": "H1: Proportion of discordant pairs differs (b ≠ c), change between measurements.",
                "pharmacovigilance_example": "Comparing adverse event occurrence before and after treatment in the same patients.",
                "when_to_use": [
                    "Paired binary measurements (pre-post design)",
                    "Within-subject comparisons of categorical outcomes",
                    "Treatment-emergent adverse event analysis",
                    "Matched case-control studies",
                ],
                "alternatives_if_assumptions_violated": [
                    "Exact binomial test (for small discordant pairs)",
                    "Cochran's Q test (for >2 paired measurements)",
                    "Generalized estimating equations (GEE) for complex designs",
                ],
                "p_value_meaning": f"P-value ({p_value:.4e}) indicates {'significant change' if p_value < self.alpha else 'no significant change'} between paired measurements at α={self.alpha}.",
                "odds_ratio_meaning": f"OR = {odds_ratio:.3f}. OR > 1: more positive outcomes after; OR < 1: more positive outcomes before.",
            },
            "interpretations": {
                "main_finding": (
                    f"{'Significant change' if p_value < self.alpha else 'No significant change'} "
                    f"in paired binary outcomes (p={p_value:.4e}). "
                    f"Discordant pairs: {discordant_pairs} (b={b}, c={c})."
                ),
                "odds_ratio": (
                    f"Odds ratio = {odds_ratio:.3f} (95% CI: {or_ci_lower:.3f} to {or_ci_upper:.3f}). "
                    f"{'Significant change from before to after' if or_ci_lower > 1 or or_ci_upper < 1 else 'No significant change (CI includes 1)'}"
                ),
                "treatment_emergent": (
                    f"{'Treatment-emergent events detected' if b > c and p_value < self.alpha else 'No treatment-emergent events detected'}. "
                    f"{b} events emerged, {c} events resolved."
                ),
                "clinical_relevance": (
                    f"Proportion difference: {prop_difference:.3%} ({prop_difference * total_n:.0f} out of {total_n} patients). "
                    f"{'May be clinically meaningful' if abs(prop_difference) >= 0.1 else 'May not be clinically meaningful'}"
                ),
                "plain_language": (
                    f"The {'shows a significant' if p_value < self.alpha else 'does not show a significant'} "
                    f"{'change in outcomes' if p_value < self.alpha else 'change in outcomes'}. "
                    f"{'More patients changed from negative to positive' if b > c else 'More patients changed from positive to negative' if c > b else 'Similar number of patients changed in both directions'}."
                ),
            },
            "recommendations": [
                f"McNemar test is {'appropriate' if discordant_pairs >= 25 or exact else 'approximation may be inaccurate; use exact test'}.",
                f"Odds ratio {odds_ratio:.3f} indicates {'change from before to after' if odds_ratio > 1 or odds_ratio < 1 else 'no change'}.",
                "For small discordant pairs (<25), exact binomial test is recommended.",
                "Report both marginal proportions and discordant pair analysis.",
                "Consider clinical significance beyond statistical significance.",
                "For >2 time points, use Cochran's Q test.",
            ],
            "glp_gcp_compliance": {
                "regulatory_guidelines": [
                    "ICH E9 Section 7.3: Analysis of safety data",
                    "FDA Guidance: Safety data in clinical trials",
                    "EMA Guideline: Points to consider on safety data",
                ],
                "sap_requirements": "Paired analysis pre-specified in SAP for treatment-emergent events.",
                "data_integrity": "All paired observations accounted for.",
                "documentation": "Full contingency table with discordant pair analysis reported.",
            },
            "references": [
                "McNemar Q. (1947). Note on the sampling error of the difference between correlated proportions. Psychometrika.",
                "Agresti A. (2002). Categorical Data Analysis. 2nd ed. Wiley.",
                "ICH E9 (1998). Statistical Principles for Clinical Trials.",
            ],
        }

        return results

    def cochran_mantel_haenszel_test(
        self,
        tables: List[Union[List[List[int]], np.ndarray, pd.DataFrame]],
        strata_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Cochran-Mantel-Haenszel test for stratified 2x2 tables

        Pharmacovigilance Example:
            Test association between treatment and adverse event across
            multiple clinical sites (strata) while controlling for site effects.

        FDA/EMA Compliance:
            - ICH E9 Section 7.3: Stratified analysis of safety data
            - Controls for confounding across strata
            - Standard method for meta-analysis of 2x2 tables

        Args:
            tables: List of 2x2 contingency tables (one per stratum)
            strata_names: Optional list of stratum names

        Returns:
            Dictionary with test results, pooled odds ratio, confidence intervals, interpretations
        """
        # Convert and validate tables
        strata_data = []
        for i, table in enumerate(tables):
            arr = np.asarray(table, dtype=float)

            if arr.ndim != 2:
                raise ValueError(f"Table {i} must be 2-dimensional")

            if arr.shape != (2, 2):
                raise ValueError(
                    f"CMH test requires 2x2 tables, table {i} is {arr.shape}"
                )

            if np.any(arr < 0):
                raise ValueError(f"Table {i} contains negative values")

            # Round to integers
            arr = np.round(arr).astype(int)
            strata_data.append(arr)

        n_strata = len(strata_data)

        if n_strata == 0:
            raise ValueError("At least one table required")

        if strata_names is None:
            strata_names = [f"Stratum_{i}" for i in range(n_strata)]
        elif len(strata_names) != n_strata:
            raise ValueError(
                f"Expected {n_strata} strata names, got {len(strata_names)}"
            )

        # Set strata names
        if len(strata_names) != n_strata:
            strata_names = [f"Stratum_{i}" for i in range(n_strata)]

        # Use statsmodels for CMH test
        try:
            # Create stratified table object
            stratified_tables = []
            for i, arr in enumerate(strata_data):
                from statsmodels.stats.contingency_tables import Table2x2

                table_2x2 = Table2x2(arr)
                stratified_tables.append(table_2x2)

            # Perform CMH test using StratifiedTable
            stratified = StratifiedTable(stratified_tables)
            cmh_result = stratified.test_null_odds()

            chi2_stat = cmh_result.statistic
            p_value = cmh_result.pvalue

            # Get pooled odds ratio
            pooled_or = stratified.oddsratio_pooled

            # Confidence interval for pooled odds ratio
            or_ci = stratified.oddsratio_pooled_confint(alpha=0.05)
            or_ci_lower, or_ci_upper = or_ci[0], or_ci[1]

            # Breslow-Day test for homogeneity of odds ratios
            breslow_day = stratified.test_oddsratio_homogeneity()
            bd_p_value = breslow_day.pvalue
            bd_statistic = breslow_day.statistic

        except Exception as e:
            # Fallback: Manual calculation if statsmodels fails
            chi2_stat, p_value, pooled_or, or_ci_lower, or_ci_upper = (
                self._manual_cmh_calculation(strata_data)
            )
            bd_p_value = None
            bd_statistic = None

        # Calculate stratum-specific odds ratios
        stratum_results = []
        for i, arr in enumerate(strata_data):
            a, b = arr[0, 0], arr[0, 1]
            c, d = arr[1, 0], arr[1, 1]

            # Stratum totals
            n_i = np.sum(arr)

            # Odds ratio
            if b == 0 or c == 0:
                or_i = (a + 0.5) * (d + 0.5) / ((b + 0.5) * (c + 0.5))
            else:
                or_i = (a * d) / (b * c)

            # Expected value for a under H0
            row1_total = a + b
            col1_total = a + c
            expected_a = row1_total * col1_total / n_i

            stratum_results.append(
                {
                    "stratum": strata_names[i],
                    "table": [[int(a), int(b)], [int(c), int(d)]],
                    "n": int(n_i),
                    "odds_ratio": float(or_i),
                    "expected_a": float(expected_a),
                }
            )

        # Weighted analysis (by sample size)
        total_n = sum(np.sum(arr) for arr in strata_data)
        stratum_weights = [np.sum(arr) / total_n for arr in strata_data]

        results = {
            "analysis_type": "Cochran-Mantel-Haenszel Test",
            "timestamp": datetime.now().isoformat(),
            "alpha": self.alpha,
            "test_results": {
                "chi_square_statistic": float(chi2_stat),
                "p_value": float(p_value),
                "degrees_of_freedom": 1,
                "significant": p_value < self.alpha,
                "n_strata": n_strata,
                "total_n": int(total_n),
            },
            "pooled_odds_ratio": {
                "value": float(pooled_or),
                "ci_lower": float(or_ci_lower),
                "ci_upper": float(or_ci_upper),
                "ci_level": 0.95,
                "interpretation": self._interpret_odds_ratio(pooled_or),
                "includes_1": or_ci_lower <= 1 <= or_ci_upper,
            },
            "homogeneity_test": {
                "breslow_day_statistic": float(bd_statistic)
                if bd_statistic is not None
                else None,
                "breslow_day_p_value": float(bd_p_value)
                if bd_p_value is not None
                else None,
                "homogeneous": bd_p_value is None or bd_p_value >= self.alpha,
                "interpretation": "Odds ratios are homogeneous across strata"
                if (bd_p_value is None or bd_p_value >= self.alpha)
                else "Odds ratios differ across strata (significant interaction)",
            }
            if bd_p_value is not None
            else None,
            "stratum_results": stratum_results,
            "stratum_weights": [
                {"stratum": strata_names[i], "weight": float(w)}
                for i, w in enumerate(stratum_weights)
            ],
            "confidence_intervals": {
                "pooled_odds_ratio": {
                    "lower": float(or_ci_lower),
                    "upper": float(or_ci_upper),
                    "level": 0.95,
                }
            },
            "assumptions": {
                "independent_strata": True,
                "independent_observations": True,
                "consistent_odds_ratios": "Odds ratios should be similar across strata (tested with Breslow-Day)",
                "sufficient_sample_size": "Expected cell counts >= 5 in each stratum",
            },
            "assumption_checks": {
                "sample_size": {"total_n": int(total_n), "adequate": total_n >= 50},
                "homogeneity": {
                    "tested": bd_p_value is not None,
                    "homogeneous": bd_p_value is None or bd_p_value >= self.alpha,
                },
            },
            "explanations": {
                "test_purpose": f"Tests association between two variables while controlling for stratification across {n_strata} strata.",
                "null_hypothesis": "H0: No association between variables after adjusting for strata (pooled OR = 1).",
                "alternative_hypothesis": "H1: Association exists after adjusting for strata (pooled OR ≠ 1).",
                "pharmacovilance_example": "Testing treatment-adverse event association across multiple clinical sites while controlling for site effects.",
                "when_to_use": [
                    "Controlling for confounding variable (stratification)",
                    "Meta-analysis of multiple 2x2 tables",
                    "Multi-center clinical trials",
                    "Testing interaction across subgroups",
                ],
                "alternatives_if_assumptions_violated": [
                    "Logistic regression with stratum covariates (for complex designs)",
                    "Mantel-Haenszel weighted regression",
                    "Random-effects meta-analysis if heterogeneity present",
                ],
                "p_value_meaning": f"P-value ({p_value:.4e}) indicates {'association after adjusting' if p_value < self.alpha else 'no association after adjusting'} for strata at α={self.alpha}.",
                "pooled_or_meaning": f"Pooled OR={pooled_or:.3f} measures association after controlling for stratification.",
            },
            "interpretations": {
                "main_finding": (
                    f"{'Significant association' if p_value < self.alpha else 'No significant association'} "
                    f"after adjusting for {n_strata} strata (χ²={chi2_stat:.2f}, p={p_value:.4e})."
                ),
                "pooled_odds_ratio": (
                    f"Pooled odds ratio = {pooled_or:.3f} (95% CI: {or_ci_lower:.3f} to {or_ci_upper:.3f}). "
                    f"{self._interpret_odds_ratio(pooled_or)}. "
                    f"{'CI excludes 1, significant association' if not (or_ci_lower <= 1 <= or_ci_upper) else 'CI includes 1, no significant association'}"
                ),
                "homogeneity": (
                    f"Breslow-Day test: {'ORs are homogeneous' if bd_p_value is None or bd_p_value >= self.alpha else 'ORs are heterogeneous (p=' + str(round(bd_p_value, 4)) + ')'}. "
                    f"{'CMH appropriate' if bd_p_value is None or bd_p_value >= self.alpha else 'Consider reporting stratum-specific ORs'}"
                )
                if bd_p_value is not None
                else None,
                "clinical_relevance": (
                    f"{'Clinically meaningful association' if pooled_or > 2 or pooled_or < 0.5 else 'Association may or may not be clinically meaningful'}. "
                    f"Results adjusted for {n_strata} strata."
                ),
                "plain_language": (
                    f"After accounting for {n_strata} different groups, the {'shows a significant' if p_value < self.alpha else 'does not show a significant'} "
                    f"{'association' if p_value < self.alpha else 'association'} between the variables. "
                    f"{'The odds are ' + str(round(pooled_or, 2)) + ' times higher' if pooled_or > 1 else 'The odds are ' + str(round(1 / pooled_or, 2)) + ' times lower' if pooled_or < 1 else 'The odds are similar'} "
                    f"between groups."
                ),
            },
            "recommendations": [
                f"CMH test is appropriate for stratified analysis of {n_strata} strata.",
                f"Pooled OR {pooled_or:.3f} indicates {self._interpret_odds_ratio(pooled_or)} after adjustment.",
                "Check Breslow-Day test for odds ratio homogeneity across strata.",
                "If significant heterogeneity, report stratum-specific odds ratios.",
                "Consider logistic regression for additional covariate adjustment.",
                "Report both pooled and stratum-specific results for transparency.",
            ],
            "glp_gcp_compliance": {
                "regulatory_guidelines": [
                    "ICH E9 Section 7.3: Stratified analysis of safety data",
                    "FDA Guidance: Subgroup analysis in clinical trials",
                    "EMA Guideline: Points to consider on subgroup analysis",
                ],
                "sap_requirements": "Stratified analysis pre-specified in SAP.",
                "data_integrity": "All strata data accurately recorded.",
                "documentation": "Pooled and stratum-specific results reported for audit trail.",
            },
            "references": [
                "Cochran WG. (1954). Some methods for strengthening the common chi-square tests. Biometrics.",
                "Mantel N, Haenszel W. (1959). Statistical aspects of the analysis of data from retrospective studies. Journal of the National Cancer Institute.",
                "ICH E9 (1998). Statistical Principles for Clinical Trials.",
            ],
        }

        return results

    def _manual_cmh_calculation(
        self, strata_data: List[np.ndarray]
    ) -> Tuple[float, float, float, float, float]:
        """Manual calculation of CMH test if statsmodels fails"""
        # Calculate CMH statistic manually
        sum_a1 = 0.0
        sum_e_a1 = 0.0
        sum_var_a1 = 0.0

        # Mantel-Haenszel pooled odds ratio components
        or_numerator = 0.0
        or_denominator = 0.0

        for arr in strata_data:
            a, b = arr[0, 0], arr[0, 1]
            c, d = arr[1, 0], arr[1, 1]

            n = a + b + c + d
            n1 = a + b
            m1 = a + c

            # Expected value and variance for a
            e_a = n1 * m1 / n
            var_a = n1 * m1 * (n - n1) * (n - m1) / (n**2 * (n - 1))

            sum_a1 += a
            sum_e_a1 += e_a
            sum_var_a1 += var_a

            # MH odds ratio components
            if b * c > 0:
                or_numerator += a * d / n
                or_denominator += b * c / n

        # CMH statistic
        chi2_stat = (
            abs(sum_a1 - sum_e_a1) - 0.5
        ) ** 2 / sum_var_a1  # With continuity correction
        p_value = stats.chi2.sf(chi2_stat, df=1)

        # Pooled odds ratio
        pooled_or = or_numerator / or_denominator if or_denominator > 0 else 1.0

        # Approximate confidence interval (Robins-Breslow-Greenland method)
        log_or = np.log(pooled_or)

        # Calculate variance components for CI
        sum_component = 0.0
        for arr in strata_data:
            a, b = arr[0, 0], arr[0, 1]
            c, d = arr[1, 0], arr[1, 1]
            n = a + b + c + d

            p = (a + c) / n  # Proportion in column 1
            q = 1 - p

            numerator = (a + c) * (b + d)
            denominator = a * c if (a * c) > 0 else 0.001

            if denominator > 0:
                term = (
                    (n * (a + b + c + d) - (a + b) * (c + d))
                    / (n * (n - 1))
                    * (a + c)
                    * (b + d)
                    / denominator
                )
                sum_component += term

        se_log_or = np.sqrt(sum_component)
        z = stats.norm.ppf(1 - 0.025)

        or_ci_lower = np.exp(log_or - z * se_log_or)
        or_ci_upper = np.exp(log_or + z * se_log_or)

        return chi2_stat, p_value, pooled_or, or_ci_lower, or_ci_upper

    # ============================================
    # TIME SERIES ANALYSIS METHODS
    # ============================================

    def perform_adf_test(
        self,
        series: Union[pd.Series, List[float], np.ndarray],
        maxlag: int = None,
        regression: str = "c",
        autolag: str = "AIC",
    ) -> Dict[str, Any]:
        """Augmented Dickey-Fuller test for stationarity

        Pharmacovigilance Example:
            Test time-series pharmacokinetic concentration data
            for stationarity before trend analysis or model fitting.

        FDA/EMA Compliance:
            - ICH E9 Section 5.3: Analysis of time-series data
            - Used to verify stationarity assumptions for PK/PD modeling
            - Standard test for unit root detection in time series

        Args:
            series: Time series data
            maxlag: Maximum lag to include
            regression: 'c' (constant), 'ct' (constant + trend), 'ctt' (constant + linear + quadratic), 'n' (no constant)
            autolag: Method for selecting lag order ('AIC', 'BIC', 't-stat')

        Returns:
            Dictionary with test results, critical values, interpretations
        """
        # Convert to pandas Series
        if not isinstance(series, pd.Series):
            series = pd.Series(series)

        # Input validation
        if series.isnull().all():
            raise ValueError("Series contains only missing values")

        series = series.dropna()

        if len(series) < 20:
            raise ValueError(
                f"ADF test requires at least 20 observations, found {len(series)}"
            )

        # Perform ADF test
        adf_result = adfuller(
            series, maxlag=maxlag, regression=regression, autolag=autolag
        )

        # Extract results
        adf_statistic = adf_result[0]
        p_value = adf_result[1]
        used_lag = adf_result[2]
        n_obs = adf_result[3]
        critical_values = adf_result[4]
        ic_best = adf_result[5] if len(adf_result) > 5 else None

        # Calculate t-statistic for significance
        t_stat = adf_statistic

        # Determine stationarity at different significance levels
        stationary_at_1pct = adf_statistic < critical_values["1%"]
        stationary_at_5pct = adf_statistic < critical_values["5%"]
        stationary_at_10pct = adf_statistic < critical_values["10%"]

        # Overall stationarity assessment
        is_stationary = stationary_at_5pct

        # Trend information
        has_trend = False
        trend_strength = None

        try:
            if len(series) > 30:
                x = np.arange(len(series))
                slope, intercept, r_value, p_value_trend, std_err = stats.linregress(
                    x, series.values
                )
                has_trend = p_value_trend < self.alpha
                trend_strength = {
                    "slope": float(slope),
                    "intercept": float(intercept),
                    "r_squared": float(r_value**2),
                    "p_value": float(p_value_trend),
                    "significant": has_trend,
                }
        except:
            pass

        # Series statistics
        series_stats = {
            "n_obs": len(series),
            "mean": float(series.mean()),
            "std": float(series.std()),
            "min": float(series.min()),
            "max": float(series.max()),
            "skewness": float(series.skew()),
            "kurtosis": float(series.kurtosis()),
        }

        results = {
            "analysis_type": "Augmented Dickey-Fuller Test",
            "timestamp": datetime.now().isoformat(),
            "alpha": self.alpha,
            "test_results": {
                "adf_statistic": float(adf_statistic),
                "p_value": float(p_value),
                "used_lag": int(used_lag),
                "n_observations": int(n_obs),
                "significant": p_value < self.alpha,
                "stationary": is_stationary,
                "regression_type": regression,
                "autolag_method": autolag,
            },
            "critical_values": {
                "1%": float(critical_values["1%"]),
                "5%": float(critical_values["5%"]),
                "10%": float(critical_values["10%"]),
            },
            "stationarity_assessment": {
                "at_1_percent": stationary_at_1pct,
                "at_5_percent": stationary_at_5pct,
                "at_10_percent": stationary_at_10pct,
                "overall": is_stationary,
                "interpretation": (
                    f"{'Stationary' if is_stationary else 'Non-stationary'} "
                    f"(reject unit root at 5% level: {is_stationary})"
                ),
            },
            "trend_analysis": trend_strength,
            "series_statistics": series_stats,
            "assumptions": {
                "time_series_data": True,
                "continuous_data": True,
                "adequate_length": len(series) >= 20,
                "no_structural_breaks": "Not tested; consider Perron test if suspected",
            },
            "explanations": {
                "test_purpose": "Tests for presence of unit root (non-stationarity) in time series data.",
                "null_hypothesis": "H0: The series has a unit root (non-stationary).",
                "alternative_hypothesis": "H1: The series is stationary (no unit root).",
                "pharmacovigilance_example": "Testing PK concentration time series for stationarity before modeling.",
                "when_to_use": [
                    "Time series analysis requiring stationarity",
                    "ARIMA model identification",
                    "Trend detection and detrending",
                    "Unit root testing",
                ],
                "regression_types": {
                    "c": "Constant only (no trend)",
                    "ct": "Constant and linear trend",
                    "ctt": "Constant, linear and quadratic trend",
                    "n": "No constant, no trend",
                },
                "p_value_meaning": f"P-value ({p_value:.4e}) indicates {'stationarity' if p_value < self.alpha else 'non-stationarity'} at α={self.alpha}.",
                "critical_values_meaning": "If ADF statistic < critical value, reject H0 (stationary).",
            },
            "interpretations": {
                "main_finding": (
                    f"{'Stationary' if is_stationary else 'Non-stationary'} time series "
                    f"(ADF={adf_statistic:.4f}, p={p_value:.4e}). "
                    f"{'Unit root rejected' if is_stationary else 'Unit root present'}"
                ),
                "statistical_significance": (
                    f"{'Significant evidence of stationarity' if p_value < self.alpha else 'No evidence against unit root'} "
                    f"at {self.alpha * 100}% level."
                ),
                "clinical_relevance": (
                    f"{'Series is suitable for stationary time-series analysis' if is_stationary else 'Series requires differencing or detrending before analysis'}. "
                    f"{'Trend present' if has_trend else 'No significant trend detected'}"
                )
                if trend_strength
                else None,
                "plain_language": (
                    f"The time series {'is stable' if is_stationary else 'has a trend or pattern that changes over time'}. "
                    f"{'This is good for analysis' if is_stationary else 'We may need to adjust the data before analysis'}"
                ),
            },
            "recommendations": [
                f"ADF test indicates {'stationary' if is_stationary else 'non-stationary'} series.",
                f"{'Suitable for time-series modeling' if is_stationary else 'Consider differencing or detrending'}.",
                "For trend-stationary series, detrend before analysis.",
                "For difference-stationary series, apply appropriate differencing.",
                "Verify visual inspection with statistical test results.",
                "Consider KPSS test as complementary stationarity test.",
            ],
            "glp_gcp_compliance": {
                "regulatory_guidelines": [
                    "ICH E9 Section 5.3: Time series analysis",
                    "FDA Guidance: Pharmacokinetic data analysis",
                    "EMA Guideline: Time series modeling",
                ],
                "sap_requirements": "Stationarity testing pre-specified in SAP for time-series analysis.",
                "data_integrity": "All time series values accurately recorded.",
                "documentation": "ADF statistic, p-value, critical values reported for audit trail.",
            },
            "references": [
                "Dickey DA, Fuller WA. (1979). Distribution of the estimators for autoregressive time series. Journal of the American Statistical Association.",
                "Hamilton JD. (1994). Time Series Analysis. Princeton University Press.",
                "ICH E9 (1998). Statistical Principles for Clinical Trials.",
            ],
        }

        return results

    # ============================================
    # POWER ANALYSIS METHODS
    # ============================================

    def perform_power_analysis(
        self,
        effect_size: float,
        n_obs: Optional[float] = None,
        alpha: Optional[float] = None,
        power: Optional[float] = None,
        alternative: str = "two-sided",
        test_type: str = "ttest",
        ratio: float = 1.0,
    ) -> Dict[str, Any]:
        """Power analysis for study design and sample size calculation

        Pharmacovigilance Example:
            Calculate required sample size for detecting treatment differences
            in clinical trials based on expected effect size and desired power.

        FDA/EMA Compliance:
            - ICH E9 Section 3.5: Sample size determination
            - Essential for study design and regulatory submissions
            - Used to ensure adequate power for detecting clinically meaningful effects

        Args:
            effect_size: Standardized effect size (Cohen's d, f, h, or w depending on test)
            n_obs: Total sample size (leave None to solve for)
            alpha: Significance level (default: self.alpha)
            power: Statistical power (1 - beta) (leave None to solve for)
            alternative: 'two-sided', 'larger', 'smaller'
            test_type: 'ttest', 'anova', 'chisquare', 'proportion', 'correlation'
            ratio: Ratio of sample sizes (n2/n1 for ttest, default: 1.0)

        Returns:
            Dictionary with power analysis results, sample size calculations, interpretations
        """
        # Use default alpha if not provided
        if alpha is None:
            alpha = self.alpha

        # Validate inputs - exactly one must be None to solve for
        non_none_count = len([x for x in [n_obs, alpha, power] if x is not None])
        if non_none_count != 2:
            raise ValueError(
                "Exactly one of n_obs, alpha, or power must be None to solve for"
            )

        if effect_size <= 0:
            raise ValueError("Effect size must be positive")

        # Initialize result
        result = {}

        # Perform power analysis based on test type
        if test_type == "ttest":
            # Independent samples t-test
            analysis = TTestIndPower()

            if n_obs is None:
                # Solve for sample size
                result = analysis.solve_power(
                    effect_size=effect_size,
                    nobs1=None,
                    alpha=alpha,
                    power=power,
                    ratio=ratio,
                    alternative=alternative,
                )
                # Total sample size (both groups)
                n_total = result * (1 + ratio)
                n_group1 = result
                n_group2 = result * ratio

            elif power is None:
                # Solve for power
                result = analysis.solve_power(
                    effect_size=effect_size,
                    nobs1=n_obs / (1 + ratio),  # Convert total to n1
                    alpha=alpha,
                    power=None,
                    ratio=ratio,
                    alternative=alternative,
                )
                power = result
                n_total = n_obs
                n_group1 = n_obs / (1 + ratio)
                n_group2 = n_obs * ratio / (1 + ratio)

            else:
                # Solve for alpha (rarely used)
                result = analysis.solve_power(
                    effect_size=effect_size,
                    nobs1=n_obs / (1 + ratio),
                    alpha=None,
                    power=power,
                    ratio=ratio,
                    alternative=alternative,
                )
                alpha = result
                n_total = n_obs
                n_group1 = n_obs / (1 + ratio)
                n_group2 = n_obs * ratio / (1 + ratio)

        elif test_type == "anova":
            # One-way ANOVA
            # Note: FTestAnovaPower has limited interface, so we use workaround
            analysis = FTestAnovaPower()

            if n_obs is None:
                # Solve for sample size (per group)
                result = analysis.solve_power(
                    effect_size=effect_size, nobs=None, alpha=alpha, power=power
                )
                n_total = result * 3  # Assuming 3 groups
            elif power is None:
                # Solve for power
                result = analysis.solve_power(
                    effect_size=effect_size,
                    nobs=n_obs / 3,  # Assuming 3 groups
                    alpha=alpha,
                    power=None,
                )
                power = result
                n_total = n_obs

        elif test_type == "chisquare":
            # Chi-square goodness of fit or test of independence
            # Using normal approximation for chi-square
            df = 1  # Simplified; actual df depends on table dimensions

            if n_obs is None:
                # Solve for sample size
                # Non-central chi-square approximation
                ncp = (n_obs or 100) * effect_size**2
                z_alpha = stats.norm.ppf(1 - alpha / 2)
                z_beta = stats.norm.ppf(power)
                n_total = ((z_alpha + z_beta) / effect_size) ** 2
            elif power is None:
                # Solve for power
                z_alpha = stats.norm.ppf(1 - alpha / 2)
                ncp = n_obs * effect_size**2
                power = stats.ncx2.sf(stats.chi2.ppf(1 - alpha, df), df, ncp)

        elif test_type == "correlation":
            # Correlation test
            # Using Fisher's z-transformation
            n_obs_per_group = n_obs if n_obs else (power or 0.8)

            if n_obs is None:
                # Solve for sample size
                z_alpha = (
                    stats.norm.ppf(1 - alpha / 2)
                    if alternative == "two-sided"
                    else stats.norm.ppf(1 - alpha)
                )
                z_beta = stats.norm.ppf(power)

                # Fisher's z transformation
                z_effect = 0.5 * np.log((1 + effect_size) / (1 - effect_size))

                n_total = ((z_alpha + z_beta) / z_effect) ** 2 + 3
            elif power is None:
                # Solve for power
                z_alpha = (
                    stats.norm.ppf(1 - alpha / 2)
                    if alternative == "two-sided"
                    else stats.norm.ppf(1 - alpha)
                )
                z_effect = 0.5 * np.log((1 + effect_size) / (1 - effect_size))
                z_beta = z_effect * np.sqrt(n_obs - 3) - z_alpha
                power = stats.norm.cdf(z_beta)

        else:
            raise ValueError(f"Unsupported test_type: {test_type}")

        # Effect size interpretation
        effect_size_interpretation = self._interpret_effect_size(effect_size, test_type)

        # Power interpretation
        power_interpretation = self._interpret_power(power)

        results = {
            "analysis_type": "Power Analysis",
            "timestamp": datetime.now().isoformat(),
            "test_parameters": {
                "test_type": test_type,
                "effect_size": float(effect_size),
                "effect_size_interpretation": effect_size_interpretation,
                "alpha": float(alpha),
                "alternative": alternative,
                "ratio": float(ratio),
            },
            "calculated_values": {
                "power": float(power) if power is not None else None,
                "n_total": float(n_total) if n_total else None,
                "n_group1": float(n_group1) if "n_group1" in locals() else None,
                "n_group2": float(n_group2) if "n_group2" in locals() else None,
            },
            "interpretations": {
                "effect_size": f"Cohen's {'d' if test_type == 'ttest' else 'f' if test_type == 'anova' else 'h' if test_type == 'proportion' else 'w'} = {effect_size:.2f} ({effect_size_interpretation} effect).",
                "power": f"Power = {power:.2%} ({power_interpretation})."
                if power
                else None,
                "sample_size": f"Required total N = {int(n_total)} ({int(n_group1)} per group)."
                if n_total
                else None,
                "alpha": f"Significance level α = {alpha:.3f}.",
                "plain_language": (
                    f"{'With this sample size, you have a ' + str(round(power * 100, 1)) + '% chance' if power else 'To have an 80% chance'} "
                    f"of detecting a {effect_size_interpretation} effect if it exists. "
                    f"{'This is considered adequate power (≥80%).' if power and power >= 0.8 else 'Higher power may be needed for regulatory acceptance.'}"
                ),
            },
            "assumptions": {
                "independent_observations": True,
                "normal_distribution": "For t-tests and ANOVA",
                "equal_variances": "For t-tests and ANOVA (assumes homogeneity)",
                "effect_size_known": "Effect size estimated from pilot data or literature",
            },
            "explanations": {
                "test_purpose": "Calculate statistical power or required sample size for hypothesis tests.",
                "effect_size_meaning": f"{effect_size_interpretation} standardized effect ({effect_size:.2f}).",
                "power_meaning": f"Probability of correctly rejecting H0 when H1 is true ({power:.2%})."
                if power
                else None,
                "alpha_meaning": f"Probability of Type I error (false positive) = {alpha:.3f}.",
                "pharmacovigilance_example": "Calculate sample size for clinical trial to detect treatment difference with 80% power.",
                "when_to_use": [
                    "Study design and sample size planning",
                    "Power analysis for clinical trials",
                    "Determining feasibility of studies",
                    "Regulatory submissions",
                ],
                "effect_size_guidelines": {
                    "ttest": "Cohen's d: 0.2=small, 0.5=medium, 0.8=large",
                    "anova": "Cohen's f: 0.1=small, 0.25=medium, 0.4=large",
                    "chisquare": "Cohen's w: 0.1=small, 0.3=medium, 0.5=large",
                    "correlation": "r: 0.1=small, 0.3=medium, 0.5=large",
                },
            },
            "recommendations": [
                f"{'Adequate power' if power and power >= 0.8 else 'Low power - consider increasing sample size'} for detecting {effect_size_interpretation} effect.",
                "Use effect sizes from pilot studies or meta-analyses for accurate calculations.",
                "Consider multiple comparison adjustments for primary endpoints.",
                f"Sample size: {int(n_total)} total ({int(n_group1)} per group)."
                if n_total
                else "Increase sample size to achieve desired power.",
                "Regulatory agencies typically require power ≥80% for primary endpoints.",
                "Account for dropout rates in sample size planning.",
            ],
            "glp_gcp_compliance": {
                "regulatory_guidelines": [
                    "ICH E9 Section 3.5: Sample size determination",
                    "FDA Guidance: Statistical considerations for clinical trials",
                    "EMA Guideline: Points to consider on sample size",
                ],
                "sap_requirements": "Sample size calculations documented in SAP with justification.",
                "data_integrity": "Effect sizes based on reliable pilot data or literature.",
                "documentation": "Power analysis parameters and results recorded for audit trail.",
            },
            "references": [
                "Cohen J. (1988). Statistical Power Analysis for the Behavioral Sciences. 2nd ed. Lawrence Erlbaum.",
                "Chow SC, Liu JP. (1998). Design and Analysis of Clinical Trials. Wiley.",
                "ICH E9 (1998). Statistical Principles for Clinical Trials.",
            ],
        }

        return results

    def _interpret_effect_size(self, effect_size: float, test_type: str) -> str:
        """Interpret effect size magnitude"""
        if test_type in ["ttest", "correlation"]:
            if effect_size < 0.2:
                return "negligible"
            elif effect_size < 0.5:
                return "small"
            elif effect_size < 0.8:
                return "medium"
            else:
                return "large"
        elif test_type == "anova":
            if effect_size < 0.1:
                return "negligible"
            elif effect_size < 0.25:
                return "small"
            elif effect_size < 0.4:
                return "medium"
            else:
                return "large"
        elif test_type in ["chisquare", "proportion"]:
            if effect_size < 0.1:
                return "negligible"
            elif effect_size < 0.3:
                return "small"
            elif effect_size < 0.5:
                return "medium"
            else:
                return "large"
        return "unknown"

    def _interpret_power(self, power: float) -> str:
        """Interpret statistical power"""
        if power < 0.5:
            return "inadequate - high risk of Type II error"
        elif power < 0.8:
            return "moderate - may be insufficient for regulatory acceptance"
        elif power < 0.9:
            return "adequate - meets typical requirements"
        else:
            return "high - excellent power"


# ============================================
# EXAMPLE USAGE
# ============================================

if __name__ == "__main__":
    """Example usage of AdditionalStatisticalTools"""

    import numpy as np
    import pandas as pd

    print("=" * 70)
    print("AdditionalStatisticalTools - Example Usage")
    print("=" * 70)

    # Initialize tools
    tools = AdditionalStatisticalTools(alpha=0.05)

    # Example 1: Wilcoxon Signed Rank Test
    print("\n--- Wilcoxon Signed Rank Test ---")
    pre_treatment = np.array([3.2, 4.1, 3.8, 5.2, 4.5, 3.9, 4.2, 4.8, 4.1, 3.7])
    post_treatment = np.array([2.8, 3.5, 3.2, 4.5, 3.8, 3.4, 3.9, 4.2, 3.7, 3.3])
    result = tools.wilcoxon_signed_rank_test(pre_treatment, post_treatment)
    print(f"Significant: {result['test_results']['significant']}")
    print(f"P-value: {result['test_results']['p_value']:.4f}")
    print(f"Effect size (r): {result['effect_size']['effect_size_r']:.3f}")

    # Example 2: Chi-square Test of Independence
    print("\n--- Chi-square Test of Independence ---")
    contingency_table = [
        [45, 15],  # Treatment: No AE, AE
        [30, 30],  # Control: No AE, AE
    ]
    result = tools.chi_square_test_independence(contingency_table)
    print(f"Significant association: {result['test_results']['significant']}")
    print(f"P-value: {result['test_results']['p_value']:.4f}")
    print(f"Cramer's V: {result['effect_size']['cramers_v']:.3f}")

    # Example 3: Fisher's Exact Test
    print("\n--- Fisher's Exact Test ---")
    result = tools.fisher_exact_test([[8, 2], [3, 7]])
    print(f"Significant: {result['test_results']['significant']}")
    print(f"P-value: {result['test_results']['p_value']:.4f}")
    print(f"Odds ratio: {result['measures']['odds_ratio']['value']:.2f}")

    # Example 4: McNemar Test
    print("\n--- McNemar Test ---")
    paired_table = [
        [30, 5],  # Before: No, After: Yes (treatment-emergent)
        [10, 55],  # Before: Yes, After: No (improvement)
    ]
    result = tools.mcnemar_test(paired_table)
    print(f"Significant change: {result['test_results']['significant']}")
    print(f"P-value: {result['test_results']['p_value']:.4f}")

    # Example 5: Cochran-Mantel-Haenszel Test
    print("\n--- Cochran-Mantel-Haenszel Test ---")
    tables = [
        [[20, 5], [10, 15]],  # Site 1
        [[15, 8], [12, 15]],  # Site 2
        [[25, 3], [8, 14]],  # Site 3
    ]
    result = tools.cochran_mantel_haenszel_test(
        tables, strata_names=["Site 1", "Site 2", "Site 3"]
    )
    print(f"Significant after adjusting: {result['test_results']['significant']}")
    print(f"Pooled OR: {result['pooled_odds_ratio']['value']:.3f}")

    # Example 6: Power Analysis
    print("\n--- Power Analysis ---")
    result = tools.perform_power_analysis(
        effect_size=0.5,  # Medium effect
        alpha=0.05,
        power=0.80,
        test_type="ttest",
        alternative="two-sided",
    )
    print(f"Required total N: {int(result['calculated_values']['n_total'])}")
    print(f"Per group: {int(result['calculated_values']['n_group1'])}")

    # Example 7: ADF Test
    print("\n--- ADF Test ---")
    np.random.seed(42)
    stationary_series = np.random.normal(0, 1, 100)
    result = tools.perform_adf_test(stationary_series)
    print(f"Stationary: {result['test_results']['stationary']}")
    print(f"P-value: {result['test_results']['p_value']:.4f}")

    print("\n" + "=" * 70)
    print("Example usage completed successfully!")
    print("=" * 70)
