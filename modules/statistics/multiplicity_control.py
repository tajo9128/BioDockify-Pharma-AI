"""Multiplicity Control Module for Pharmaceutical Statistics

Provides comprehensive multiplicity correction methods for controlling
Type I error rates in clinical trial analyses.

Complies with:
- Good Laboratory Practice (GLP)
- Good Clinical Practice (GCP)
- FDA Multiplicity Adjustments in Clinical Trials Guidance (2019)
- EMA Guideline on Multiplicity Issues in Clinical Trials (2016)
- ICH E9 Statistical Principles for Clinical Trials
"""

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.stats.multitest as smm
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")


class MultiplicityControl:
    """Comprehensive multiplicity control for pharmaceutical statistics

    Provides multiple testing correction methods for:
    - Family-wise error rate (FWER) control
    - False discovery rate (FDR) control
    - Clinical trial multiplicity adjustments
    - Multiple endpoints analysis
    - Subgroup analyses
    - Interim analyses

    Methods:
        bonferroni_correction: Bonferroni correction (conservative)
        holm_bonferroni_correction: Holm step-down (more powerful)
        benjamini_hochberg_fdr: FDR control (BH procedure)
        benjamini_yekutieli_fdr: FDR under dependence
        sidak_correction: Šidák correction (independent tests)
        hochberg_correction: Hochberg step-up procedure
        hommel_correction: Hommel correction (global test)
        calculate_adjusted_pvalues: Unified p-value adjustment
        family_wise_error_rate: FWER calculation and control
        compare_correction_methods: Comparative analysis
    """

    def __init__(self, alpha: float = 0.05, independence: bool = True):
        """Initialize multiplicity control engine

        Args:
            alpha: Family-wise error rate (default: 0.05)
            independence: Assume test independence (affects method selection)
        """
        self.alpha = alpha
        self.independence = independence
        self.analysis_history = []
        self.supported_methods = [
            "bonferroni", "holm", "fdr_bh", "fdr_by",
            "sidak", "hochberg", "hommel"
        ]

    def bonferroni_correction(self, pvalues: np.ndarray,
                               test_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """Apply Bonferroni correction for multiple comparisons

        Conservative method that controls FWER at alpha/m.
        Guarantees control but reduces power with many tests.

        FDA/EMA Guidance:
        - Suitable for pre-specified primary endpoints
        - Conservative but robust for confirmatory trials
        - Recommended when number of tests is small (<10)

        Clinical Example:
            Testing 3 primary endpoints in a cardiovascular trial:
            - MACE (Major Adverse Cardiac Events)
            - All-cause mortality
            - Hospitalization for heart failure

        Args:
            pvalues: Array of p-values from hypothesis tests
            test_names: Optional list of test/hypothesis names

        Returns:
            Dictionary with original/adjusted p-values, significance, interpretation
        """
        try:
            pvalues = np.asarray(pvalues)
            n_tests = len(pvalues)

            # Validate inputs
            if n_tests == 0:
                raise ValueError("No p-values provided")
            if np.any(pvalues < 0) or np.any(pvalues > 1):
                raise ValueError("P-values must be between 0 and 1")

            # Apply Bonferroni correction
            adjusted_p = np.minimum(pvalues * n_tests, 1.0)
            significant = adjusted_p < self.alpha

            # Generate test names if not provided
            if test_names is None:
                test_names = [f"Test {i+1}" for i in range(n_tests)]

            # Build results
            results = {
                "method": "Bonferroni Correction",
                "original_pvalues": pvalues.tolist(),
                "adjusted_pvalues": adjusted_p.tolist(),
                "significant": significant.tolist(),
                "test_names": test_names,
                "n_tests": n_tests,
                "alpha": self.alpha,
                "power_vs_control": {
                    "description": "Conservative method with low power",
                    "tradeoff": "Strong FWER control but reduced statistical power",
                    "best_for": "Small number of pre-specified tests"
                },
                "interpretation": self._interpret_bonferroni(adjusted_p, significant),
                "clinical_guidance": self._bonferroni_clinical_guidance(n_tests),
                "assumptions": {
                    "independence": "Not required",
                    "FWER_control": "Exact",
                    "monotonicity": "Maintained"
                },
                "timestamp": datetime.now().isoformat()
            }

            self.analysis_history.append({
                "method": "bonferroni",
                "n_tests": n_tests,
                "n_significant": int(np.sum(significant)),
                "timestamp": datetime.now().isoformat()
            })

            return results

        except Exception as e:
            raise ValueError(f"Bonferroni correction failed: {str(e)}")

    def holm_bonferroni_correction(self, pvalues: np.ndarray,
                                    test_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """Apply Holm-Bonferroni step-down procedure

        More powerful than Bonferroni while maintaining FWER control.
        Uses sequential testing with adjusted significance levels.

        FDA/EMA Guidance:
        - Preferred over Bonferroni for multiple comparisons
        - Suitable for ordered or pre-specified hypotheses
        - Maintains strong FWER control

        Clinical Example:
            Testing efficacy across multiple dose levels:
            - Low dose vs placebo
            - Medium dose vs placebo
            - High dose vs placebo
            - Trend test

        Algorithm:
            1. Sort p-values: p(1) <= p(2) <= ... <= p(m)
            2. Compare p(i) to alpha/(m-i+1)
            3. Reject smallest significant p-value and all smaller
            4. Stop at first non-significant result

        Args:
            pvalues: Array of p-values from hypothesis tests
            test_names: Optional list of test/hypothesis names

        Returns:
            Dictionary with detailed results and interpretation
        """
        try:
            pvalues = np.asarray(pvalues)
            n_tests = len(pvalues)

            if n_tests == 0:
                raise ValueError("No p-values provided")
            if np.any(pvalues < 0) or np.any(pvalues > 1):
                raise ValueError("P-values must be between 0 and 1")

            # Apply Holm step-down procedure
            _, adjusted_p, _, _ = smm.multipletests(
                pvalues, alpha=self.alpha, method='holm'
            )
            significant = adjusted_p < self.alpha

            if test_names is None:
                test_names = [f"Test {i+1}" for i in range(n_tests)]

            results = {
                "method": "Holm-Bonferroni Step-Down",
                "original_pvalues": pvalues.tolist(),
                "adjusted_pvalues": adjusted_p.tolist(),
                "significant": significant.tolist(),
                "test_names": test_names,
                "n_tests": n_tests,
                "alpha": self.alpha,
                "power_vs_control": {
                    "description": "More powerful than Bonferroni",
                    "advantage": "Step-down procedure increases power",
                    "complexity": "Requires sorting p-values"
                },
                "interpretation": self._interpret_holm(adjusted_p, significant, n_tests),
                "clinical_guidance": self._holm_clinical_guidance(),
                "algorithm": self._explain_holm_algorithm(),
                "assumptions": {
                    "independence": "Not required",
                    "FWER_control": "Exact",
                    "ordering": "P-values sorted ascending"
                },
                "timestamp": datetime.now().isoformat()
            }

            self.analysis_history.append({
                "method": "holm",
                "n_tests": n_tests,
                "n_significant": int(np.sum(significant)),
                "timestamp": datetime.now().isoformat()
            })

            return results

        except Exception as e:
            raise ValueError(f"Holm-Bonferroni correction failed: {str(e)}")

    def benjamini_hochberg_fdr(self, pvalues: np.ndarray,
                                test_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """Apply Benjamini-Hochberg False Discovery Rate control

        Controls the expected proportion of false discoveries (FDR).
        Less conservative than FWER methods, increases power.

        FDA/EMA Guidance:
        - Suitable for exploratory analyses and biomarker discovery
        - Not recommended for primary confirmatory endpoints
        - Appropriate for large-scale testing (e.g., genomics)

        Clinical Example:
            Screening hundreds of biomarkers for drug response:
            - Gene expression profiles
            - Protein biomarkers
            - Predictive signatures

        Algorithm:
            1. Sort p-values: p_(1) <= p_(2) <= ... <= p_(m)
            2. Find largest k such that p_(k) <= (k/m) * q
            3. Reject hypotheses 1, 2, ..., k
            4. Accept hypotheses k+1, ..., m

        Args:
            pvalues: Array of p-values from hypothesis tests
            test_names: Optional list of test/hypothesis names

        Returns:
            Dictionary with FDR-controlled results and interpretation
        """
        try:
            pvalues = np.asarray(pvalues)
            n_tests = len(pvalues)

            if n_tests == 0:
                raise ValueError("No p-values provided")
            if np.any(pvalues < 0) or np.any(pvalues > 1):
                raise ValueError("P-values must be between 0 and 1")

            # Apply BH procedure
            _, adjusted_p, _, _ = smm.multipletests(
                pvalues, alpha=self.alpha, method='fdr_bh'
            )
            significant = adjusted_p < self.alpha

            if test_names is None:
                test_names = [f"Test {i+1}" for i in range(n_tests)]

            # Calculate actual FDR
            n_rejected = np.sum(significant)
            fdr_estimate = np.mean(adjusted_p[significant]) if n_rejected > 0 else 0

            results = {
                "method": "Benjamini-Hochberg FDR",
                "original_pvalues": pvalues.tolist(),
                "adjusted_pvalues": adjusted_p.tolist(),
                "significant": significant.tolist(),
                "test_names": test_names,
                "n_tests": n_tests,
                "n_rejected": int(n_rejected),
                "estimated_fdr": float(fdr_estimate),
                "q_level": self.alpha,
                "power_vs_control": {
                    "description": "Higher power than FWER methods",
                    "tradeoff": "Controls FDR, not FWER",
                    "best_for": "Exploratory analyses, biomarker screening"
                },
                "interpretation": self._interpret_bh_fdr(adjusted_p, significant, n_tests, n_rejected),
                "clinical_guidance": self._bh_fdr_clinical_guidance(),
                "algorithm": self._explain_bh_algorithm(),
                "assumptions": {
                    "independence": "Assumed (positive dependency OK)",
                    "FDR_control": "Valid under independence",
                    "monotonicity": "Maintained"
                },
                "timestamp": datetime.now().isoformat()
            }

            self.analysis_history.append({
                "method": "bh_fdr",
                "n_tests": n_tests,
                "n_significant": int(n_rejected),
                "estimated_fdr": float(fdr_estimate),
                "timestamp": datetime.now().isoformat()
            })

            return results

        except Exception as e:
            raise ValueError(f"Benjamini-Hochberg FDR failed: {str(e)}")

    def benjamini_yekutieli_fdr(self, pvalues: np.ndarray,
                                 test_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """Apply Benjamini-Yekutieli FDR control under dependence

        Conservative FDR control that works under arbitrary dependence.
        More powerful than Bonferroni, less powerful than BH.

        FDA/EMA Guidance:
            - Use when test dependence is suspected
            - Applicable for correlated measurements
            - Conservative but robust

        Clinical Example:
            Testing correlated clinical lab parameters:
            - Multiple cardiac enzymes
            - Inflammatory markers
            - Metabolic panels

        Args:
            pvalues: Array of p-values from hypothesis tests
            test_names: Optional list of test/hypothesis names

        Returns:
            Dictionary with BY FDR-controlled results
        """
        try:
            pvalues = np.asarray(pvalues)
            n_tests = len(pvalues)

            if n_tests == 0:
                raise ValueError("No p-values provided")
            if np.any(pvalues < 0) or np.any(pvalues > 1):
                raise ValueError("P-values must be between 0 and 1")

            # Apply BY procedure
            _, adjusted_p, _, _ = smm.multipletests(
                pvalues, alpha=self.alpha, method='fdr_by'
            )
            significant = adjusted_p < self.alpha

            if test_names is None:
                test_names = [f"Test {i+1}" for i in range(n_tests)]

            # Calculate harmonic series correction factor
            harmonic_m = sum(1.0 / (i + 1) for i in range(n_tests))

            n_rejected = np.sum(significant)
            fdr_estimate = np.mean(adjusted_p[significant]) if n_rejected > 0 else 0

            results = {
                "method": "Benjamini-Yekutieli FDR (Dependence)",
                "original_pvalues": pvalues.tolist(),
                "adjusted_pvalues": adjusted_p.tolist(),
                "significant": significant.tolist(),
                "test_names": test_names,
                "n_tests": n_tests,
                "n_rejected": int(n_rejected),
                "estimated_fdr": float(fdr_estimate),
                "harmonic_correction": float(harmonic_m),
                "q_level": self.alpha,
                "power_vs_control": {
                    "description": "Conservative FDR for dependent tests",
                    "tradeoff": "More conservative than BH, handles dependence",
                    "best_for": "Correlated tests, unknown dependency structure"
                },
                "interpretation": self._interpret_by_fdr(adjusted_p, significant, n_tests, n_rejected, harmonic_m),
                "clinical_guidance": self._by_fdr_clinical_guidance(),
                "assumptions": {
                    "independence": "Not required",
                    "FDR_control": "Valid under arbitrary dependence",
                    "conservativeness": "More conservative than BH"
                },
                "timestamp": datetime.now().isoformat()
            }

            self.analysis_history.append({
                "method": "by_fdr",
                "n_tests": n_tests,
                "n_significant": int(n_rejected),
                "estimated_fdr": float(fdr_estimate),
                "timestamp": datetime.now().isoformat()
            })

            return results

        except Exception as e:
            raise ValueError(f"Benjamini-Yekutieli FDR failed: {str(e)}")

    def sidak_correction(self, pvalues: np.ndarray,
                          test_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """Apply Šidák correction for independent tests

        Slightly more powerful than Bonferroni for independent tests.
        Uses the formula: alpha_adj = 1 - (1 - alpha)^(1/m)

        FDA/EMA Guidance:
            - Requires independent tests (orthogonal)
            - More powerful than Bonferroni for independent hypotheses
            - Slight power gain diminishes with many tests

        Clinical Example:
            Testing independent clinical endpoints:
            - Blood pressure (systolic)
            - Blood pressure (diastolic)
            - Heart rate
            - All measured independently

        Args:
            pvalues: Array of p-values from hypothesis tests
            test_names: Optional list of test/hypothesis names

        Returns:
            Dictionary with Šidák-adjusted results
        """
        try:
            pvalues = np.asarray(pvalues)
            n_tests = len(pvalues)

            if n_tests == 0:
                raise ValueError("No p-values provided")
            if np.any(pvalues < 0) or np.any(pvalues > 1):
                raise ValueError("P-values must be between 0 and 1")

            # Apply Šidák correction
            sidak_alpha = 1 - (1 - self.alpha) ** (1 / n_tests)
            adjusted_p = 1 - (1 - pvalues) ** n_tests
            adjusted_p = np.minimum(adjusted_p, 1.0)
            significant = pvalues < sidak_alpha

            if test_names is None:
                test_names = [f"Test {i+1}" for i in range(n_tests)]

            # Calculate power improvement vs Bonferroni
            bonferroni_alpha = self.alpha / n_tests
            power_gain_pct = ((sidak_alpha - bonferroni_alpha) / bonferroni_alpha * 100) if bonferroni_alpha > 0 else 0

            results = {
                "method": "Šidák Correction",
                "original_pvalues": pvalues.tolist(),
                "adjusted_pvalues": adjusted_p.tolist(),
                "significant": significant.tolist(),
                "test_names": test_names,
                "n_tests": n_tests,
                "alpha": self.alpha,
                "sidak_alpha": float(sidak_alpha),
                "bonferroni_alpha": float(bonferroni_alpha),
                "power_improvement": f"{power_gain_pct:.2f}%",
                "power_vs_control": {
                    "description": "More powerful than Bonferroni",
                    "advantage": "Uses joint probability formula",
                    "requirement": "Requires independent tests"
                },
                "interpretation": self._interpret_sidak(adjusted_p, significant, n_tests, sidak_alpha, power_gain_pct),
                "clinical_guidance": self._sidak_clinical_guidance(),
                "assumptions": {
                    "independence": "Required (strict)",
                    "FWER_control": "Exact under independence",
                    "orthogonality": "Tests must be independent"
                },
                "timestamp": datetime.now().isoformat()
            }

            self.analysis_history.append({
                "method": "sidak",
                "n_tests": n_tests,
                "n_significant": int(np.sum(significant)),
                "timestamp": datetime.now().isoformat()
            })

            return results

        except Exception as e:
            raise ValueError(f"Šidák correction failed: {str(e)}")

    def hochberg_correction(self, pvalues: np.ndarray,
                            test_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """Apply Hochberg step-up procedure

        More powerful than Holm under independence.
        Uses step-up approach starting from largest p-value.

        FDA/EMA Guidance:
            - Step-up procedure increases power
            - Assumes test independence
            - Suitable for multiple ordered comparisons

        Clinical Example:
            Testing multiple dose levels vs placebo:
            - Dose 1 vs placebo
            - Dose 2 vs placebo
            - Dose 3 vs placebo
            - Tests ordered by dose

        Algorithm:
            1. Sort p-values: p_(1) <= p_(2) <= ... <= p_(m)
            2. Find largest k such that p_(k) <= alpha/(m-k+1)
            3. Reject all hypotheses with p-values <= p_(k)
            4. Step-up procedure, more powerful than Holm under independence

        Args:
            pvalues: Array of p-values from hypothesis tests
            test_names: Optional list of test/hypothesis names

        Returns:
            Dictionary with Hochberg-adjusted results
        """
        try:
            pvalues = np.asarray(pvalues).copy()
            n_tests = len(pvalues)

            if n_tests == 0:
                raise ValueError("No p-values provided")
            if np.any(pvalues < 0) or np.any(pvalues > 1):
                raise ValueError("P-values must be between 0 and 1")

            # Get original indices
            original_indices = np.arange(n_tests)

            # Sort p-values and keep track of original order
            sorted_indices = np.argsort(pvalues)
            sorted_p = pvalues[sorted_indices]

            # Hochberg step-up procedure
            # Find largest k such that p_(k) <= alpha/(m-k+1)
            reject_mask = np.zeros(n_tests, dtype=bool)

            # Check from largest to smallest p-value (step-up)
            for k in range(n_tests, 0, -1):
                threshold = self.alpha / (n_tests - k + 1)
                if sorted_p[k-1] <= threshold:
                    # Reject all hypotheses with p <= p_(k)
                    reject_mask[:k] = True
                    break

            # Create adjusted p-values
            adjusted_p = np.zeros(n_tests)
            for i in range(n_tests):
                adjusted_p[i] = min(sorted_p[i] * (n_tests - i), 1.0)

            # If any test was rejected, set its adjusted p-value appropriately
            if reject_mask.any():
                # Find the cutoff index
                cutoff_idx = np.where(reject_mask)[0].max()
                for i in range(cutoff_idx + 1):
                    adjusted_p[i] = min(sorted_p[i] * (n_tests - i), 1.0)

            # Sort adjusted p-values back to original order
            adjusted_p_sorted = np.zeros(n_tests)
            for i, idx in enumerate(sorted_indices):
                adjusted_p_sorted[idx] = adjusted_p[i]
            adjusted_p = adjusted_p_sorted

            # Determine significance
            significant = reject_mask.copy()

            # Sort significance back to original order
            significant_sorted = np.zeros(n_tests, dtype=bool)
            for i, idx in enumerate(sorted_indices):
                significant_sorted[idx] = significant[i]
            significant = significant_sorted

            if test_names is None:
                test_names = [f"Test {i+1}" for i in range(n_tests)]

            results = {
                "method": "Hochberg Step-Up",
                "original_pvalues": pvalues.tolist(),
                "adjusted_pvalues": adjusted_p.tolist(),
                "significant": significant.tolist(),
                "test_names": test_names,
                "n_tests": n_tests,
                "alpha": self.alpha,
                "power_vs_control": {
                    "description": "More powerful than Holm under independence",
                    "advantage": "Step-up procedure",
                    "complexity": "Requires sorted p-values"
                },
                "interpretation": self._interpret_hochberg(adjusted_p, significant, n_tests),
                "clinical_guidance": self._hochberg_clinical_guidance(),
                "algorithm": self._explain_hochberg_algorithm(),
                "assumptions": {
                    "independence": "Assumed for optimal performance",
                    "FWER_control": "Exact under independence",
                    "ordering": "P-values sorted ascending"
                },
                "timestamp": datetime.now().isoformat()
            }

            self.analysis_history.append({
                "method": "hochberg",
                "n_tests": n_tests,
                "n_significant": int(np.sum(significant)),
                "timestamp": datetime.now().isoformat()
            })

            return results

        except Exception as e:
            raise ValueError(f"Hochberg correction failed: {str(e)}")

    def hommel_correction(self, pvalues: np.ndarray,
                           test_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """Apply Hommel correction (global test)

        More powerful than Bonferroni, especially for many tests.
        Uses closed testing procedure to find maximum rejected set.

        FDA/EMA Guidance:
            - More powerful than Bonferroni for confirmatory trials
            - Suitable for primary endpoints and key secondary endpoints
            - Maintains strong FWER control

        Clinical Example:
            Testing multiple clinical endpoints in diabetes trial:
            - HbA1c reduction
            - Fasting plasma glucose
            - Postprandial glucose
            - Body weight change
            - Blood pressure

        Args:
            pvalues: Array of p-values from hypothesis tests
            test_names: Optional list of test/hypothesis names

        Returns:
            Dictionary with Hommel-adjusted results
        """
        try:
            pvalues = np.asarray(pvalues)
            n_tests = len(pvalues)

            if n_tests == 0:
                raise ValueError("No p-values provided")
            if np.any(pvalues < 0) or np.any(pvalues > 1):
                raise ValueError("P-values must be between 0 and 1")

            # Apply Hommel correction
            _, adjusted_p, _, _ = smm.multipletests(
                pvalues, alpha=self.alpha, method='hommel'
            )
            significant = adjusted_p < self.alpha

            if test_names is None:
                test_names = [f"Test {i+1}" for i in range(n_tests)]

            results = {
                "method": "Hommel Correction",
                "original_pvalues": pvalues.tolist(),
                "adjusted_pvalues": adjusted_p.tolist(),
                "significant": significant.tolist(),
                "test_names": test_names,
                "n_tests": n_tests,
                "alpha": self.alpha,
                "power_vs_control": {
                    "description": "More powerful than Bonferroni",
                    "advantage": "Closed testing procedure",
                    "complexity": "Computationally intensive for many tests"
                },
                "interpretation": self._interpret_hommel(adjusted_p, significant, n_tests),
                "clinical_guidance": self._hommel_clinical_guidance(),
                "assumptions": {
                    "independence": "Not required",
                    "FWER_control": "Exact",
                    "computational": "May be slow for >100 tests"
                },
                "timestamp": datetime.now().isoformat()
            }

            self.analysis_history.append({
                "method": "hommel",
                "n_tests": n_tests,
                "n_significant": int(np.sum(significant)),
                "timestamp": datetime.now().isoformat()
            })

            return results

        except Exception as e:
            raise ValueError(f"Hommel correction failed: {str(e)}")

    def calculate_adjusted_pvalues(self, pvalues: np.ndarray,
                                      method: str = 'holm',
                                      test_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """Calculate adjusted p-values using specified method

        Unified interface for all multiplicity correction methods.
        Returns comprehensive results with interpretation.

        FDA/EMA Guidance:
            - Method selection should be pre-specified in SAP
            - Consider endpoint hierarchy and importance
            - Document rationale for method choice

        Clinical Example:
            Analyzing multiple secondary endpoints:
            - Quality of life measures
            - Functional status scales
            - Patient-reported outcomes

        Args:
            pvalues: Array of p-values from hypothesis tests
            method: Correction method ('bonferroni', 'holm', 'fdr_bh',
                   'fdr_by', 'sidak', 'hochberg', 'hommel')
            test_names: Optional list of test/hypothesis names

        Returns:
            Dictionary with adjusted p-values and comprehensive analysis
        """
        try:
            if method not in self.supported_methods:
                raise ValueError(f"Unsupported method: {method}. "
                               f"Supported: {self.supported_methods}")

            # Route to appropriate method
            method_map = {
                'bonferroni': self.bonferroni_correction,
                'holm': self.holm_bonferroni_correction,
                'fdr_bh': self.benjamini_hochberg_fdr,
                'fdr_by': self.benjamini_yekutieli_fdr,
                'sidak': self.sidak_correction,
                'hochberg': self.hochberg_correction,
                'hommel': self.hommel_correction
            }

            results = method_map[method](pvalues, test_names)

            # Add method comparison info
            results['method_selection'] = {
                'selected_method': method,
                'alternatives': [m for m in self.supported_methods if m != method],
                'selection_rationale': self._method_selection_rationale(method)
            }

            return results

        except Exception as e:
            raise ValueError(f"Adjusted p-value calculation failed: {str(e)}")

    def family_wise_error_rate(self, pvalues: np.ndarray,
                                  method: str = 'holm',
                                  test_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """Calculate and control Family-Wise Error Rate (FWER)

        FWER is the probability of making at least one Type I error
        (false positive) among all hypotheses tested.

        FDA/EMA Guidance:
            - Primary endpoints require FWER control
            - Strong control preferred for confirmatory trials
            - Bonferroni, Holm, Hommel, Šidák provide FWER control

        Clinical Example:
            Testing multiple primary endpoints in confirmatory trial:
            - Overall survival
            - Progression-free survival
            - Response rate

        Args:
            pvalues: Array of p-values from hypothesis tests
            method: FWER control method ('bonferroni', 'holm',
                   'sidak', 'hochberg', 'hommel')
            test_names: Optional list of test/hypothesis names

        Returns:
            Dictionary with FWER analysis and controlled results
        """
        try:
            pvalues = np.asarray(pvalues)
            n_tests = len(pvalues)

            # Validate method (FWER methods only)
            fwer_methods = ['bonferroni', 'holm', 'sidak', 'hochberg', 'hommel']
            if method not in fwer_methods:
                raise ValueError(f"Method {method} does not control FWER. "
                               f"Use: {fwer_methods}")

            # Calculate FWER at different correction levels
            uncorrected_rejections = np.sum(pvalues < self.alpha)

            # Apply correction
            results = self.calculate_adjusted_pvalues(pvalues, method, test_names)
            corrected_rejections = np.sum(results['significant'])

            # Estimate FWER without correction (Bonferroni inequality)
            fwer_uncorrected = 1 - (1 - self.alpha) ** n_tests

            results['fwer_analysis'] = {
                'n_tests': n_tests,
                'alpha': self.alpha,
                'uncorrected_rejections': int(uncorrected_rejections),
                'corrected_rejections': int(corrected_rejections),
                'fwer_uncorrected_estimate': float(fwer_uncorrected),
                'fwer_control': "Strong" if method in fwer_methods else "Not controlled",
                'control_level': float(self.alpha)
            }

            results['fwer_interpretation'] = self._interpret_fwer(
                uncorrected_rejections,
                corrected_rejections,
                fwer_uncorrected,
                method
            )

            return results

        except Exception as e:
            raise ValueError(f"FWER calculation failed: {str(e)}")

    def compare_correction_methods(self, pvalues: np.ndarray,
                                      test_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """Compare different multiplicity correction methods

        Runs all supported methods and provides comparative analysis
        of adjusted p-values, significance, and power.

        FDA/EMA Guidance:
            - Compare methods during analysis planning
            - Select method balancing FWER control and power
            - Document method selection rationale in SAP

        Clinical Example:
            Comparing methods for multiple endpoints:
            - Primary endpoint: Survival
            - Secondary endpoints: Quality of life, response rate
            - Exploratory endpoints: Biomarkers

        Args:
            pvalues: Array of p-values from hypothesis tests
            test_names: Optional list of test/hypothesis names

        Returns:
            Dictionary with comparative analysis across all methods
        """
        try:
            pvalues = np.asarray(pvalues)
            n_tests = len(pvalues)

            if test_names is None:
                test_names = [f"Test {i+1}" for i in range(n_tests)]

            # Run all methods
            methods = self.supported_methods
            comparison_results = {}

            for method in methods:
                try:
                    result = self.calculate_adjusted_pvalues(pvalues, method, test_names)
                    comparison_results[method] = {
                        'adjusted_pvalues': result['adjusted_pvalues'],
                        'significant': result['significant'],
                        'n_significant': sum(result['significant']),
                        'method': result['method']
                    }
                except Exception as e:
                    comparison_results[method] = {
                        'error': str(e),
                        'n_significant': 0
                    }

            # Build comparison table
            comparison_df = pd.DataFrame({
                'Test': test_names,
                'Original_p': pvalues.tolist(),
                **{f'{method}_adj': comparison_results[method].get('adjusted_pvalues', [None]*n_tests)
                   for method in methods}
            })

            # Count significant tests per method
            significance_counts = {
                method: comparison_results[method].get('n_significant', 0)
                for method in methods
            }

            # Determine power ranking
            power_ranking = sorted(
                significance_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )

            # Generate recommendations
            recommendations = self._generate_method_recommendations(
                pvalues,
                significance_counts,
                power_ranking
            )

            results = {
                "comparison_summary": {
                    "n_tests": n_tests,
                    "methods_compared": methods,
                    "alpha": self.alpha,
                    "power_ranking": power_ranking,
                    "significance_counts": significance_counts
                },
                "method_results": comparison_results,
                "comparison_table": comparison_df.to_dict('records'),
                "recommendations": recommendations,
                "interpretation": self._interpret_comparison(
                    power_ranking,
                    significance_counts,
                    n_tests
                ),
                "clinical_guidance": self._comparison_clinical_guidance(),
                "timestamp": datetime.now().isoformat()
            }

            return results

        except Exception as e:
            raise ValueError(f"Method comparison failed: {str(e)}")

    # ==================== HELPER METHODS ====================

    def _interpret_bonferroni(self, adjusted_p: np.ndarray,
                                significant: np.ndarray) -> List[str]:
        """Generate Bonferroni interpretation"""
        n_tests = len(adjusted_p)
        n_sig = np.sum(significant)
        bonf_alpha = self.alpha / n_tests

        interpretation = [
            f"Bonferroni correction applied to {n_tests} tests",
            f"Adjusted significance level: {bonf_alpha:.6f} (alpha/{n_tests})",
            f"Tests significant after correction: {n_sig} of {n_tests}",
            "",
            "Interpretation:",
            "- Very conservative method with strong FWER control",
            "- Guarantees FWER <= alpha for any number of tests",
            "- Statistical power decreases with more tests",
            "- Suitable for confirmatory trials with few tests"
        ]

        if n_sig == 0:
            interpretation.extend([
                "",
                "No tests remain significant after Bonferroni correction",
                "Consider: Fewer tests, higher alpha, or more powerful method"
            ])

        return interpretation

    def _bonferroni_clinical_guidance(self, n_tests: int) -> Dict[str, str]:
        """Provide Bonferroni clinical guidance"""
        if n_tests <= 3:
            power_level = "Good power for small number of tests"
            recommendation = "Suitable for primary endpoint analyses"
        elif n_tests <= 10:
            power_level = "Moderate power loss acceptable"
            recommendation = "Consider for confirmatory secondary endpoints"
        else:
            power_level = "Severe power loss likely"
            recommendation = "Consider FDR methods or hierarchical testing"

        return {
            "power_assessment": power_level,
            "recommendation": recommendation,
            "regulatory_acceptance": "Widely accepted by FDA/EMA for confirmatory trials",
            "documentation": "Document pre-specification in statistical analysis plan"
        }

    def _interpret_holm(self, adjusted_p: np.ndarray,
                        significant: np.ndarray,
                        n_tests: int) -> List[str]:
        """Generate Holm-Bonferroni interpretation"""
        n_sig = np.sum(significant)

        interpretation = [
            f"Holm-Bonferroni step-down applied to {n_tests} tests",
            f"Tests significant after correction: {n_sig} of {n_tests}",
            "",
            "Interpretation:",
            "- Step-down procedure more powerful than Bonferroni",
            "- Rejects hypotheses sequentially from smallest p-value",
            "- Maintains strong FWER control",
            "- Good balance between control and power"
        ]

        if n_sig > 0:
            interpretation.extend([
                "",
                f"Holm correction identified {n_sig} significant tests",
                "Preferable to Bonferroni for multiple comparisons"
            ])

        return interpretation

    def _holm_clinical_guidance(self) -> Dict[str, str]:
        """Provide Holm clinical guidance"""
        return {
            "power_assessment": "Higher power than Bonferroni",
            "recommendation": "Preferred for multiple comparisons",
            "regulatory_acceptance": "Accepted by FDA/EMA for confirmatory trials",
            "best_use": "Multiple primary/secondary endpoints"
        }

    def _interpret_bh_fdr(self, adjusted_p: np.ndarray,
                           significant: np.ndarray,
                           n_tests: int,
                           n_rejected: int) -> List[str]:
        """Generate BH FDR interpretation"""
        interpretation = [
            f"Benjamini-Hochberg FDR control applied to {n_tests} tests",
            f"Tests rejected (FDR-controlled): {n_rejected} of {n_tests}",
            f"FDR control level: {self.alpha}",
            "",
            "Interpretation:",
            "- Controls expected proportion of false discoveries",
            "- Less conservative than FWER methods",
            "- Higher power for exploratory analyses",
            "- Not for primary confirmatory endpoints"
        ]

        if n_rejected > 0:
            avg_fdr = np.mean(adjusted_p[significant])
            interpretation.extend([
                "",
                f"Average FDR among rejected: {avg_fdr:.4f}",
                f"Expected false discoveries: {avg_fdr * n_rejected:.2f} of {n_rejected}"
            ])

        return interpretation

    def _bh_fdr_clinical_guidance(self) -> Dict[str, str]:
        """Provide BH FDR clinical guidance"""
        return {
            "power_assessment": "High power for large-scale testing",
            "recommendation": "Exploratory analyses, biomarker screening",
            "regulatory_acceptance": "Accepted for exploratory endpoints",
            "not_recommended": "Primary confirmatory endpoints (use FWER methods)"
        }

    def _interpret_by_fdr(self, adjusted_p: np.ndarray,
                           significant: np.ndarray,
                           n_tests: int,
                           n_rejected: int,
                           harmonic_m: float) -> List[str]:
        """Generate BY FDR interpretation"""
        interpretation = [
            f"Benjamini-Yekutieli FDR control applied to {n_tests} tests",
            f"Tests rejected (FDR-controlled): {n_rejected} of {n_tests}",
            f"Harmonic correction factor: {harmonic_m:.4f}",
            "",
            "Interpretation:",
            "- Conservative FDR control under dependence",
            "- Works for arbitrary test correlations",
            "- More conservative than BH method",
            "- Suitable for correlated measurements"
        ]

        if harmonic_m > 5:
            interpretation.extend([
                "",
                f"Note: Large harmonic factor ({harmonic_m:.2f}) indicates strong conservatism",
                "Consider test independence assumption or use FWER methods"
            ])

        return interpretation

    def _by_fdr_clinical_guidance(self) -> Dict[str, str]:
        """Provide BY FDR clinical guidance"""
        return {
            "power_assessment": "Conservative FDR control for dependent tests",
            "recommendation": "When test independence is questionable",
            "regulatory_acceptance": "Accepted for exploratory analyses",
            "best_use": "Correlated measurements, complex dependency structures"
        }

    def _interpret_sidak(self, adjusted_p: np.ndarray,
                           significant: np.ndarray,
                           n_tests: int,
                           sidak_alpha: float,
                           power_gain_pct: float) -> List[str]:
        """Generate Šidák interpretation"""
        n_sig = np.sum(significant)
        bonf_alpha = self.alpha / n_tests

        interpretation = [
            f"Šidák correction applied to {n_tests} independent tests",
            f"Adjusted significance level: {sidak_alpha:.6f}",
            f"Bonferroni would use: {bonf_alpha:.6f}",
            f"Power improvement: {power_gain_pct:.2f}%",
            f"Tests significant after correction: {n_sig} of {n_tests}",
            "",
            "Interpretation:",
            "- Slightly more powerful than Bonferroni for independent tests",
            "- Uses joint probability formula: 1 - (1-alpha)^(1/m)",
            "- Requires independent (orthogonal) tests",
            "- Exact FWER control under independence"
        ]

        if not self.independence:
            interpretation.extend([
                "",
                "WARNING: Tests may not be independent",
                "Šidák may not provide proper FWER control",
                "Consider Holm or Bonferroni instead"
            ])

        return interpretation

    def _sidak_clinical_guidance(self) -> Dict[str, str]:
        """Provide Šidák clinical guidance"""
        return {
            "power_assessment": "Slightly higher power than Bonferroni",
            "recommendation": "Use when tests are truly independent",
            "regulatory_acceptance": "Accepted by FDA/EMA for independent tests",
            "caution": "Verify independence assumption"
        }

    def _interpret_hochberg(self, adjusted_p: np.ndarray,
                             significant: np.ndarray,
                             n_tests: int) -> List[str]:
        """Generate Hochberg interpretation"""
        n_sig = np.sum(significant)

        interpretation = [
            f"Hochberg step-up procedure applied to {n_tests} tests",
            f"Tests significant after correction: {n_sig} of {n_tests}",
            "",
            "Interpretation:",
            "- Step-up procedure more powerful than Holm under independence",
            "- Starts from largest p-value and moves down",
            "- Maintains strong FWER control",
            "- Good for ordered hypotheses"
        ]

        if n_sig > 0:
            interpretation.extend([
                "",
                f"Hochberg identified {n_sig} significant tests",
                "Power advantage over Holm likely achieved"
            ])

        return interpretation

    def _hochberg_clinical_guidance(self) -> Dict[str, str]:
        """Provide Hochberg clinical guidance"""
        return {
            "power_assessment": "Higher power than Holm under independence",
            "recommendation": "Preferred over Holm for independent tests",
            "regulatory_acceptance": "Accepted by FDA/EMA",
            "best_use": "Multiple comparisons with independent tests"
        }

    def _interpret_hommel(self, adjusted_p: np.ndarray,
                           significant: np.ndarray,
                           n_tests: int) -> List[str]:
        """Generate Hommel interpretation"""
        n_sig = np.sum(significant)

        interpretation = [
            f"Hommel correction applied to {n_tests} tests",
            f"Tests significant after correction: {n_sig} of {n_tests}",
            "",
            "Interpretation:",
            "- More powerful than Bonferroni for many tests",
            "- Uses closed testing procedure",
            "- Maintains strong FWER control",
            "- Computationally intensive for >100 tests"
        ]

        if n_tests > 50:
            interpretation.extend([
                "",
                f"Note: Large number of tests ({n_tests})",
                "Consider Holm for faster computation"
            ])

        return interpretation

    def _hommel_clinical_guidance(self) -> Dict[str, str]:
        """Provide Hommel clinical guidance"""
        return {
            "power_assessment": "Higher power than Bonferroni, especially for many tests",
            "recommendation": "Preferred for multiple primary endpoints",
            "regulatory_acceptance": "Accepted by FDA/EMA",
            "best_use": "Confirmatory trials with multiple endpoints"
        }

    def _interpret_fwer(self, uncorrected_rejections: int,
                           corrected_rejections: int,
                           fwer_uncorrected: float,
                           method: str) -> List[str]:
        """Generate FWER interpretation"""
        interpretation = [
            f"Family-Wise Error Rate analysis using {method}",
            f"Uncorrected significant tests: {uncorrected_rejections}",
            f"FWER-controlled significant tests: {corrected_rejections}",
            f"Estimated FWER without correction: {fwer_uncorrected:.4f}",
            f"Target FWER (alpha): {self.alpha}",
            "",
            "Interpretation:",
            f"- Without correction, FWER would be ~{fwer_uncorrected:.1%}",
            "- FWER is the probability of at least one false positive",
            f"- {method} correction ensures FWER <= {self.alpha}",
            "- Strong control for all hypotheses tested"
        ]

        if fwer_uncorrected > 0.3:
            interpretation.extend([
                "",
                "WARNING: High FWER without correction",
                "Multiplicity correction is strongly recommended"
            ])

        return interpretation

    def _method_selection_rationale(self, method: str) -> str:
        """Provide method selection rationale"""
        rationale = {
            "bonferroni": "Conservative, robust, suitable for confirmatory trials with few tests",
            "holm": "More powerful than Bonferroni, good balance of control and power",
            "fdr_bh": "High power for exploratory analyses, controls FDR not FWER",
            "fdr_by": "Conservative FDR for dependent tests, handles correlations",
            "sidak": "Slightly more powerful than Bonferroni for independent tests",
            "hochberg": "More powerful than Holm under independence, step-up procedure",
            "hommel": "High power for many tests, computationally intensive"
        }
        return rationale.get(method, "Standard multiplicity correction")

    def _explain_holm_algorithm(self) -> List[str]:
        """Explain Holm algorithm step-by-step"""
        return [
            "Algorithm:",
            "1. Sort p-values: p_(1) <= p_(2) <= ... <= p_(m)",
            "2. Compare p_(1) to alpha/m, p_(2) to alpha/(m-1), ...",
            "3. Find largest k where p_(k) <= alpha/(m-k+1)",
            "4. Reject hypotheses 1, 2, ..., k",
            "5. Accept hypotheses k+1, ..., m",
            "Step-down procedure, controls FWER at level alpha"
        ]

    def _explain_bh_algorithm(self) -> List[str]:
        """Explain Benjamini-Hochberg algorithm step-by-step"""
        return [
            "Algorithm:",
            "1. Sort p-values: p_(1) <= p_(2) <= ... <= p_(m)",
            "2. Find largest k such that p_(k) <= (k/m) * q",
            "3. Reject hypotheses 1, 2, ..., k",
            "4. Accept hypotheses k+1, ..., m",
            "Step-up procedure, controls FDR at level q"
        ]

    def _explain_hochberg_algorithm(self) -> List[str]:
        """Explain Hochberg algorithm step-by-step"""
        return [
            "Algorithm:",
            "1. Sort p-values: p_(1) <= p_(2) <= ... <= p_(m)",
            "2. Find largest k such that p_(k) <= alpha/(m-k+1)",
            "3. Reject all hypotheses with p-values <= p_(k)",
            "Step-up procedure, more powerful than Holm under independence"
        ]

    def _generate_method_recommendations(self,
                                            pvalues: np.ndarray,
                                            significance_counts: Dict[str, int],
                                            power_ranking: List[Tuple[str, int]]) -> Dict[str, Any]:
        """Generate method recommendations based on analysis"""
        n_tests = len(pvalues)
        alpha = self.alpha

        # Get most powerful method
        most_powerful = power_ranking[0][0] if power_ranking else None
        most_powerful_count = power_ranking[0][1] if power_ranking else 0

        # Get FWER methods
        fwer_methods = ['bonferroni', 'holm', 'sidak', 'hochberg', 'hommel']
        fwer_counts = {k: v for k, v in significance_counts.items() if k in fwer_methods}
        best_fwer = max(fwer_counts, key=fwer_counts.get) if fwer_counts else None

        # Get FDR methods
        fdr_methods = ['fdr_bh', 'fdr_by']
        fdr_counts = {k: v for k, v in significance_counts.items() if k in fdr_methods}
        best_fdr = max(fdr_counts, key=fdr_counts.get) if fdr_counts else None

        # Generate recommendations
        recommendations = {}

        # Recommendation for confirmatory trials
        if n_tests <= 5:
            recommendations["confirmatory"] = {
                "recommended": "Bonferroni or Holm",
                "rationale": "Small number of tests, strong FWER control needed",
                "method": best_fwer if best_fwer else "holm"
            }
        else:
            recommendations["confirmatory"] = {
                "recommended": "Holm or Hommel",
                "rationale": "Multiple tests, need balance of control and power",
                "method": best_fwer if best_fwer else "holm"
            }

        # Recommendation for exploratory analyses
        recommendations["exploratory"] = {
            "recommended": "Benjamini-Hochberg (FDR)",
            "rationale": "Higher power for discovery, controls FDR",
            "method": best_fdr if best_fdr else "fdr_bh"
        }

        # Power analysis
        if most_powerful_count == 0:
            power_assessment = "No methods identified significant results"
            suggestions = [
                "Consider increasing sample size",
                "Review effect sizes and study design",
                "Check test assumptions"
            ]
        elif most_powerful_count == 1:
            power_assessment = "Low power - only one method found significance"
            suggestions = [
                "Consider using the most powerful method: " + most_powerful,
                "Validate findings with additional analyses"
            ]
        else:
            power_assessment = f"Good power - {most_powerful_count} significant tests with {most_powerful}"
            suggestions = [
                f"{most_powerful} provides optimal balance of control and power",
                "Document method selection in statistical analysis plan"
            ]

        recommendations["power_analysis"] = {
            "assessment": power_assessment,
            "suggestions": suggestions,
            "most_powerful_method": most_powerful,
            "most_powerful_count": most_powerful_count
        }

        return recommendations

    def _interpret_comparison(self,
                                power_ranking: List[Tuple[str, int]],
                                significance_counts: Dict[str, int],
                                n_tests: int) -> List[str]:
        """Generate comparison interpretation"""
        interpretation = [
            f"Comparison of {len(power_ranking)} multiplicity correction methods",
            f"Testing {n_tests} hypotheses with alpha={self.alpha}",
            "",
            "Power Ranking (most to least significant):"
        ]

        for i, (method, count) in enumerate(power_ranking):
            interpretation.append(f"  {i+1}. {method}: {count} significant tests")

        interpretation.extend([
            "",
            "Key Observations:"
        ])

        # Compare FWER vs FDR methods
        fwer_max = max([count for method, count in power_ranking if method in ['bonferroni', 'holm', 'sidak', 'hochberg', 'hommel']])
        fdr_max = max([count for method, count in power_ranking if method in ['fdr_bh', 'fdr_by']])

        if fdr_max > fwer_max:
            interpretation.append(f"- FDR methods (BH, BY) identified {fdr_max - fwer_max} more significant tests")
            interpretation.append("  - Higher power for exploratory analyses")
            interpretation.append("  - Controls FDR, not FWER")

        if fwer_max == 0:
            interpretation.append("- No FWER-controlled tests significant - conservative approach")
            interpretation.append("  - May indicate insufficient evidence or sample size")

        # Check consistency across methods
        unique_counts = set(significance_counts.values())
        if len(unique_counts) == 1:
            interpretation.append("- All methods identified same number of significant tests")
            interpretation.append("  - Results are robust to method selection")
        else:
            interpretation.append("- Methods differ in significance identification")
            interpretation.append("  - Choose method based on study objectives and regulatory requirements")

        return interpretation

    def _comparison_clinical_guidance(self) -> Dict[str, str]:
        """Provide comparison clinical guidance"""
        return {
            "method_selection": "Pre-specify in statistical analysis plan",
            "confirmatory_trials": "Use FWER methods (Bonferroni, Holm, Hommel)",
            "exploratory_analyses": "Consider FDR methods (BH, BY) for biomarker screening",
            "regulatory_documentation": "Document method rationale and pre-specification",
            "multiple_testing_problem": "Address in protocol to avoid inflation of Type I error",
            "interim_analyses": "Use alpha spending functions or group sequential methods",
            "endpoint_hierarchy": "Consider hierarchical testing when endpoints are ordered"
        }

    def get_analysis_history(self) -> List[Dict[str, Any]]:
        """Get analysis history for audit trail

        Returns:
            List of analysis records with method, timestamp, and results
        """
        return self.analysis_history.copy()

    def clear_analysis_history(self) -> None:
        """Clear analysis history (for new analyses)"""
        self.analysis_history = []

    def __repr__(self) -> str:
        """String representation"""
        return f"MultiplicityControl(alpha={self.alpha}, independence={self.independence})"
