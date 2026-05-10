"""
Enhanced Regression Module for BioDockify
Implements logistic regression, ROC curves, and model diagnostics.

Dependencies: scipy, numpy, sklearn (optional)
"""

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize
from typing import Dict, List, Optional, Any, Tuple
import logging
from dataclasses import dataclass
import io
import base64

# Optional sklearn imports
try:
    from sklearn.linear_model import LogisticRegression as SklearnLogistic
    from sklearn.metrics import roc_curve, auc, confusion_matrix, classification_report
    from sklearn.model_selection import cross_val_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# Matplotlib for plots
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class LogisticResult:
    """Results from logistic regression."""
    coefficients: Dict[str, float]
    odds_ratios: Dict[str, float]
    confidence_intervals: Dict[str, Tuple[float, float]]
    p_values: Dict[str, float]
    auc: float
    accuracy: float
    confusion_matrix: Optional[np.ndarray]
    roc_curve_base64: Optional[str]
    model_summary: str


@dataclass 
class ROCResult:
    """ROC curve analysis results."""
    auc: float
    optimal_threshold: float
    sensitivity: float
    specificity: float
    fpr: List[float]
    tpr: List[float]
    thresholds: List[float]
    plot_base64: Optional[str]


class RegressionAnalyzer:
    """
    Enhanced regression analysis including logistic regression,
    ROC curves, and model diagnostics.
    """
    
    def __init__(self):
        if not SKLEARN_AVAILABLE:
            logger.warning(
                "Scikit-learn not installed. Using basic implementation. "
                "Install with: pip install scikit-learn"
            )
    
    def logistic_regression(
        self,
        data: pd.DataFrame,
        outcome_col: str,
        predictors: List[str],
        alpha: float = 0.05
    ) -> LogisticResult:
        """
        Perform logistic regression analysis.
        
        Args:
            data: DataFrame with outcome and predictors
            outcome_col: Binary outcome column (0/1)
            predictors: List of predictor column names
            alpha: Significance level for CIs
        
        Returns:
            LogisticResult with odds ratios, p-values, and diagnostics
        """
        logger.info(f"Running logistic regression: {outcome_col} ~ {predictors}")
        
        # Prepare data
        df = data[[outcome_col] + predictors].dropna()
        X = df[predictors].values
        y = df[outcome_col].values
        
        # Add intercept
        X_with_intercept = np.column_stack([np.ones(X.shape[0]), X])
        
        if SKLEARN_AVAILABLE:
            return self._logistic_sklearn(X, y, predictors, alpha)
        else:
            return self._logistic_basic(X_with_intercept, y, predictors, alpha)
    
    def _logistic_sklearn(
        self,
        X: np.ndarray,
        y: np.ndarray,
        predictors: List[str],
        alpha: float
    ) -> LogisticResult:
        """Logistic regression using sklearn."""
        # Fit model
        model = SklearnLogistic(solver='lbfgs', max_iter=1000)
        model.fit(X, y)
        
        # Predictions
        y_pred = model.predict(X)
        y_prob = model.predict_proba(X)[:, 1]
        
        # Coefficients and odds ratios
        coefficients = {'intercept': model.intercept_[0]}
        odds_ratios = {'intercept': np.exp(model.intercept_[0])}
        
        for i, pred in enumerate(predictors):
            coefficients[pred] = model.coef_[0][i]
            odds_ratios[pred] = np.exp(model.coef_[0][i])
        
        # Confidence intervals (Wald)
        confidence_intervals = {}
        p_values = {}
        
        # Calculate standard errors using Hessian approximation
        X_with_intercept = np.column_stack([np.ones(X.shape[0]), X])
        p_hat = y_prob
        W = np.diag(p_hat * (1 - p_hat))
        
        try:
            var_covar = np.linalg.inv(X_with_intercept.T @ W @ X_with_intercept)
            se = np.sqrt(np.diag(var_covar))
            
            z_crit = stats.norm.ppf(1 - alpha / 2)
            
            all_coefs = [model.intercept_[0]] + list(model.coef_[0])
            all_names = ['intercept'] + predictors
            
            for i, name in enumerate(all_names):
                coef = all_coefs[i]
                se_i = se[i]
                
                # CI for log-odds
                ci_lower = coef - z_crit * se_i
                ci_upper = coef + z_crit * se_i
                
                # CI for odds ratio
                confidence_intervals[name] = (np.exp(ci_lower), np.exp(ci_upper))
                
                # P-value (Wald test)
                z_stat = coef / se_i
                p_values[name] = 2 * (1 - stats.norm.cdf(abs(z_stat)))
        except:
            # Fallback if matrix is singular
            for name in ['intercept'] + predictors:
                confidence_intervals[name] = (np.nan, np.nan)
                p_values[name] = np.nan
        
        # ROC and AUC
        fpr, tpr, _ = roc_curve(y, y_prob)
        auc_score = auc(fpr, tpr)
        
        # Accuracy
        accuracy = np.mean(y_pred == y)
        
        # Confusion matrix
        cm = confusion_matrix(y, y_pred)
        
        # Generate ROC plot
        roc_plot = self._plot_roc(fpr, tpr, auc_score) if MATPLOTLIB_AVAILABLE else None
        
        # Model summary
        summary = self._generate_logistic_summary(
            predictors, odds_ratios, confidence_intervals, p_values, auc_score, accuracy
        )
        
        return LogisticResult(
            coefficients=coefficients,
            odds_ratios=odds_ratios,
            confidence_intervals=confidence_intervals,
            p_values=p_values,
            auc=auc_score,
            accuracy=accuracy,
            confusion_matrix=cm,
            roc_curve_base64=roc_plot,
            model_summary=summary
        )
    
    def _logistic_basic(
        self,
        X: np.ndarray,
        y: np.ndarray,
        predictors: List[str],
        alpha: float
    ) -> LogisticResult:
        """Basic logistic regression without sklearn."""
        # Simple gradient descent implementation
        def sigmoid(z):
            return 1 / (1 + np.exp(-np.clip(z, -500, 500)))
        
        def loss(beta):
            z = X @ beta
            p = sigmoid(z)
            p = np.clip(p, 1e-10, 1 - 1e-10)
            return -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
        
        # Initialize and optimize
        beta_init = np.zeros(X.shape[1])
        result = minimize(loss, beta_init, method='BFGS')
        beta = result.x
        
        # Extract results
        coefficients = {'intercept': beta[0]}
        odds_ratios = {'intercept': np.exp(beta[0])}
        
        for i, pred in enumerate(predictors):
            coefficients[pred] = beta[i + 1]
            odds_ratios[pred] = np.exp(beta[i + 1])
        
        # Basic predictions
        y_prob = sigmoid(X @ beta)
        y_pred = (y_prob >= 0.5).astype(int)
        accuracy = np.mean(y_pred == y)
        
        # Basic AUC calculation
        auc_score = self._calculate_auc_basic(y, y_prob)
        
        return LogisticResult(
            coefficients=coefficients,
            odds_ratios=odds_ratios,
            confidence_intervals={k: (np.nan, np.nan) for k in odds_ratios},
            p_values={k: np.nan for k in odds_ratios},
            auc=auc_score,
            accuracy=accuracy,
            confusion_matrix=None,
            roc_curve_base64=None,
            model_summary=f"Logistic regression completed. AUC: {auc_score:.3f}, Accuracy: {accuracy:.1%}"
        )
    
    def calculate_roc(
        self,
        y_true: np.ndarray,
        y_prob: np.ndarray
    ) -> ROCResult:
        """
        Calculate ROC curve and optimal cutoff.
        
        Args:
            y_true: True binary labels
            y_prob: Predicted probabilities
        
        Returns:
            ROCResult with AUC, optimal threshold, and curve data
        """
        if SKLEARN_AVAILABLE:
            fpr, tpr, thresholds = roc_curve(y_true, y_prob)
            auc_score = auc(fpr, tpr)
        else:
            # Basic ROC calculation
            fpr, tpr, thresholds = self._roc_curve_basic(y_true, y_prob)
            auc_score = self._calculate_auc_basic(y_true, y_prob)
        
        # Find optimal threshold (Youden's J)
        j_scores = tpr - fpr
        optimal_idx = np.argmax(j_scores)
        optimal_threshold = thresholds[optimal_idx]
        
        # Sensitivity and specificity at optimal threshold
        sensitivity = tpr[optimal_idx]
        specificity = 1 - fpr[optimal_idx]
        
        # Generate plot
        plot = self._plot_roc(fpr, tpr, auc_score) if MATPLOTLIB_AVAILABLE else None
        
        return ROCResult(
            auc=auc_score,
            optimal_threshold=optimal_threshold,
            sensitivity=sensitivity,
            specificity=specificity,
            fpr=fpr.tolist(),
            tpr=tpr.tolist(),
            thresholds=thresholds.tolist(),
            plot_base64=plot
        )
    
    def _roc_curve_basic(
        self,
        y_true: np.ndarray,
        y_prob: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Basic ROC curve calculation without sklearn."""
        thresholds = np.sort(np.unique(y_prob))[::-1]
        tpr_list = []
        fpr_list = []
        
        for thresh in thresholds:
            y_pred = (y_prob >= thresh).astype(int)
            
            tp = np.sum((y_pred == 1) & (y_true == 1))
            fp = np.sum((y_pred == 1) & (y_true == 0))
            tn = np.sum((y_pred == 0) & (y_true == 0))
            fn = np.sum((y_pred == 0) & (y_true == 1))
            
            tpr = tp / (tp + fn) if (tp + fn) > 0 else 0
            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
            
            tpr_list.append(tpr)
            fpr_list.append(fpr)
        
        return np.array(fpr_list), np.array(tpr_list), thresholds
    
    def _calculate_auc_basic(self, y_true: np.ndarray, y_prob: np.ndarray) -> float:
        """Calculate AUC using trapezoidal rule."""
        fpr, tpr, _ = self._roc_curve_basic(y_true, y_prob)
        
        # Sort by FPR
        sorted_idx = np.argsort(fpr)
        fpr = fpr[sorted_idx]
        tpr = tpr[sorted_idx]
        
        # Trapezoidal integration
        auc_score = np.trapz(tpr, fpr)
        return auc_score
    
    def _plot_roc(self, fpr: np.ndarray, tpr: np.ndarray, auc_score: float) -> str:
        """Generate ROC curve plot."""
        fig, ax = plt.subplots(figsize=(8, 6))
        
        ax.plot(fpr, tpr, 'b-', linewidth=2, label=f'ROC (AUC = {auc_score:.3f})')
        ax.plot([0, 1], [0, 1], 'k--', linewidth=1, label='Random')
        
        ax.set_xlabel('False Positive Rate (1 - Specificity)')
        ax.set_ylabel('True Positive Rate (Sensitivity)')
        ax.set_title('Receiver Operating Characteristic (ROC) Curve')
        ax.legend(loc='lower right')
        ax.grid(True, alpha=0.3)
        ax.set_xlim([0, 1])
        ax.set_ylim([0, 1])
        
        # Save to base64
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()
        plt.close(fig)
        
        return img_base64
    
    def _generate_logistic_summary(
        self,
        predictors: List[str],
        odds_ratios: Dict[str, float],
        confidence_intervals: Dict[str, Tuple[float, float]],
        p_values: Dict[str, float],
        auc: float,
        accuracy: float
    ) -> str:
        """Generate human-readable summary."""
        lines = [
            "LOGISTIC REGRESSION RESULTS",
            "=" * 40,
            "",
            f"Model Performance:",
            f"  AUC (Area Under ROC): {auc:.3f}",
            f"  Accuracy: {accuracy:.1%}",
            "",
            "Odds Ratios:",
        ]
        
        for pred in predictors:
            or_val = odds_ratios[pred]
            ci = confidence_intervals[pred]
            p = p_values[pred]
            
            sig = "*" if p < 0.05 else ""
            sig += "*" if p < 0.01 else ""
            sig += "*" if p < 0.001 else ""
            
            lines.append(
                f"  {pred}: OR={or_val:.3f} (95% CI: {ci[0]:.3f}-{ci[1]:.3f}), p={p:.4f} {sig}"
            )
        
        lines.append("")
        lines.append("* p<0.05, ** p<0.01, *** p<0.001")
        
        return "\n".join(lines)


def is_regression_available() -> bool:
    """Check if enhanced regression is available."""
    return SKLEARN_AVAILABLE
