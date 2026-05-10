"""
Power Analysis Module for BioDockify
Implements statistical power calculations and sample size estimation.

Supports: t-test, ANOVA, correlation, survival analysis
Dependencies: statsmodels, scipy, numpy
"""

import numpy as np
from scipy import stats
from typing import Dict, List, Optional, Any, Tuple, Literal
import logging
from dataclasses import dataclass

# Power analysis imports
try:
    from statsmodels.stats.power import TTestPower, TTestIndPower, FTestAnovaPower
    from statsmodels.stats.power import NormalIndPower
    POWER_AVAILABLE = True
except ImportError:
    POWER_AVAILABLE = False
    TTestPower = None
    TTestIndPower = None
    FTestAnovaPower = None

logger = logging.getLogger(__name__)


@dataclass
class PowerResult:
    """Results from power analysis."""
    test_type: str
    power: float
    sample_size: Optional[int]
    effect_size: float
    alpha: float
    interpretation: str
    recommendation: str


@dataclass
class SampleSizeResult:
    """Results from sample size calculation."""
    test_type: str
    required_n: int
    per_group_n: Optional[int]  # For multi-group designs
    target_power: float
    effect_size: float
    alpha: float
    interpretation: str


class PowerAnalyzer:
    """
    Statistical power analysis and sample size estimation.
    Essential for study design and grant proposals.
    """
    
    def __init__(self):
        if not POWER_AVAILABLE:
            logger.warning(
                "Full power analysis requires 'statsmodels'. "
                "Using basic scipy-based calculations as fallback."
            )
    
    def calculate_power(
        self,
        effect_size: float,
        n: int,
        alpha: float = 0.05,
        test_type: Literal['two_sample', 'paired', 'one_sample', 'anova', 'correlation'] = 'two_sample',
        n_groups: int = 2
    ) -> PowerResult:
        """
        Calculate statistical power for a given sample size.
        
        Args:
            effect_size: Cohen's d (t-tests), f (ANOVA), or r (correlation)
            n: Sample size (total or per group depending on test)
            alpha: Significance level (default 0.05)
            test_type: Type of statistical test
            n_groups: Number of groups for ANOVA
        
        Returns:
            PowerResult with achieved power and interpretation
        """
        logger.info(f"Calculating power for {test_type} test: d={effect_size}, n={n}, alpha={alpha}")
        
        power = 0.0
        
        if test_type in ['two_sample', 'paired', 'one_sample']:
            power = self._power_ttest(effect_size, n, alpha, test_type)
        elif test_type == 'anova':
            power = self._power_anova(effect_size, n, alpha, n_groups)
        elif test_type == 'correlation':
            power = self._power_correlation(effect_size, n, alpha)
        else:
            raise ValueError(f"Unknown test type: {test_type}")
        
        # Interpretation
        interpretation = self._interpret_power(power)
        recommendation = self._power_recommendation(power, n, effect_size)
        
        return PowerResult(
            test_type=test_type,
            power=round(power, 4),
            sample_size=n,
            effect_size=effect_size,
            alpha=alpha,
            interpretation=interpretation,
            recommendation=recommendation
        )
    
    def calculate_sample_size(
        self,
        effect_size: float,
        power: float = 0.8,
        alpha: float = 0.05,
        test_type: Literal['two_sample', 'paired', 'one_sample', 'anova', 'correlation'] = 'two_sample',
        n_groups: int = 2
    ) -> SampleSizeResult:
        """
        Calculate required sample size for desired power.
        
        Args:
            effect_size: Expected effect size (Cohen's d, f, or r)
            power: Target power (default 0.8 = 80%)
            alpha: Significance level (default 0.05)
            test_type: Type of statistical test
            n_groups: Number of groups for ANOVA
        
        Returns:
            SampleSizeResult with required N
        """
        logger.info(f"Calculating sample size for power={power}: d={effect_size}")
        
        n = 0
        per_group_n = None
        
        if test_type in ['two_sample', 'paired', 'one_sample']:
            n = self._sample_size_ttest(effect_size, power, alpha, test_type)
            if test_type == 'two_sample':
                per_group_n = n
                n = n * 2  # Total for both groups
        elif test_type == 'anova':
            per_group_n = self._sample_size_anova(effect_size, power, alpha, n_groups)
            n = per_group_n * n_groups
        elif test_type == 'correlation':
            n = self._sample_size_correlation(effect_size, power, alpha)
        
        # Interpretation
        interpretation = self._interpret_sample_size(n, effect_size, test_type)
        
        return SampleSizeResult(
            test_type=test_type,
            required_n=int(np.ceil(n)),
            per_group_n=int(np.ceil(per_group_n)) if per_group_n else None,
            target_power=power,
            effect_size=effect_size,
            alpha=alpha,
            interpretation=interpretation
        )
    
    def effect_size_from_data(
        self,
        group1: List[float],
        group2: Optional[List[float]] = None
    ) -> Dict[str, float]:
        """
        Calculate effect size from raw data.
        
        Args:
            group1: First group data
            group2: Second group data (for two-sample)
        
        Returns:
            Dict with Cohen's d, Hedges' g, and interpretation
        """
        g1 = np.array(group1)
        
        if group2 is not None:
            g2 = np.array(group2)
            
            # Cohen's d (pooled SD)
            pooled_std = np.sqrt(
                ((len(g1) - 1) * np.var(g1, ddof=1) + 
                 (len(g2) - 1) * np.var(g2, ddof=1)) / 
                (len(g1) + len(g2) - 2)
            )
            
            cohens_d = (np.mean(g1) - np.mean(g2)) / pooled_std
            
            # Hedges' g (bias corrected)
            n_total = len(g1) + len(g2)
            correction = 1 - (3 / (4 * n_total - 9))
            hedges_g = cohens_d * correction
            
        else:
            # One-sample: compare to 0
            cohens_d = np.mean(g1) / np.std(g1, ddof=1)
            hedges_g = cohens_d
        
        return {
            "cohens_d": round(abs(cohens_d), 4),
            "hedges_g": round(abs(hedges_g), 4),
            "interpretation": self._interpret_effect_size(abs(cohens_d))
        }
    
    def generate_power_curve(
        self,
        effect_size: float,
        alpha: float = 0.05,
        test_type: str = 'two_sample',
        n_range: Tuple[int, int] = (10, 200)
    ) -> Dict[str, List[float]]:
        """
        Generate power curve data for plotting.
        
        Args:
            effect_size: Fixed effect size
            alpha: Significance level
            test_type: Type of test
            n_range: Range of sample sizes (min, max)
        
        Returns:
            Dict with 'n' and 'power' lists for plotting
        """
        n_values = list(range(n_range[0], n_range[1] + 1, 5))
        power_values = []
        
        for n in n_values:
            result = self.calculate_power(effect_size, n, alpha, test_type)
            power_values.append(result.power)
        
        return {
            "n": n_values,
            "power": power_values,
            "effect_size": effect_size,
            "alpha": alpha,
            "target_n": self._find_target_n(n_values, power_values, 0.8)
        }
    
    # =================== Private Methods ===================
    
    def _power_ttest(self, d: float, n: int, alpha: float, test_type: str) -> float:
        """Calculate power for t-test using non-central t distribution."""
        if POWER_AVAILABLE:
            if test_type == 'two_sample':
                analysis = TTestIndPower()
                return analysis.power(effect_size=d, nobs1=n, ratio=1.0, alpha=alpha)
            elif test_type == 'paired' or test_type == 'one_sample':
                analysis = TTestPower()
                return analysis.power(effect_size=d, nobs=n, alpha=alpha)
        
        # Fallback: use non-central t approximation
        df = n - 1 if test_type in ['paired', 'one_sample'] else 2 * n - 2
        ncp = d * np.sqrt(n / 2) if test_type == 'two_sample' else d * np.sqrt(n)
        
        t_crit = stats.t.ppf(1 - alpha / 2, df)
        power = 1 - stats.nct.cdf(t_crit, df, ncp) + stats.nct.cdf(-t_crit, df, ncp)
        
        return power
    
    def _power_anova(self, f: float, n_per_group: int, alpha: float, n_groups: int) -> float:
        """Calculate power for one-way ANOVA."""
        if POWER_AVAILABLE:
            analysis = FTestAnovaPower()
            return analysis.power(effect_size=f, nobs=n_per_group * n_groups, 
                                  alpha=alpha, k_groups=n_groups)
        
        # Fallback
        df1 = n_groups - 1
        df2 = n_groups * (n_per_group - 1)
        ncp = n_per_group * n_groups * f ** 2
        
        f_crit = stats.f.ppf(1 - alpha, df1, df2)
        power = 1 - stats.ncf.cdf(f_crit, df1, df2, ncp)
        
        return power
    
    def _power_correlation(self, r: float, n: int, alpha: float) -> float:
        """Calculate power for correlation test."""
        # Fisher z transformation
        z = 0.5 * np.log((1 + r) / (1 - r))
        se = 1 / np.sqrt(n - 3)
        z_crit = stats.norm.ppf(1 - alpha / 2)
        
        power = 1 - stats.norm.cdf(z_crit - z / se) + stats.norm.cdf(-z_crit - z / se)
        return power
    
    def _sample_size_ttest(self, d: float, power: float, alpha: float, test_type: str) -> int:
        """Calculate sample size for t-test."""
        if POWER_AVAILABLE:
            if test_type == 'two_sample':
                analysis = TTestIndPower()
                return int(np.ceil(analysis.solve_power(
                    effect_size=d, power=power, alpha=alpha, ratio=1.0, nobs1=None
                )))
            else:
                analysis = TTestPower()
                return int(np.ceil(analysis.solve_power(
                    effect_size=d, power=power, alpha=alpha, nobs=None
                )))
        
        # Fallback: iterative search
        for n in range(5, 10000):
            if self._power_ttest(d, n, alpha, test_type) >= power:
                return n
        return 10000
    
    def _sample_size_anova(self, f: float, power: float, alpha: float, n_groups: int) -> int:
        """Calculate sample size per group for ANOVA."""
        if POWER_AVAILABLE:
            analysis = FTestAnovaPower()
            n_total = analysis.solve_power(
                effect_size=f, power=power, alpha=alpha, k_groups=n_groups, nobs=None
            )
            return int(np.ceil(n_total / n_groups))
        
        # Fallback
        for n in range(5, 5000):
            if self._power_anova(f, n, alpha, n_groups) >= power:
                return n
        return 5000
    
    def _sample_size_correlation(self, r: float, power: float, alpha: float) -> int:
        """Calculate sample size for correlation."""
        for n in range(10, 10000):
            if self._power_correlation(r, n, alpha) >= power:
                return n
        return 10000
    
    def _interpret_power(self, power: float) -> str:
        """Interpret power value."""
        if power >= 0.9:
            return "Excellent power (>90%). Very likely to detect the effect if it exists."
        elif power >= 0.8:
            return "Adequate power (80-90%). Standard threshold for most studies."
        elif power >= 0.6:
            return "Moderate power (60-80%). Some risk of missing a true effect."
        elif power >= 0.4:
            return "Low power (40-60%). High risk of Type II error."
        else:
            return "Insufficient power (<40%). Study likely underpowered."
    
    def _interpret_effect_size(self, d: float) -> str:
        """Interpret Cohen's d effect size."""
        if d < 0.2:
            return "Negligible effect"
        elif d < 0.5:
            return "Small effect"
        elif d < 0.8:
            return "Medium effect"
        else:
            return "Large effect"
    
    def _interpret_sample_size(self, n: int, d: float, test_type: str) -> str:
        """Generate interpretation for sample size result."""
        return (
            f"To detect an effect size of {d:.2f} ({self._interpret_effect_size(d).lower()}) "
            f"with 80% power using a {test_type.replace('_', '-')} test at alpha=0.05, "
            f"you need a total sample size of {n} participants."
        )
    
    def _power_recommendation(self, power: float, n: int, d: float) -> str:
        """Generate recommendation based on power."""
        if power >= 0.8:
            return f"Sample size of {n} is adequate to detect an effect of d={d:.2f}."
        else:
            target_n = self._sample_size_ttest(d, 0.8, 0.05, 'two_sample')
            return f"Consider increasing sample size to {target_n} per group for 80% power."
    
    def _find_target_n(self, n_values: List[int], power_values: List[float], target: float) -> int:
        """Find N needed to achieve target power."""
        for n, p in zip(n_values, power_values):
            if p >= target:
                return n
        return n_values[-1]


def is_power_available() -> bool:
    """Check if full power analysis is available."""
    return POWER_AVAILABLE
