"""
Survival Analysis Module for BioDockify
Implements Kaplan-Meier estimator and Cox proportional hazards regression.

Dependencies: lifelines, matplotlib, pandas, numpy
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
import logging
from dataclasses import dataclass
import io
import base64

# Survival analysis imports
try:
    from lifelines import KaplanMeierFitter, CoxPHFitter
    from lifelines.statistics import logrank_test, multivariate_logrank_test
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    SURVIVAL_AVAILABLE = True
except ImportError:
    SURVIVAL_AVAILABLE = False
    KaplanMeierFitter = None
    CoxPHFitter = None

logger = logging.getLogger(__name__)

@dataclass
class SurvivalResult:
    """Results from survival analysis."""
    analysis_type: str  # 'kaplan_meier' or 'cox_regression'
    median_survival: Dict[str, float]  # Group -> median time
    confidence_intervals: Dict[str, Tuple[float, float]]  # Group -> (lower, upper)
    p_value: Optional[float] = None  # Log-rank p-value
    hazard_ratios: Optional[Dict[str, float]] = None  # Cox HR
    survival_table: Optional[pd.DataFrame] = None
    plot_base64: Optional[str] = None  # Base64 encoded plot


class SurvivalAnalyzer:
    """
    Survival analysis using Kaplan-Meier and Cox regression.
    Designed for clinical trial data with time-to-event outcomes.
    """
    
    def __init__(self):
        if not SURVIVAL_AVAILABLE:
            raise ImportError(
                "Survival analysis requires 'lifelines' package. "
                "Install with: pip install lifelines"
            )
        self.kmf = KaplanMeierFitter()
        self.cph = CoxPHFitter()
    
    def kaplan_meier(
        self,
        data: pd.DataFrame,
        time_col: str,
        event_col: str,
        group_col: Optional[str] = None,
        alpha: float = 0.05
    ) -> SurvivalResult:
        """
        Perform Kaplan-Meier survival analysis.
        
        Args:
            data: DataFrame with survival data
            time_col: Column name for time-to-event
            event_col: Column name for event indicator (1=event, 0=censored)
            group_col: Optional column for group comparison
            alpha: Significance level for confidence intervals
        
        Returns:
            SurvivalResult with median survival times, CI, and optional log-rank test
        """
        logger.info(f"Running Kaplan-Meier analysis on {len(data)} observations")
        
        median_survival = {}
        confidence_intervals = {}
        p_value = None
        
        if group_col is None:
            # Single group analysis
            self.kmf.fit(
                durations=data[time_col],
                event_observed=data[event_col],
                alpha=alpha
            )
            
            median_survival['overall'] = self.kmf.median_survival_time_
            ci = self.kmf.confidence_interval_survival_function_
            confidence_intervals['overall'] = (
                ci.iloc[0, 0] if len(ci) > 0 else None,
                ci.iloc[0, 1] if len(ci) > 0 else None
            )
            
            # Generate plot
            plot_base64 = self._plot_single_km(self.kmf, time_col)
            
        else:
            # Multi-group analysis with log-rank test
            groups = data[group_col].unique()
            
            # Fit KM for each group
            fig, ax = plt.subplots(figsize=(10, 6))
            
            for group in groups:
                group_data = data[data[group_col] == group]
                kmf_group = KaplanMeierFitter()
                kmf_group.fit(
                    durations=group_data[time_col],
                    event_observed=group_data[event_col],
                    label=str(group),
                    alpha=alpha
                )
                
                median_survival[str(group)] = kmf_group.median_survival_time_
                
                # Plot
                kmf_group.plot_survival_function(ax=ax, ci_show=True)
            
            ax.set_xlabel('Time')
            ax.set_ylabel('Survival Probability')
            ax.set_title('Kaplan-Meier Survival Curves')
            ax.legend(loc='best')
            ax.grid(True, alpha=0.3)
            
            # Save plot to base64
            plot_base64 = self._fig_to_base64(fig)
            plt.close(fig)
            
            # Log-rank test
            if len(groups) == 2:
                group1_data = data[data[group_col] == groups[0]]
                group2_data = data[data[group_col] == groups[1]]
                
                results = logrank_test(
                    durations_A=group1_data[time_col],
                    durations_B=group2_data[time_col],
                    event_observed_A=group1_data[event_col],
                    event_observed_B=group2_data[event_col]
                )
                p_value = results.p_value
                logger.info(f"Log-rank test p-value: {p_value:.4f}")
            else:
                # Multivariate log-rank for >2 groups
                results = multivariate_logrank_test(
                    data[time_col],
                    data[group_col],
                    data[event_col]
                )
                p_value = results.p_value
        
        return SurvivalResult(
            analysis_type='kaplan_meier',
            median_survival=median_survival,
            confidence_intervals=confidence_intervals,
            p_value=p_value,
            plot_base64=plot_base64
        )
    
    def cox_regression(
        self,
        data: pd.DataFrame,
        time_col: str,
        event_col: str,
        covariates: List[str],
        alpha: float = 0.05
    ) -> SurvivalResult:
        """
        Perform Cox proportional hazards regression.
        
        Args:
            data: DataFrame with survival data
            time_col: Column name for time-to-event
            event_col: Column name for event indicator
            covariates: List of covariate column names
            alpha: Significance level
        
        Returns:
            SurvivalResult with hazard ratios and p-values
        """
        logger.info(f"Running Cox regression with covariates: {covariates}")
        
        # Prepare data for Cox model
        cox_data = data[[time_col, event_col] + covariates].copy()
        cox_data = cox_data.dropna()
        
        # Fit Cox model (alpha is not a parameter for fit in lifelines 0.30+)
        self.cph.fit(
            cox_data,
            duration_col=time_col,
            event_col=event_col
        )
        
        # Extract hazard ratios
        hazard_ratios = {}
        for covariate in covariates:
            hr = np.exp(self.cph.params_[covariate])
            hazard_ratios[covariate] = hr
        
        # Get summary
        summary = self.cph.summary
        
        # Generate forest plot
        plot_base64 = self._plot_forest(self.cph, covariates)
        
        return SurvivalResult(
            analysis_type='cox_regression',
            median_survival={},  # Not applicable for Cox
            confidence_intervals={},
            p_value=None,  # Multiple p-values in summary
            hazard_ratios=hazard_ratios,
            survival_table=summary,
            plot_base64=plot_base64
        )
    
    def _plot_single_km(self, kmf: KaplanMeierFitter, time_label: str) -> str:
        """Generate plot for single KM curve."""
        fig, ax = plt.subplots(figsize=(10, 6))
        kmf.plot_survival_function(ax=ax, ci_show=True)
        ax.set_xlabel(f'Time ({time_label})')
        ax.set_ylabel('Survival Probability')
        ax.set_title('Kaplan-Meier Survival Curve')
        ax.grid(True, alpha=0.3)
        
        plot_base64 = self._fig_to_base64(fig)
        plt.close(fig)
        return plot_base64
    
    def _plot_forest(self, cph: CoxPHFitter, covariates: List[str]) -> str:
        """Generate forest plot for Cox regression hazard ratios."""
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            cph.plot(ax=ax)
            ax.set_title('Cox Regression Hazard Ratios (Forest Plot)')
            ax.grid(True, alpha=0.3, axis='x')
            
            plot_base64 = self._fig_to_base64(fig)
            plt.close(fig)
            return plot_base64
        except Exception as e:
            logger.warning(f"Forest plot generation failed: {e}")
            return None
    
    def _fig_to_base64(self, fig) -> str:
        """Convert matplotlib figure to base64 string."""
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()
        return img_base64


def is_survival_available() -> bool:
    """Check if survival analysis dependencies are available."""
    return SURVIVAL_AVAILABLE
