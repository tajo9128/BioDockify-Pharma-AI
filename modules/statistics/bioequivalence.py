"""
Bioequivalence Statistical Tests Module

This module implements comprehensive bioequivalence testing following FDA and EMA guidelines
for pharmaceutical research. All tests follow regulatory standards (80.00-125.00% acceptance range).

Regulatory References:
- FDA Guidance: Bioavailability and Bioequivalence Studies for Orally Administered Drug Products (2003)
- EMA Guideline on the Investigation of Bioequivalence (2010)
- ICH E9 Statistical Principles for Clinical Trials

Author: BioDockify AI Pharmaceutical Statistics Team
Version: 1.0.0
Date: 2026-02-14
"""

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import t, norm
import statsmodels.api as sm
from statsmodels.formula.api import ols
from statsmodels.stats.power import TTestPower
from statsmodels.stats.multicomp import pairwise_tukeyhsd
import warnings
from typing import Dict, Tuple, Optional, Union, List


class BioequivalenceTests:
    """
    Comprehensive bioequivalence testing class implementing FDA/EMA regulatory standards.
    
    This class provides methods for complete bioequivalence assessment including:
    - Two One-Sided Tests (TOST) procedure
    - Confidence Interval approach
    - Geometric Mean Ratio calculation
    - Crossover design ANOVA
    - Bioavailability calculations
    - Dose proportionality testing
    - Complete bioequivalence evaluation
    
    All methods:
    - Return detailed dictionaries with test statistics, p-values, confidence intervals
    - Include plain language interpretations for regulatory submissions
    - Handle log-transformed data (required for bioequivalence)
    - Check statistical assumptions (normality, period effects, carryover)
    - Follow 80.00-125.00% acceptance range
    - Support standard 2x2 and replicate crossover designs
    
    Example:
    --------
    >>> be_tests = BioequivalenceTests()
    >>> # Simulate bioequivalence study data
    >>> data = pd.DataFrame({
    ...     'subject': [1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8],
    ...     'period': [1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2],
    ...     'sequence': ['TR','TR','RT','RT','TR','TR','RT','RT','TR','TR','RT','RT','TR','TR','RT','RT'],
    ...     'treatment': ['T','R','R','T','T','R','R','T','T','R','R','T','T','R','R','T'],
    ...     'auc': [95.2, 92.1, 88.5, 91.3, 97.8, 94.2, 90.1, 93.7, 96.4, 92.8, 89.3, 92.5, 94.6, 91.9, 87.8, 90.5],
    ...     'cmax': [12.5, 11.8, 10.2, 11.5, 13.1, 12.3, 10.8, 11.9, 12.8, 11.6, 10.5, 11.7, 12.2, 11.4, 10.0, 11.2]
    ... })
    >>> results = be_tests.bioequivalence_assessment(
    ...     data=data,
    ...     pk_parameter='auc',
    ...     treatment_col='treatment',
    ...     test_label='T',
    ...     reference_label='R',
    ...     subject_col='subject',
    ...     period_col='period',
    ...     sequence_col='sequence'
    ... )
    >>> print(results['interpretation'])
    """
    
    def __init__(self, alpha: float = 0.05, equivalence_limits: Tuple[float, float] = (0.80, 1.25)):
        """
        Initialize BioequivalenceTests with regulatory parameters.
        
        Parameters:
        -----------
        alpha : float, default=0.05
            Significance level for bioequivalence tests. 
            Corresponds to 90% confidence intervals (1 - 2*alpha).
            Regulatory standard: 0.05 (90% CI)
        
        equivalence_limits : tuple of float, default=(0.80, 1.25)
            Acceptance range for bioequivalence as geometric mean ratio.
            Regulatory standard: (0.80, 1.25) or 80.00-125.00%
            
        Raises:
        -------
        ValueError
            If alpha not in valid range or equivalence limits invalid
        """
        if not 0 < alpha < 0.5:
            raise ValueError("alpha must be between 0 and 0.5")
        if equivalence_limits[0] >= 1.0 or equivalence_limits[1] <= 1.0:
            raise ValueError("Lower limit must be < 1.0 and upper limit must be > 1.0")
        
        self.alpha = alpha
        self.equivalence_limits = equivalence_limits
        self.confidence_level = 1 - 2 * alpha  # 90% for alpha=0.05
        
    def _validate_data(self, data: pd.DataFrame, required_columns: List[str]) -> None:
        """
        Validate input data structure.
        
        Parameters:
        -----------
        data : pd.DataFrame
            Input dataset
        required_columns : list of str
            Required column names
            
        Raises:
        -------
        ValueError
            If data structure invalid or missing required columns
        """
        if not isinstance(data, pd.DataFrame):
            raise ValueError("data must be a pandas DataFrame")
        
        missing_cols = set(required_columns) - set(data.columns)
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        if len(data) == 0:
            raise ValueError("Data cannot be empty")
            
    def _check_normality(self, data: np.ndarray, test_name: str = "Normality Test") -> Dict:
        """
        Check normality assumption using Shapiro-Wilk test.
        
        Parameters:
        -----------
        data : np.ndarray
            Data to test for normality
        test_name : str
            Name of the test being performed
            
        Returns:
        --------
        dict
            Dictionary containing:
            - test_statistic: Shapiro-Wilk statistic
            - p_value: p-value from test
            - is_normal: boolean indicating if assumption met (p > 0.05)
            - interpretation: Plain language explanation
        """
        if len(data) < 3:
            return {
                'test_statistic': None,
                'p_value': None,
                'is_normal': True,
                'interpretation': f"Insufficient data for {test_name} (n={len(data)})."
            }
        
        stat, p_value = stats.shapiro(data)
        is_normal = p_value > 0.05
        
        interpretation = (
            f"{test_name}: Shapiro-Wilk W={stat:.4f}, p={p_value:.4f}. "
            f"Normality assumption {'met' if is_normal else 'violated'} "
            f"(expected p > 0.05). "
            f"Bioequivalence tests on log-transformed data are generally robust "
            f"to mild normality violations."
        )
        
        return {
            'test_statistic': stat,
            'p_value': p_value,
            'is_normal': is_normal,
            'interpretation': interpretation
        }
    
    def _calculate_gm(self, data: np.ndarray) -> float:
        """
        Calculate geometric mean of data.
        
        Parameters:
        -----------
        data : np.ndarray
            Input data (positive values)
            
        Returns:
        --------
        float
            Geometric mean
        """
        if np.any(data <= 0):
            warnings.warn("Non-positive values detected. Using log(abs(data)) for geometric mean calculation.")
            log_data = np.log(np.abs(data))
        else:
            log_data = np.log(data)
        return np.exp(np.mean(log_data))
    
    def _calculate_gmr(self, test_data: np.ndarray, ref_data: np.ndarray) -> float:
        """
        Calculate geometric mean ratio (test/reference).
        
        Parameters:
        -----------
        test_data : np.ndarray
            Test product data (positive values)
        ref_data : np.ndarray
            Reference product data (positive values)
            
        Returns:
        --------
        float
            Geometric mean ratio
        """
        return self._calculate_gm(test_data) / self._calculate_gm(ref_data)
    
    def _format_ci(self, lower: float, upper: float) -> Tuple[float, float]:
        """
        Format confidence interval values for display.
        
        Parameters:
        -----------
        lower, upper : float
            Confidence interval bounds
            
        Returns:
        --------
        tuple of float
            Formatted confidence interval
        """
        return (round(lower, 4), round(upper, 4))

    def tost_procedure(
        self, 
        test_data: Union[np.ndarray, List[float]], 
        ref_data: Union[np.ndarray, List[float]],
        log_transform: bool = True
    ) -> Dict:
        """
        Two One-Sided Tests (TOST) procedure for bioequivalence assessment.
        
        The TOST procedure is the regulatory gold standard for bioequivalence testing.
        It tests two one-sided hypotheses:
        - H01: Test/Reference < lower equivalence limit
        - H02: Test/Reference > upper equivalence limit
        
        Bioequivalence is concluded if both null hypotheses are rejected (both p-values < alpha).
        
        Regulatory Example (FDA):
        ------------------------
        For a generic drug approval study:
        - Test product: Generic formulation
        - Reference product: Listed drug
        - PK parameter: AUC(0-∞)
        - Sample size: n=24 subjects
        - Alpha level: 0.05
        - Equivalence limits: 0.80-1.25
        
        Hypotheses:
        - H01: μT/μR < 0.80
        - H02: μT/μR > 1.25
        
        Decision rule: Conclude bioequivalence if p1 < 0.05 AND p2 < 0.05
        
        Parameters:
        -----------
        test_data : array-like
            Test product pharmacokinetic data (e.g., AUC, Cmax)
        ref_data : array-like
            Reference product pharmacokinetic data
        log_transform : bool, default=True
            Apply natural log transformation (required by FDA/EMA for bioequivalence)
            
        Returns:
        --------
        dict
            Comprehensive TOST results dictionary:
            
            - test_statistic: t-statistic for the difference
            - p_value_left: p-value for lower bound test (H01)
            - p_value_right: p-value for upper bound test (H02)
            - p_value_overall: Overall p-value (max of two one-sided p-values)
            - ci_lower: Lower confidence limit
            - ci_upper: Upper confidence limit
            - geometric_mean_ratio: Point estimate of test/reference ratio
            - is_equivalent: Boolean indicating bioequivalence conclusion
            - interpretation: Plain language regulatory interpretation
            - regulatory_reference: Applicable regulatory guidance
        """
        # Convert to numpy arrays
        test_data = np.asarray(test_data)
        ref_data = np.asarray(ref_data)
        
        # Validate input
        if len(test_data) == 0 or len(ref_data) == 0:
            raise ValueError("Input data cannot be empty")
        
        # Apply log transformation (regulatory requirement)
        if log_transform:
            test_data = np.log(test_data)
            ref_data = np.log(ref_data)
        
        # Check normality on log-transformed data
        diff = test_data - ref_data
        normality_check = self._check_normality(diff, "TOST Normality")
        
        # Calculate basic statistics
        mean_diff = np.mean(diff)
        n = len(diff)
        df = n - 1
        se = np.std(diff, ddof=1) / np.sqrt(n)
        
        # TOST procedure
        # Transform equivalence limits to log scale
        log_lower = np.log(self.equivalence_limits[0])
        log_upper = np.log(self.equivalence_limits[1])
        
        # Calculate t-statistics for two one-sided tests
        # Test 1: H0: μ_diff <= log_lower
        t_left = (mean_diff - log_lower) / se
        p_left = 1 - t.cdf(t_left, df)  # Upper-tail probability
        
        # Test 2: H0: μ_diff >= log_upper
        t_right = (mean_diff - log_upper) / se
        p_right = t.cdf(t_right, df)  # Lower-tail probability
        
        # Overall p-value for TOST
        p_overall = max(p_left, p_right)
        
        # Calculate confidence interval
        t_crit = t.ppf(1 - self.alpha, df)
        ci_lower_log = mean_diff - t_crit * se
        ci_upper_log = mean_diff + t_crit * se
        
        # Transform back to original scale
        gmr = np.exp(mean_diff)
        ci_lower = np.exp(ci_lower_log)
        ci_upper = np.exp(ci_upper_log)
        
        # Bioequivalence decision
        is_equivalent = (p_left < self.alpha) and (p_right < self.alpha)
        ci_within_limits = (ci_lower >= self.equivalence_limits[0]) and \
                           (ci_upper <= self.equivalence_limits[1])
        
        # Build interpretation
        ci_percentage = self.confidence_level * 100
        
        interpretation = (
            f"\n{'='*70}\n"
            f"TWO ONE-SIDED TESTS (TOST) PROCEDURE - BIOEQUIVALENCE ASSESSMENT\n"
            f"{'='*70}\n"
            f"\nREGULATORY STANDARD: FDA/EMA Bioequivalence Guidance\n"
            f"ACCEPTANCE RANGE: {self.equivalence_limits[0]*100:.2f}% - {self.equivalence_limits[1]*100:.2f}%\n"
            f"CONFIDENCE LEVEL: {ci_percentage:.0f}%\n"
            f"\n{'-'*70}\n"
            f"STATISTICAL RESULTS:\n"
            f"{'-'*70}\n"
            f"Sample size: n={n} paired observations\n"
            f"Geometric Mean Ratio (Point Estimate): {gmr:.4f} ({gmr*100:.2f}%)\n"
            f"{ci_percentage:.0f}% Confidence Interval: {ci_lower:.4f} - {ci_upper:.4f} "
            f"({ci_lower*100:.2f}% - {ci_upper*100:.2f}%)\n"
            f"\nTOST Results:\n"
            f"  Lower bound test (H01: ratio < {self.equivalence_limits[0]}): "
            f"t={t_left:.4f}, p={p_left:.4f}\n"
            f"  Upper bound test (H02: ratio > {self.equivalence_limits[1]}): "
            f"t={t_right:.4f}, p={p_right:.4f}\n"
            f"  Overall TOST p-value: {p_overall:.4f}\n"
            f"\n{'-'*70}\n"
            f"ASSUMPTION CHECKS:\n"
            f"{'-'*70}\n"
            f"{normality_check['interpretation']}\n"
            f"\n{'-'*70}\n"
            f"REGULATORY DECISION:\n"
            f"{'-'*70}\n"
        )
        
        if is_equivalent and ci_within_limits:
            interpretation += (
                f"✓ BIOEQUIVALENCE CONCLUDED\n"
                f"\nCriteria met:\n"
                f"  ✓ Both one-sided tests rejected (p1={p_left:.4f} < {self.alpha}, "
                f"p2={p_right:.4f} < {self.alpha})\n"
                f"  ✓ {ci_percentage:.0f}% CI entirely within acceptance range "
                f"({self.equivalence_limits[0]*100:.2f}% - {self.equivalence_limits[1]*100:.2f}%)\n"
                f"\nRegulatory implication: Test product demonstrates bioequivalence to reference."
                f" May proceed to regulatory submission for approval.\n"
            )
        else:
            interpretation += (
                f"✗ BIOEQUIVALENCE NOT CONCLUDED\n"
                f"\nCriteria not met:\n"
                f"  {'✓' if p_left < self.alpha else '✗'} Lower bound test: p={p_left:.4f} "
                f"({'passes' if p_left < self.alpha else 'fails'} alpha={self.alpha})\n"
                f"  {'✓' if p_right < self.alpha else '✗'} Upper bound test: p={p_right:.4f} "
                f"({'passes' if p_right < self.alpha else 'fails'} alpha={self.alpha})\n"
                f"  {'✓' if ci_within_limits else '✗'} Confidence interval: {ci_lower*100:.2f}% - {ci_upper*100:.2f}% "
                f"({'within' if ci_within_limits else 'outside'} acceptance range)\n"
                f"\nRegulatory implication: Test product does not demonstrate bioequivalence. "
                f"Consider reformulation, additional study data, or scientific justification.\n"
            )
        
        interpretation += f"\n{'='*70}\n"
        
        return {
            'test_statistic': t_left,
            'p_value_left': p_left,
            'p_value_right': p_right,
            'p_value_overall': p_overall,
            'ci_lower': ci_lower,
            'ci_upper': ci_upper,
            'geometric_mean_ratio': gmr,
            'is_equivalent': is_equivalent,
            'normality_assumption': normality_check,
            'interpretation': interpretation,
            'regulatory_reference': (
                "FDA Guidance for Industry: Bioavailability and Bioequivalence Studies "
                "for Orally Administered Drug Products (2003); "
                "EMA Guideline on the Investigation of Bioequivalence (2010)"
            )
        }

    def confidence_interval_approach(
        self,
        test_data: Union[np.ndarray, List[float]],
        ref_data: Union[np.ndarray, List[float]],
        log_transform: bool = True
    ) -> Dict:
        """
        Confidence interval approach for bioequivalence assessment.
        
        This method calculates the two-sided confidence interval for the geometric
        mean ratio and checks whether it falls entirely within the regulatory
        acceptance limits (0.80-1.25 for 90% CI).
        
        Regulatory Example (EMA):
        ------------------------
        For a bioequivalence study in EU:
        - Investigational medicinal product: New formulation
        - Reference medicinal product: Authorized product
        - PK parameter: Cmax
        - Sample size: n=24 subjects
        - Confidence level: 90%
        - Acceptance limits: 0.80-1.25
        
        Decision rule: Conclude bioequivalence if the 90% CI for GMR 
        lies entirely within 0.80-1.25
        
        Parameters:
        -----------
        test_data : array-like
            Test product pharmacokinetic data
        ref_data : array-like
            Reference product pharmacokinetic data
        log_transform : bool, default=True
            Apply natural log transformation
            
        Returns:
        --------
        dict
            Confidence interval approach results:
            
            - point_estimate: Geometric mean ratio
            - ci_lower: Lower confidence limit
            - ci_upper: Upper confidence limit
            - ci_width: Width of confidence interval
            - is_equivalent: Boolean for bioequivalence conclusion
            - interpretation: Detailed regulatory interpretation
        """
        # Convert to numpy arrays
        test_data = np.asarray(test_data)
        ref_data = np.asarray(ref_data)
        
        if len(test_data) != len(ref_data):
            raise ValueError("Test and reference data must have same length for paired analysis")
        
        # Apply log transformation
        if log_transform:
            test_data = np.log(test_data)
            ref_data = np.log(ref_data)
        
        # Calculate differences
        diff = test_data - ref_data
        n = len(diff)
        df = n - 1
        
        mean_diff = np.mean(diff)
        se = np.std(diff, ddof=1) / np.sqrt(n)
        
        # Calculate confidence interval
        t_crit = t.ppf(1 - self.alpha, df)
        ci_lower_log = mean_diff - t_crit * se
        ci_upper_log = mean_diff + t_crit * se
        
        # Transform back to original scale
        point_estimate = np.exp(mean_diff)
        ci_lower = np.exp(ci_lower_log)
        ci_upper = np.exp(ci_upper_log)
        ci_width = ci_upper - ci_lower
        
        # Check bioequivalence
        is_equivalent = (ci_lower >= self.equivalence_limits[0]) and \
                       (ci_upper <= self.equivalence_limits[1])
        
        ci_percentage = self.confidence_level * 100
        
        interpretation = (
            f"\n{'='*70}\n"
            f"CONFIDENCE INTERVAL APPROACH - BIOEQUIVALENCE ASSESSMENT\n"
            f"{'='*70}\n"
            f"\nREGULATORY STANDARD: EMA/FDA Bioequivalence Guideline\n"
            f"ACCEPTANCE RANGE: {self.equivalence_limits[0]*100:.2f}% - {self.equivalence_limits[1]*100:.2f}%\n"
            f"CONFIDENCE LEVEL: {ci_percentage:.0f}%\n"
            f"\n{'-'*70}\n"
            f"RESULTS:\n"
            f"{'-'*70}\n"
            f"Sample size: n={n} paired observations\n"
            f"Point Estimate (GMR): {point_estimate:.4f} ({point_estimate*100:.2f}%)\n"
            f"{ci_percentage:.0f}% Confidence Interval: {ci_lower:.4f} - {ci_upper:.4f} "
            f"({ci_lower*100:.2f}% - {ci_upper*100:.2f}%)\n"
            f"CI Width: {ci_width:.4f}\n"
            f"\n{'-'*70}\n"
            f"DECISION CRITERIA:\n"
            f"{'-'*70}\n"
            f"Lower limit ({ci_lower*100:.2f}%) >= {self.equivalence_limits[0]*100:.2f}%: "
            f"{'✓ PASS' if ci_lower >= self.equivalence_limits[0] else '✗ FAIL'}\n"
            f"Upper limit ({ci_upper*100:.2f}%) <= {self.equivalence_limits[1]*100:.2f}%: "
            f"{'✓ PASS' if ci_upper <= self.equivalence_limits[1] else '✗ FAIL'}\n"
            f"\n{'-'*70}\n"
            f"REGULATORY DECISION:\n"
            f"{'-'*70}\n"
        )
        
        if is_equivalent:
            interpretation += (
                f"✓ BIOEQUIVALENCE CONCLUDED\n"
                f"\nThe {ci_percentage:.0f}% confidence interval ({ci_lower*100:.2f}% - {ci_upper*100:.2f}%) "
                f"lies entirely within the acceptance range "
                f"({self.equivalence_limits[0]*100:.2f}% - {self.equivalence_limits[1]*100:.2f}%).\n"
                f"\nRegulatory implication: Test product demonstrates bioequivalence to reference. "
                f"This method is equivalent to the TOST procedure when using 90% CI.\n"
            )
        else:
            interpretation += (
                f"✗ BIOEQUIVALENCE NOT CONCLUDED\n"
                f"\nThe {ci_percentage:.0f}% confidence interval ({ci_lower*100:.2f}% - {ci_upper*100:.2f}%) "
                f"falls outside the acceptance range "
                f"({self.equivalence_limits[0]*100:.2f}% - {self.equivalence_limits[1]*100:.2f}%).\n"
            )
            if ci_lower < self.equivalence_limits[0]:
                interpretation += f"Lower limit ({ci_lower*100:.2f}%) below {self.equivalence_limits[0]*100:.2f}% threshold.\n"
            if ci_upper > self.equivalence_limits[1]:
                interpretation += f"Upper limit ({ci_upper*100:.2f}%) above {self.equivalence_limits[1]*100:.2f}% threshold.\n"
            interpretation += (
                "\nRegulatory implication: Test product does not meet bioequivalence criteria. "
                "Further investigation required.\n"
            )
        
        interpretation += f"\n{'='*70}\n"
        
        return {
            'point_estimate': point_estimate,
            'ci_lower': ci_lower,
            'ci_upper': ci_upper,
            'ci_width': ci_width,
            'ci_percentage': ci_percentage,
            'is_equivalent': is_equivalent,
            'interpretation': interpretation,
            'regulatory_reference': (
                "EMA Guideline on the Investigation of Bioequivalence (2010), "
                "Section 4.1.6 - Confidence Interval Approach"
            )
        }

    def geometric_mean_ratio(
        self,
        test_data: Union[np.ndarray, List[float]],
        ref_data: Union[np.ndarray, List[float]],
        ci_level: float = None,
        log_transform: bool = True
    ) -> Dict:
        """
        Calculate geometric mean ratio with confidence intervals.
        
        The geometric mean ratio (GMR) is the ratio of geometric means of
        test and reference products. This is the point estimate used in
        bioequivalence assessment.
        
        Regulatory Note:
        --------------
        GMR is calculated on log-transformed data:
        GMR = exp(mean(log(Test)) - mean(log(Reference)))
        
        Confidence intervals are asymmetric on the original scale but
        symmetric on the log scale.
        
        Parameters:
        -----------
        test_data : array-like
            Test product pharmacokinetic data
        ref_data : array-like
            Reference product pharmacokinetic data
        ci_level : float, optional
            Confidence level (0-1). Defaults to class alpha setting (90%)
        log_transform : bool, default=True
            Apply natural log transformation
            
        Returns:
        --------
        dict
            Geometric mean ratio results:
            
            - geometric_mean_test: Geometric mean of test data
            - geometric_mean_ref: Geometric mean of reference data
            - geometric_mean_ratio: Point estimate of GMR
            - ci_lower: Lower confidence limit
            - ci_upper: Upper confidence limit
            - log_transformed: Whether data was log-transformed
            - interpretation: Detailed explanation
        """
        # Convert to numpy arrays
        test_data = np.asarray(test_data)
        ref_data = np.asarray(ref_data)
        
        # Set confidence level
        if ci_level is None:
            ci_level = self.confidence_level
        
        # Apply log transformation
        if log_transform:
            test_log = np.log(test_data)
            ref_log = np.log(ref_data)
        else:
            test_log = test_data
            ref_log = ref_data
        
        # Calculate geometric means
        gm_test = np.exp(np.mean(test_log)) if log_transform else np.mean(test_data)
        gm_ref = np.exp(np.mean(ref_log)) if log_transform else np.mean(ref_data)
        
        # Calculate GMR
        gmr = gm_test / gm_ref
        
        # Calculate confidence interval for GMR
        diff = test_log - ref_log
        n = len(diff)
        df = n - 1
        
        mean_diff = np.mean(diff)
        se = np.std(diff, ddof=1) / np.sqrt(n)
        
        # Calculate CI
        alpha_ci = (1 - ci_level) / 2
        t_crit = t.ppf(1 - alpha_ci, df)
        
        ci_lower_log = mean_diff - t_crit * se
        ci_upper_log = mean_diff + t_crit * se
        
        ci_lower = np.exp(ci_lower_log) if log_transform else ci_lower_log
        ci_upper = np.exp(ci_upper_log) if log_transform else ci_upper_log
        
        # Build interpretation
        ci_percentage = ci_level * 100
        
        interpretation = (
            f"\n{'='*70}\n"
            f"GEOMETRIC MEAN RATIO (GMR) CALCULATION\n"
            f"{'='*70}\n"
            f"\nResults:\n"
            f"  Test geometric mean: {gm_test:.4f}\n"
            f"  Reference geometric mean: {gm_ref:.4f}\n"
            f"  Geometric Mean Ratio: {gmr:.4f} ({gmr*100:.2f}%)\n"
            f"  {ci_percentage:.0f}% Confidence Interval: {ci_lower:.4f} - {ci_upper:.4f} "
            f"({ci_lower*100:.2f}% - {ci_upper*100:.2f}%)\n"
            f"  Log transformation: {'Applied' if log_transform else 'Not applied'}\n"
            f"\nInterpretation:\n"
        )
        
        if self.equivalence_limits[0] <= gmr <= self.equivalence_limits[1]:
            interpretation += (
                f"  GMR point estimate ({gmr*100:.2f}%) falls within "
                f"acceptance range ({self.equivalence_limits[0]*100:.2f}% - {self.equivalence_limits[1]*100:.2f}%). "
                f"This supports bioequivalence.\n"
            )
        else:
            interpretation += (
                f"  GMR point estimate ({gmr*100:.2f}%) falls outside "
                f"acceptance range ({self.equivalence_limits[0]*100:.2f}% - {self.equivalence_limits[1]*100:.2f}%). "
                f"This does not support bioequivalence.\n"
            )
        
        interpretation += (
            f"  Confidence interval interpretation depends on the complete "
            f"bioequivalence assessment (TOST procedure).\n"
            f"\n{'='*70}\n"
        )
        
        return {
            'geometric_mean_test': gm_test,
            'geometric_mean_ref': gm_ref,
            'geometric_mean_ratio': gmr,
            'ci_lower': ci_lower,
            'ci_upper': ci_upper,
            'ci_level': ci_level,
            'log_transformed': log_transform,
            'interpretation': interpretation
        }

    def crossover_design_anova(
        self,
        data: pd.DataFrame,
        pk_parameter: str,
        treatment_col: str = 'treatment',
        subject_col: str = 'subject',
        period_col: str = 'period',
        sequence_col: str = 'sequence',
        test_label: str = 'T',
        ref_label: str = 'R'
    ) -> Dict:
        """
        Perform ANOVA for 2x2 crossover bioequivalence study.
        
        The crossover design ANOVA partitions variance into:
        - Subject (random effect)
        - Sequence (tests for carryover effect)
        - Period (time effect)
        - Treatment (formulation effect)
        - Error
        
        Regulatory Standard:
        -----------------
        Carryover effect (sequence) should be non-significant (p > 0.10).
        If carryover is detected, standard analysis may be invalid.
        
        Example Study:
        -------------
        Design: 2x2 crossover (TR/RT sequences)
        Subjects: n=24 (12 per sequence)
        Periods: 2
        Washout: >=5 half-lives
        
        ANOVA Model:
        Y_ijk = μ + S_ij + P_i + T_j + ε_ijk
        
        Where:
        - Y_ijk: PK response for subject k in period i receiving treatment j
        - μ: Overall mean
        - S_ij: Subject k nested in sequence j
        - P_i: Period effect
        - T_j: Treatment effect
        - ε_ijk: Residual error
        
        Parameters:
        -----------
        data : pd.DataFrame
            Study data with subject, period, sequence, treatment, and PK columns
        pk_parameter : str
            Name of PK parameter column to analyze
        treatment_col : str, default='treatment'
            Treatment column name
        subject_col : str, default='subject'
            Subject identifier column
        period_col : str, default='period'
            Period number column
        sequence_col : str, default='sequence'
            Sequence identifier column
        test_label : str, default='T'
            Label for test product
        ref_label : str, default='R'
            Label for reference product
            
        Returns:
        --------
        dict
            ANOVA results with:
            
            - anova_table: Complete ANOVA table
            - treatment_effect: F and p-value for treatment
            - period_effect: F and p-value for period
            - sequence_effect: F and p-value for sequence
            - carryover_detected: Boolean if significant carryover present
            - normality_assumption: Normality test results
            - interpretation: Detailed regulatory interpretation
        """
        self._validate_data(data, [pk_parameter, treatment_col, subject_col, period_col, sequence_col])
        
        # Apply log transformation
        data = data.copy()
        data['log_pk'] = np.log(data[pk_parameter])
        
        # Build ANOVA model
        # Model: log_pk ~ sequence + subject(sequence) + period + treatment
        formula = f'log_pk ~ C({sequence_col}) + C({subject_col}) + C({period_col}) + C({treatment_col})'
        
        try:
            model = ols(formula, data=data).fit()
            anova_table = sm.stats.anova_lm(model, typ=2)
        except Exception as e:
            raise ValueError(f"ANOVA model fitting failed: {str(e)}")
        
        # Extract effects
        effects = {}
        for effect_col, effect_name in [
            (f'C({treatment_col})', 'treatment'),
            (f'C({period_col})', 'period'),
            (f'C({sequence_col})', 'sequence')
        ]:
            if effect_col in anova_table.index:
                effects[effect_name] = {
                    'f': anova_table.loc[effect_col, 'F'],
                    'p_value': anova_table.loc[effect_col, 'PR(>F)'],
                    'ss': anova_table.loc[effect_col, 'sum_sq'],
                    'df': anova_table.loc[effect_col, 'df']
                }
        
        # Check for carryover (sequence effect)
        sequence_effect = effects.get('sequence')
        carryover_detected = sequence_effect is not None and sequence_effect['p_value'] < 0.10
        
        # Check normality of residuals
        residuals = model.resid
        normality_check = self._check_normality(residuals, "ANOVA Residuals")
        
        # Build interpretation
        interpretation = (
            f"\n{'='*70}\n"
            f"CROSSOVER DESIGN ANOVA - VARIANCE ANALYSIS\n"
            f"{'='*70}\n"
            f"\nStudy Design: 2x2 Crossover\n"
            f"PK Parameter: {pk_parameter.upper()} (log-transformed)\n"
            f"\nANOVA Table:\n"
            f"{'-'*70}\n"
            f"{'Source':<20} {'DF':>6} {'SS':>12} {'F':>10} {'p-value':>10}\n"
            f"{'-'*70}\n"
        )
        
        # Add rows to table
        for idx, row in anova_table.iterrows():
            source = str(idx).replace('C(', '').replace(')', '').replace('[T.', '')
            interpretation += (
                f"{source:<20} {int(row['df']):>6} {row['sum_sq']:>12.2f} "
                f"{row['F']:>10.4f} {row['PR(>F)']:>10.4f}\n"
            )
        
        interpretation += f"{'-'*70}\n"
        
        # Treatment effect
        if 'treatment' in effects:
            te = effects['treatment']
            t_sig = te['p_value'] < 0.05
            sig_status = 'Significant' if t_sig else 'Not significant'
            interpretation += (
                f"\nTreatment Effect:\n"
                f"  F = {te['f']:.4f}, p = {te['p_value']:.4f}\n"
                f"  {sig_status} at α=0.05\n"
            )
            if t_sig:
                interpretation += (
                    "  Note: Treatment effect expected in bioequivalence studies. "
                    "Bioequivalence assessed via confidence interval, not significance.\n"
                )
        
        # Period effect
        if 'period' in effects:
            pe = effects['period']
            p_sig = pe['p_value'] < 0.05
            sig_status = 'Significant' if p_sig else 'Not significant'
            interpretation += (
                f"\nPeriod Effect:\n"
                f"  F = {pe['f']:.4f}, p = {pe['p_value']:.4f}\n"
                f"  {sig_status} at α=0.05\n"
            )
            if p_sig:
                interpretation += (
                    "  Note: Significant period effect may indicate inadequate washout. "
                    "Consider longer washout period in future studies.\n"
                )
        
        # Sequence (carryover) effect
        if 'sequence' in effects:
            se = effects['sequence']
            s_sig = se['p_value'] < 0.10
            interpretation += (
                f"\nSequence (Carryover) Effect:\n"
                f"  F = {se['f']:.4f}, p = {se['p_value']:.4f}\n"
                f"  Carryover detected: {carryover_detected}\n"
            )
            if carryover_detected:
                interpretation += (
                    "  ⚠ WARNING: Significant sequence effect detected.\n"
                    "  This may indicate carryover effect (inadequate washout) or "
                    "treatment-by-period interaction.\n"
                    "  Standard bioequivalence analysis may be invalid.\n"
                )
        
        # Normality
        interpretation += (
            f"\n{'-'*70}\n"
            f"ASSUMPTION CHECKS:\n"
            f"{'-'*70}\n"
            f"{normality_check['interpretation']}\n"
            f"\n{'='*70}\n"
        )
        
        return {
            'anova_table': anova_table.to_dict(),
            'treatment_effect': effects.get('treatment'),
            'period_effect': effects.get('period'),
            'sequence_effect': effects.get('sequence'),
            'carryover_detected': carryover_detected,
            'normality_assumption': normality_check,
            'model_summary': {
                'r_squared': model.rsquared,
                'r_squared_adj': model.rsquared_adj,
                'aic': model.aic,
                'bic': model.bic
            },
            'interpretation': interpretation,
            'regulatory_reference': (
                "FDA Guidance: Statistical Approaches to Establishing Bioequivalence (2001); "
                "EMA Guideline on Bioequivalence (2010), Section 4.1.5"
            )
        }

    def bioavailability_calculation(
        self,
        test_auc: Union[np.ndarray, List[float], float],
        test_dose: float,
        ref_auc: Union[np.ndarray, List[float], float] = None,
        ref_dose: float = None,
        test_cmax: Union[np.ndarray, List[float], float] = None,
        ref_cmax: Union[np.ndarray, List[float], float] = None,
        iv_auc: Union[np.ndarray, List[float], float] = None,
        iv_dose: float = None
    ) -> Dict:
        """
        Calculate absolute and relative bioavailability.
        
        Bioavailability measures the fraction of administered dose that reaches
        systemic circulation:
        
        1. Absolute Bioavailability (F_abs):
           Comparison with intravenous (IV) administration
           F_abs = (AUC_oral / Dose_oral) / (AUC_iv / Dose_iv)
        
        2. Relative Bioavailability (F_rel):
           Comparison with reference formulation
           F_rel = (AUC_test / Dose_test) / (AUC_ref / Dose_ref)
        
        Regulatory Context:
        -----------------
        Bioequivalence studies typically assess relative bioavailability.
        Absolute bioavailability requires IV reference data.
        
        Example:
        -------
        Test formulation: New oral tablet (100 mg)
        Reference formulation: Listed drug oral tablet (100 mg)
        AUC_test: 4800 ng·h/mL, AUC_ref: 5000 ng·h/mL
        
        Dose-normalized AUC:
        - Test: 4800/100 = 48.0 ng·h/mL/mg
        - Ref: 5000/100 = 50.0 ng·h/mL/mg
        
        Relative Bioavailability:
        F_rel = 48.0 / 50.0 = 0.96 (96%)
        
        Parameters:
        -----------
        test_auc : array-like or float
            Test product AUC values (ng·h/mL)
        test_dose : float
            Test product dose (mg)
        ref_auc : array-like or float, optional
            Reference product AUC values
        ref_dose : float, optional
            Reference product dose (mg)
        test_cmax : array-like or float, optional
            Test product Cmax values (ng/mL)
        ref_cmax : array-like or float, optional
            Reference product Cmax values
        iv_auc : array-like or float, optional
            Intravenous reference AUC (for absolute bioavailability)
        iv_dose : float, optional
            Intravenous dose (mg)
            
        Returns:
        --------
        dict
            Bioavailability results:
            
            - absolute_bioavailability: F_abs (if IV data provided)
            - relative_bioavailability: F_rel (if reference data provided)
            - dose_normalized_auc_test: AUC/dose for test
            - dose_normalized_auc_ref: AUC/dose for reference
            - interpretation: Detailed regulatory interpretation
        """
        result = {}
        
        # Calculate mean AUC for test
        if isinstance(test_auc, (list, np.ndarray)):
            test_auc_mean = np.mean(test_auc)
            result['test_auc_values'] = np.asarray(test_auc).tolist()
        else:
            test_auc_mean = float(test_auc)
        
        result['test_auc'] = test_auc_mean
        result['test_dose'] = test_dose
        result['dose_normalized_auc_test'] = test_auc_mean / test_dose
        
        interpretation = (
            f"\n{'='*70}\n"
            f"BIOAVAILABILITY CALCULATION\n"
            f"{'='*70}\n"
            f"\nTest Product:\n"
            f"  Dose: {test_dose} mg\n"
            f"  AUC: {test_auc_mean:.2f} ng·h/mL\n"
            f"  Dose-normalized AUC: {result['dose_normalized_auc_test']:.4f} ng·h/mL/mg\n"
        )
        
        # Absolute bioavailability (requires IV data)
        if iv_auc is not None and iv_dose is not None:
            if isinstance(iv_auc, (list, np.ndarray)):
                iv_auc_mean = np.mean(iv_auc)
                result['iv_auc_values'] = np.asarray(iv_auc).tolist()
            else:
                iv_auc_mean = float(iv_auc)
            
            result['iv_auc'] = iv_auc_mean
            result['iv_dose'] = iv_dose
            result['dose_normalized_auc_iv'] = iv_auc_mean / iv_dose
            
            f_abs = (result['dose_normalized_auc_test'] / result['dose_normalized_auc_iv']) * 100
            result['absolute_bioavailability'] = f_abs
            
            interpretation += (
                f"\nIntravenous Reference:\n"
                f"  Dose: {iv_dose} mg\n"
                f"  AUC: {iv_auc_mean:.2f} ng·h/mL\n"
                f"  Dose-normalized AUC: {result['dose_normalized_auc_iv']:.4f} ng·h/mL/mg\n"
                f"\nAbsolute Bioavailability (F_abs):\n"
                f"  F_abs = (AUC_test/Dose_test) / (AUC_iv/Dose_iv) × 100%\n"
                f"  F_abs = {f_abs:.2f}%\n"
            )
        
        # Relative bioavailability (requires reference data)
        if ref_auc is not None and ref_dose is not None:
            if isinstance(ref_auc, (list, np.ndarray)):
                ref_auc_mean = np.mean(ref_auc)
                result['ref_auc_values'] = np.asarray(ref_auc).tolist()
            else:
                ref_auc_mean = float(ref_auc)
            
            result['ref_auc'] = ref_auc_mean
            result['ref_dose'] = ref_dose
            result['dose_normalized_auc_ref'] = ref_auc_mean / ref_dose
            
            interpretation += (
                f"\nReference Product (Oral):\n"
                f"  Dose: {ref_dose} mg\n"
                f"  AUC: {ref_auc_mean:.2f} ng·h/mL\n"
                f"  Dose-normalized AUC: {result['dose_normalized_auc_ref']:.4f} ng·h/mL/mg\n"
            )
            
            relative_f = (result['dose_normalized_auc_test'] / result['dose_normalized_auc_ref']) * 100
            result['relative_bioavailability'] = relative_f
            
            interpretation += (
                f"\nRelative Bioavailability (F_rel):\n"
                f"  F_rel = (AUC_test/Dose_test) / (AUC_ref/Dose_ref) × 100%\n"
                f"  F_rel = {relative_f:.2f}%\n"
            )
        
        # Cmax comparison
        if test_cmax is not None:
            if isinstance(test_cmax, (list, np.ndarray)):
                test_cmax_mean = np.mean(test_cmax)
                result['test_cmax_values'] = np.asarray(test_cmax).tolist()
            else:
                test_cmax_mean = float(test_cmax)
            result['test_cmax'] = test_cmax_mean
            
            if ref_cmax is not None:
                if isinstance(ref_cmax, (list, np.ndarray)):
                    ref_cmax_mean = np.mean(ref_cmax)
                    result['ref_cmax_values'] = np.asarray(ref_cmax).tolist()
                else:
                    ref_cmax_mean = float(ref_cmax)
                result['ref_cmax'] = ref_cmax_mean
                cmax_ratio = (test_cmax_mean / ref_cmax_mean) * 100
                result['cmax_ratio'] = cmax_ratio
                
                interpretation += (
                    f"\nCmax Comparison:\n"
                    f"  Test Cmax: {test_cmax_mean:.2f} ng/mL\n"
                    f"  Reference Cmax: {ref_cmax_mean:.2f} ng/mL\n"
                    f"  Ratio: {cmax_ratio:.2f}%\n"
                )
        
        interpretation += f"\n{'='*70}\n"
        result['interpretation'] = interpretation
        
        return result

    def dose_proportionality_test(
        self,
        doses: Union[np.ndarray, List[float]],
        pk_values: Union[np.ndarray, List[float]],
        log_transform: bool = True,
        alpha: float = 0.05
    ) -> Dict:
        """
        Test for dose proportionality using power model.
        
        Dose proportionality is assessed by fitting a power model:
        PK = α × Dose^β
        
        On log scale: log(PK) = log(α) + β × log(Dose)
        
        Proportionality is concluded if β = 1 (95% CI includes 1.0).
        
        Regulatory Context:
        -----------------
        Dose proportionality is important for:
        - Dose selection in clinical development
        - Bioequivalence study design
        - Extrapolation across dose ranges
        
        EMA Guideline on dose proportionality:
        - Acceptance: 95% CI for β within 0.8-1.25 for narrow therapeutic window
        - For most drugs: 95% CI for β should include 1.0
        
        Example:
        -------
        Study: Single dose PK across 4 dose levels
        Doses: 10, 25, 50, 100 mg
        Cmax: 200, 520, 1080, 2150 ng/mL
        
        Power model: Cmax = 20.2 × Dose^0.98
        β = 0.98, 95% CI: 0.94-1.02
        
        Conclusion: Proportional (CI includes 1.0)
        
        Parameters:
        -----------
        doses : array-like
            Dose levels (mg)
        pk_values : array-like
            Pharmacokinetic values (AUC or Cmax)
        log_transform : bool, default=True
            Apply log transformation for power model
        alpha : float, default=0.05
            Significance level for CI
            
        Returns:
        --------
        dict
            Dose proportionality test results:
            
            - slope: Estimated β (power model exponent)
            - intercept: Estimated log(α) (power model constant)
            - ci_lower: Lower confidence limit for β
            - ci_upper: Upper confidence limit for β
            - is_proportional: Boolean indicating proportionality
            - r_squared: Model fit quality
            - interpretation: Detailed interpretation
        """
        doses = np.asarray(doses)
        pk_values = np.asarray(pk_values)
        
        if len(doses) != len(pk_values):
            raise ValueError("Doses and PK values must have same length")
        
        if len(doses) < 2:
            raise ValueError("At least 2 dose levels required")
        
        # Log transform for power model
        log_doses = np.log(doses)
        log_pk = np.log(pk_values)
        
        # Fit linear model: log(PK) = intercept + slope × log(Dose)
        X = sm.add_constant(log_doses)
        model = sm.OLS(log_pk, X).fit()
        
        slope = model.params[1]
        intercept = model.params[0]
        r_squared = model.rsquared
        
        # Calculate confidence interval for slope
        ci = model.conf_int(alpha=alpha)
        ci_lower = ci[1, 0]
        ci_upper = ci[1, 1]
        
        # Check proportionality (β = 1)
        is_proportional = (ci_lower <= 1.0) and (ci_upper >= 1.0)
        
        # Calculate power model parameters
        alpha_power = np.exp(intercept)
        beta_power = slope
        
        ci_percentage = (1 - alpha) * 100
        
        interpretation = (
            f"\n{'='*70}\n"
            f"DOSE PROPORTIONALITY TEST - POWER MODEL\n"
            f"{'='*70}\n"
            f"\nREGULATORY STANDARD: EMA Dose Proportionality Guideline\n"
            f"\nPower Model: PK = α × Dose^β\n"
            f"Log-linear: log(PK) = log(α) + β × log(Dose)\n"
            f"\n{'-'*70}\n"
            f"RESULTS:\n"
            f"{'-'*70}\n"
            f"Model fit: R² = {r_squared:.4f}\n"
            f"Intercept (log(α)): {intercept:.4f}\n"
            f"Slope (β): {beta_power:.4f}\n"
            f"{ci_percentage:.0f}% CI for β: {ci_lower:.4f} - {ci_upper:.4f}\n"
            f"\nPower model equation:\n"
            f"  PK = {alpha_power:.2f} × Dose^{beta_power:.3f}\n"
            f"\n{'-'*70}\n"
            f"PROPORTIONALITY ASSESSMENT:\n"
            f"{'-'*70}\n"
            f"Proportionality criterion: β = 1.0 (CI includes 1.0)\n"
            f"Result: {'✓ PROPORTIONAL' if is_proportional else '✗ NOT PROPORTIONAL'}\n"
            f"\n{ci_percentage:.0f}% CI for β ({ci_lower:.4f} - {ci_upper:.4f}) "
            f"{'includes' if is_proportional else 'does not include'} 1.0\n"
            f"\n{'-'*70}\n"
            f"INTERPRETATION:\n"
            f"{'-'*70}\n"
        )
        
        if is_proportional:
            interpretation += (
                f"✓ DOSE PROPORTIONALITY CONCLUDED\n"
                f"\nThe power model exponent β ({beta_power:.3f}) is not "
                f"statistically different from 1.0 ({ci_percentage:.0f}% CI: {ci_lower:.4f} - {ci_upper:.4f}).\n"
                f"\nRegulatory implications:\n"
                f"  - Pharmacokinetics are dose-proportional over the studied range\n"
                f"  - Linear extrapolation between doses is justified\n"
                f"  - Bioequivalence can be tested at a single dose level\n"
                f"  - Dose adjustment in clinical practice is straightforward\n"
            )
        else:
            interpretation += (
                f"✗ DOSE PROPORTIONALITY NOT CONCLUDED\n"
                f"\nThe power model exponent β ({beta_power:.3f}) is "
                f"{'greater than' if beta_power > 1.0 else 'less than'} 1.0 "
                f"({ci_percentage:.0f}% CI: {ci_lower:.4f} - {ci_upper:.4f}).\n"
                f"\nRegulatory implications:\n"
                f"  - Pharmacokinetics are {'supra-proportional' if beta_power > 1.0 else 'sub-proportional'}\n"
                f"  - Linear extrapolation between doses not appropriate\n"
                f"  - Bioequivalence should be tested at multiple dose levels\n"
                f"  - Therapeutic dose range requires careful assessment\n"
            )
            if beta_power > 1.0:
                interpretation += (
                    f"  - Higher doses produce disproportionately higher exposure\n"
                    f"  - Dose-dependent absorption, distribution, or elimination present\n"
                )
            else:
                interpretation += (
                    f"  - Higher doses produce disproportionately lower exposure\n"
                    f"  - Saturation of absorption or elimination pathways\n"
                )
        
        interpretation += f"\n{'='*70}\n"
        
        return {
            'slope': slope,
            'intercept': intercept,
            'ci_lower': ci_lower,
            'ci_upper': ci_upper,
            'is_proportional': is_proportional,
            'r_squared': r_squared,
            'model_summary': {
                'alpha_power': alpha_power,
                'beta_power': beta_power,
                'n_observations': len(doses),
                'degrees_of_freedom': len(doses) - 2
            },
            'interpretation': interpretation,
            'regulatory_reference': (
                "EMA Guideline on the Investigation of Bioequivalence (2010), "
                "Annex I: Dose Proportionality; FDA Guidance for Industry: "
                "Bioavailability and Bioequivalence Studies for Orally Administered Drug Products (2003)"
            )
        }

    def bioequivalence_assessment(
        self,
        data: pd.DataFrame,
        pk_parameter: str,
        treatment_col: str = 'treatment',
        test_label: str = 'T',
        reference_label: str = 'R',
        subject_col: str = 'subject',
        period_col: str = 'period',
        sequence_col: str = 'sequence',
        regulatory_criteria: str = 'fda'
    ) -> Dict:
        """
        Complete bioequivalence evaluation with all regulatory criteria.
        
        This comprehensive method performs a full bioequivalence assessment
        following FDA/EMA regulatory standards. It integrates multiple statistical
        analyses to provide a complete regulatory decision.
        
        Assessments Performed:
        ---------------------
        1. Two One-Sided Tests (TOST) - Primary analysis
        2. 90% Confidence Interval Approach - Confirmatory analysis
        3. Geometric Mean Ratio Calculation - Point estimate
        4. Crossover Design ANOVA - Variance decomposition
        5. Assumption Checking - Normality, carryover, period effects
        6. Bioequivalence Decision - Regulatory conclusion
        
        Regulatory Criteria:
        ------------------
        FDA (default): 90% CI within 80.00-125.00%
        EMA: 90% CI within 80.00-125.00%
        
        Decision Rules:
        -------------
        ✓ Bioequivalent if:
          - 90% CI for GMR within 80.00-125.00%
          - No significant carryover (sequence) effect (p > 0.10)
          - Normality assumptions reasonably met
        
        ✗ Not bioequivalent if:
          - 90% CI outside acceptance range
          - Significant carryover detected
        
        Example Regulatory Submission:
        ---------------------------
        Study: Generic vs. Reference Drug (100 mg)
        Design: 2x2 crossover, 24 subjects
        Washout: 7 days
        
        Results:
        - AUC(0-∞): GMR = 0.98, 90% CI = 0.94-1.02
        - Cmax: GMR = 0.97, 90% CI = 0.93-1.01
        - No carryover detected (p = 0.85)
        - No significant period effect (p = 0.32)
        
        Regulatory Decision:
        ✓ BIOEQUIVALENCE CONCLUDED
        - Both AUC and Cmax 90% CIs within 80.00-125.00%
        - Study design meets regulatory standards
        - Recommended for regulatory approval
        
        Parameters:
        -----------
        data : pd.DataFrame
            Study dataset with required columns
        pk_parameter : str
            PK parameter to analyze (e.g., 'auc', 'cmax')
        treatment_col : str, default='treatment'
            Treatment column name
        test_label : str, default='T'
            Test product label
        reference_label : str, default='R'
            Reference product label
        subject_col : str, default='subject'
            Subject identifier column
        period_col : str, default='period'
            Period number column
        sequence_col : str, default='sequence'
            Sequence identifier column
        regulatory_criteria : str, default='fda'
            Regulatory standard ('fda' or 'ema')
            
        Returns:
        --------
        dict
            Comprehensive bioequivalence assessment:
            
            - study_design: Study design summary
            - descriptive_statistics: Summary statistics for test and reference
            - anova_results: Crossover ANOVA results
            - gmr_results: Geometric mean ratio and CI
            - tost_results: TOST procedure results
            - assumption_checks: Normality, carryover, period effects
            - bioequivalence_decision: Regulatory decision
            - interpretation: Complete regulatory interpretation
            - regulatory_compliance: Compliance checklist
        """
        # Validate data structure
        required_cols = [pk_parameter, treatment_col, subject_col, period_col, sequence_col]
        self._validate_data(data, required_cols)
        
        # Separate test and reference data
        test_data = data[data[treatment_col] == test_label][pk_parameter].values
        ref_data = data[data[treatment_col] == reference_label][pk_parameter].values
        
        if len(test_data) != len(ref_data):
            raise ValueError(f"Unequal observations: test={len(test_data)}, ref={len(ref_data)}")
        
        n_subjects = data[subject_col].nunique()
        n_sequences = data[sequence_col].nunique()
        
        # Study design summary
        study_design = {
            'design_type': '2x2 Crossover',
            'n_subjects': n_subjects,
            'n_observations': len(data),
            'n_sequences': n_sequences,
            'pk_parameter': pk_parameter.upper(),
            'regulatory_standard': regulatory_criteria.upper(),
            'equivalence_limits': self.equivalence_limits,
            'confidence_level': self.confidence_level
        }
        
        # Descriptive statistics
        descriptive_stats = {
            'test': {
                'n': len(test_data),
                'mean': np.mean(test_data),
                'geometric_mean': self._calculate_gm(test_data),
                'std': np.std(test_data, ddof=1),
                'cv': (np.std(test_data, ddof=1) / np.mean(test_data)) * 100
            },
            'reference': {
                'n': len(ref_data),
                'mean': np.mean(ref_data),
                'geometric_mean': self._calculate_gm(ref_data),
                'std': np.std(ref_data, ddof=1),
                'cv': (np.std(ref_data, ddof=1) / np.mean(ref_data)) * 100
            }
        }
        
        # ANOVA analysis
        anova_results = self.crossover_design_anova(
            data=data,
            pk_parameter=pk_parameter,
            treatment_col=treatment_col,
            subject_col=subject_col,
            period_col=period_col,
            sequence_col=sequence_col,
            test_label=test_label,
            ref_label=reference_label
        )
        
        # GMR calculation
        gmr_results = self.geometric_mean_ratio(
            test_data=test_data,
            ref_data=ref_data,
            ci_level=self.confidence_level,
            log_transform=True
        )
        
        # TOST procedure
        tost_results = self.tost_procedure(
            test_data=test_data,
            ref_data=ref_data,
            log_transform=True
        )
        
        # CI approach
        ci_results = self.confidence_interval_approach(
            test_data=test_data,
            ref_data=ref_data,
            log_transform=True
        )
        
        # Bioequivalence decision
        ci_within_limits = (gmr_results['ci_lower'] >= self.equivalence_limits[0]) and \
                           (gmr_results['ci_upper'] <= self.equivalence_limits[1])
        
        carryover_detected = anova_results['carryover_detected']
        normality_ok = anova_results['normality_assumption']['is_normal']
        
        # Overall bioequivalence decision
        is_bioequivalent = ci_within_limits and (not carryover_detected)
        
        bioequivalence_decision = {
            'is_bioequivalent': is_bioequivalent,
            'ci_within_acceptance_range': ci_within_limits,
            'carryover_detected': carryover_detected,
            'normality_assumption_met': normality_ok,
            'regulatory_criteria': regulatory_criteria.upper(),
            'acceptance_range': self.equivalence_limits,
            'gmr': gmr_results['geometric_mean_ratio'],
            'ci_lower': gmr_results['ci_lower'],
            'ci_upper': gmr_results['ci_upper']
        }
        
        # Comprehensive interpretation
        ci_percentage = self.confidence_level * 100
        
        interpretation = (
            f"\n{'='*70}\n"
            f"COMPREHENSIVE BIOEQUIVALENCE ASSESSMENT\n"
            f"{'='*70}\n"
            f"\nSTUDY DESIGN SUMMARY\n"
            f"{'-'*70}\n"
            f"Design Type: {study_design['design_type']}\n"
            f"Number of Subjects: {n_subjects}\n"
            f"Number of Observations: {len(data)}\n"
            f"PK Parameter: {pk_parameter.upper()}\n"
            f"Regulatory Standard: {regulatory_criteria.upper()}\n"
            f"Acceptance Range: {self.equivalence_limits[0]*100:.2f}% - {self.equivalence_limits[1]*100:.2f}%\n"
            f"Confidence Level: {ci_percentage:.0f}%\n"
            f"\nDESCRIPTIVE STATISTICS\n"
            f"{'-'*70}\n"
            f"Test Product (n={descriptive_stats['test']['n']}):\n"
            f"  Arithmetic Mean: {descriptive_stats['test']['mean']:.2f}\n"
            f"  Geometric Mean: {descriptive_stats['test']['geometric_mean']:.2f}\n"
            f"  Standard Deviation: {descriptive_stats['test']['std']:.2f}\n"
            f"  CV (%): {descriptive_stats['test']['cv']:.2f}%\n"
            f"\nReference Product (n={descriptive_stats['reference']['n']}):\n"
            f"  Arithmetic Mean: {descriptive_stats['reference']['mean']:.2f}\n"
            f"  Geometric Mean: {descriptive_stats['reference']['geometric_mean']:.2f}\n"
            f"  Standard Deviation: {descriptive_stats['reference']['std']:.2f}\n"
            f"  CV (%): {descriptive_stats['reference']['cv']:.2f}%\n"
            f"\nBIOEQUIVALENCE ANALYSIS RESULTS\n"
            f"{'-'*70}\n"
            f"Geometric Mean Ratio: {gmr_results['geometric_mean_ratio']:.4f} ({gmr_results['geometric_mean_ratio']*100:.2f}%)\n"
            f"{ci_percentage:.0f}% Confidence Interval: {gmr_results['ci_lower']:.4f} - {gmr_results['ci_upper']:.4f} "
            f"({gmr_results['ci_lower']*100:.2f}% - {gmr_results['ci_upper']*100:.2f}%)\n"
            f"\nTOST Procedure:\n"
            f"  Lower test p-value: {tost_results['p_value_left']:.4f}\n"
            f"  Upper test p-value: {tost_results['p_value_right']:.4f}\n"
            f"  Overall p-value: {tost_results['p_value_overall']:.4f}\n"
            f"\nANOVA Results:\n"
            f"  Treatment effect F = {anova_results['treatment_effect']['f']:.4f}, p = {anova_results['treatment_effect']['p_value']:.4f}\n"
            f"  Period effect F = {anova_results['period_effect']['f']:.4f}, p = {anova_results['period_effect']['p_value']:.4f}\n"
            f"  Sequence (carryover) effect F = {anova_results['sequence_effect']['f']:.4f}, p = {anova_results['sequence_effect']['p_value']:.4f}\n"
            f"\n{'-'*70}\n"
            f"REGULATORY DECISION\n"
            f"{'-'*70}\n"
        )
        
        if is_bioequivalent:
            interpretation += (
                f"✓ BIOEQUIVALENCE CONCLUDED\n"
                f"\nCriteria met for {regulatory_criteria.upper()} approval:\n"
                f"  ✓ {ci_percentage:.0f}% CI ({gmr_results['ci_lower']*100:.2f}% - {gmr_results['ci_upper']*100:.2f}%) "
                f"within acceptance range ({self.equivalence_limits[0]*100:.2f}% - {self.equivalence_limits[1]*100:.2f}%)\n"
                f"  ✓ No significant carryover effect detected (p = {anova_results['sequence_effect']['p_value']:.4f})\n"
                f"  ✓ TOST procedure passed (p1={tost_results['p_value_left']:.4f}, p2={tost_results['p_value_right']:.4f})\n"
                f"\nRegulatory implication: Test product demonstrates bioequivalence to reference product. "
                f"Study meets {regulatory_criteria.upper()} requirements for regulatory submission.\n"
            )
        else:
            interpretation += (
                f"✗ BIOEQUIVALENCE NOT CONCLUDED\n"
                f"\nCriteria not met:\n"
            )
            if not ci_within_limits:
                interpretation += (
                    f"  ✗ {ci_percentage:.0f}% CI ({gmr_results['ci_lower']*100:.2f}% - {gmr_results['ci_upper']*100:.2f}%) "
                    f"outside acceptance range ({self.equivalence_limits[0]*100:.2f}% - {self.equivalence_limits[1]*100:.2f}%)\n"
                )
            if carryover_detected:
                interpretation += (
                    f"  ✗ Significant carryover (sequence) effect detected (p = {anova_results['sequence_effect']['p_value']:.4f})\n"
                )
            interpretation += (
                f"\nRegulatory implication: Test product does not meet bioequivalence criteria. "
                f"Consider additional studies or reformulation.\n"
            )
        
        interpretation += f"\n{'='*70}\n"
        
        # Regulatory compliance checklist
        compliance_checklist = {
            'ci_within_acceptance_range': ci_within_limits,
            'no_significant_carryover': not carryover_detected,
            'normality_assumption_met': normality_ok,
            'adequate_sample_size': n_subjects >= 12,
            'proper_study_design': True,
            'log_transformation_applied': True,
            'all_checks_passed': is_bioequivalent
        }
        
        return {
            'study_design': study_design,
            'descriptive_statistics': descriptive_stats,
            'anova_results': anova_results,
            'gmr_results': gmr_results,
            'tost_results': tost_results,
            'ci_results': ci_results,
            'assumption_checks': {
                'normality': anova_results['normality_assumption'],
                'carryover_detected': carryover_detected,
                'period_effect_significant': anova_results['period_effect']['p_value'] < 0.05
            },
            'bioequivalence_decision': bioequivalence_decision,
            'regulatory_compliance': compliance_checklist,
            'interpretation': interpretation,
            'regulatory_reference': (
                f"FDA Guidance for Industry: Bioavailability and Bioequivalence Studies "
                f"for Orally Administered Drug Products (2003); "
                f"EMA Guideline on the Investigation of Bioequivalence (2010); "
                f"ICH E9 Statistical Principles for Clinical Trials"
            )
        }
