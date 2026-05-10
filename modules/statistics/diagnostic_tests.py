"""Diagnostic Tests for Pharmaceutical Statistics

Comprehensive diagnostic testing suite for statistical assumptions validation
in pharmaceutical research and clinical trials.

Complies with:
- Good Laboratory Practice (GLP)
- Good Clinical Practice (GCP)
- FDA Statistical Guidance for Clinical Trials
- EMA Guideline on Statistical Principles for Clinical Trials
- ICH E9 Statistical Principles for Clinical Trials

Usage Examples:
    >>> tests = DiagnosticTests(alpha=0.05)
    >>> 
    >>> # Check normality of biomarker data
    >>> result = tests.test_normality_shapiro_wilk(df['biomarker_level'])
    >>> print(result['interpretation'])
    >>> 
    >>> # Check homogeneity of variance across treatment groups
    >>> groups = [df[df['treatment']==g]['response'] for g in df['treatment'].unique()]
    >>> result = tests.test_homogeneity_variance_levene(groups)
    >>> 
    >>> # Run comprehensive diagnostics
    >>> full_report = tests.comprehensive_diagnostics(df, 
    ...     numeric_cols=['biomarker', 'response'],
    ...     group_col='treatment')
"""

import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
from scipy.spatial.distance import mahalanobis
import warnings
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime

warnings.filterwarnings('ignore')


class DiagnosticTests:
    """Comprehensive diagnostic testing suite for pharmaceutical statistics

    Provides:
    - Normality testing (Shapiro-Wilk, KS, Anderson-Darling)
    - Homogeneity of variance testing (Levene, Bartlett)
    - Multicollinearity detection (VIF)
    - Outlier detection (IQR, Z-score, Mahalanobis)
    - Comprehensive diagnostic reports
    """

    def __init__(self, alpha: float = 0.05):
        """Initialize diagnostic tests

        Args:
            alpha: Significance level for hypothesis tests (default: 0.05)
        """
        self.alpha = alpha
        self.analysis_history = []
        self.current_analysis = None

    # ============================================================================
    # NORMALITY TESTS
    # ============================================================================

    def test_normality_shapiro_wilk(
        self, 
        data: Union[pd.Series, np.ndarray, List[float]],
        variable_name: str = "variable"
    ) -> Dict[str, Any]:
        """Shapiro-Wilk test for normality (recommended for n < 50)

        The Shapiro-Wilk test is one of the most powerful tests for normality,
        especially for small to moderate sample sizes. It tests the null hypothesis
        that the data was drawn from a normal distribution.

        Pharmaceutical Example:
            In a Phase I trial, researcher wants to verify if baseline ALT levels
            (n=30 subjects) follow a normal distribution before conducting ANOVA.

        Args:
            data: Numeric data to test for normality
            variable_name: Name of the variable being tested

        Returns:
            Dictionary containing test statistic, p-value, interpretation,
            assumption status, and recommendations

        Raises:
            ValueError: If data has fewer than 3 observations or contains non-numeric data
        """
        # Data validation
        if isinstance(data, pd.Series):
            data = data.dropna().values
        elif isinstance(data, list):
            data = np.array(data)
        
        if len(data) < 3:
            raise ValueError(f"Shapiro-Wilk test requires at least 3 observations. Got {len(data)}.")
        
        if not np.issubdtype(data.dtype, np.number):
            raise ValueError("Data must be numeric for Shapiro-Wilk test.")

        # Perform test
        statistic, p_value = stats.shapiro(data)
        
        # Interpretation
        is_normal = p_value > self.alpha
        
        result = {
            'test_type': 'Shapiro-Wilk Normality Test',
            'variable_name': variable_name,
            'sample_size': len(data),
            'statistic': float(statistic),
            'p_value': float(p_value),
            'alpha': self.alpha,
            'is_normal': is_normal,
            'assumption_met': is_normal,
            'timestamp': datetime.now().isoformat()
        }

        # Generate interpretation
        result['interpretation'] = self._interpret_shapiro_wilk(statistic, p_value, len(data), variable_name)
        result['explanation'] = self._explain_shapiro_wilk()
        result['recommendations'] = self._recommend_shapiro_wilk(is_normal, len(data), variable_name)
        
        # Store in history
        self._log_analysis('shapiro_wilk', result)
        
        return result

    def _interpret_shapiro_wilk(
        self, 
        statistic: float, 
        p_value: float, 
        n: int, 
        var_name: str
    ) -> str:
        """Generate interpretation for Shapiro-Wilk test"""
        if p_value > self.alpha:
            return (
                f"The Shapiro-Wilk test (W = {statistic:.4f}, p = {p_value:.4f}) "
                f"does NOT reject the null hypothesis at α = {self.alpha}. "
                f"There is insufficient evidence to conclude that {var_name} (n = {n}) "
                f"deviates from a normal distribution. The normality assumption appears satisfied."
            )
        else:
            return (
                f"The Shapiro-Wilk test (W = {statistic:.4f}, p = {p_value:.4f}) "
                f"rejects the null hypothesis at α = {self.alpha}. "
                f"{var_name} (n = {n}) shows significant deviation from normal distribution. "
                f"The normality assumption is violated."
            )

    def _explain_shapiro_wilk(self) -> str:
        """Provide explanation of Shapiro-Wilk test"""
        return (
            "Shapiro-Wilk Test Explanation:\n"
            "- Tests whether data follows a normal (Gaussian) distribution\n"
            "- Null Hypothesis (H0): Data is normally distributed\n"
            "- Alternative Hypothesis (H1): Data is NOT normally distributed\n"
            "- Most powerful test for small to moderate samples (n < 50)\n"
            "- Statistic W ranges from 0 to 1 (closer to 1 = more normal)\n"
            "- Sensitive to sample size: large n may detect trivial deviations\n"
            "\nClinical Relevance:\n"
            "Many parametric tests (t-tests, ANOVA, linear regression) assume normality. "
            "Violating this assumption can lead to incorrect Type I/II error rates in "
            "clinical trial analyses."
        )

    def _recommend_shapiro_wilk(
        self, 
        is_normal: bool, 
        n: int, 
        var_name: str
    ) -> List[str]:
        """Generate recommendations based on Shapiro-Wilk results"""
        recommendations = []
        
        if is_normal:
            recommendations.append(
                f"✓ Normality assumption satisfied for {var_name}. "
                f"Parametric tests (t-test, ANOVA) are appropriate."
            )
            recommendations.append(
                "Consider visual inspection (Q-Q plot, histogram) as supplementary evidence."
            )
        else:
            recommendations.append(
                f"✗ Normality assumption violated for {var_name}. "
                f"Consider the following options:"
            )
            recommendations.append(
                "  1. Data transformation: Try log, square root, or Box-Cox transformation"
            )
            recommendations.append(
                "  2. Non-parametric alternatives: Mann-Whitney U test, Kruskal-Wallis test"
            )
            recommendations.append(
                "  3. Bootstrap methods: Resampling-based inference"
            )
            
            if n >= 30:
                recommendations.append(
                    "  4. Central Limit Theorem: With n ≥ 30, parametric tests may be robust "
                    "to moderate non-normality for mean comparisons"
                )
            
            recommendations.append(
                "  5. Verify outliers: Extreme values can cause apparent non-normality"
            )
        
        return recommendations

    def test_normality_ks(
        self, 
        data: Union[pd.Series, np.ndarray, List[float]],
        variable_name: str = "variable"
    ) -> Dict[str, Any]:
        """Kolmogorov-Smirnov test for normality

        The KS test compares the empirical distribution function of the data
        with the cumulative distribution function of a normal distribution.
        It is non-parametric and can be used with larger sample sizes.

        Pharmaceutical Example:
            In a Phase III trial with n=200 subjects per arm, researcher uses
            KS test to assess normality of primary endpoint (change in HbA1c).

        Args:
            data: Numeric data to test for normality
            variable_name: Name of the variable being tested

        Returns:
            Dictionary containing test statistic, p-value, interpretation,
            assumption status, and recommendations

        Note:
            Unlike Shapiro-Wilk, KS test estimates parameters from data. For stricter
            testing with known parameters, use `scipy.stats.kstest` with specified args.
        """
        # Data validation
        if isinstance(data, pd.Series):
            data = data.dropna().values
        elif isinstance(data, list):
            data = np.array(data)
        
        if len(data) < 5:
            raise ValueError(f"KS test requires at least 5 observations. Got {len(data)}.")
        
        if not np.issubdtype(data.dtype, np.number):
            raise ValueError("Data must be numeric for KS test.")

        # Estimate parameters and perform test
        mu, sigma = data.mean(), data.std(ddof=1)
        
        if sigma == 0:
            raise ValueError("Cannot perform KS test: data has zero variance.")
        
        statistic, p_value = stats.kstest(data, 'norm', args=(mu, sigma))
        
        # Interpretation
        is_normal = p_value > self.alpha
        
        result = {
            'test_type': 'Kolmogorov-Smirnov Normality Test',
            'variable_name': variable_name,
            'sample_size': len(data),
            'mean': float(mu),
            'std': float(sigma),
            'statistic': float(statistic),
            'p_value': float(p_value),
            'alpha': self.alpha,
            'is_normal': is_normal,
            'assumption_met': is_normal,
            'timestamp': datetime.now().isoformat()
        }

        # Generate interpretation
        result['interpretation'] = self._interpret_ks_test(statistic, p_value, len(data), variable_name)
        result['explanation'] = self._explain_ks_test()
        result['recommendations'] = self._recommend_ks_test(is_normal, len(data), variable_name)
        
        self._log_analysis('kolmogorov_smirnov', result)
        
        return result

    def _interpret_ks_test(
        self, 
        statistic: float, 
        p_value: float, 
        n: int, 
        var_name: str
    ) -> str:
        """Generate interpretation for KS test"""
        if p_value > self.alpha:
            return (
                f"The Kolmogorov-Smirnov test (D = {statistic:.4f}, p = {p_value:.4f}) "
                f"does NOT reject the null hypothesis at α = {self.alpha}. "
                f"The empirical distribution of {var_name} (n = {n}) does not significantly "
                f"deviate from a normal distribution with the estimated parameters."
            )
        else:
            return (
                f"The Kolmogorov-Smirnov test (D = {statistic:.4f}, p = {p_value:.4f}) "
                f"rejects the null hypothesis at α = {self.alpha}. "
                f"The empirical distribution of {var_name} (n = {n}) significantly "
                f"differs from a normal distribution."
            )

    def _explain_ks_test(self) -> str:
        """Provide explanation of KS test"""
        return (
            "Kolmogorov-Smirnov Test Explanation:\n"
            "- Compares empirical distribution to theoretical normal distribution\n"
            "- Null Hypothesis (H0): Data follows normal distribution\n"
            "- Alternative Hypothesis (H1): Data does NOT follow normal distribution\n"
            "- Statistic D represents maximum distance between distributions\n"
            "- Suitable for larger sample sizes (n ≥ 50)\n"
            "- Less powerful than Shapiro-Wilk for small samples\n"
            "- Parameters estimated from data (conservative approach)\n"
            "\nClinical Relevance:\n"
            "The KS test is distribution-free and can detect any deviation from normality. "
            "It is particularly useful for large clinical trial datasets where Shapiro-Wilk "
            "may be overly sensitive to minor departures from normality."
        )

    def _recommend_ks_test(
        self, 
        is_normal: bool, 
        n: int, 
        var_name: str
    ) -> List[str]:
        """Generate recommendations based on KS test results"""
        recommendations = []
        
        if is_normal:
            recommendations.append(
                f"✓ Normality assumption satisfied for {var_name} (KS test). "
                f"Parametric tests are appropriate."
            )
            if n < 50:
                recommendations.append(
                    "Note: For n < 50, Shapiro-Wilk test is generally more powerful. "
                    "Consider running both tests for confirmation."
                )
        else:
            recommendations.append(
                f"✗ Normality assumption violated for {var_name} (KS test)."
            )
            recommendations.append(
                "Recommendations (same as Shapiro-Wilk):\n"
                "  1. Data transformation (log, sqrt, Box-Cox)\n"
                "  2. Non-parametric alternatives\n"
                "  3. Bootstrap methods\n"
                "  4. Outlier investigation"
            )
        
        return recommendations

    def test_normality_anderson_darling(
        self, 
        data: Union[pd.Series, np.ndarray, List[float]],
        variable_name: str = "variable"
    ) -> Dict[str, Any]:
        """Anderson-Darling test for normality

        The Anderson-Darling test is a modification of the KS test that gives
        more weight to the tails of the distribution. It is particularly
        sensitive to deviations in the tails, which is important for detecting
        outliers and tail behavior.

        Pharmaceutical Example:
            In a bioequivalence study, researcher wants to verify that Cmax
            distribution has normal tails, as extreme values can affect bioequivalence
            conclusions. Anderson-Darling test is ideal for this purpose.

        Args:
            data: Numeric data to test for normality
            variable_name: Name of the variable being tested

        Returns:
            Dictionary containing test statistic, critical values,
            significance levels, interpretation, and recommendations
        """
        # Data validation
        if isinstance(data, pd.Series):
            data = data.dropna().values
        elif isinstance(data, list):
            data = np.array(data)
        
        if len(data) < 5:
            raise ValueError(f"Anderson-Darling test requires at least 5 observations. Got {len(data)}.")
        
        if not np.issubdtype(data.dtype, np.number):
            raise ValueError("Data must be numeric for Anderson-Darling test.")

        # Perform test
        result = stats.anderson(data, dist='norm')
        
        statistic = result.statistic
        critical_values = result.critical_values
        significance_levels = result.significance_level
        
        # Determine if normality is rejected at alpha level
        # Find the critical value corresponding to our alpha
        is_normal = statistic < critical_values[2]  # Using 5% significance level (index 2)
        
        result_dict = {
            'test_type': 'Anderson-Darling Normality Test',
            'variable_name': variable_name,
            'sample_size': len(data),
            'statistic': float(statistic),
            'critical_values': [float(cv) for cv in critical_values],
            'significance_levels': [float(sl) for sl in significance_levels],
            'alpha': self.alpha,
            'is_normal': is_normal,
            'assumption_met': is_normal,
            'timestamp': datetime.now().isoformat()
        }

        # Generate interpretation
        result_dict['interpretation'] = self._interpret_anderson_darling(
            statistic, critical_values, significance_levels, len(data), variable_name
        )
        result_dict['explanation'] = self._explain_anderson_darling()
        result_dict['recommendations'] = self._recommend_anderson_darling(is_normal, len(data), variable_name)
        
        self._log_analysis('anderson_darling', result_dict)
        
        return result_dict

    def _interpret_anderson_darling(
        self, 
        statistic: float,
        critical_values: np.ndarray,
        significance_levels: np.ndarray,
        n: int,
        var_name: str
    ) -> str:
        """Generate interpretation for Anderson-Darling test"""
        interpretation = (
            f"The Anderson-Darling test statistic is A² = {statistic:.4f} "
            f"for {var_name} (n = {n}).\n\n"
            "Critical Values at various significance levels:\n"
        )
        
        for cv, sl in zip(critical_values, significance_levels):
            interpretation += f"  {sl}% significance: {cv:.4f}\n"
        
        interpretation += "\n"
        
        # Determine at which levels normality is rejected
        rejected_levels = []
        for cv, sl in zip(critical_values, significance_levels):
            if statistic > cv:
                rejected_levels.append(f"{sl}%")
        
        if statistic < critical_values[2]:  # 5% level
            interpretation += (
                f"The test statistic is below the critical value at the 5% significance level "
                f"({critical_values[2]:.4f}). Normality is NOT rejected at α = 0.05. "
                f"The distribution appears normal, including in the tails."
            )
        else:
            interpretation += (
                f"The test statistic exceeds the critical value at the 5% significance level "
                f"({critical_values[2]:.4f}). Normality is REJECTED at α = 0.05. "
                f"The distribution significantly deviates from normal, particularly in the tails."
            )
            
            if rejected_levels:
                interpretation += f" Normality rejected at: {', '.join(rejected_levels)} significance levels."
        
        return interpretation

    def _explain_anderson_darling(self) -> str:
        """Provide explanation of Anderson-Darling test"""
        return (
            "Anderson-Darling Test Explanation:\n"
            "- Tests normality with emphasis on distribution tails\n"
            "- Null Hypothesis (H0): Data follows normal distribution\n"
            "- Alternative Hypothesis (H1): Data does NOT follow normal distribution\n"
            "- Statistic A²: Larger values indicate greater deviation from normality\n"
            "- More sensitive to tail behavior than KS test\n"
            "- Critical values provided at multiple significance levels\n"
            "- Particularly useful for detecting outliers and tail deviations\n"
            "\nClinical Relevance:\n"
            "In pharmaceutical research, tail behavior is critical for safety assessment. "
            "The Anderson-Darling test helps identify if extreme values (e.g., adverse events, "
            "outlier lab values) are more common than expected under normality."
        )

    def _recommend_anderson_darling(
        self, 
        is_normal: bool, 
        n: int, 
        var_name: str
    ) -> List[str]:
        """Generate recommendations based on Anderson-Darling results"""
        recommendations = []
        
        if is_normal:
            recommendations.append(
                f"✓ Normality assumption satisfied for {var_name} (including tails). "
                f"Parametric tests are appropriate."
            )
            recommendations.append(
                "The distribution shows no significant deviations in the tails, "
                "suggesting extreme values are within expected limits."
            )
        else:
            recommendations.append(
                f"✗ Normality assumption violated for {var_name} (Anderson-Darling test)."
            )
            recommendations.append(
                "The deviation is likely in the distribution tails. Consider:\n"
                "  1. Investigating outliers: Examine extreme values for data quality issues\n"
                "  2. Robust methods: Use tests resistant to outliers\n"
                "  3. Truncation: Consider winsorization if outliers are legitimate\n"
                "  4. Alternative distributions: Consider log-normal or other distributions"
            )
        
        return recommendations

    # ============================================================================
    # HOMOGENEITY OF VARIANCE TESTS
    # ============================================================================

    def test_homogeneity_variance_levene(
        self, 
        groups: List[Union[pd.Series, np.ndarray, List[float]]],
        group_names: Optional[List[str]] = None,
        center: str = 'median'
    ) -> Dict[str, Any]:
        """Levene's test for homogeneity of variance

        Levene's test assesses whether variances are equal across groups.
        It is robust to departures from normality, making it suitable for
        pharmaceutical data that may not meet normality assumptions.

        Pharmaceutical Example:
            In a parallel-group study comparing 3 doses of a new drug,
            researcher uses Levene's test to verify that response variability
            is similar across dose groups before conducting ANOVA.

        Args:
            groups: List of arrays containing data for each group
            group_names: Optional names for each group
            center: Method for centering data ('median', 'mean', 'trimmed').
                    'median' is default and most robust to non-normality.

        Returns:
            Dictionary containing test statistic, p-value, interpretation,
            assumption status, and recommendations

        Note:
            Levene's test with median centering is the Brown-Forsythe test,
            which is robust to non-normality and recommended for most applications.
        """
        # Data validation
        if len(groups) < 2:
            raise ValueError("Levene's test requires at least 2 groups.")
        
        # Convert and clean data
        cleaned_groups = []
        for i, group in enumerate(groups):
            if isinstance(group, pd.Series):
                group = group.dropna().values
            elif isinstance(group, list):
                group = np.array(group)
            
            if len(group) < 2:
                raise ValueError(f"Group {i} has only {len(group)} observations. Minimum 2 required.")
            
            cleaned_groups.append(group)
        
        # Generate group names if not provided
        if group_names is None:
            group_names = [f"Group {i+1}" for i in range(len(groups))]
        
        # Perform test
        statistic, p_value = stats.levene(*cleaned_groups, center=center)
        
        # Calculate variances for each group
        variances = [float(np.var(g, ddof=1)) for g in cleaned_groups]
        
        # Interpretation
        is_homogeneous = p_value > self.alpha
        
        result = {
            'test_type': f"Levene's Test for Homogeneity of Variance (center={center})",
            'group_names': group_names,
            'group_sizes': [len(g) for g in cleaned_groups],
            'group_variances': variances,
            'variance_ratio': float(max(variances) / min(variances)) if min(variances) > 0 else float('inf'),
            'statistic': float(statistic),
            'p_value': float(p_value),
            'alpha': self.alpha,
            'is_homogeneous': is_homogeneous,
            'assumption_met': is_homogeneous,
            'timestamp': datetime.now().isoformat()
        }

        # Generate interpretation
        result['interpretation'] = self._interpret_levene(
            statistic, p_value, variances, group_names, is_homogeneous
        )
        result['explanation'] = self._explain_levene()
        result['recommendations'] = self._recommend_levene(is_homogeneous, variances)
        
        self._log_analysis('levene', result)
        
        return result

    def _interpret_levene(
        self, 
        statistic: float, 
        p_value: float,
        variances: List[float],
        group_names: List[str],
        is_homogeneous: bool
    ) -> str:
        """Generate interpretation for Levene's test"""
        interpretation = (
            f"Levene's Test (W = {statistic:.4f}, p = {p_value:.4f}) "
            f"at α = {self.alpha}.\n\n"
            "Group Variances:\n"
        )
        
        for name, var in zip(group_names, variances):
            interpretation += f"  {name}: {var:.4f}\n"
        
        variance_ratio = max(variances) / min(variances) if min(variances) > 0 else float('inf')
        interpretation += f"\nVariance Ratio (max/min): {variance_ratio:.2f}\n\n"
        
        if is_homogeneous:
            interpretation += (
                "The test does NOT reject the null hypothesis. "
                "There is insufficient evidence to conclude that variances differ across groups. "
                "The homogeneity of variance assumption is satisfied."
            )
        else:
            interpretation += (
                "The test rejects the null hypothesis. "
                "Variances are significantly different across groups. "
                "The homogeneity of variance assumption is violated."
            )
        
        return interpretation

    def _explain_levene(self) -> str:
        """Provide explanation of Levene's test"""
        return (
            "Levene's Test Explanation:\n"
            "- Tests equality of variances across multiple groups\n"
            "- Null Hypothesis (H0): All group variances are equal\n"
            "- Alternative Hypothesis (H1): At least one group variance differs\n"
            "- Robust to non-normality (unlike Bartlett's test)\n"
            "- Centering options: median (robust), mean, trimmed mean\n"
            "- Recommended for most pharmaceutical applications\n"
            "\nClinical Relevance:\n"
            "Homogeneity of variance is a key assumption for ANOVA and t-tests. "
            "Violating this assumption can affect Type I error rates. In dose-response "
            "studies, unequal variances may indicate heterogeneity in patient response "
            "across dose levels."
        )

    def _recommend_levene(
        self, 
        is_homogeneous: bool, 
        variances: List[float]
    ) -> List[str]:
        """Generate recommendations based on Levene's test results"""
        recommendations = []
        
        if is_homogeneous:
            recommendations.append(
                "✓ Homogeneity of variance assumption satisfied. "
                "Standard ANOVA and t-tests are appropriate."
            )
        else:
            recommendations.append(
                "✗ Homogeneity of variance assumption violated. Consider:\n"
                "  1. Welch's ANOVA: Robust to unequal variances\n"
                "  2. Welch's t-test: For two-group comparisons\n"
                "  3. Data transformation: Log or square root to stabilize variance\n"
                "  4. Non-parametric tests: Kruskal-Wallis, Mann-Whitney U"
            )
            
            # Identify extreme variance ratios
            if len(variances) >= 2:
                variance_ratio = max(variances) / min(variances)
                if variance_ratio > 3:
                    recommendations.append(
                        f"\nWarning: Variance ratio ({variance_ratio:.2f}) > 3, indicating substantial "
                        "heterogeneity. Welch's correction is strongly recommended."
                    )
        
        return recommendations

    def test_homogeneity_variance_bartlett(
        self, 
        groups: List[Union[pd.Series, np.ndarray, List[float]]],
        group_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Bartlett's test for homogeneity of variance

        Bartlett's test assesses whether variances are equal across groups.
        It is more sensitive to departures from normality than Levene's test
        and should only be used when normality is confirmed.

        Pharmaceutical Example:
            In a bioequivalence study where normality of log-transformed Cmax
            has been verified, researcher uses Bartlett's test to confirm equal
            variance across formulation groups for more powerful detection.

        Args:
            groups: List of arrays containing data for each group
            group_names: Optional names for each group

        Returns:
            Dictionary containing test statistic, p-value, interpretation,
            assumption status, and recommendations

        Warning:
            Bartlett's test is sensitive to non-normality. Only use this test
            if normality has been confirmed for all groups. Otherwise, use
            Levene's test instead.
        """
        # Data validation
        if len(groups) < 2:
            raise ValueError("Bartlett's test requires at least 2 groups.")
        
        # Convert and clean data
        cleaned_groups = []
        for i, group in enumerate(groups):
            if isinstance(group, pd.Series):
                group = group.dropna().values
            elif isinstance(group, list):
                group = np.array(group)
            
            if len(group) < 2:
                raise ValueError(f"Group {i} has only {len(group)} observations. Minimum 2 required.")
            
            cleaned_groups.append(group)
        
        # Generate group names if not provided
        if group_names is None:
            group_names = [f"Group {i+1}" for i in range(len(groups))]
        
        # Perform test
        statistic, p_value = stats.bartlett(*cleaned_groups)
        
        # Calculate variances for each group
        variances = [float(np.var(g, ddof=1)) for g in cleaned_groups]
        
        # Interpretation
        is_homogeneous = p_value > self.alpha
        
        result = {
            'test_type': "Bartlett's Test for Homogeneity of Variance",
            'group_names': group_names,
            'group_sizes': [len(g) for g in cleaned_groups],
            'group_variances': variances,
            'variance_ratio': float(max(variances) / min(variances)) if min(variances) > 0 else float('inf'),
            'statistic': float(statistic),
            'p_value': float(p_value),
            'alpha': self.alpha,
            'is_homogeneous': is_homogeneous,
            'assumption_met': is_homogeneous,
            'timestamp': datetime.now().isoformat()
        }

        # Generate interpretation
        result['interpretation'] = self._interpret_bartlett(
            statistic, p_value, variances, group_names, is_homogeneous
        )
        result['explanation'] = self._explain_bartlett()
        result['recommendations'] = self._recommend_bartlett(is_homogeneous)
        
        self._log_analysis('bartlett', result)
        
        return result

    def _interpret_bartlett(
        self, 
        statistic: float, 
        p_value: float,
        variances: List[float],
        group_names: List[str],
        is_homogeneous: bool
    ) -> str:
        """Generate interpretation for Bartlett's test"""
        interpretation = (
            f"Bartlett's Test (K² = {statistic:.4f}, p = {p_value:.4f}) "
            f"at α = {self.alpha}.\n\n"
            "Group Variances:\n"
        )
        
        for name, var in zip(group_names, variances):
            interpretation += f"  {name}: {var:.4f}\n"
        
        variance_ratio = max(variances) / min(variances) if min(variances) > 0 else float('inf')
        interpretation += f"\nVariance Ratio (max/min): {variance_ratio:.2f}\n\n"
        
        if is_homogeneous:
            interpretation += (
                "The test does NOT reject the null hypothesis. "
                "There is insufficient evidence to conclude that variances differ across groups. "
                "The homogeneity of variance assumption is satisfied."
            )
        else:
            interpretation += (
                "The test rejects the null hypothesis. "
                "Variances are significantly different across groups. "
                "The homogeneity of variance assumption is violated."
            )
        
        return interpretation

    def _explain_bartlett(self) -> str:
        """Provide explanation of Bartlett's test"""
        return (
            "Bartlett's Test Explanation:\n"
            "- Tests equality of variances across multiple groups\n"
            "- Null Hypothesis (H0): All group variances are equal\n"
            "- Alternative Hypothesis (H1): At least one group variance differs\n"
            "- More powerful than Levene's test when normality holds\n"
            "- Sensitive to departures from normality (use Levene's if non-normal)\n"
            "- Recommended when data is confirmed to be normally distributed\n"
            "\nClinical Relevance:\n"
            "Bartlett's test provides higher power than Levene's test when the "
            "normality assumption is met. In bioequivalence studies with log-transformed "
            "PK parameters (which are typically normal), Bartlett's test is often preferred."
        )

    def _recommend_bartlett(
        self, 
        is_homogeneous: bool
    ) -> List[str]:
        """Generate recommendations based on Bartlett's test results"""
        recommendations = []
        
        if is_homogeneous:
            recommendations.append(
                "✓ Homogeneity of variance assumption satisfied. "
                "Standard ANOVA and t-tests are appropriate."
            )
        else:
            recommendations.append(
                "✗ Homogeneity of variance assumption violated. Consider:\n"
                "  1. Welch's ANOVA: Robust to unequal variances\n"
                "  2. Welch's t-test: For two-group comparisons\n"
                "  3. Data transformation: Log or square root to stabilize variance\n"
                "  4. Non-parametric tests: Kruskal-Wallis, Mann-Whitney U"
            )
            recommendations.append(
                "\nNote: Bartlett's test assumes normality. If data is non-normal, "
                "the result may be due to non-normality rather than unequal variances. "
                "Consider Levene's test as a robust alternative."
            )
        
        return recommendations

    # ============================================================================
    # MULTICOLLINEARITY DETECTION
    # ============================================================================

    def detect_multicollinearity_vif(
        self,
        df: pd.DataFrame,
        features: Optional[List[str]] = None,
        threshold: float = 5.0
    ) -> Dict[str, Any]:
        """Detect multicollinearity using Variance Inflation Factor (VIF)

        VIF quantifies how much the variance of an estimated regression
        coefficient increases due to multicollinearity. High VIF values
        indicate problematic collinearity that can affect model stability
        and interpretability.

        Pharmaceutical Example:
            In a pharmacokinetic model predicting drug clearance, researcher
            checks VIF for covariates (age, weight, BMI, creatinine clearance)
            to ensure stable coefficient estimates for regulatory submission.

        Args:
            df: DataFrame containing predictor variables
            features: List of column names to analyze (default: all numeric columns)
            threshold: VIF threshold for problematic multicollinearity
                      (common thresholds: 5.0 moderate, 10.0 severe)

        Returns:
            Dictionary containing VIF values for each feature, interpretation,
            and recommendations for handling multicollinearity
        """
        # Data validation
        if features is None:
            features = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if len(features) < 2:
            raise ValueError("VIF calculation requires at least 2 features.")
        
        # Check for missing values
        data = df[features].dropna()
        if len(data) < len(df):
            warnings.warn(f"Removed {len(df) - len(data)} rows with missing values.")
        
        if len(data) < len(features):
            raise ValueError(
                f"Insufficient data ({len(data)} rows) for {len(features)} features. "
                f"Minimum {len(features)} rows required."
            )
        
        # Calculate VIF for each feature
        vif_data = []
        for feature in features:
            # Prepare data: feature as dependent, others as independent
            X = data[features].copy()
            y = X.pop(feature)
            X = sm.add_constant(X)
            
            # Fit regression and calculate VIF
            model = sm.OLS(y, X).fit()
            rsquared = model.rsquared
            
            if rsquared >= 1:
                vif = float('inf')
            else:
                vif = 1 / (1 - rsquared)
            
            vif_data.append({
                'feature': feature,
                'vif': vif,
                'r_squared': rsquared,
                'tolerance': 1 - rsquared if rsquared < 1 else 0
            })
        
        # Identify problematic features
        problematic = [v['feature'] for v in vif_data if v['vif'] > threshold]
        severe = [v['feature'] for v in vif_data if v['vif'] > 10]
        
        result = {
            'test_type': 'Variance Inflation Factor (VIF) Analysis',
            'threshold': threshold,
            'vif_results': vif_data,
            'max_vif': max(v['vif'] for v in vif_data),
            'problematic_features': problematic,
            'severe_multicollinearity': severe,
            'has_multicollinearity': len(problematic) > 0,
            'timestamp': datetime.now().isoformat()
        }

        # Generate interpretation
        result['interpretation'] = self._interpret_vif(vif_data, threshold)
        result['explanation'] = self._explain_vif()
        result['recommendations'] = self._recommend_vif(problematic, severe, threshold)
        
        self._log_analysis('vif', result)
        
        return result

    def _interpret_vif(
        self, 
        vif_data: List[Dict], 
        threshold: float
    ) -> str:
        """Generate interpretation for VIF analysis"""
        interpretation = "Variance Inflation Factor (VIF) Results:\n\n"
        
        for vif_info in sorted(vif_data, key=lambda x: x['vif'], reverse=True):
            feature = vif_info['feature']
            vif = vif_info['vif']
            tolerance = vif_info['tolerance']
            
            if vif < 5:
                status = "OK"
            elif vif < 10:
                status = "MODERATE"
            else:
                status = "SEVERE"
            
            interpretation += (
                f"{feature}:\n"
                f"  VIF = {vif:.2f}\n"
                f"  Tolerance = {tolerance:.4f}\n"
                f"  Status: {status}\n\n"
            )
        
        max_vif = max(v['vif'] for v in vif_data)
        if max_vif < threshold:
            interpretation += (
                f"All features have VIF < {threshold}. "
                "Multicollinearity is not a concern."
            )
        else:
            interpretation += (
                f"Some features exceed the VIF threshold of {threshold}. "
                "Multicollinearity may affect model stability and interpretation."
            )
        
        return interpretation

    def _explain_vif(self) -> str:
        """Provide explanation of VIF"""
        return (
            "Variance Inflation Factor (VIF) Explanation:\n"
            "- Measures how much variance of a coefficient is inflated by multicollinearity\n"
            "- VIF = 1: No correlation with other predictors\n"
            "- VIF 1-5: Moderate correlation (often acceptable)\n"
            "- VIF 5-10: High correlation (investigate further)\n"
            "- VIF > 10: Severe multicollinearity (address required)\n"
            "- Tolerance = 1/VIF: Proportion of variance not shared with other predictors\n"
            "\nClinical Relevance:\n"
            "Multicollinearity in pharmacometric models can lead to unstable coefficient "
            "estimates and unreliable predictions. For regulatory submissions, it's essential "
            "to demonstrate that predictors are not excessively collinear."
        )

    def _recommend_vif(
        self, 
        problematic: List[str], 
        severe: List[str],
        threshold: float
    ) -> List[str]:
        """Generate recommendations based on VIF results"""
        recommendations = []
        
        if not problematic:
            recommendations.append(
                f"✓ All features have VIF < {threshold}. "
                "No action needed regarding multicollinearity."
            )
        else:
            recommendations.append(
                f"✗ {len(problematic)} feature(s) exceed VIF threshold of {threshold}."
            )
            
            if severe:
                recommendations.append(
                    f"⚠ SEVERE: {len(severe)} feature(s) have VIF > 10. "
                    f"These require immediate attention: {', '.join(severe)}"
                )
            
            recommendations.append(
                "Recommended actions:\n"
                "  1. Remove one of the correlated features (prefer the more interpretable one)\n"
                "  2. Combine correlated features using PCA or PLS\n"
                "  3. Use regularization (Ridge/Lasso) to handle collinearity\n"
                "  4. Domain knowledge: Keep only clinically relevant predictors"
            )
        
        return recommendations

    # ============================================================================
    # OUTLIER DETECTION
    # ============================================================================

    def detect_outliers_iqr(
        self,
        data: Union[pd.Series, np.ndarray, List[float]],
        variable_name: str = "variable",
        multiplier: float = 1.5
    ) -> Dict[str, Any]:
        """Detect outliers using Interquartile Range (IQR) method

        The IQR method identifies outliers as values outside the range:
        [Q1 - multiplier × IQR, Q3 + multiplier × IQR]. This is a robust,
        non-parametric method that is resistant to the influence of outliers.

        Pharmaceutical Example:
            In a clinical trial database, researcher uses IQR method to flag
            extreme lab values (e.g., ALT, AST) for data cleaning before analysis.

        Args:
            data: Numeric data to analyze for outliers
            variable_name: Name of the variable being analyzed
            multiplier: IQR multiplier for outlier threshold
                       (1.5 for mild outliers, 3.0 for extreme outliers)

        Returns:
            Dictionary containing outlier information, statistics,
            interpretation, and recommendations
        """
        # Data validation
        if isinstance(data, pd.Series):
            data = data.dropna().values
        elif isinstance(data, list):
            data = np.array(data)
        
        if len(data) < 4:
            raise ValueError(f"IQR method requires at least 4 observations. Got {len(data)}.")
        
        if not np.issubdtype(data.dtype, np.number):
            raise ValueError("Data must be numeric for IQR outlier detection.")

        # Calculate quartiles and IQR
        q1 = np.percentile(data, 25)
        q3 = np.percentile(data, 75)
        iqr = q3 - q1
        
        # Calculate bounds
        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr
        
        # Identify outliers
        outlier_mask = (data < lower_bound) | (data > upper_bound)
        outliers = data[outlier_mask]
        outlier_indices = np.where(outlier_mask)[0]
        
        # Calculate statistics
        n_outliers = len(outliers)
        outlier_percentage = (n_outliers / len(data)) * 100
        
        result = {
            'method': 'IQR Outlier Detection',
            'variable_name': variable_name,
            'sample_size': len(data),
            'q1': float(q1),
            'q3': float(q3),
            'iqr': float(iqr),
            'lower_bound': float(lower_bound),
            'upper_bound': float(upper_bound),
            'multiplier': multiplier,
            'n_outliers': n_outliers,
            'outlier_percentage': float(outlier_percentage),
            'outliers': outliers.tolist() if n_outliers > 0 else [],
            'outlier_indices': outlier_indices.tolist() if n_outliers > 0 else [],
            'has_outliers': n_outliers > 0,
            'timestamp': datetime.now().isoformat()
        }

        # Generate interpretation
        result['interpretation'] = self._interpret_iqr_outliers(result)
        result['explanation'] = self._explain_iqr_method()
        result['recommendations'] = self._recommend_iqr_outliers(n_outliers, outlier_percentage, multiplier)
        
        self._log_analysis('iqr_outliers', result)
        
        return result

    def _interpret_iqr_outliers(self, result: Dict) -> str:
        """Generate interpretation for IQR outlier detection"""
        n = result['sample_size']
        n_out = result['n_outliers']
        pct = result['outlier_percentage']
        multiplier = result['multiplier']
        
        interpretation = (
            f"IQR Outlier Detection ({multiplier}×IQR threshold) for {result['variable_name']}:\n\n"
            f"  Q1 (25th percentile): {result['q1']:.4f}\n"
            f"  Q3 (75th percentile): {result['q3']:.4f}\n"
            f"  IQR: {result['iqr']:.4f}\n"
            f"  Lower bound: {result['lower_bound']:.4f}\n"
            f"  Upper bound: {result['upper_bound']:.4f}\n\n"
        )
        
        if n_out == 0:
            interpretation += (
                f"No outliers detected in {n} observations. "
                "All values fall within acceptable range."
            )
        else:
            interpretation += (
                f"Detected {n_out} outlier(s) in {n} observations ({pct:.2f}% of data).\n\n"
                f"Outlier values: {result['outliers']}\n\n"
            )
            
            if pct > 5:
                interpretation += (
                    "Warning: Outlier percentage exceeds 5%. This may indicate: "
                    "(1) Data quality issues, (2) Mixed subpopulations, or "
                    "(3) Heavy-tailed distribution."
                )
            else:
                interpretation += (
                    "Outlier percentage is within expected range (<5% for normal distributions)."
                )
        
        return interpretation

    def _explain_iqr_method(self) -> str:
        """Provide explanation of IQR method"""
        return (
            "IQR Outlier Detection Method:\n"
            "- Non-parametric method based on quartiles\n"
            "- Outlier range: [Q1 - k×IQR, Q3 + k×IQR]\n"
            "- k = 1.5: Mild outliers (approximately 2.7 SD from median)\n"
            "- k = 3.0: Extreme outliers (approximately 4 SD from median)\n"
            "- Robust to extreme values (uses median-based quartiles)\n"
            "- Does not assume normality\n"
            "\nClinical Relevance:\n"
            "The IQR method is widely used in clinical data cleaning because it's "
            "robust and doesn't require distributional assumptions. It's particularly "
            "useful for identifying data entry errors or unusual patient responses."
        )

    def _recommend_iqr_outliers(
        self, 
        n_outliers: int, 
        outlier_percentage: float,
        multiplier: float
    ) -> List[str]:
        """Generate recommendations based on IQR outlier detection"""
        recommendations = []
        
        if n_outliers == 0:
            recommendations.append(
                "✓ No outliers detected. No action required."
            )
        else:
            recommendations.append(
                f"⚠ Detected {n_outliers} outlier(s) ({outlier_percentage:.2f}% of data)."
            )
            recommendations.append(
                "Investigation steps:\n"
                "  1. Verify data: Check for data entry errors or unit inconsistencies\n"
                "  2. Clinical review: Consult with medical experts to assess plausibility\n"
                "  3. Documentation: Record decision for each outlier (keep/remove/correct)\n"
                "  4. Sensitivity analysis: Compare results with and without outliers"
            )
            
            if outlier_percentage > 5:
                recommendations.append(
                    "\nHigh outlier percentage detected. Consider:\n"
                    "  - Checking for data collection issues\n"
                    "  - Investigating subpopulation differences\n"
                    "  - Using robust statistical methods"
                )
        
        return recommendations

    def detect_outliers_zscore(
        self,
        data: Union[pd.Series, np.ndarray, List[float]],
        variable_name: str = "variable",
        threshold: float = 3.0
    ) -> Dict[str, Any]:
        """Detect outliers using Z-score method

        The Z-score method identifies outliers as values with absolute Z-score
        exceeding the threshold. Z-scores measure how many standard deviations
        a value is from the mean. This method assumes normality.

        Pharmaceutical Example:
            In a bioequivalence study, researcher uses Z-score method to
            identify extreme Cmax values in log-transformed data (which should
            be approximately normal).

        Args:
            data: Numeric data to analyze for outliers
            variable_name: Name of the variable being analyzed
            threshold: Z-score threshold for outlier detection
                       (common: 2.5 for moderate, 3.0 for strict)

        Returns:
            Dictionary containing outlier information, statistics,
            interpretation, and recommendations

        Warning:
            Z-score method assumes normality. For non-normal data, use
            IQR method or robust Z-score with median and MAD.
        """
        # Data validation
        if isinstance(data, pd.Series):
            data = data.dropna().values
        elif isinstance(data, list):
            data = np.array(data)
        
        if len(data) < 3:
            raise ValueError(f"Z-score method requires at least 3 observations. Got {len(data)}.")
        
        if not np.issubdtype(data.dtype, np.number):
            raise ValueError("Data must be numeric for Z-score outlier detection.")

        # Calculate statistics
        mean = np.mean(data)
        std = np.std(data, ddof=1)
        
        if std == 0:
            raise ValueError("Cannot calculate Z-scores: data has zero variance.")
        
        # Calculate Z-scores
        z_scores = (data - mean) / std
        
        # Identify outliers
        outlier_mask = np.abs(z_scores) > threshold
        outliers = data[outlier_mask]
        outlier_indices = np.where(outlier_mask)[0]
        outlier_z_scores = z_scores[outlier_mask]
        
        # Calculate statistics
        n_outliers = len(outliers)
        outlier_percentage = (n_outliers / len(data)) * 100
        
        result = {
            'method': 'Z-score Outlier Detection',
            'variable_name': variable_name,
            'sample_size': len(data),
            'mean': float(mean),
            'std': float(std),
            'threshold': threshold,
            'n_outliers': n_outliers,
            'outlier_percentage': float(outlier_percentage),
            'outliers': outliers.tolist() if n_outliers > 0 else [],
            'outlier_indices': outlier_indices.tolist() if n_outliers > 0 else [],
            'outlier_z_scores': outlier_z_scores.tolist() if n_outliers > 0 else [],
            'has_outliers': n_outliers > 0,
            'timestamp': datetime.now().isoformat()
        }

        # Generate interpretation
        result['interpretation'] = self._interpret_zscore_outliers(result)
        result['explanation'] = self._explain_zscore_method()
        result['recommendations'] = self._recommend_zscore_outliers(n_outliers, outlier_percentage)
        
        self._log_analysis('zscore_outliers', result)
        
        return result

    def _interpret_zscore_outliers(self, result: Dict) -> str:
        """Generate interpretation for Z-score outlier detection"""
        n = result['sample_size']
        n_out = result['n_outliers']
        pct = result['outlier_percentage']
        threshold = result['threshold']
        
        interpretation = (
            f"Z-score Outlier Detection (threshold = ±{threshold}) for {result['variable_name']}:\n\n"
            f"  Mean: {result['mean']:.4f}\n"
            f"  Standard deviation: {result['std']:.4f}\n"
            f"  Outlier threshold: [{result['mean'] - threshold*result['std']:.4f}, "
            f"{result['mean'] + threshold*result['std']:.4f}]\n\n"
        )
        
        if n_out == 0:
            interpretation += (
                f"No outliers detected in {n} observations. "
                f"All values have |Z-score| < {threshold}."
            )
        else:
            interpretation += (
                f"Detected {n_out} outlier(s) in {n} observations ({pct:.2f}% of data).\n\n"
                f"Outlier details:\n"
            )
            for val, z in zip(result['outliers'], result['outlier_z_scores']):
                interpretation += f"  Value: {val:.4f}, Z-score: {z:.2f}\n"
            
            interpretation += "\n"
            
            if pct > 1:  # For normal distribution, expect ~0.3% at 3σ
                interpretation += (
                    "Warning: Outlier percentage exceeds 1%. "
                    "This may indicate non-normality or data quality issues."
                )
            else:
                interpretation += (
                    "Outlier percentage is consistent with normal distribution expectations."
                )
        
        return interpretation

    def _explain_zscore_method(self) -> str:
        """Provide explanation of Z-score method"""
        return (
            "Z-score Outlier Detection Method:\n"
            "- Parametric method assuming normality\n"
            "- Z-score = (value - mean) / standard deviation\n"
            "- Outlier: |Z-score| > threshold\n"
            "- Threshold = 2.5: ~1.2% expected as outliers (under normality)\n"
            "- Threshold = 3.0: ~0.3% expected as outliers (under normality)\n"
            "- Sensitive to outliers themselves (mean/std affected by outliers)\n"
            "\nClinical Relevance:\n"
            "Z-score method is appropriate for normally distributed data, such as "
            "log-transformed PK parameters. For non-normal data, the IQR method or "
            "robust Z-score (using median and MAD) is preferred."
        )

    def _recommend_zscore_outliers(
        self, 
        n_outliers: int, 
        outlier_percentage: float
    ) -> List[str]:
        """Generate recommendations based on Z-score outlier detection"""
        recommendations = []
        
        if n_outliers == 0:
            recommendations.append(
                "✓ No outliers detected. No action required."
            )
        else:
            recommendations.append(
                f"⚠ Detected {n_outliers} outlier(s) ({outlier_percentage:.2f}% of data)."
            )
            recommendations.append(
                "Note: Z-score method assumes normality. If data is non-normal, "
                "consider IQR method or robust Z-score."
            )
            recommendations.append(
                "Investigation steps:\n"
                "  1. Verify data entry and units\n"
                "  2. Clinical assessment of outlier plausibility\n"
                "  3. Check normality assumption before trusting Z-score results\n"
                "  4. Sensitivity analysis with and without outliers"
            )
        
        return recommendations

    def detect_outliers_mahalanobis(
        self,
        df: pd.DataFrame,
        features: Optional[List[str]] = None,
        threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """Detect multivariate outliers using Mahalanobis distance

        Mahalanobis distance measures the distance of a point from the
        multivariate distribution, accounting for correlations between
        variables. It's the multivariate generalization of Z-score.

        Pharmaceutical Example:
            In a Phase II trial, researcher identifies patients with unusual
        
        Args:
            df: DataFrame containing the features
            features: List of column names to analyze (default: all numeric columns)
            threshold: Chi-squared threshold for outlier detection
                      (default: critical value at p = 0.001 for df = n_features)

        Returns:
            Dictionary containing outlier information, distances,
            interpretation, and recommendations
        """
        # Data validation
        if features is None:
            features = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if len(features) < 2:
            raise ValueError("Mahalanobis distance requires at least 2 features.")
        
        # Check for missing values
        data = df[features].dropna()
        if len(data) < len(df):
            warnings.warn(f"Removed {len(df) - len(data)} rows with missing values.")
        
        n_obs = len(data)
        n_features = len(features)
        
        if n_obs < n_features + 1:
            raise ValueError(
                f"Insufficient data ({n_obs} rows) for {n_features} features. "
                f"Minimum {n_features + 1} rows required."
            )
        
        # Calculate Mahalanobis distances
        try:
            cov_matrix = np.cov(data.T)
            inv_cov_matrix = np.linalg.inv(cov_matrix)
            
            mean = data.mean(axis=0)
            
            distances = []
            for i in range(n_obs):
                diff = data.iloc[i] - mean
                distance = mahalanobis(data.iloc[i], mean, inv_cov_matrix)
                distances.append(distance)
            
            distances = np.array(distances)
            
            # Set default threshold (chi-squared critical value)
            if threshold is None:
                threshold = stats.chi2.ppf(0.999, df=n_features)
            
            # Identify outliers
            outlier_mask = distances > threshold
            outlier_indices = np.where(outlier_mask)[0]
            n_outliers = len(outlier_indices)
            outlier_percentage = (n_outliers / n_obs) * 100
            
            result = {
                'method': 'Mahalanobis Distance Outlier Detection',
                'features': features,
                'sample_size': n_obs,
                'n_features': n_features,
                'threshold': float(threshold),
                'mean': mean.tolist(),
                'covariance_determinant': float(np.linalg.det(cov_matrix)),
                'distances': distances.tolist(),
                'max_distance': float(np.max(distances)),
                'mean_distance': float(np.mean(distances)),
                'n_outliers': n_outliers,
                'outlier_percentage': float(outlier_percentage),
                'outlier_indices': outlier_indices.tolist() if n_outliers > 0 else [],
                'outlier_distances': distances[outlier_mask].tolist() if n_outliers > 0 else [],
                'has_outliers': n_outliers > 0,
                'timestamp': datetime.now().isoformat()
            }

            # Generate interpretation
            result['interpretation'] = self._interpret_mahalanobis_outliers(result)
            result['explanation'] = self._explain_mahalanobis_method()
            result['recommendations'] = self._recommend_mahalanobis_outliers(
                n_outliers, outlier_percentage, threshold
            )
            
            self._log_analysis('mahalanobis_outliers', result)
            
            return result
            
        except np.linalg.LinAlgError:
            raise ValueError(
                "Cannot compute Mahalanobis distance: Covariance matrix is singular. "
                "This may be due to multicollinearity or insufficient data. "
                "Consider removing redundant features or using VIF analysis first."
            )

    def _interpret_mahalanobis_outliers(self, result: Dict) -> str:
        """Generate interpretation for Mahalanobis outlier detection"""
        n = result['sample_size']
        n_out = result['n_outliers']
        pct = result['outlier_percentage']
        threshold = result['threshold']
        
        interpretation = (
            f"Mahalanobis Distance Outlier Detection for {len(result['features'])} features:\n\n"
            f"  Features: {', '.join(result['features'])}\n"
            f"  Sample size: {n}\n"
            f"  Chi-squared threshold (α = 0.001): {threshold:.4f}\n"
            f"  Mean distance: {result['mean_distance']:.4f}\n"
            f"  Maximum distance: {result['max_distance']:.4f}\n\n"
        )
        
        if n_out == 0:
            interpretation += (
                f"No multivariate outliers detected in {n} observations. "
                "All points fall within expected multivariate distribution."
            )
        else:
            interpretation += (
                f"Detected {n_out} multivariate outlier(s) in {n} observations "
                f"({pct:.2f}% of data).\n\n"
                f"Outlier row indices: {result['outlier_indices']}\n"
                f"Outlier distances: {result['outlier_distances']}\n\n"
            )
            
            if pct > 1:
                interpretation += (
                    "Warning: Outlier percentage exceeds 1%. This may indicate "
                    "mixed subpopulations, data quality issues, or non-elliptical distribution."
                )
            else:
                interpretation += (
                    "Outlier percentage is within acceptable range."
                )
        
        return interpretation

    def _explain_mahalanobis_method(self) -> str:
        """Provide explanation of Mahalanobis distance method"""
        return (
            "Mahalanobis Distance Outlier Detection:\n"
            "- Multivariate distance metric accounting for feature correlations\n"
            "- D² = (x - μ)ᵀ Σ⁻¹ (x - μ) where Σ is covariance matrix\n"
            "- Distance follows chi-squared distribution under normality\n"
            "- Identifies unusual combinations of values (not just extreme values)\n"
            "- Threshold typically set using chi-squared critical values\n"
            "- Requires invertible covariance matrix (no perfect multicollinearity)\n"
            "\nClinical Relevance:\n"
            "Mahalanobis distance is essential for detecting multivariate outliers "
            "that may not be apparent in univariate analyses. In clinical trials, it can "
            "identify patients with unusual biomarker combinations that may indicate "
            "subpopulations or data issues."
        )

    def _recommend_mahalanobis_outliers(
        self, 
        n_outliers: int, 
        outlier_percentage: float,
        threshold: float
    ) -> List[str]:
        """Generate recommendations based on Mahalanobis outlier detection"""
        recommendations = []
        
        if n_outliers == 0:
            recommendations.append(
                "✓ No multivariate outliers detected. No action required."
            )
        else:
            recommendations.append(
                f"⚠ Detected {n_outliers} multivariate outlier(s) ({outlier_percentage:.2f}% of data)."
            )
            recommendations.append(
                "Investigation steps:\n"
                "  1. Examine individual features: Check univariate outliers for each variable\n"
                "  2. Feature combinations: Identify unusual combinations causing high distance\n"
                "  3. Clinical review: Assess if outliers represent legitimate subpopulations\n"
                "  4. Sensitivity analysis: Compare models with and without outliers"
            )
            
            if outlier_percentage > 1:
                recommendations.append(
                    "\nHigh outlier percentage detected. Consider:\n"
                    "  - Checking for data collection issues\n"
                    "  - Investigating population heterogeneity\n"
                    "  - Using mixture models or cluster analysis"
                )
        
        return recommendations

    # ============================================================================
    # COMPREHENSIVE DIAGNOSTICS
    # ============================================================================

    def comprehensive_diagnostics(
        self,
        df: pd.DataFrame,
        numeric_cols: Optional[List[str]] = None,
        group_col: Optional[str] = None,
        vif_threshold: float = 5.0,
        outlier_threshold: float = 3.0
    ) -> Dict[str, Any]:
        """Run all diagnostic tests and generate comprehensive assumption violation report

        This method performs a complete diagnostic analysis including normality tests,
        homogeneity of variance tests, multicollinearity detection, and outlier
        detection for all specified variables and groups.

        Pharmaceutical Example:
            In a Phase III clinical trial, statistician runs comprehensive diagnostics
            before primary efficacy analysis to ensure all statistical assumptions are met
            and document any violations for regulatory submission.

        Args:
            df: DataFrame containing the data to analyze
            numeric_cols: List of numeric column names to analyze
                         (default: all numeric columns)
            group_col: Column name containing group labels for variance tests
            vif_threshold: Threshold for VIF multicollinearity detection
            outlier_threshold: Z-score threshold for outlier detection

        Returns:
            Dictionary containing all diagnostic test results,
            assumption violation summary, and overall recommendations
        """
        # Data validation
        if numeric_cols is None:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if not numeric_cols:
            raise ValueError("No numeric columns found for analysis.")
        
        # Initialize report
        report = {
            'analysis_type': 'Comprehensive Statistical Diagnostics',
            'timestamp': datetime.now().isoformat(),
            'data_summary': {
                'total_rows': len(df),
                'numeric_columns': numeric_cols,
                'group_column': group_col,
                'alpha': self.alpha
            },
            'normality_tests': {},
            'homogeneity_tests': {},
            'multicollinearity': None,
            'outlier_detection': {},
            'assumption_violations': [],
            'recommendations': []
        }
        
        # 1. Normality tests for each numeric column
        for col in numeric_cols:
            col_data = df[col].dropna()
            
            if len(col_data) < 3:
                report['normality_tests'][col] = {
                    'error': f'Insufficient data for normality testing (n={len(col_data)})'
                }
                continue
            
            # Run appropriate test based on sample size
            if len(col_data) < 50:
                normality_result = self.test_normality_shapiro_wilk(col_data, col)
            else:
                normality_result = self.test_normality_ks(col_data, col)
            
            report['normality_tests'][col] = normality_result
            
            # Track violations
            if not normality_result['assumption_met']:
                report['assumption_violations'].append({
                    'type': 'Normality',
                    'variable': col,
                    'severity': 'high' if normality_result['p_value'] < 0.01 else 'moderate'
                })
        
        # 2. Homogeneity of variance tests (if groups provided)
        if group_col and group_col in df.columns:
            groups = df[group_col].unique()
            
            if len(groups) >= 2:
                for col in numeric_cols:
                    group_data = [df[df[group_col] == g][col].dropna().values for g in groups]
                    
                    # Check if all groups have sufficient data
                    if all(len(g) >= 2 for g in group_data):
                        # Use Levene's test (robust to non-normality)
                        levene_result = self.test_homogeneity_variance_levene(
                            group_data, 
                            group_names=[str(g) for g in groups],
                            center='median'
                        )
                        report['homogeneity_tests'][col] = levene_result
                        
                        # Track violations
                        if not levene_result['assumption_met']:
                            report['assumption_violations'].append({
                                'type': 'Homogeneity of Variance',
                                'variable': col,
                                'group_variable': group_col,
                                'severity': 'high' if levene_result['p_value'] < 0.01 else 'moderate'
                            })
        
        # 3. Multicollinearity detection (if multiple numeric columns)
        if len(numeric_cols) >= 2:
            try:
                vif_result = self.detect_multicollinearity_vif(
                    df, 
                    features=numeric_cols, 
                    threshold=vif_threshold
                )
                report['multicollinearity'] = vif_result
                
                # Track violations
                if vif_result['has_multicollinearity']:
                    for feature in vif_result['problematic_features']:
                        report['assumption_violations'].append({
                            'type': 'Multicollinearity',
                            'variable': feature,
                            'vif': next(v['vif'] for v in vif_result['vif_results'] if v['feature'] == feature),
                            'severity': 'severe' if feature in vif_result['severe_multicollinearity'] else 'moderate'
                        })
            except Exception as e:
                report['multicollinearity'] = {'error': str(e)}
        
        # 4. Outlier detection for each numeric column
        for col in numeric_cols:
            col_data = df[col].dropna()
            
            if len(col_data) >= 4:
                # IQR method
                iqr_result = self.detect_outliers_iqr(col_data, col, multiplier=1.5)
                report['outlier_detection'][f'{col}_iqr'] = iqr_result
                
                # Z-score method
                try:
                    zscore_result = self.detect_outliers_zscore(col_data, col, threshold=outlier_threshold)
                    report['outlier_detection'][f'{col}_zscore'] = zscore_result
                except:
                    pass  # Skip if variance is zero
                
                # Track outliers
                if iqr_result['has_outliers']:
                    report['assumption_violations'].append({
                        'type': 'Outliers (IQR)',
                        'variable': col,
                        'n_outliers': iqr_result['n_outliers'],
                        'percentage': iqr_result['outlier_percentage'],
                        'severity': 'high' if iqr_result['outlier_percentage'] > 5 else 'moderate'
                    })
        
        # 5. Multivariate outlier detection (if multiple columns)
        if len(numeric_cols) >= 2:
            try:
                mahalanobis_result = self.detect_outliers_mahalanobis(df, features=numeric_cols)
                report['outlier_detection']['multivariate'] = mahalanobis_result
                
                if mahalanobis_result['has_outliers']:
                    report['assumption_violations'].append({
                        'type': 'Multivariate Outliers',
                        'variables': numeric_cols,
                        'n_outliers': mahalanobis_result['n_outliers'],
                        'percentage': mahalanobis_result['outlier_percentage'],
                        'severity': 'high' if mahalanobis_result['outlier_percentage'] > 1 else 'moderate'
                    })
            except Exception as e:
                report['outlier_detection']['multivariate'] = {'error': str(e)}
        
        # 6. Generate overall recommendations
        report['recommendations'] = self._generate_comprehensive_recommendations(report)
        
        # 7. Summary statistics
        report['summary'] = {
            'total_violations': len(report['assumption_violations']),
            'high_severity': sum(1 for v in report['assumption_violations'] if v.get('severity') == 'high'),
            'moderate_severity': sum(1 for v in report['assumption_violations'] if v.get('severity') == 'moderate'),
            'violation_types': list(set(v['type'] for v in report['assumption_violations']))
        }
        
        self._log_analysis('comprehensive_diagnostics', report)
        
        return report

    def _generate_comprehensive_recommendations(self, report: Dict) -> List[str]:
        """Generate overall recommendations based on comprehensive diagnostics"""
        recommendations = []
        violations = report['assumption_violations']
        
        if not violations:
            recommendations.append(
                "✓ All statistical assumptions appear to be satisfied. "
                "Standard parametric tests are appropriate."
            )
            return recommendations
        
        # Summary of issues
        recommendations.append(
            f"Detected {len(violations)} assumption violation(s) requiring attention."
        )
        
        # Normality violations
        normality_violations = [v for v in violations if v['type'] == 'Normality']
        if normality_violations:
            affected_vars = ', '.join(v['variable'] for v in normality_violations)
            recommendations.append(
                f"\nNormality violations detected for: {affected_vars}\n"
                "  - Consider non-parametric alternatives (Mann-Whitney, Kruskal-Wallis)\n"
                "  - Try data transformations (log, square root, Box-Cox)\n"
                "  - Verify for outliers that may cause apparent non-normality"
            )
        
        # Homogeneity violations
        homogeneity_violations = [v for v in violations if 'Homogeneity' in v['type']]
        if homogeneity_violations:
            affected_vars = ', '.join(v['variable'] for v in homogeneity_violations)
            recommendations.append(
                f"\nHomogeneity of variance violations detected for: {affected_vars}\n"
                "  - Use Welch's ANOVA or Welch's t-test instead of standard tests\n"
                "  - Consider data transformation to stabilize variance\n"
                "  - Non-parametric tests as alternative"
            )
        
        # Multicollinearity violations
        multicollinearity_violations = [v for v in violations if v['type'] == 'Multicollinearity']
        if multicollinearity_violations:
            affected_vars = ', '.join(v['variable'] for v in multicollinearity_violations)
            recommendations.append(
                f"\nMulticollinearity detected for: {affected_vars}\n"
                "  - Remove one of the correlated variables\n"
                "  - Use regularization (Ridge/Lasso)\n"
                "  - Consider dimensionality reduction (PCA)"
            )
        
        # Outlier violations
        outlier_violations = [v for v in violations if 'Outlier' in v['type']]
        if outlier_violations:
            high_outlier_count = sum(
                1 for v in outlier_violations 
                if v.get('severity') == 'high'
            )
            recommendations.append(
                f"\nOutliers detected in {len(outlier_violations)} variable(s) "
                f"({high_outlier_count} with high percentage)\n"
                "  - Investigate data quality and entry errors\n"
                "  - Clinical review of outlier plausibility\n"
                "  - Consider robust statistical methods\n"
                "  - Perform sensitivity analysis with and without outliers"
            )
        
        # General guidance
        recommendations.append(
            "\nDocumentation Requirements:\n"
            "  - Document all assumption tests performed\n"
            "  - Record decisions made for each violation\n"
            "  - Provide justification for any transformations\n"
                "  - Include sensitivity analysis results in study report"
        )
        
        return recommendations

    # ============================================================================
    # UTILITY METHODS
    # ============================================================================

    def _log_analysis(self, analysis_type: str, result: Dict) -> None:
        """Log analysis to history for audit trail"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'analysis_type': analysis_type,
            'result_summary': {
                'assumption_met': result.get('assumption_met', result.get('has_multicollinearity', True) == False),
                'key_metrics': self._extract_key_metrics(result)
            }
        }
        self.analysis_history.append(log_entry)
    
    def _extract_key_metrics(self, result: Dict) -> Dict:
        """Extract key metrics from result for logging"""
        metrics = {}
        
        if 'p_value' in result:
            metrics['p_value'] = result['p_value']
        if 'statistic' in result:
            metrics['test_statistic'] = result['statistic']
        if 'is_normal' in result:
            metrics['is_normal'] = result['is_normal']
        if 'is_homogeneous' in result:
            metrics['is_homogeneous'] = result['is_homogeneous']
        if 'max_vif' in result:
            metrics['max_vif'] = result['max_vif']
        if 'n_outliers' in result:
            metrics['n_outliers'] = result['n_outliers']
        
        return metrics

    def get_analysis_history(self) -> List[Dict]:
        """Return complete analysis history for audit trail"""
        return self.analysis_history

    def export_report(self, result: Dict, format: str = 'json') -> str:
        """Export diagnostic results in specified format

        Args:
            result: Diagnostic result dictionary
            format: Export format ('json' or 'text')

        Returns:
            Formatted report string
        """
        if format == 'json':
            return json.dumps(result, indent=2)
        elif format == 'text':
            return self._format_text_report(result)
        else:
            raise ValueError(f"Unsupported format: {format}. Use 'json' or 'text'.")

    def _format_text_report(self, result: Dict) -> str:
        """Format diagnostic result as readable text report"""
        lines = []
        lines.append("="*60)
        lines.append(result.get('test_type', 'Diagnostic Test Report'))
        lines.append("="*60)
        lines.append("")
        
        if 'interpretation' in result:
            lines.append("INTERPRETATION:")
            lines.append("-"*40)
            lines.append(result['interpretation'])
            lines.append("")
        
        if 'explanation' in result:
            lines.append("EXPLANATION:")
            lines.append("-"*40)
            lines.append(result['explanation'])
            lines.append("")
        
        if 'recommendations' in result:
            lines.append("RECOMMENDATIONS:")
            lines.append("-"*40)
            for rec in result['recommendations']:
                lines.append(f"• {rec}")
            lines.append("")
        
        lines.append("="*60)
        lines.append(f"Generated: {result.get('timestamp', 'N/A')}")
        
        return "\n".join(lines)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Initialize diagnostic tests
    tests = DiagnosticTests(alpha=0.05)
    
    # Example 1: Normality testing
    print("Example 1: Normality Testing")
    print("-"*40)
    
    # Generate sample data
    np.random.seed(42)
    normal_data = np.random.normal(100, 15, 30)
    skewed_data = np.random.exponential(2, 30)
    
    result_normal = tests.test_normality_shapiro_wilk(normal_data, "biomarker_normal")
    print(f"Normal data result: {result_normal['assumption_met']}")
    
    result_skewed = tests.test_normality_shapiro_wilk(skewed_data, "biomarker_skewed")
    print(f"Skewed data result: {result_skewed['assumption_met']}")
    print()
    
    # Example 2: Homogeneity of variance
    print("Example 2: Homogeneity of Variance")
    print("-"*40)
    
    group1 = np.random.normal(100, 10, 30)
    group2 = np.random.normal(105, 10, 30)
    group3 = np.random.normal(102, 25, 30)  # Different variance
    
    levene_result = tests.test_homogeneity_variance_levene(
        [group1, group2, group3],
        group_names=["Dose A", "Dose B", "Dose C"]
    )
    print(f"Homogeneous: {levene_result['is_homogeneous']}")
    print(f"P-value: {levene_result['p_value']:.4f}")
    print()
    
    # Example 3: Multicollinearity detection
    print("Example 3: VIF Analysis")
    print("-"*40)
    
    df_example = pd.DataFrame({
        'age': np.random.normal(50, 10, 100),
        'weight': np.random.normal(70, 15, 100),
        'bmi': np.random.normal(25, 5, 100),
        'response': np.random.normal(100, 20, 100)
    })
    
    vif_result = tests.detect_multicollinearity_vif(df_example)
    print(f"Max VIF: {vif_result['max_vif']:.2f}")
    print(f"Problematic features: {vif_result['problematic_features']}")
    print()
    
    # Example 4: Outlier detection
    print("Example 4: Outlier Detection")
    print("-"*40)
    
    data_with_outliers = np.concatenate([
        np.random.normal(100, 10, 45),
        [200, 190, 15, 10]  # Outliers
    ])
    
    iqr_result = tests.detect_outliers_iqr(data_with_outliers, "biomarker")
    print(f"IQR outliers: {iqr_result['n_outliers']}")
    
    zscore_result = tests.detect_outliers_zscore(data_with_outliers, "biomarker")
    print(f"Z-score outliers: {zscore_result['n_outliers']}")
    print()
    
    print("Diagnostic tests module loaded successfully!")
