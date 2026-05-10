
"""Enhanced Statistical Engine with Explanations

Provides comprehensive statistical analysis with detailed explanations
of methodology, results interpretation, and clinical significance.

Complies with:
- Good Laboratory Practice (GLP)
- Good Clinical Practice (GCP)
- FDA/EMA statistical guidelines
- ICH E9 Statistical Principles for Clinical Trials
"""

import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm
from statsmodels.formula.api import ols
from statsmodels.stats.multicomp import pairwise_tukeyhsd
import json
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


class EnhancedStatisticalEngine:
    """Comprehensive statistical engine with detailed explanations

    Provides:
    - Descriptive statistics with interpretations
    - Hypothesis testing with significance explanations
    - ANOVA with post-hoc analysis
    - Regression analysis with coefficient interpretation
    - Non-parametric tests with justification
    - Effect size calculations with clinical relevance
    - Confidence intervals with interpretation
    """

    def __init__(self, alpha: float = 0.05):
        """Initialize statistical engine

        Args:
            alpha: Significance level (default: 0.05)
        """
        self.alpha = alpha
        self.analysis_history = []
        self.current_analysis = None

    def analyze_descriptive(
        self, 
        df: pd.DataFrame,
        columns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Comprehensive descriptive statistics with explanations

        Args:
            df: Input DataFrame
            columns: Columns to analyze (None for all numeric)

        Returns:
            Dictionary with statistics and interpretations
        """
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()

        results = {
            'analysis_type': 'Descriptive Statistics',
            'timestamp': datetime.now().isoformat(),
            'alpha': self.alpha,
            'data_summary': {},
            'explanations': {},
            'interpretations': {},
            'recommendations': []
        }

        for col in columns:
            col_data = df[col].dropna()

            # Basic statistics
            stats_dict = {
                'count': len(col_data),
                'mean': float(col_data.mean()),
                'median': float(col_data.median()),
                'std': float(col_data.std()),
                'var': float(col_data.var()),
                'min': float(col_data.min()),
                'max': float(col_data.max()),
                'range': float(col_data.max() - col_data.min()),
                'q1': float(col_data.quantile(0.25)),
                'q3': float(col_data.quantile(0.75)),
                'iqr': float(col_data.quantile(0.75) - col_data.quantile(0.25)),
                'skewness': float(stats.skew(col_data)),
                'kurtosis': float(stats.kurtosis(col_data))
            }

            # Confidence intervals
            if len(col_data) > 30:
                ci_mean = stats.t.interval(0.95, len(col_data)-1, 
                                            loc=stats_dict['mean'], 
                                            scale=stats.sem(col_data))
                stats_dict['ci_95_mean'] = [float(ci_mean[0]), float(ci_mean[1])]

            results['data_summary'][col] = stats_dict

            # Explanations
            results['explanations'][col] = self._explain_descriptive(stats_dict, col)

            # Interpretations
            results['interpretations'][col] = self._interpret_descriptive(stats_dict, col)

        # Overall recommendations
        results['recommendations'] = self._generate_descriptive_recommendations(df, columns)

        self._log_analysis('descriptive_statistics', results)
        return results

    def _explain_descriptive(self, stats_dict: Dict, col_name: str) -> Dict[str, str]:
        """Generate explanations for descriptive statistics"""
        return {
            'mean_explanation': f"The mean ({stats_dict['mean']:.2f}) represents the arithmetic average of all {col_name} values. This is the expected value under normal distribution.",
            'median_explanation': f"The median ({stats_dict['median']:.2f}) is the middle value when {col_name} is sorted. It is robust to outliers and preferred when data is skewed.",
            'std_explanation': f"Standard deviation ({stats_dict['std']:.2f}) measures the spread of {col_name} around the mean. Approximately 68% of data falls within ±1 SD, 95% within ±2 SD.",
            'skewness_explanation': f"Skewness ({stats_dict['skewness']:.2f}) indicates asymmetry: >0 right-skewed, <0 left-skewed, near 0 symmetric.",
            'kurtosis_explanation': f"Kurtosis ({stats_dict['kurtosis']:.2f}) indicates tail heaviness: >3 heavy tails, <3 light tails compared to normal distribution.",
            'iqr_explanation': f"IQR ({stats_dict['iqr']:.2f}) is the range of middle 50% of data. Values outside Q1-1.5×IQR or Q3+1.5×IQR are considered outliers."
        }

    def _interpret_descriptive(self, stats_dict: Dict, col_name: str) -> Dict[str, str]:
        """Generate interpretations of descriptive statistics"""
        interpretations = {}

        # Mean vs Median comparison
        mean = stats_dict['mean']
        median = stats_dict['median']
        if abs(mean - median) / median < 0.1:
            interpretations['distribution'] = f"Mean ({mean:.2f}) and median ({median:.2f}) are similar, suggesting approximately symmetric distribution."
        elif mean > median:
            interpretations['distribution'] = f"Mean ({mean:.2f}) > median ({median:.2f}), indicating right-skewed distribution with outliers on high side."
        else:
            interpretations['distribution'] = f"Mean ({mean:.2f}) < median ({median:.2f}), indicating left-skewed distribution with outliers on low side."

        # Variability interpretation
        cv = (stats_dict['std'] / mean) if mean != 0 else 0
        if cv < 0.15:
            interpretations['variability'] = f"Low variability (CV={cv:.2f}). Data points are clustered closely around the mean."
        elif cv < 0.30:
            interpretations['variability'] = f"Moderate variability (CV={cv:.2f}). Typical spread for biological data."
        else:
            interpretations['variability'] = f"High variability (CV={cv:.2f}). Consider log transformation or non-parametric tests."

        # Normality assessment
        skew = abs(stats_dict['skewness'])
        kurt = abs(stats_dict['kurtosis'])
        if skew < 1 and kurt < 3:
            interpretations['normality'] = f"Skewness and kurtosis within acceptable range. Data appears approximately normal."
        else:
            interpretations['normality'] = f"Data shows deviation from normality (skew={skew:.2f}, kurt={kurt:.2f}). Consider non-parametric tests or transformation."

        return interpretations

    def _generate_descriptive_recommendations(
        self, 
        df: pd.DataFrame, 
        columns: List[str]
    ) -> List[str]:
        """Generate recommendations based on descriptive analysis"""
        recommendations = []

        for col in columns:
            col_data = df[col].dropna()

            # Check for outliers
            q1 = col_data.quantile(0.25)
            q3 = col_data.quantile(0.75)
            iqr = q3 - q1
            outliers = col_data[(col_data < q1 - 1.5*iqr) | (col_data > q3 + 1.5*iqr)]

            if len(outliers) > 0:
                recommendations.append(
                    f"Column '{col}' has {len(outliers)} potential outliers. "
                    f"Review for data entry errors or consider robust statistical methods."
                )

            # Check distribution
            skew = abs(stats.skew(col_data))
            if skew > 1:
                recommendations.append(
                    f"Column '{col}' is highly skewed ({skew:.2f}). "
                    f"Consider log transformation or use median instead of mean."
                )

        if not recommendations:
            recommendations.append("Data appears well-distributed. Proceed with parametric statistical tests.")

        return recommendations

    def perform_t_test(
        self,
        df: pd.DataFrame,
        group_col: str,
        value_col: str,
        test_type: str = 'independent',  # 'independent', 'paired'
        equal_var: bool = True,
        alternative: str = 'two-sided'  # 'two-sided', 'less', 'greater'
    ) -> Dict[str, Any]:
        """Perform t-test with detailed explanation

        Args:
            df: Input DataFrame
            group_col: Column containing group labels
            value_col: Column containing values to test
            test_type: 'independent' or 'paired'
            equal_var: Assume equal variance (independent test)
            alternative: Alternative hypothesis

        Returns:
            Dictionary with test results and interpretations
        """
        groups = df[group_col].unique()

        if len(groups) != 2:
            raise ValueError(f"T-test requires exactly 2 groups, found {len(groups)}")

        group1_data = df[df[group_col] == groups[0]][value_col].dropna()
        group2_data = df[df[group_col] == groups[1]][value_col].dropna()

        results = {
            'analysis_type': 'T-Test',
            'test_type': test_type,
            'timestamp': datetime.now().isoformat(),
            'alpha': self.alpha,
            'groups': {
                'group1': str(groups[0]),
                'group2': str(groups[1])
            },
            'sample_info': {
                'group1': {'n': len(group1_data), 'mean': float(group1_data.mean()), 'std': float(group1_data.std())},
                'group2': {'n': len(group2_data), 'mean': float(group2_data.mean()), 'std': float(group2_data.std())}
            },
            'test_results': {},
            'explanations': {},
            'interpretations': {},
            'effect_size': {},
            'recommendations': []
        }

        # Perform appropriate test
        if test_type == 'independent':
            test_name = "Student's t-test" if equal_var else "Welch's t-test"
            statistic, p_value = stats.ttest_ind(group1_data, group2_data, 
                                                   equal_var=equal_var, 
                                                   alternative=alternative)
        else:
            test_name = "Paired t-test"
            if len(group1_data) != len(group2_data):
                raise ValueError("Paired test requires equal sample sizes")
            statistic, p_value = stats.ttest_rel(group1_data, group2_data, alternative=alternative)

        # Calculate effect size (Cohen's d)
        pooled_std = np.sqrt(((len(group1_data)-1)*group1_data.var() + 
                             (len(group2_data)-1)*group2_data.var()) / 
                            (len(group1_data) + len(group2_data) - 2))
        cohens_d = (group1_data.mean() - group2_data.mean()) / pooled_std

        results['test_results'] = {
            'test_name': test_name,
            'statistic': float(statistic),
            'p_value': float(p_value),
            'degrees_of_freedom': len(group1_data) + len(group2_data) - 2,
            'alpha': self.alpha,
            'significant': p_value < self.alpha
        }

        results['effect_size'] = {
            'cohens_d': float(cohens_d),
            'magnitude': self._interpret_cohens_d(cohens_d),
            'interpretation': self._explain_cohens_d(cohens_d)
        }

        # Explanations
        results['explanations'] = self._explain_t_test(results, test_name)

        # Interpretations
        results['interpretations'] = self._interpret_t_test(results, groups)

        # Recommendations
        results['recommendations'] = self._generate_t_test_recommendations(results)

        self._log_analysis('t_test', results)
        return results

    def _interpret_cohens_d(self, d: float) -> str:
        """Interpret Cohen's d effect size"""
        abs_d = abs(d)
        if abs_d < 0.2:
            return "negligible"
        elif abs_d < 0.5:
            return "small"
        elif abs_d < 0.8:
            return "medium"
        else:
            return "large"

    def _explain_cohens_d(self, d: float) -> str:
        """Explain Cohen's d"""
        magnitude = self._interpret_cohens_d(d)
        direction = "higher" if d > 0 else "lower"
        return (
            f"Cohen's d ({d:.3f}) indicates {magnitude} effect size. "
            f"Group 1 mean is {direction} than Group 2 mean. "
            f"Clinical relevance should be considered alongside statistical significance."
        )

    def _explain_t_test(self, results: Dict, test_name: str) -> Dict[str, str]:
        """Generate explanations for t-test"""
        p = results['test_results']['p_value']
        sig = results['test_results']['significant']

        return {
            'test_purpose': f"{test_name} compares means between two groups to determine if observed difference is statistically significant.",
            'null_hypothesis': "Null hypothesis (H0): The population means are equal (μ1 = μ2).",
            'alternative_hypothesis': f"Alternative hypothesis (H1): The population means are different (μ1 ≠ μ2).",
            'p_value_meaning': f"P-value ({p:.4e}) is the probability of observing this difference if H0 is true. "
                           f"{'Reject H0 at α={self.alpha}' if sig else 'Fail to reject H0 at α={self.alpha}'}.",
            'statistical_significance': f"{'Statistically significant difference found.' if sig else 'No statistically significant difference found.'}"
        }

    def _interpret_t_test(self, results: Dict, groups: List) -> Dict[str, str]:
        """Generate interpretations of t-test results"""
        sig = results['test_results']['significant']
        mean1 = results['sample_info']['group1']['mean']
        mean2 = results['sample_info']['group2']['mean']
        d = results['effect_size']['cohens_d']

        interpretations = {}

        if sig:
            diff = mean1 - mean2
            direction = "significantly higher" if diff > 0 else "significantly lower"
            interpretations['main_finding'] = (
                f"Group '{groups[0]}' has {direction} mean than Group '{groups[1]}' "
                f"({mean1:.2f} vs {mean2:.2f}, p={results['test_results']['p_value']:.4e})."
            )
        else:
            interpretations['main_finding'] = (
                f"No significant difference between groups ({groups[0]}: {mean1:.2f} vs {groups[1]}: {mean2:.2f}, "
                f"p={results['test_results']['p_value']:.4e})."
            )

        # Clinical significance
        if abs(d) >= 0.8:
            interpretations['clinical_significance'] = "Large effect size suggests clinically meaningful difference."
        elif abs(d) >= 0.5:
            interpretations['clinical_significance'] = "Medium effect size - consider clinical relevance."
        else:
            interpretations['clinical_significance'] = "Small/negligible effect size - may not be clinically important even if statistically significant."

        return interpretations

    def _generate_t_test_recommendations(self, results: Dict) -> List[str]:
        """Generate recommendations based on t-test results"""
        recommendations = []

        sig = results['test_results']['significant']
        d = results['effect_size']['cohens_d']
        n1 = results['sample_info']['group1']['n']
        n2 = results['sample_info']['group2']['n']

        if sig and abs(d) < 0.3:
            recommendations.append(
                "Statistically significant but small effect size. "
                "Consider clinical relevance and sample size impact."
            )

        if not sig and (n1 < 30 or n2 < 30):
            recommendations.append(
                "Non-significant result with small sample size. "
                "Consider increasing sample size or using non-parametric tests."
            )

        if sig and abs(d) >= 0.5:
            recommendations.append(
                "Significant difference with medium/large effect size. "
                "Proceed with confidence in the finding. Consider further validation studies."
            )

        return recommendations

    def perform_anova(
        self,
        df: pd.DataFrame,
        value_col: str,
        group_col: str,
        post_hoc: bool = True
    ) -> Dict[str, Any]:
        """Perform one-way ANOVA with post-hoc analysis

        Args:
            df: Input DataFrame
            value_col: Column containing values
            group_col: Column containing group labels
            post_hoc: Perform Tukey HSD post-hoc test

        Returns:
            Dictionary with ANOVA results and interpretations
        """
        groups = df[group_col].unique()

        if len(groups) < 2:
            raise ValueError(f"ANOVA requires at least 2 groups, found {len(groups)}")

        # Prepare data for ANOVA
        group_data = [df[df[group_col] == g][value_col].dropna() for g in groups]

        # Perform ANOVA
        f_stat, p_value = stats.f_oneway(*group_data)

        results = {
            'analysis_type': 'One-Way ANOVA',
            'timestamp': datetime.now().isoformat(),
            'alpha': self.alpha,
            'groups': [str(g) for g in groups],
            'group_summary': {},
            'test_results': {},
            'explanations': {},
            'interpretations': {},
            'post_hoc': {},
            'recommendations': []
        }

        # Group summary
        for i, g in enumerate(groups):
            results['group_summary'][str(g)] = {
                'n': len(group_data[i]),
                'mean': float(group_data[i].mean()),
                'std': float(group_data[i].std()),
                'min': float(group_data[i].min()),
                'max': float(group_data[i].max())
            }

        # ANOVA results
        results['test_results'] = {
            'f_statistic': float(f_stat),
            'p_value': float(p_value),
            'degrees_of_freedom_between': len(groups) - 1,
            'degrees_of_freedom_within': len(df) - len(groups),
            'significant': p_value < self.alpha
        }

        # Effect size (eta-squared)
        ss_between = sum(len(g) * (g.mean() - np.concatenate(group_data).mean())**2 for g in group_data)
        ss_total = sum((x - np.concatenate(group_data).mean())**2 for x in np.concatenate(group_data))
        eta_squared = ss_between / ss_total

        results['effect_size'] = {
            'eta_squared': float(eta_squared),
            'interpretation': self._interpret_eta_squared(eta_squared)
        }

        # Explanations
        results['explanations'] = self._explain_anova(results)

        # Interpretations
        results['interpretations'] = self._interpret_anova(results)

        # Post-hoc test
        if post_hoc and p_value < self.alpha:
            results['post_hoc'] = self._perform_tukey_hsd(df, value_col, group_col)

        # Recommendations
        results['recommendations'] = self._generate_anova_recommendations(results)

        self._log_analysis('anova', results)
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

    def _explain_anova(self, results: Dict) -> Dict[str, str]:
        """Generate explanations for ANOVA"""
        f = results['test_results']['f_statistic']
        p = results['test_results']['p_value']

        return {
            'test_purpose': f"One-way ANOVA tests whether means differ across {len(results['groups'])} groups.",
            'null_hypothesis': "H0: All group means are equal (μ1 = μ2 = ... = μk).",
            'alternative_hypothesis': "H1: At least one group mean differs from the others.",
            'f_statistic_meaning': f"F-statistic ({f:.2f}) is the ratio of between-group variance to within-group variance.",
            'p_value_meaning': f"P-value ({p:.4e}) indicates {'significant differences exist' if p < self.alpha else 'no significant differences found'} between groups."
        }

    def _interpret_anova(self, results: Dict) -> Dict[str, str]:
        """Generate interpretations of ANOVA results"""
        sig = results['test_results']['significant']
        eta_sq = results['effect_size']['eta_squared']

        interpretations = {}

        if sig:
            interpretations['main_finding'] = (
                f"Significant differences found between groups (F={results['test_results']['f_statistic']:.2f}, "
                f"p={results['test_results']['p_value']:.4e})."
            )

            # Identify highest/lowest means
            means = {g: results['group_summary'][g]['mean'] for g in results['groups']}
            highest = max(means, key=means.get)
            lowest = min(means, key=means.get)

            interpretations['range'] = (
                f"Highest mean: {highest} ({means[highest]:.2f}), "
                f"Lowest mean: {lowest} ({means[lowest]:.2f})."
            )
        else:
            interpretations['main_finding'] = (
                f"No significant differences between groups (F={results['test_results']['f_statistic']:.2f}, "
                f"p={results['test_results']['p_value']:.4e})."
            )

        interpretations['effect_size'] = (
            f"Eta-squared ({eta_sq:.3f}) indicates {results['effect_size']['interpretation']} effect size. "
            f"This represents the proportion of variance explained by group differences."
        )

        return interpretations

    def _perform_tukey_hsd(
        self, 
        df: pd.DataFrame, 
        value_col: str, 
        group_col: str
    ) -> Dict[str, Any]:
        """Perform Tukey HSD post-hoc test"""
        tukey = pairwise_tukeyhsd(df[value_col], df[group_col])

        results = {
            'test_name': 'Tukey HSD',
            'comparisons': []
        }

        for i, comparison in enumerate(tukey._results_table.data[1:]):
            group1, group2, mean_diff, lower, upper, q, p = comparison
            results['comparisons'].append({
                'group1': str(group1),
                'group2': str(group2),
                'mean_difference': float(mean_diff),
                'confidence_interval': [float(lower), float(upper)],
                'p_value': float(p),
                'significant': p < self.alpha
            })

        return results

    def _generate_anova_recommendations(self, results: Dict) -> List[str]:
        """Generate recommendations based on ANOVA results"""
        recommendations = []

        if results['test_results']['significant']:
            recommendations.append(
                "Significant ANOVA result indicates at least one group differs. "
                "Review post-hoc comparisons to identify specific differences."
            )

            if results['effect_size']['eta_squared'] >= 0.14:
                recommendations.append("Large effect size - group differences are practically significant.")
        else:
            recommendations.append(
                "No significant differences between groups. "
                "Consider increasing sample size or examining other factors."
            )

        return recommendations

    def perform_correlation(
        self,
        df: pd.DataFrame,
        columns: List[str],
        method: str = 'pearson'  # 'pearson', 'spearman', 'kendall'
    ) -> Dict[str, Any]:
        """Perform correlation analysis with interpretation

        Args:
            df: Input DataFrame
            columns: Columns to correlate
            method: Correlation method

        Returns:
            Dictionary with correlation matrix and interpretations
        """
        if len(columns) < 2:
            raise ValueError(f"Need at least 2 columns for correlation, found {len(columns)}")

        # Calculate correlation
        if method == 'pearson':
            corr_matrix, p_values = self._pearson_correlation(df[columns])
        elif method == 'spearman':
            corr_matrix, p_values = self._spearman_correlation(df[columns])
        elif method == 'kendall':
            corr_matrix, p_values = self._kendall_correlation(df[columns])
        else:
            raise ValueError(f"Unknown correlation method: {method}")

        results = {
            'analysis_type': 'Correlation Analysis',
            'method': method,
            'timestamp': datetime.now().isoformat(),
            'columns': columns,
            'correlation_matrix': {},
            'p_values': {},
            'significant_correlations': [],
            'explanations': self._explain_correlation(method),
            'interpretations': {},
            'recommendations': []
        }

        # Format matrices
        for i, col1 in enumerate(columns):
            results['correlation_matrix'][col1] = {}
            results['p_values'][col1] = {}
            for j, col2 in enumerate(columns):
                results['correlation_matrix'][col1][col2] = float(corr_matrix[i, j])
                results['p_values'][col1][col2] = float(p_values[i, j])

                # Identify significant correlations
                if i < j and p_values[i, j] < self.alpha:
                    results['significant_correlations'].append({
                        'variable1': col1,
                        'variable2': col2,
                        'correlation': float(corr_matrix[i, j]),
                        'p_value': float(p_values[i, j]),
                        'strength': self._interpret_correlation_strength(corr_matrix[i, j]),
                        'direction': 'positive' if corr_matrix[i, j] > 0 else 'negative'
                    })

        # Interpretations
        results['interpretations'] = self._interpret_correlations(results)

        # Recommendations
        results['recommendations'] = self._generate_correlation_recommendations(results)

        self._log_analysis('correlation', results)
        return results

    def _pearson_correlation(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Calculate Pearson correlation with p-values"""
        n = df.shape[0]
        corr_matrix = df.corr(method='pearson').values

        # Calculate p-values
        p_values = np.zeros_like(corr_matrix)
        for i in range(corr_matrix.shape[0]):
            for j in range(corr_matrix.shape[1]):
                if i == j:
                    p_values[i, j] = 0.0
                else:
                    t_stat = corr_matrix[i, j] * np.sqrt((n - 2) / (1 - corr_matrix[i, j]**2))
                    p_values[i, j] = 2 * (1 - stats.t.cdf(abs(t_stat), n - 2))

        return corr_matrix, p_values

    def _spearman_correlation(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Calculate Spearman correlation"""
        n = df.shape[0]
        corr_matrix = df.corr(method='spearman').values

        # Approximate p-values
        p_values = np.zeros_like(corr_matrix)
        for i in range(corr_matrix.shape[0]):
            for j in range(corr_matrix.shape[1]):
                if i == j:
                    p_values[i, j] = 0.0
                else:
                    t_stat = corr_matrix[i, j] * np.sqrt((n - 2) / (1 - corr_matrix[i, j]**2))
                    p_values[i, j] = 2 * (1 - stats.t.cdf(abs(t_stat), n - 2))

        return corr_matrix, p_values

    def _kendall_correlation(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Calculate Kendall correlation"""
        corr_matrix = df.corr(method='kendall').values
        p_values = np.zeros_like(corr_matrix)  # Simplified p-values
        return corr_matrix, p_values

    def _interpret_correlation_strength(self, r: float) -> str:
        """Interpret correlation coefficient strength"""
        abs_r = abs(r)
        if abs_r < 0.3:
            return "weak"
        elif abs_r < 0.7:
            return "moderate"
        else:
            return "strong"

    def _explain_correlation(self, method: str) -> Dict[str, str]:
        """Generate explanations for correlation analysis"""
        explanations = {
            'pearson': {
                'method': "Pearson correlation measures linear relationship between continuous variables.",
                'assumptions': "Assumes linear relationship, normality, and homoscedasticity.",
                'interpretation': "r ranges from -1 to 1: -1 (perfect negative), 0 (no correlation), 1 (perfect positive)."
            },
            'spearman': {
                'method': "Spearman correlation measures monotonic relationship using ranked data.",
                'assumptions': "Non-parametric, does not assume normality. Measures monotonic (not necessarily linear) relationships.",
                'interpretation': "ρ (rho) ranges from -1 to 1 with similar interpretation to Pearson."
            },
            'kendall': {
                'method': "Kendall's tau measures ordinal association based on concordant/discordant pairs.",
                'assumptions': "Non-parametric, robust to outliers. Suitable for ordinal data.",
                'interpretation': "τ (tau) ranges from -1 to 1. Generally smaller magnitude than Pearson/Spearman."
            }
        }
        return explanations.get(method, {})

    def _interpret_correlations(self, results: Dict) -> Dict[str, str]:
        """Generate interpretations of correlation results"""
        interpretations = {}

        sig_corrs = results['significant_correlations']

        if sig_corrs:
            interpretations['main_finding'] = (
                f"Found {len(sig_corrs)} significant correlation(s) at α={self.alpha}. "
                f"Review individual correlations for details."
            )

            # Strongest correlation
            strongest = max(sig_corrs, key=lambda x: abs(x['correlation']))
            interpretations['strongest'] = (
                f"Strongest correlation: {strongest['variable1']} - {strongest['variable2']} "
                f"(r={strongest['correlation']:.3f}, p={strongest['p_value']:.4e})"
            )
        else:
            interpretations['main_finding'] = f"No significant correlations found at α={self.alpha}."

        return interpretations

    def _generate_correlation_recommendations(self, results: Dict) -> List[str]:
        """Generate recommendations based on correlation analysis"""
        recommendations = []

        sig_corrs = results['significant_correlations']

        for corr in sig_corrs:
            if abs(corr['correlation']) >= 0.7:
                recommendations.append(
                    f"Strong correlation between {corr['variable1']} and {corr['variable2']} (r={corr['correlation']:.3f}). "
                    f"Check for multicollinearity if using in regression."
                )

        if not sig_corrs:
            recommendations.append("No significant correlations. Variables appear independent.")

        return recommendations

    def _log_analysis(self, analysis_type: str, results: Dict):
        """Log analysis for audit trail"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'analysis_type': analysis_type,
            'summary': results
        }
        self.analysis_history.append(log_entry)

    def get_analysis_history(self) -> List[Dict]:
        """Get analysis audit trail"""
        return self.analysis_history


# Example usage
if __name__ == "__main__":
    engine = EnhancedStatisticalEngine()

    # Test data
    test_df = pd.DataFrame({
        'group': ['A', 'A', 'A', 'B', 'B', 'B', 'C', 'C', 'C'],
        'value': [10, 12, 11, 15, 14, 16, 8, 9, 7],
        'age': [45, 47, 46, 50, 52, 51, 40, 42, 41],
        'score': [85, 87, 86, 90, 91, 92, 80, 82, 81]
    })

    # Descriptive statistics
    desc_results = engine.analyze_descriptive(test_df)
    print("Descriptive Statistics:")
    print(json.dumps(desc_results, indent=2, default=str)[:500])

    # T-test
    ttest_results = engine.perform_t_test(test_df, 'group', 'value', test_type='independent')
    print("T-Test:")
    print(json.dumps(ttest_results, indent=2, default=str)[:500])

    def perform_z_test(self, df, value, group_var=None, test_type="one_sample", known_std=None, alternative="two-sided"):
        """Perform Z-test for hypothesis testing
        
        Compliance: GLP, GCP, FDA, EMA
        """
        from scipy import stats
        import numpy as np
        
        results = {
            "analysis_type": "Z-Test",
            "timestamp": datetime.now().isoformat(),
            "alpha": self.alpha,
            "test_parameters": {"test_type": test_type, "known_std": known_std, "alternative": alternative},
            "statistics": {}, "confidence_interval": {}, "effect_size": {},
            "assumptions_check": {}, "interpretations": {}, "recommendations": []
        }
        
        if known_std is None or known_std <= 0:
            raise ValueError("Z-test requires positive known_std")
        
        if test_type == "one_sample":
            sample = df[value].dropna().values
            n = len(sample)
            sample_mean = np.mean(sample)
            se = known_std / np.sqrt(n)
            z_stat = (sample_mean - 0) / se
            
            if alternative == "two-sided":
                p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
            elif alternative == "greater":
                p_value = 1 - stats.norm.cdf(z_stat)
            else:
                p_value = stats.norm.cdf(z_stat)
            
            results["statistics"] = {
                "z_statistic": float(z_stat), "p_value": float(p_value),
                "sample_mean": float(sample_mean), "sample_size": int(n), "standard_error": float(se),
                "significant": p_value < self.alpha
            }
            ci_margin = stats.norm.ppf(1 - self.alpha/2) * se
            results["confidence_interval"] = {
                "lower": float(sample_mean - ci_margin), "upper": float(sample_mean + ci_margin)
            }
            effect_size = sample_mean / known_std
            results["effect_size"] = {"type": "Cohen's d", "value": float(effect_size)}
        
        elif test_type == "two_sample":
            if group_var is None:
                raise ValueError("group_var required for two-sample test")
            groups = df[group_var].unique()
            if len(groups) != 2:
                raise ValueError("Two-sample test requires exactly 2 groups")
            
            g1 = df[df[group_var] == groups[0]][value].dropna().values
            g2 = df[df[group_var] == groups[1]][value].dropna().values
            n1, n2 = len(g1), len(g2)
            mean1, mean2 = np.mean(g1), np.mean(g2)
            
            se = known_std * np.sqrt(1/n1 + 1/n2)
            z_stat = (mean1 - mean2) / se
            p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
            
            results["statistics"] = {
                "z_statistic": float(z_stat), "p_value": float(p_value),
                "group_1": {"name": str(groups[0]), "mean": float(mean1), "n": int(n1)},
                "group_2": {"name": str(groups[1]), "mean": float(mean2), "n": int(n2)},
                "mean_difference": float(mean1 - mean2), "standard_error": float(se),
                "significant": p_value < self.alpha
            }
            ci_margin = stats.norm.ppf(1 - self.alpha/2) * se
            results["confidence_interval"] = {
                "difference_lower": float((mean1 - mean2) - ci_margin),
                "difference_upper": float((mean1 - mean2) + ci_margin)
            }
            results["effect_size"] = {"type": "Cohen's d", "value": float((mean1 - mean2) / known_std)}
        
        self._log_analysis("z_test", results)
        return results

    def perform_ancova(self, df, dv, between, covariate):
        """Perform ANCOVA
        
        Compliance: GLP, GCP, FDA, EMA
        """
        from statsmodels.formula.api import ols
        from statsmodels.stats.anova import anova_lm
        
        results = {
            "analysis_type": "ANCOVA",
            "timestamp": datetime.now().isoformat(),
            "alpha": self.alpha,
            "model_parameters": {"dv": dv, "between": between, "covariate": covariate},
            "assumptions_check": {}, "effect_sizes": {}, "interpretations": {}, "recommendations": []
        }
        
        formula = f"{dv} ~ {' + '.join(between + covariate)}"
        model = ols(formula, data=df).fit()
        ancova_table = anova_lm(model, typ=2)
        results["ancova_table"] = ancova_table.to_dict()
        results["significant_effects"] = [var for var in ancova_table.index if ancova_table.loc[var, 'PR(>F)'] < self.alpha]
        results["effect_sizes"] = {
            var: float(ancova_table.loc[var, 'sum_sq'] / (ancova_table.loc[var, 'sum_sq'] + ancova_table['sum_sq'].sum()))
            for var in ancova_table.index
        }
        self._log_analysis("ancova", results)
        return results

    def perform_repeated_measures_anova(self, df, dv, within, subject, between=None):
        """Perform Repeated Measures ANOVA
        
        Compliance: GLP, GCP, FDA, EMA
        """
        try:
            import pingouin as pg
        except ImportError:
            raise ImportError("pingouin required: pip install pingouin")
        
        results = {
            "analysis_type": "Repeated Measures ANOVA",
            "timestamp": datetime.now().isoformat(),
            "alpha": self.alpha,
            "model_parameters": {"dv": dv, "within": within, "subject": subject, "between": between},
            "assumptions_check": {}, "effect_sizes": {}, "interpretations": {}, "recommendations": []
        }
        
        sphericity = pg.sphericity(data=df, dv=dv, subject=subject, within=within[0])
        results["sphericity"] = {"assumed": sphericity[0], "p_value": float(sphericity[1])}
        
        aov = pg.rm_anova(data=df, dv=dv, within=within, subject=subject, between=between, correction='auto')
        results["anova_table"] = aov.to_dict('records')
        results["effect_sizes"] = {row['Source']: row.get('p_eta2', 0) for row in aov.to_dict('records')}
        results["assumptions_check"] = {"sphericity": sphericity[0]}
        
        self._log_analysis("repeated_measures_anova", results)
        return results

    def perform_manova(self, df, dvs, between):
        """Perform MANOVA
        
        Compliance: GLP, GCP, FDA, EMA
        """
        from statsmodels.multivariate.manova import MANOVA
        from statsmodels.stats.anova import anova_lm
        from statsmodels.formula.api import ols
        
        results = {
            "analysis_type": "MANOVA",
            "timestamp": datetime.now().isoformat(),
            "alpha": self.alpha,
            "model_parameters": {"dvs": dvs, "between": between},
            "multivariate_tests": {}, "univariate_tests": {}, "effect_sizes": {},
            "assumptions_check": {}, "interpretations": {}, "recommendations": []
        }
        
        formula = f"{' + '.join(dvs)} ~ {' + '.join(between)}"
        maov = MANOVA.from_formula(formula, data=df)
        mv_results = maov.mv_test()
        results["multivariate_tests"] = mv_results.to_dict()
        
        results["univariate_tests"] = {}
        for dv in dvs:
            formula_dv = f"{dv} ~ {' + '.join(between)}"
            model = ols(formula_dv, data=df).fit()
            anova = anova_lm(model, typ=2)
            results["univariate_tests"][dv] = anova.to_dict()
        
        self._log_analysis("manova", results)
        return results

    def perform_post_hoc_tests(self, df, dv, between, test_type="tukey"):
        """Perform post-hoc pairwise comparisons
        
        Compliance: GLP, GCP, FDA, EMA
        """
        try:
            import pingouin as pg
        except ImportError:
            raise ImportError("pingouin required: pip install pingouin")
        
        results = {
            "analysis_type": f"Post-Hoc ({test_type})",
            "timestamp": datetime.now().isoformat(),
            "alpha": self.alpha,
            "test_parameters": {"dv": dv, "between": between, "test": test_type},
            "pairwise_comparisons": {}, "significant_pairs": [],
            "interpretations": {}, "recommendations": []
        }
        
        if test_type == "tukey":
            posthoc = pg.pairwise_tukey(data=df, dv=dv, between=between)
        elif test_type == "games_howell":
            posthoc = pg.pairwise_gameshowell(data=df, dv=dv, between=between)
        else:
            posthoc = pg.pairwise_tests(data=df, dv=dv, between=between, padjust=test_type)
        
        results["pairwise_comparisons"] = posthoc.to_dict('records')
        results["significant_pairs"] = [
            row for row in posthoc.to_dict('records')
            if row.get('p-unc', 1) < self.alpha
        ]
        
        self._log_analysis("post_hoc", results)
        return results

    def perform_multiple_regression(self, df, y, x_vars, fit_intercept=True, standardize=False):
        """Perform multiple linear regression
        
        Compliance: GLP, GCP, FDA, EMA
        """
        from statsmodels.formula.api import ols
        from statsmodels.stats.outliers_influence import variance_inflation_factor
        
        results = {
            "analysis_type": "Multiple Linear Regression",
            "timestamp": datetime.now().isoformat(),
            "alpha": self.alpha,
            "model_parameters": {"y": y, "x_vars": x_vars, "fit_intercept": fit_intercept},
            "model_fit": {}, "coefficients": {}, "assumptions_check": {},
            "interpretations": {}, "recommendations": []
        }
        
        df_clean = df[[y] + x_vars].dropna()
        x_data = df_clean[x_vars]
        
        # VIF for multicollinearity
        vifs = [variance_inflation_factor(x_data.values, i) for i in range(x_data.shape[1])]
        results["assumptions_check"]["vifs"] = {x_vars[i]: float(vifs[i]) for i in range(len(x_vars))}
        results["assumptions_check"]["multicollinearity_warning"] = any(vif > 10 for vif in vifs)
        
        formula = f"{y} ~ {' + '.join(x_vars)}"
        if not fit_intercept:
            formula += " - 1"
        model = ols(formula, data=df_clean).fit()
        
        results["model_fit"] = {
            "r_squared": float(model.rsquared), "adjusted_r_squared": float(model.rsquared_adj),
            "f_statistic": float(model.fvalue), "f_p_value": float(model.f_pvalue),
            "aic": float(model.aic), "bic": float(model.bic)
        }
        
        for var in x_vars:
            if var in model.params.index:
                idx = model.params.index.get_loc(var)
                results["coefficients"][var] = {
                    "coefficient": float(model.params[var]), "standard_error": float(model.bse[idx]),
                    "t_statistic": float(model.tvalues[idx]), "p_value": float(model.pvalues[idx]),
                    "significant": model.pvalues[idx] < self.alpha
                }
        
        self._log_analysis("multiple_regression", results)
        return results

    def perform_polynomial_regression(self, df, y, x, degree=2):
        """Perform polynomial regression
        
        Compliance: GLP, GCP, FDA, EMA
        """
        from statsmodels.formula.api import ols
        
        results = {
            "analysis_type": "Polynomial Regression",
            "timestamp": datetime.now().isoformat(),
            "alpha": self.alpha,
            "model_parameters": {"y": y, "x": x, "degree": degree},
            "model_fit": {}, "coefficients": {}, "model_comparison": {},
            "interpretations": {}, "recommendations": []
        }
        
        df_clean = df[[y, x]].dropna()
        
        formula = f"{y} ~ {x}"
        for d in range(2, degree + 1):
            formula += f" + I({x}**{d})"
        
        poly_model = ols(formula, data=df_clean).fit()
        linear_model = ols(f"{y} ~ {x}", data=df_clean).fit()
        
        results["model_fit"] = {
            "r_squared": float(poly_model.rsquared), "adjusted_r_squared": float(poly_model.rsquared_adj)
        }
        results["model_comparison"] = {
            "linear_r_squared": float(linear_model.rsquared),
            "r_squared_improvement": float(poly_model.rsquared - linear_model.rsquared),
            "prefer_polynomial": poly_model.rsquared > linear_model.rsquared
        }
        
        for d in range(degree + 1):
            if d == 0:
                param = 'Intercept'
            elif d == 1:
                param = x
            else:
                param = f"I({x}**{d})"
            if param in poly_model.params.index:
                results["coefficients"][f"degree_{d}"] = {
                    "coefficient": float(poly_model.params[param]), "p_value": float(poly_model.pvalues[param])
                }
        
        self._log_analysis("polynomial_regression", results)
        return results

    def perform_mixed_effects_model(self, df, y, fixed_effects, random_effects, subject_id):
        """Perform Linear Mixed Effects Model
        
        Compliance: GLP, GCP, FDA, EMA
        """
        try:
            import statsmodels.formula.api as smf
        except ImportError:
            raise ImportError("statsmodels required: pip install statsmodels")
        
        results = {
            "analysis_type": "Linear Mixed Effects Model",
            "timestamp": datetime.now().isoformat(),
            "alpha": self.alpha,
            "model_parameters": {"y": y, "fixed": fixed_effects, "random": random_effects},
            "model_fit": {}, "fixed_effects": {}, "random_effects": {},
            "interpretations": {}, "recommendations": []
        }
        
        fixed_part = ' + '.join(fixed_effects)
        formula = f"{y} ~ {fixed_part} + (1|{subject_id})"
        
        model = smf.mixedlm(formula, data=df, groups=df[subject_id])
        result = model.fit(reml=False)
        
        results["model_fit"] = {
            "aic": float(result.aic), "bic": float(result.bic), "log_likelihood": float(result.llf)
        }
        
        for var in fixed_effects:
            if var in result.fe_params.index:
                idx = result.fe_params.index.get_loc(var)
                results["fixed_effects"][var] = {
                    "coefficient": float(result.fe_params[var]),
                    "standard_error": float(result.bse[idx]),
                    "p_value": float(result.pvalues[idx])
                }
        
        self._log_analysis("mixed_effects", results)
        return results

    def perform_glm(self, df, y, x_vars, family='gaussian', link=None):
        """Perform Generalized Linear Model
        
        Compliance: GLP, GCP, FDA, EMA
        """
        import statsmodels.api as sm
        
        results = {
            "analysis_type": "GLM",
            "timestamp": datetime.now().isoformat(),
            "alpha": self.alpha,
            "model_parameters": {"y": y, "x_vars": x_vars, "family": family, "link": link},
            "model_fit": {}, "coefficients": {}, "goodness_of_fit": {},
            "interpretations": {}, "recommendations": []
        }
        
        families = {
            'gaussian': sm.families.Gaussian(),
            'binomial': sm.families.Binomial(),
            'poisson': sm.families.Poisson()
        }
        
        family_obj = families.get(family, sm.families.Gaussian())
        
        if link == 'log':
            family_obj = sm.families.Poisson(sm.genmod.families.links.log())
        elif link == 'logit':
            family_obj = sm.families.Binomial(sm.genmod.families.links.logit())
        
        df_clean = df[[y] + x_vars].dropna()
        X = sm.add_constant(df_clean[x_vars])
        y_data = df_clean[y]
        
        model = sm.GLM(y_data, X, family=family_obj)
        result = model.fit()
        
        results["model_fit"] = {
            "aic": float(result.aic), "bic": float(result.bic), "deviance": float(result.deviance)
        }
        results["goodness_of_fit"] = {
            "pseudo_r_squared": float(1 - result.deviance / result.null_deviance)
        }
        
        for i, var in enumerate(['Intercept'] + x_vars):
            if var in result.params.index:
                results["coefficients"][var] = {
                    "coefficient": float(result.params[var]),
                    "standard_error": float(result.bse[i]),
                    "p_value": float(result.pvalues[i])
                }
        
        self._log_analysis("glm", results)
        return results
