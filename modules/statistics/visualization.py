"""
Statistical Visualization Module for BioDockify
Implements Q-Q plots, forest plots, and publication-ready tables.

Dependencies: matplotlib, numpy, scipy
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Optional, Any, Tuple
import logging
from dataclasses import dataclass
import io
import base64

# Matplotlib imports
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class NormalityResult:
    """Results from normality testing."""
    shapiro_statistic: float
    shapiro_pvalue: float
    is_normal: bool
    interpretation: str
    qq_plot_base64: Optional[str]


@dataclass
class BootstrapResult:
    """Results from bootstrap analysis."""
    estimate: float
    ci_lower: float
    ci_upper: float
    se: float
    n_bootstrap: int
    distribution_base64: Optional[str]


class StatisticalVisualizer:
    """
    Statistical visualization tools for diagnostics and publication.
    """
    
    def __init__(self):
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("Matplotlib not available. Plots will be disabled.")
    
    # =================== Q-Q Plots ===================
    
    def qq_plot(
        self,
        data: np.ndarray,
        title: str = "Q-Q Plot",
        distribution: str = "norm"
    ) -> Tuple[str, NormalityResult]:
        """
        Generate Q-Q plot and test normality.
        
        Args:
            data: 1D array of values
            title: Plot title
            distribution: Reference distribution ('norm', 't', 'uniform')
        
        Returns:
            Tuple of (base64 plot, NormalityResult)
        """
        data = np.array(data)
        data = data[~np.isnan(data)]
        
        # Shapiro-Wilk test
        if len(data) >= 3:
            stat, pvalue = stats.shapiro(data)
        else:
            stat, pvalue = np.nan, np.nan
        
        is_normal = pvalue > 0.05 if not np.isnan(pvalue) else False
        
        interpretation = self._interpret_normality(pvalue, len(data))
        
        # Generate plot
        plot_base64 = None
        if MATPLOTLIB_AVAILABLE:
            fig, ax = plt.subplots(figsize=(8, 6))
            
            # Calculate theoretical quantiles
            n = len(data)
            theoretical = stats.norm.ppf((np.arange(1, n + 1) - 0.5) / n)
            observed = np.sort(data)
            
            # Standardize observed
            observed_std = (observed - np.mean(observed)) / np.std(observed)
            
            ax.scatter(theoretical, observed_std, alpha=0.6, edgecolors='b', facecolors='none')
            
            # Reference line
            min_val = min(theoretical.min(), observed_std.min())
            max_val = max(theoretical.max(), observed_std.max())
            ax.plot([min_val, max_val], [min_val, max_val], 'r--', linewidth=2)
            
            ax.set_xlabel('Theoretical Quantiles')
            ax.set_ylabel('Sample Quantiles (Standardized)')
            ax.set_title(f'{title}\nShapiro-Wilk: W={stat:.4f}, p={pvalue:.4f}')
            ax.grid(True, alpha=0.3)
            
            # Add normality indicator
            color = 'green' if is_normal else 'red'
            label = 'Normal' if is_normal else 'Non-Normal'
            ax.text(0.05, 0.95, label, transform=ax.transAxes,
                   fontsize=12, verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor=color, alpha=0.3))
            
            plot_base64 = self._fig_to_base64(fig)
            plt.close(fig)
        
        return plot_base64, NormalityResult(
            shapiro_statistic=stat,
            shapiro_pvalue=pvalue,
            is_normal=is_normal,
            interpretation=interpretation,
            qq_plot_base64=plot_base64
        )
    
    # =================== Forest Plots ===================
    
    def forest_plot(
        self,
        estimates: Dict[str, float],
        confidence_intervals: Dict[str, Tuple[float, float]],
        title: str = "Forest Plot",
        xlabel: str = "Effect Size",
        reference_line: float = 1.0
    ) -> str:
        """
        Generate a forest plot for effect sizes.
        
        Args:
            estimates: Dict of {name: estimate}
            confidence_intervals: Dict of {name: (lower, upper)}
            title: Plot title
            xlabel: X-axis label
            reference_line: Reference line value (1 for OR, 0 for mean diff)
        
        Returns:
            Base64 encoded plot
        """
        if not MATPLOTLIB_AVAILABLE:
            return None
        
        names = list(estimates.keys())
        n_items = len(names)
        
        fig, ax = plt.subplots(figsize=(10, max(4, n_items * 0.5)))
        
        y_positions = np.arange(n_items)
        
        for i, name in enumerate(names):
            est = estimates[name]
            ci = confidence_intervals.get(name, (np.nan, np.nan))
            
            # Point estimate
            ax.scatter(est, i, s=100, c='blue', zorder=3)
            
            # Confidence interval
            if not np.isnan(ci[0]) and not np.isnan(ci[1]):
                ax.hlines(i, ci[0], ci[1], color='blue', linewidth=2)
                ax.scatter([ci[0], ci[1]], [i, i], s=30, c='blue', marker='|')
        
        # Reference line
        ax.axvline(x=reference_line, color='red', linestyle='--', linewidth=1, alpha=0.7)
        
        ax.set_yticks(y_positions)
        ax.set_yticklabels(names)
        ax.set_xlabel(xlabel)
        ax.set_title(title)
        ax.grid(True, alpha=0.3, axis='x')
        
        # Invert y-axis for top-to-bottom reading
        ax.invert_yaxis()
        
        plt.tight_layout()
        plot_base64 = self._fig_to_base64(fig)
        plt.close(fig)
        
        return plot_base64
    
    # =================== Publication Tables ===================
    
    def create_summary_table(
        self,
        data: pd.DataFrame,
        group_col: Optional[str] = None,
        numeric_cols: Optional[List[str]] = None,
        format_style: str = "apa"
    ) -> Dict[str, Any]:
        """
        Create publication-ready summary table.
        
        Args:
            data: DataFrame
            group_col: Optional grouping column
            numeric_cols: Columns to summarize
            format_style: 'apa' or 'simple'
        
        Returns:
            Dict with table data and formatted string
        """
        if numeric_cols is None:
            numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
        
        if group_col and group_col in data.columns:
            # Grouped summary
            summary = data.groupby(group_col)[numeric_cols].agg(['mean', 'std', 'count'])
            
            # Flatten columns
            summary.columns = ['_'.join(col).strip() for col in summary.columns.values]
            
            table_data = summary.to_dict()
            
            # Format for publication
            formatted_rows = []
            for col in numeric_cols:
                row = {"Variable": col}
                for group in data[group_col].unique():
                    mean = summary.loc[group, f'{col}_mean']
                    std = summary.loc[group, f'{col}_std']
                    row[str(group)] = f"{mean:.2f} ({std:.2f})"
                formatted_rows.append(row)
            
            formatted_table = pd.DataFrame(formatted_rows)
            
        else:
            # Overall summary
            summary = data[numeric_cols].agg(['mean', 'std', 'min', 'max', 'count'])
            table_data = summary.to_dict()
            
            formatted_rows = []
            for col in numeric_cols:
                formatted_rows.append({
                    "Variable": col,
                    "Mean (SD)": f"{summary.loc['mean', col]:.2f} ({summary.loc['std', col]:.2f})",
                    "Range": f"{summary.loc['min', col]:.2f} - {summary.loc['max', col]:.2f}",
                    "N": int(summary.loc['count', col])
                })
            
            formatted_table = pd.DataFrame(formatted_rows)
        
        return {
            "raw_data": table_data,
            "formatted_table": formatted_table.to_dict('records'),
            "markdown": self._table_to_markdown(formatted_table),
            "latex": self._table_to_latex(formatted_table)
        }
    
    def create_results_table(
        self,
        estimates: Dict[str, float],
        confidence_intervals: Dict[str, Tuple[float, float]],
        p_values: Dict[str, float],
        title: str = "Results"
    ) -> Dict[str, Any]:
        """
        Create publication-ready results table.
        
        Args:
            estimates: Effect size estimates
            confidence_intervals: CIs
            p_values: P-values
            title: Table title
        
        Returns:
            Dict with formatted tables
        """
        rows = []
        for name in estimates.keys():
            est = estimates[name]
            ci = confidence_intervals.get(name, (np.nan, np.nan))
            p = p_values.get(name, np.nan)
            
            # Significance stars
            stars = ""
            if not np.isnan(p):
                if p < 0.001:
                    stars = "***"
                elif p < 0.01:
                    stars = "**"
                elif p < 0.05:
                    stars = "*"
            
            rows.append({
                "Variable": name,
                "Estimate": f"{est:.3f}",
                "95% CI": f"[{ci[0]:.3f}, {ci[1]:.3f}]" if not np.isnan(ci[0]) else "N/A",
                "p-value": f"{p:.4f}{stars}" if not np.isnan(p) else "N/A"
            })
        
        df = pd.DataFrame(rows)
        
        return {
            "formatted_table": df.to_dict('records'),
            "markdown": self._table_to_markdown(df),
            "latex": self._table_to_latex(df),
            "title": title
        }
    
    # =================== Bootstrap ===================
    
    def bootstrap_ci(
        self,
        data: np.ndarray,
        statistic: str = "mean",
        n_bootstrap: int = 1000,
        confidence_level: float = 0.95
    ) -> BootstrapResult:
        """
        Calculate bootstrap confidence intervals.
        
        Args:
            data: 1D array of values
            statistic: 'mean', 'median', or 'std'
            n_bootstrap: Number of bootstrap samples
            confidence_level: CI level (default 0.95)
        
        Returns:
            BootstrapResult with CI and distribution
        """
        data = np.array(data)
        data = data[~np.isnan(data)]
        n = len(data)
        
        # Select statistic function
        stat_funcs = {
            'mean': np.mean,
            'median': np.median,
            'std': np.std
        }
        stat_func = stat_funcs.get(statistic, np.mean)
        
        # Original estimate
        original_estimate = stat_func(data)
        
        # Bootstrap samples
        bootstrap_estimates = []
        np.random.seed(42)  # Reproducibility
        
        for _ in range(n_bootstrap):
            sample = np.random.choice(data, size=n, replace=True)
            bootstrap_estimates.append(stat_func(sample))
        
        bootstrap_estimates = np.array(bootstrap_estimates)
        
        # Percentile CI
        alpha = 1 - confidence_level
        ci_lower = np.percentile(bootstrap_estimates, alpha / 2 * 100)
        ci_upper = np.percentile(bootstrap_estimates, (1 - alpha / 2) * 100)
        
        # Standard error
        se = np.std(bootstrap_estimates)
        
        # Distribution plot
        plot_base64 = None
        if MATPLOTLIB_AVAILABLE:
            fig, ax = plt.subplots(figsize=(8, 5))
            
            ax.hist(bootstrap_estimates, bins=50, density=True, alpha=0.7, color='steelblue')
            ax.axvline(original_estimate, color='red', linestyle='--', linewidth=2, 
                      label=f'Estimate = {original_estimate:.3f}')
            ax.axvline(ci_lower, color='green', linestyle=':', linewidth=2,
                      label=f'{confidence_level*100:.0f}% CI')
            ax.axvline(ci_upper, color='green', linestyle=':', linewidth=2)
            
            ax.set_xlabel(f'{statistic.capitalize()}')
            ax.set_ylabel('Density')
            ax.set_title(f'Bootstrap Distribution (n={n_bootstrap})')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            plot_base64 = self._fig_to_base64(fig)
            plt.close(fig)
        
        return BootstrapResult(
            estimate=original_estimate,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            se=se,
            n_bootstrap=n_bootstrap,
            distribution_base64=plot_base64
        )
    
    # =================== Residual Diagnostics ===================
    
    def residual_plots(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        title: str = "Residual Diagnostics"
    ) -> str:
        """
        Generate residual diagnostic plots.
        
        Args:
            y_true: Actual values
            y_pred: Predicted values
            title: Plot title
        
        Returns:
            Base64 encoded plot
        """
        if not MATPLOTLIB_AVAILABLE:
            return None
        
        residuals = y_true - y_pred
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        # 1. Residuals vs Fitted
        ax1 = axes[0, 0]
        ax1.scatter(y_pred, residuals, alpha=0.5)
        ax1.axhline(y=0, color='r', linestyle='--')
        ax1.set_xlabel('Fitted Values')
        ax1.set_ylabel('Residuals')
        ax1.set_title('Residuals vs Fitted')
        
        # 2. Q-Q Plot of Residuals
        ax2 = axes[0, 1]
        stats.probplot(residuals, dist="norm", plot=ax2)
        ax2.set_title('Normal Q-Q')
        
        # 3. Scale-Location
        ax3 = axes[1, 0]
        sqrt_abs_resid = np.sqrt(np.abs(residuals))
        ax3.scatter(y_pred, sqrt_abs_resid, alpha=0.5)
        ax3.set_xlabel('Fitted Values')
        ax3.set_ylabel('√|Residuals|')
        ax3.set_title('Scale-Location')
        
        # 4. Histogram of Residuals
        ax4 = axes[1, 1]
        ax4.hist(residuals, bins=30, density=True, alpha=0.7)
        x = np.linspace(residuals.min(), residuals.max(), 100)
        ax4.plot(x, stats.norm.pdf(x, np.mean(residuals), np.std(residuals)), 'r-', linewidth=2)
        ax4.set_xlabel('Residuals')
        ax4.set_ylabel('Density')
        ax4.set_title('Residual Distribution')
        
        plt.suptitle(title, fontsize=14)
        plt.tight_layout()
        
        plot_base64 = self._fig_to_base64(fig)
        plt.close(fig)
        
        return plot_base64
    
    # =================== Helper Methods ===================
    
    def _interpret_normality(self, pvalue: float, n: int) -> str:
        """Interpret normality test results."""
        if np.isnan(pvalue):
            return "Unable to assess normality (insufficient data)"
        
        if pvalue > 0.05:
            return f"Data appears normally distributed (p = {pvalue:.4f}). Parametric tests are appropriate."
        else:
            return f"Data deviates from normality (p = {pvalue:.4f}). Consider non-parametric alternatives or data transformation."
    
    def _fig_to_base64(self, fig) -> str:
        """Convert matplotlib figure to base64."""
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()
        return img_base64
    
    def _table_to_markdown(self, df: pd.DataFrame) -> str:
        """Convert DataFrame to markdown table."""
        return df.to_markdown(index=False)
    
    def _table_to_latex(self, df: pd.DataFrame) -> str:
        """Convert DataFrame to LaTeX table."""
        return df.to_latex(index=False)


def is_visualization_available() -> bool:
    """Check if visualization is available."""
    return MATPLOTLIB_AVAILABLE
