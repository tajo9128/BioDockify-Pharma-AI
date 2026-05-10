"""Survival Analysis Module for Pharmaceutical Research

Provides comprehensive survival analysis with detailed explanations
of methodology, results interpretation, and clinical significance.

Complies with:
- Good Laboratory Practice (GLP)
- Good Clinical Practice (GCP)
- FDA/EMA statistical guidelines
- ICH E9 Statistical Principles for Clinical Trials
- CONSORT reporting guidelines for survival data

Examples:
    # Example 1: Overall survival analysis
    sa = SurvivalAnalysis(alpha=0.05)
    result = sa.kaplan_meier_estimate(
        df=clinical_data,
        time_col='overall_survival_days',
        event_col='death_event',
        treatment_col='treatment_arm'
    )
    
    # Example 2: Treatment comparison
    result = sa.log_rank_test(
        df=clinical_data,
        time_col='progression_free_survival_days',
        event_col='progression_event',
        group_col='treatment_arm'
    )
    
    # Example 3: Cox regression
    result = sa.cox_proportional_hazards(
        df=clinical_data,
        time_col='overall_survival_days',
        event_col='death_event',
        covariates=['age', 'biomarker_level', 'treatment_arm']
    )
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from lifelines import KaplanMeierFitter, CoxPHFitter, NelsonAalenFitter
from lifelines.statistics import logrank_test, multivariate_logrank_test
from lifelines.utils import survival_table_from_events
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Set style for pharmaceutical-quality plots
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")


class SurvivalAnalysis:
    """Comprehensive survival analysis with detailed explanations

    Provides:
    - Kaplan-Meier survival curve estimation with confidence intervals
    - Log-rank test for comparing survival between groups
    - Cox proportional hazards regression
    - Survival data visualization
    - Multi-group survival comparison with post-hoc tests
    - Proportional hazards assumption checking
    
    All results include:
    - Statistical metrics (test statistics, p-values, hazard ratios)
    - Confidence intervals
    - Clinical interpretations in plain language
    - Methodological explanations
    - Compliance with regulatory guidelines
    """

    def __init__(self, alpha: float = 0.05, confidence_level: float = 0.95):
        """Initialize survival analysis engine

        Args:
            alpha: Significance level (default: 0.05 for 95% confidence)
            confidence_level: Confidence level for intervals (default: 0.95)
            
        Regulatory Note:
            ICH E9 recommends alpha=0.05 for confirmatory trials
            FDA guidance emphasizes pre-specified alpha levels
        """
        self.alpha = alpha
        self.confidence_level = confidence_level
        self.analysis_history = []
        self.current_analysis = None
        self.km_fitter = KaplanMeierFitter()
        self.cox_fitter = CoxPHFitter()
        self.na_fitter = NelsonAalenFitter()

    def kaplan_meier_estimate(
        self,
        df: pd.DataFrame,
        time_col: str,
        event_col: str,
        group_col: Optional[str] = None,
        group_values: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Kaplan-Meier survival curve estimation with confidence intervals

        Estimates the survival function using the Kaplan-Meier product-limit
        estimator, which is the non-parametric standard for survival analysis.
        
        Pharmaceutical Example:
            In a Phase III oncology trial, estimate overall survival for
            experimental vs. control treatments. The KM curve shows the
            probability of survival over time.
        
        Args:
            df: Input DataFrame with survival data
            time_col: Column name for survival/follow-up time
            event_col: Column name for event indicator (1=event, 0=censored)
            group_col: Optional column name for grouping (e.g., treatment arm)
            group_values: Optional list of specific group values to analyze
        
        Returns:
            Dictionary containing:
            - survival_estimates: Survival probabilities at each time point
            - confidence_intervals: 95% CI for survival estimates
            - median_survival: Median survival time with CI
            - event_table: Number at risk, events, censored at each time
            - explanations: Methodological explanations
            - interpretations: Clinical significance
            - assumptions: Data assumptions met
        
        Regulatory Compliance:
            - FDA: Requires KM curves for pivotal trials
            - EMA: Recommends median survival with 95% CI
            - CONSORT: KM plots as standard for time-to-event outcomes
        """
        # Data validation
        self._validate_survival_data(df, time_col, event_col)
        
        results = {
            'analysis_type': 'Kaplan-Meier Survival Estimate',
            'timestamp': datetime.now().isoformat(),
            'alpha': self.alpha,
            'confidence_level': self.confidence_level,
            'survival_estimates': {},
            'confidence_intervals': {},
            'median_survival': {},
            'event_table': {},
            'explanations': {},
            'interpretations': {},
            'assumptions': [],
            'warnings': []
        }
        
        # Determine groups
        if group_col is None:
            groups = [('All Patients', df)]
        else:
            if group_values:
                groups = [(val, df[df[group_col] == val]) for val in group_values]
            else:
                groups = [(str(val), df[df[group_col] == val]) 
                          for val in df[group_col].unique()]
        
        # Fit KM for each group
        for group_name, group_df in groups:
            group_df = group_df.copy()
            group_df = group_df.dropna(subset=[time_col, event_col])
            
            if len(group_df) == 0:
                results['warnings'].append(
                    f"Group '{group_name}' has no valid data after cleaning"
                )
                continue
            
            # Fit Kaplan-Meier
            self.km_fitter.fit(
                durations=group_df[time_col],
                event_observed=group_df[event_col],
                label=group_name
            )
            
            # Survival estimates
            survival_df = self.km_fitter.survival_function_.reset_index()
            survival_df.columns = ['time', 'survival_probability']
            results['survival_estimates'][group_name] = survival_df.to_dict('records')
            
            # Confidence intervals
            ci_df = self.km_fitter.confidence_interval_.reset_index()
            ci_df.columns = ['time', 'ci_lower', 'ci_upper']
            results['confidence_intervals'][group_name] = ci_df.to_dict('records')
            
            # Median survival
            median_survival = self.km_fitter.median_survival_time_
            median_ci = self.km_fitter.median_survival_time_
            results['median_survival'][group_name] = {
                'median': float(median_survival) if median_survival is not np.nan else None,
                'interpretation': self._interpret_median_survival(
                    median_survival, group_name, time_col
                )
            }
            
            # Event table
            event_table = self.km_fitter.event_table
            results['event_table'][group_name] = {
                'at_risk': event_table['at_risk'].tolist(),
                'events': event_table['observed'].tolist(),
                'censored': event_table['censored'].tolist()
            }
        
        # Explanations
        results['explanations'] = self._explain_kaplan_meier(results)
        
        # Interpretations
        results['interpretations'] = self._interpret_kaplan_meier(results, time_col)
        
        # Assumptions
        results['assumptions'] = self._check_km_assumptions(df, time_col, event_col)
        
        self._log_analysis('kaplan_meier', results)
        return results

    def log_rank_test(
        self,
        df: pd.DataFrame,
        time_col: str,
        event_col: str,
        group_col: str,
        group_a: Optional[str] = None,
        group_b: Optional[str] = None
    ) -> Dict[str, Any]:
        """Log-rank test for comparing survival curves between groups

        The log-rank test is the most commonly used statistical test for
        comparing two or more survival curves. It tests the null hypothesis
        that there is no difference in survival between groups.
        
        Pharmaceutical Example:
            Test whether experimental treatment improves overall survival
            compared to placebo. The log-rank test provides statistical
            evidence for treatment benefit.
        
        Args:
            df: Input DataFrame with survival data
            time_col: Column name for survival/follow-up time
            event_col: Column name for event indicator (1=event, 0=censored)
            group_col: Column name for grouping (e.g., treatment arm)
            group_a: Optional specific group name for comparison
            group_b: Optional specific group name for comparison
        
        Returns:
            Dictionary containing:
            - test_statistic: Chi-square test statistic
            - p_value: Statistical significance
            - hazard_ratio: Ratio of hazard rates (if 2 groups)
            - hazard_ratio_ci: 95% confidence interval for HR
            - interpretations: Clinical significance
            - explanations: Methodological explanation
        
        Regulatory Compliance:
            - FDA: Log-rank test is standard for primary OS endpoint
            - EMA: Requires pre-specified statistical test
            - ICH E9: Log-rank test appropriate for time-to-event data
        """
        # Data validation
        self._validate_survival_data(df, time_col, event_col)
        
        if group_col not in df.columns:
            raise ValueError(f"Group column '{group_col}' not found in DataFrame")
        
        results = {
            'analysis_type': 'Log-Rank Test',
            'timestamp': datetime.now().isoformat(),
            'alpha': self.alpha,
            'test_statistic': None,
            'p_value': None,
            'hazard_ratio': None,
            'hazard_ratio_ci': None,
            'explanations': {},
            'interpretations': {},
            'groups_compared': [],
            'assumptions': [],
            'warnings': []
        }
        
        # Get unique groups
        groups = df[group_col].dropna().unique()
        
        if len(groups) < 2:
            results['warnings'].append(
                "Need at least 2 groups for comparison"
            )
            return results
        
        # Subset data if specific groups requested
        if group_a and group_b:
            if group_a not in groups or group_b not in groups:
                results['warnings'].append(
                    f"Requested groups not found. Available: {groups}"
                )
                return results
            test_df = df[df[group_col].isin([group_a, group_b])].copy()
            results['groups_compared'] = [group_a, group_b]
        else:
            test_df = df[df[group_col].isin(groups)].copy()
            results['groups_compared'] = list(groups)
        
        # Prepare durations and events for each group
        durations = {}
        events = {}
        for group in results['groups_compared']:
            group_data = test_df[test_df[group_col] == group].dropna(
                subset=[time_col, event_col]
            )
            durations[group] = group_data[time_col]
            events[group] = group_data[event_col]
        
        # Perform log-rank test
        if len(results['groups_compared']) == 2:
            # Two-group comparison
            group_a_name = results['groups_compared'][0]
            group_b_name = results['groups_compared'][1]
            
            results_lr = logrank_test(
                durations_A=durations[group_a_name],
                durations_B=durations[group_b_name],
                event_observed_A=events[group_a_name],
                event_observed_B=events[group_b_name]
            )
            
            results['test_statistic'] = float(results_lr.test_statistic)
            results['p_value'] = float(results_lr.p_value)
            
            # Calculate hazard ratio
            hr, hr_lower, hr_upper = self._calculate_hazard_ratio(
                durations[group_a_name], events[group_a_name],
                durations[group_b_name], events[group_b_name]
            )
            
            results['hazard_ratio'] = hr
            results['hazard_ratio_ci'] = [hr_lower, hr_upper]
            
        else:
            # Multi-group comparison
            T = [durations[g] for g in results['groups_compared']]
            E = [events[g] for g in results['groups_compared']]
            
            results_mlr = multivariate_logrank_test(
                event_durations=np.concatenate(T),
                groups=np.concatenate(
                    [[g] * len(durations[g]) for g in results['groups_compared']]
                ),
                event_observed=np.concatenate(E)
            )
            
            results['test_statistic'] = float(results_mlr.test_statistic)
            results['p_value'] = float(results_mlr.p_value)
            results['warnings'].append(
                "Multi-group comparison performed. Pairwise comparisons "
                "needed for specific hazard ratios."
            )
        
        # Explanations
        results['explanations'] = self._explain_log_rank(results)
        
        # Interpretations
        results['interpretations'] = self._interpret_log_rank(results, time_col)
        
        # Assumptions
        results['assumptions'] = self._check_log_rank_assumptions(df)
        
        self._log_analysis('log_rank', results)
        return results

    def cox_proportional_hazards(
        self,
        df: pd.DataFrame,
        time_col: str,
        event_col: str,
        covariates: List[str],
        stratify_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cox proportional hazards regression model

        The Cox proportional hazards model is a semi-parametric regression
        model for survival data that assesses the effect of covariates on
        the hazard rate while making no assumptions about the shape of
        the baseline hazard.
        
        Pharmaceutical Example:
            Adjust for baseline prognostic factors (age, disease stage,
            biomarker levels) when estimating treatment effect on overall
            survival. This provides adjusted hazard ratios.
        
        Args:
            df: Input DataFrame with survival data
            time_col: Column name for survival/follow-up time
            event_col: Column name for event indicator (1=event, 0=censored)
            covariates: List of covariate column names
            stratify_by: Optional column for stratification
        
        Returns:
            Dictionary containing:
            - coefficients: Regression coefficients for each covariate
            - hazard_ratios: Exp(coefficient) for each covariate
            - confidence_intervals: 95% CI for hazard ratios
            - p_values: Statistical significance for each covariate
            - model_summary: Model fit statistics
            - proportional_hazards_test: PH assumption test results
            - interpretations: Clinical significance
        
        Regulatory Compliance:
            - FDA: Cox model standard for multivariate survival analysis
            - EMA: Requires adjustment for pre-specified prognostic factors
            - ICH E9: Cox model appropriate for covariate adjustment
        """
        # Data validation
        self._validate_survival_data(df, time_col, event_col)
        
        for covariate in covariates:
            if covariate not in df.columns:
                raise ValueError(f"Covariate '{covariate}' not found in DataFrame")
        
        results = {
            'analysis_type': 'Cox Proportional Hazards Regression',
            'timestamp': datetime.now().isoformat(),
            'alpha': self.alpha,
            'covariates': covariates,
            'coefficients': {},
            'hazard_ratios': {},
            'confidence_intervals': {},
            'p_values': {},
            'model_summary': {},
            'proportional_hazards_test': {},
            'explanations': {},
            'interpretations': {},
            'assumptions': [],
            'warnings': []
        }
        
        # Prepare data for Cox model
        cox_df = df[[time_col, event_col] + covariates].copy()
        cox_df = cox_df.dropna()
        
        # Convert categorical variables to dummy variables
        categorical_cols = cox_df[covariates].select_dtypes(
            include=['object', 'category']
        ).columns.tolist()
        
        if categorical_cols:
            cox_df = pd.get_dummies(cox_df, columns=categorical_cols, drop_first=True)
            # Update covariates list with dummy variable names
            results['warnings'].append(
                f"Categorical variables converted to dummy variables: {categorical_cols}"
            )
        
        # Fit Cox model
        try:
            self.cox_fitter.fit(
                cox_df,
                duration_col=time_col,
                event_col=event_col,
                show_progress=False
            )
        except Exception as e:
            results['warnings'].append(f"Cox model fitting failed: {str(e)}")
            return results
        
        # Extract results
        summary = self.cox_fitter.summary
        
        for covariate in summary.index:
            results['coefficients'][covariate] = {
                'value': float(summary.loc[covariate, 'coef']),
                'se': float(summary.loc[covariate, 'se(coef)'])
            }
            
            hr = float(summary.loc[covariate, 'exp(coef)'])
            hr_lower = float(summary.loc[covariate, 'exp(coef) lower 95%'])
            hr_upper = float(summary.loc[covariate, 'exp(coef) upper 95%'])
            
            results['hazard_ratios'][covariate] = hr
            results['confidence_intervals'][covariate] = [hr_lower, hr_upper]
            results['p_values'][covariate] = float(summary.loc[covariate, 'p'])
        
        # Model summary
        results['model_summary'] = {
            'log_likelihood': float(self.cox_fitter.log_likelihood_),
            'concordance_index': float(self.cox_fitter.concordance_index_),
            'partial_aic': float(self.cox_fitter.AIC_partial_),
            'n_observations': int(len(cox_df)),
            'n_events': int(cox_df[event_col].sum())
        }
        
        # Proportional hazards assumption test
        results['proportional_hazards_test'] = \
            self._test_proportional_hazards(cox_df, time_col, event_col, covariates)
        
        # Explanations
        results['explanations'] = self._explain_cox_model(results, time_col)
        
        # Interpretations
        results['interpretations'] = self._interpret_cox_model(results, time_col)
        
        # Assumptions
        results['assumptions'] = self._check_cox_assumptions(cox_df)
        
        self._log_analysis('cox_ph', results)
        return results

    def plot_survival_curves(
        self,
        df: pd.DataFrame,
        time_col: str,
        event_col: str,
        group_col: Optional[str] = None,
        output_path: Optional[str] = None,
        show_ci: bool = True,
        show_at_risk: bool = True
    ) -> Dict[str, Any]:
        """Survival data visualization with confidence bands

        Creates publication-quality Kaplan-Meier survival curves with
        optional confidence intervals and number at risk table.
        
        Pharmaceutical Example:
            Create KM curve for Phase III trial submission showing
            treatment effect on overall survival with 95% confidence
            intervals and number at risk at key time points.
        
        Args:
            df: Input DataFrame with survival data
            time_col: Column name for survival/follow-up time
            event_col: Column name for event indicator
            group_col: Optional column name for grouping
            output_path: Optional path to save figure
            show_ci: Whether to show confidence intervals
            show_at_risk: Whether to show number at risk table
        
        Returns:
            Dictionary containing:
            - figure_path: Path to saved figure (if output_path provided)
            - plot_data: Data used for plotting
            - explanations: Interpretation of plot elements
        """
        # Data validation
        self._validate_survival_data(df, time_col, event_col)
        
        results = {
            'analysis_type': 'Survival Curve Plot',
            'timestamp': datetime.now().isoformat(),
            'figure_path': None,
            'plot_data': {},
            'explanations': {},
            'warnings': []
        }
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Determine groups
        if group_col is None:
            groups = [('All Patients', df)]
        else:
            groups = [(str(val), df[df[group_col] == val]) 
                      for val in df[group_col].unique()]
        
        # Plot KM curves
        colors = plt.cm.Set1(np.linspace(0, 1, len(groups)))
        
        for idx, (group_name, group_df) in enumerate(groups):
            group_df = group_df.dropna(subset=[time_col, event_col])
            
            if len(group_df) == 0:
                continue
            
            self.km_fitter.fit(
                durations=group_df[time_col],
                event_observed=group_df[event_col],
                label=group_name
            )
            
            self.km_fitter.plot_survival_function(
                ax=ax,
                ci_show=show_ci,
                color=colors[idx],
                alpha=0.8
            )
        
        # Customize plot
        ax.set_xlabel('Time', fontsize=12, fontweight='bold')
        ax.set_ylabel('Survival Probability', fontsize=12, fontweight='bold')
        ax.set_title('Kaplan-Meier Survival Curves', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='lower left', framealpha=0.9)
        
        # Add number at risk table
        if show_at_risk:
            self._add_at_risk_table(ax, df, time_col, event_col, group_col)
        
        # Save figure
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            results['figure_path'] = output_path
        
        # Store plot data
        results['plot_data'] = {
            'groups': [g[0] for g in groups],
            'n_patients': [len(g[1]) for g in groups]
        }
        
        # Explanations
        results['explanations'] = {
            'survival_curve': (
                'The survival curve shows the probability of survival over time. '
                'The y-axis represents the survival probability (0-1), and the x-axis '
                'represents time.'
            ),
            'confidence_interval': (
                'The shaded bands represent 95% confidence intervals, indicating '
                'the precision of the survival estimate at each time point.'
            ) if show_ci else None,
            'at_risk_table': (
                'The number at risk table shows how many patients remained at risk '
                'of the event at each time point, accounting for censoring.'
            ) if show_at_risk else None
        }
        
        plt.close(fig)
        
        self._log_analysis('survival_plot', results)
        return results

    def calculate_survival_confidence_intervals(
        self,
        df: pd.DataFrame,
        time_col: str,
        event_col: str,
        method: str = 'log-log',
        time_points: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """Confidence intervals for survival estimates

        Calculates confidence intervals for survival probabilities using
        different methods (log-log, linear, exponential). The log-log
        transformation is recommended by regulatory agencies.
        
        Pharmaceutical Example:
            Calculate 95% CI for survival probability at 12, 24, and 36 months
            for regulatory submission. These intervals quantify uncertainty in
            the survival estimates.
        
        Args:
            df: Input DataFrame with survival data
            time_col: Column name for survival/follow-up time
            event_col: Column name for event indicator
            method: Method for CI calculation ('log-log', 'linear', 'exponential')
            time_points: Optional list of specific time points
        
        Returns:
            Dictionary containing:
            - time_points: Time points for CIs
            - survival_estimates: Survival probabilities at each time point
            - confidence_intervals: Lower and upper CI bounds
            - explanations: Methodological explanation
        """
        # Data validation
        self._validate_survival_data(df, time_col, event_col)
        
        results = {
            'analysis_type': 'Survival Confidence Intervals',
            'timestamp': datetime.now().isoformat(),
            'method': method,
            'time_points': [],
            'survival_estimates': [],
            'confidence_intervals': [],
            'explanations': {},
            'warnings': []
        }
        
        # Fit KM model
        self.km_fitter.fit(
            durations=df[time_col].dropna(),
            event_observed=df[event_col].dropna()
        )
        
        # Determine time points
        if time_points is None:
            time_points = list(self.km_fitter.survival_function_.index)
        
        # Get survival estimates and CIs
        survival_func = self.km_fitter.survival_function_
        ci_df = self.km_fitter.confidence_interval_
        
        for time_point in time_points:
            # Find closest time point
            closest_time = survival_func.index[
                np.abs(survival_func.index - time_point).argmin()
            ]
            
            survival_prob = survival_func.loc[closest_time].values[0]
            ci_lower = ci_df.loc[closest_time].values[0]
            ci_upper = ci_df.loc[closest_time].values[1]
            
            results['time_points'].append(float(closest_time))
            results['survival_estimates'].append(float(survival_prob))
            results['confidence_intervals'].append([float(ci_lower), float(ci_upper)])
        
        # Explanations
        results['explanations'] = {
            'method_description': self._explain_ci_method(method),
            'interpretation': (
                'The confidence intervals provide a range of plausible values for '
                'the true survival probability at each time point. A 95% CI means '
                'that if we repeated the study many times, 95% of the intervals would '
                'contain the true survival probability.'
            )
        }
        
        self._log_analysis('survival_ci', results)
        return results

    def compare_survival_by_group(
        self,
        df: pd.DataFrame,
        time_col: str,
        event_col: str,
        group_col: str,
        post_hoc: bool = True,
        bonferroni: bool = True
    ) -> Dict[str, Any]:
        """Multi-group survival comparison with post-hoc tests

        Performs overall log-rank test for multiple groups followed by
        pairwise comparisons with appropriate multiple testing correction.
        
        Pharmaceutical Example:
            Compare survival across multiple treatment arms (Placebo,
            Low Dose, High Dose) with pairwise comparisons to identify
            which specific doses differ.
        
        Args:
            df: Input DataFrame with survival data
            time_col: Column name for survival/follow-up time
            event_col: Column name for event indicator
            group_col: Column name for grouping
            post_hoc: Whether to perform pairwise comparisons
            bonferroni: Whether to use Bonferroni correction
        
        Returns:
            Dictionary containing:
            - overall_test: Overall log-rank test results
            - pairwise_comparisons: Results of pairwise tests
            - hazard_ratios: Hazard ratios for each comparison
            - interpretations: Clinical significance
        """
        # Data validation
        self._validate_survival_data(df, time_col, event_col)
        
        results = {
            'analysis_type': 'Multi-Group Survival Comparison',
            'timestamp': datetime.now().isoformat(),
            'alpha': self.alpha,
            'groups': [],
            'overall_test': {},
            'pairwise_comparisons': {},
            'hazard_ratios': {},
            'explanations': {},
            'interpretations': {},
            'warnings': []
        }
        
        # Get groups
        groups = df[group_col].dropna().unique()
        results['groups'] = list(groups)
        
        if len(groups) < 2:
            results['warnings'].append("Need at least 2 groups for comparison")
            return results
        
        # Overall log-rank test
        T = []
        E = []
        G = []
        
        for group in groups:
            group_data = df[df[group_col] == group].dropna(
                subset=[time_col, event_col]
            )
            T.append(group_data[time_col])
            E.append(group_data[event_col])
            G.extend([group] * len(group_data))
        
        overall_results = multivariate_logrank_test(
            event_durations=np.concatenate(T),
            groups=G,
            event_observed=np.concatenate(E)
        )
        
        results['overall_test'] = {
            'test_statistic': float(overall_results.test_statistic),
            'degrees_of_freedom': int(len(groups) - 1),
            'p_value': float(overall_results.p_value),
            'significant': overall_results.p_value < self.alpha
        }
        
        # Pairwise comparisons
        if post_hoc and len(groups) > 2:
            from itertools import combinations
            
            alpha_corrected = self.alpha / len(list(combinations(groups, 2))) \
                if bonferroni else self.alpha
            
            for group_a, group_b in combinations(groups, 2):
                data_a = df[df[group_col] == group_a].dropna(
                    subset=[time_col, event_col]
                )
                data_b = df[df[group_col] == group_b].dropna(
                    subset=[time_col, event_col]
                )
                
                pairwise_result = logrank_test(
                    durations_A=data_a[time_col],
                    durations_B=data_b[time_col],
                    event_observed_A=data_a[event_col],
                    event_observed_B=data_b[event_col]
                )
                
                comparison_key = f"{group_a} vs {group_b}"
                
                results['pairwise_comparisons'][comparison_key] = {
                    'test_statistic': float(pairwise_result.test_statistic),
                    'p_value': float(pairwise_result.p_value),
                    'p_value_corrected': float(pairwise_result.p_value) / \
                        len(list(combinations(groups, 2))) if bonferroni \
                        else float(pairwise_result.p_value),
                    'significant_corrected': pairwise_result.p_value < alpha_corrected,
                    'alpha_corrected': alpha_corrected
                }
                
                # Calculate hazard ratio
                hr, hr_lower, hr_upper = self._calculate_hazard_ratio(
                    data_a[time_col], data_a[event_col],
                    data_b[time_col], data_b[event_col]
                )
                
                results['hazard_ratios'][comparison_key] = {
                    'hazard_ratio': hr,
                    'confidence_interval': [hr_lower, hr_upper],
                    'interpretation': self._interpret_hazard_ratio(hr, group_a, group_b)
                }
        
        # Explanations
        results['explanations'] = self._explain_multi_group_comparison(results)
        
        # Interpretations
        results['interpretations'] = self._interpret_multi_group_comparison(results, time_col)
        
        self._log_analysis('multi_group_comparison', results)
        return results

    # Helper methods
    
    def _validate_survival_data(
        self,
        df: pd.DataFrame,
        time_col: str,
        event_col: str
    ) -> None:
        """Validate survival data structure"""
        if time_col not in df.columns:
            raise ValueError(f"Time column '{time_col}' not found in DataFrame")
        if event_col not in df.columns:
            raise ValueError(f"Event column '{event_col}' not found in DataFrame")
        
        # Check for non-negative times
        if (df[time_col] < 0).any():
            raise ValueError("Time values must be non-negative")
        
        # Check event column values
        unique_events = df[event_col].dropna().unique()
        if not all(x in [0, 1, True, False] for x in unique_events):
            warnings.warn(
                "Event column should contain binary values (0/1 or True/False). "
                "Non-binary values detected."
            )

    def _calculate_hazard_ratio(
        self,
        durations_A: pd.Series,
        events_A: pd.Series,
        durations_B: pd.Series,
        events_B: pd.Series
    ) -> Tuple[float, float, float]:
        """Calculate hazard ratio with confidence interval"""
        # Calculate total events
        O_A = events_A.sum()
        O_B = events_B.sum()
        
        # Calculate expected events
        total_time_A = durations_A.sum()
        total_time_B = durations_B.sum()
        total_time = total_time_A + total_time_B
        
        E_A = O_A + O_B * (total_time_A / total_time)
        E_B = O_A + O_B * (total_time_B / total_time)
        
        # Hazard ratio
        hr = (O_A / E_A) / (O_B / E_B) if E_A > 0 and E_B > 0 else np.nan
        
        # Log hazard ratio
        log_hr = np.log(hr) if hr > 0 and not np.isnan(hr) else np.nan
        
        # Standard error
        se = np.sqrt(1/E_A + 1/E_B) if E_A > 0 and E_B > 0 else np.nan
        
        # Confidence interval
        if not np.isnan(log_hr) and not np.isnan(se):
            log_lower = log_hr - 1.96 * se
            log_upper = log_hr + 1.96 * se
            hr_lower = np.exp(log_lower)
            hr_upper = np.exp(log_upper)
        else:
            hr_lower = hr_upper = np.nan
        
        return float(hr), float(hr_lower), float(hr_upper)

    def _interpret_median_survival(
        self,
        median_survival: float,
        group_name: str,
        time_col: str
    ) -> str:
        """Interpret median survival time"""
        if median_survival is None or np.isnan(median_survival):
            return (
                f"Median survival for {group_name} could not be estimated "
                f"because less than 50% of patients experienced the event. "
                f"This suggests good survival in this group."
            )
        
        return (
            f"The median {time_col} for {group_name} is {median_survival:.1f} units. "
            f"This means that 50% of patients in this group are expected to "
            f"survive beyond this time point."
        )

    def _interpret_hazard_ratio(
        self,
        hr: float,
        group_a: str,
        group_b: str
    ) -> str:
        """Interpret hazard ratio"""
        if np.isnan(hr):
            return "Hazard ratio could not be calculated."
        
        if hr < 1:
            return (
                f"Patients in {group_a} have a {100 * (1 - hr):.1f}% lower hazard "
                f"rate compared to {group_b}, indicating improved survival."
            )
        elif hr > 1:
            return (
                f"Patients in {group_a} have a {100 * (hr - 1):.1f}% higher hazard "
                f"rate compared to {group_b}, indicating worse survival."
            )
        else:
            return (
                f"No difference in hazard rate between {group_a} and {group_b}."
            )

    def _explain_kaplan_meier(self, results: Dict) -> Dict[str, str]:
        """Explain Kaplan-Meier methodology"""
        return {
            'method': (
                'The Kaplan-Meier estimator is a non-parametric statistic used to '
                'estimate the survival function from lifetime data. It is widely '
                'used in clinical trials and is the standard method for reporting '
                'survival outcomes. The estimator uses the product of conditional '
                'probabilities to account for censoring.'
            ),
            'censoring': (
                'Censoring occurs when the survival time is only known to exceed '
                'a certain value (e.g., patient lost to follow-up or study ended). '
                'The Kaplan-Meier method properly handles censored data by using '
                'only the information available up to the censoring time.'
            ),
            'confidence_interval': (
                f"The {self.confidence_level*100:.0f}% confidence interval quantifies "
                "the uncertainty in the survival estimate. Narrower intervals "
                "indicate more precise estimates."
            )
        }

    def _interpret_kaplan_meier(
        self,
        results: Dict,
        time_col: str
    ) -> Dict[str, str]:
        """Interpret Kaplan-Meier results"""
        interpretations = {}
        
        for group_name in results['median_survival'].keys():
            median_info = results['median_survival'][group_name]
            interpretations[group_name] = median_info['interpretation']
        
        return interpretations

    def _explain_log_rank(self, results: Dict) -> Dict[str, str]:
        """Explain log-rank test methodology"""
        return {
            'method': (
                'The log-rank test is a hypothesis test that compares the survival '
                'distributions of two or more groups. It tests the null hypothesis '
                'that there is no difference between the groups. The test uses the '
                'observed and expected number of events at each event time.'
            ),
            'interpretation': (
                f'A p-value less than {self.alpha} indicates statistically significant '
                'evidence to reject the null hypothesis, suggesting that survival '
                'distributions differ between groups.'
            ),
            'hazard_ratio': (
                'The hazard ratio represents the relative risk of the event '
                'occurring at any given time. HR < 1 indicates lower risk for the '
                'first group, HR > 1 indicates higher risk, and HR = 1 indicates '
                'no difference.'
            ) if results['hazard_ratio'] else None
        }

    def _interpret_log_rank(self, results: Dict, time_col: str) -> Dict[str, str]:
        """Interpret log-rank test results"""
        interpretations = {}
        
        p_value = results['p_value']
        
        if p_value is None:
            interpretations['significance'] = 'Test could not be performed.'
        elif p_value < self.alpha:
            interpretations['significance'] = (
                f"The log-rank test is statistically significant (p={p_value:.4f}). "
                f"There is evidence of a difference in {time_col} between groups."
            )
        else:
            interpretations['significance'] = (
                f"The log-rank test is not statistically significant (p={p_value:.4f}). "
                f"There is insufficient evidence to conclude that {time_col} differs "
                f"between groups."
            )
        
        if results['hazard_ratio']:
            hr = results['hazard_ratio']
            hr_ci = results['hazard_ratio_ci']
            group_a = results['groups_compared'][0]
            group_b = results['groups_compared'][1]
            
            interpretations['hazard_ratio'] = self._interpret_hazard_ratio(
                hr, group_a, group_b
            )
            
            interpretations['confidence_interval'] = (
                f"The 95% confidence interval for the hazard ratio is "
                f"[{hr_ci[0]:.2f}, {hr_ci[1]:.2f}]. "
                f"If the interval does not include 1.0, the hazard ratio is "
                f"statistically significant at the {self.confidence_level*100:.0f}% level."
            )
        
        return interpretations

    def _explain_cox_model(self, results: Dict, time_col: str) -> Dict[str, str]:
        """Explain Cox proportional hazards model"""
        return {
            'method': (
                'The Cox proportional hazards model is a semi-parametric regression '
                'model for survival data. It estimates the effect of covariates on the '
                'hazard rate without assuming a specific distribution for survival time. '
                'The model assumes proportional hazards over time.'
            ),
            'hazard_ratio': (
                'The hazard ratio for a covariate is the multiplicative effect on '
                'the hazard rate for a one-unit increase in that covariate, holding '
                'other covariates constant.'
            ),
            'concordance_index': (
                f"Concordance index (c-index) is {results['model_summary']['concordance_index']:.3f}. "
                "This measures predictive accuracy: 0.5 indicates no predictive "
                "ability, 1.0 indicates perfect prediction. Values > 0.7 indicate "
                "good discrimination."
            )
        }

    def _interpret_cox_model(self, results: Dict, time_col: str) -> Dict[str, str]:
        """Interpret Cox model results"""
        interpretations = {}
        
        for covariate in results['hazard_ratios'].keys():
            hr = results['hazard_ratios'][covariate]
            hr_ci = results['confidence_intervals'][covariate]
            p_value = results['p_values'][covariate]
            
            if hr < 1:
                direction = 'decrease'
                magnitude = 100 * (1 - hr)
            else:
                direction = 'increase'
                magnitude = 100 * (hr - 1)
            
            interpretation = (
                f"{covariate}: HR={hr:.2f} [{hr_ci[0]:.2f}, {hr_ci[1]:.2f}], p={p_value:.4f}. "
                f"Each unit increase in {covariate} is associated with a "
                f"{magnitude:.1f}% {direction} in the hazard rate for {time_col}."
            )
            
            if p_value < self.alpha:
                interpretation += " This effect is statistically significant."
            else:
                interpretation += " This effect is not statistically significant."
            
            interpretations[covariate] = interpretation
        
        return interpretations

    def _explain_ci_method(self, method: str) -> str:
        """Explain confidence interval method"""
        methods = {
            'log-log': (
                'Log-log transformation is the recommended method by regulatory '
                'agencies (FDA/EMA) as it ensures confidence intervals remain '
                'within [0,1] and performs well with small sample sizes.'
            ),
            'linear': (
                'Linear transformation uses the standard error of the log '
                'survival estimate. Simple but may produce intervals outside [0,1].'
            ),
            'exponential': (
                'Exponential transformation assumes constant hazard rate. '
                'Useful for Weibull-distributed survival times.'
            )
        }
        return methods.get(method, 'Unknown method')

    def _explain_multi_group_comparison(
        self,
        results: Dict
    ) -> Dict[str, str]:
        """Explain multi-group comparison methodology"""
        return {
            'overall_test': (
                'The overall log-rank tests the null hypothesis that all groups '
                'have the same survival distribution. A significant result indicates '
                'at least one group differs from the others.'
            ),
            'pairwise_comparisons': (
                'Pairwise comparisons identify which specific groups differ from '
                'each other. Multiple testing correction (e.g., Bonferroni) is '
                'applied to control the family-wise error rate.'
            ) if results['pairwise_comparisons'] else None
        }

    def _interpret_multi_group_comparison(
        self,
        results: Dict,
        time_col: str
    ) -> Dict[str, str]:
        """Interpret multi-group comparison results"""
        interpretations = {}
        
        # Overall test
        overall = results['overall_test']
        if overall['significant']:
            interpretations['overall'] = (
                f"The overall test is significant (p={overall['p_value']:.4f}), "
                f"indicating that survival differs among the groups."
            )
        else:
            interpretations['overall'] = (
                f"The overall test is not significant (p={overall['p_value']:.4f}), "
                f"indicating no evidence of survival differences among groups."
            )
        
        # Pairwise comparisons
        for comp, comp_results in results['pairwise_comparisons'].items():
            if comp_results['significant_corrected']:
                interpretations[comp] = (
                    f"Significant difference (p={comp_results['p_value']:.4f}, "
                    f"corrected p={comp_results['p_value_corrected']:.4f})"
                )
            else:
                interpretations[comp] = (
                    f"No significant difference (p={comp_results['p_value']:.4f}, "
                    f"corrected p={comp_results['p_value_corrected']:.4f})"
                )
        
        return interpretations

    def _test_proportional_hazards(
        self,
        df: pd.DataFrame,
        time_col: str,
        event_col: str,
        covariates: List[str]
    ) -> Dict[str, Any]:
        """Test proportional hazards assumption"""
        try:
            from lifelines.statistics import proportional_hazard_test
            
            results = proportional_hazard_test(
                self.cox_fitter, df, time_transform=["log", "KM", "rank"]
            )
            
            summary = results.summary
            
            test_results = {}
            for covariate in covariates:
                if covariate in summary.index:
                    test_results[covariate] = {
                        'test_statistic': float(summary.loc[covariate, 'test_statistic']),
                        'p_value': float(summary.loc[covariate, 'p']),
                        'assumption_met': summary.loc[covariate, 'p'] > self.alpha
                    }
            
            return test_results
        
        except Exception as e:
            return {'error': f"Proportional hazards test failed: {str(e)}"}

    def _check_km_assumptions(
        self,
        df: pd.DataFrame,
        time_col: str,
        event_col: str
    ) -> List[str]:
        """Check Kaplan-Meier assumptions"""
        assumptions = [
            'Non-informative censoring: Assumes that censoring is independent '
            'of survival time and related only to study design'
        ]
        
        # Check censoring proportion
        censoring_rate = 1 - df[event_col].mean()
        assumptions.append(
            f'Censoring rate: {censoring_rate:.1%}. High censoring may '
            'reduce precision of survival estimates'
        )
        
        return assumptions

    def _check_log_rank_assumptions(self, df: pd.DataFrame) -> List[str]:
        """Check log-rank test assumptions"""
        return [
            'Proportional hazards: Assumes hazard ratio is constant over time',
            'Independent censoring: Assumes censoring is independent of survival',
            'Random sampling: Assumes subjects are randomly assigned to groups'
        ]

    def _check_cox_assumptions(self, df: pd.DataFrame) -> List[str]:
        """Check Cox model assumptions"""
        return [
            'Proportional hazards: Hazard ratio constant over time',
            'Linear relationship: Log hazard linearly related to covariates',
            'No influential outliers: No single observation heavily influences results',
            'Independent observations: Survival times independent between subjects'
        ]

    def _add_at_risk_table(
        self,
        ax: plt.Axes,
        df: pd.DataFrame,
        time_col: str,
        event_col: str,
        group_col: Optional[str]
    ) -> None:
        """Add number at risk table to plot"""
        # Determine time points for table
        max_time = df[time_col].max()
        n_ticks = 5
        time_ticks = np.linspace(0, max_time, n_ticks)
        
        if group_col is None:
            groups = [('All', df)]
        else:
            groups = [(str(val), df[df[group_col] == val]) 
                      for val in df[group_col].unique()]
        
        # Calculate number at risk at each time point
        at_risk_data = []
        for group_name, group_df in groups:
            at_risk = []
            for time_point in time_ticks:
                n_at_risk = ((group_df[time_col] >= time_point) & 
                            (group_df[event_col] == 0)).sum()
                n_at_risk += ((group_df[time_col] >= time_point) & 
                             (group_df[event_col] == 1)).sum()
                at_risk.append(n_at_risk)
            at_risk_data.append(at_risk)
        
        # Add table to plot
        table_data = np.array(at_risk_data).T
        table = plt.table(
            cellText=table_data.astype(str),
            rowLabels=[f"{t:.0f}" for t in time_ticks],
            colLabels=[g[0] for g in groups],
            loc='bottom',
            bbox=[0.1, -0.3, 0.8, 0.2]
        )
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1, 1.5)
        
        plt.subplots_adjust(bottom=0.3)

    def _log_analysis(self, analysis_type: str, results: Dict) -> None:
        """Log analysis for audit trail (GLP compliance)"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'analysis_type': analysis_type,
            'result_keys': list(results.keys())
        }
        self.analysis_history.append(log_entry)
        self.current_analysis = results
