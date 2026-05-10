"""
Comprehensive Test Suite for Survival Analysis Module

Tests Kaplan-Meier, Cox regression, and integration with 3-tier framework.
"""

import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from modules.statistics.survival import SurvivalAnalyzer, is_survival_available
from modules.statistics.engine import StatisticalEngine


class TestSurvivalAnalysis(unittest.TestCase):
    """Test suite for survival analysis functionality."""
    
    def setUp(self):
        """Set up test data."""
        if not is_survival_available():
            self.skipTest("Survival analysis not available (lifelines not installed)")
        
        # Create sample clinical trial data
        np.random.seed(42)
        n = 50
        
        # Treatment group: better survival
        treatment_time = np.random.exponential(scale=24, size=n//2)
        treatment_event = np.random.binomial(1, 0.4, size=n//2)
        
        # Control group: worse survival
        control_time = np.random.exponential(scale=12, size=n//2)
        control_event = np.random.binomial(1, 0.6, size=n//2)
        
        self.test_data = pd.DataFrame({
            'patient_id': range(n),
            'time': np.concatenate([treatment_time, control_time]),
            'event': np.concatenate([treatment_event, control_event]),
            'group': ['treatment'] * (n//2) + ['control'] * (n//2),
            'age': np.random.normal(60, 10, n),
            'biomarker': np.random.normal(100, 20, n)
        })
        
        self.analyzer = SurvivalAnalyzer()
    
    def test_kaplan_meier_single_group(self):
        """Test 1: Basic Kaplan-Meier curve for single group."""
        result = self.analyzer.kaplan_meier(
            data=self.test_data,
            time_col='time',
            event_col='event'
        )
        
        self.assertEqual(result.analysis_type, 'kaplan_meier')
        self.assertIn('overall', result.median_survival)
        self.assertIsNotNone(result.plot_base64)
        self.assertIsNone(result.p_value)  # No groups to compare
    
    def test_kaplan_meier_two_groups(self):
        """Test 2: Kaplan-Meier with group comparison and log-rank test."""
        result = self.analyzer.kaplan_meier(
            data=self.test_data,
            time_col='time',
            event_col='event',
            group_col='group'
        )
        
        self.assertEqual(result.analysis_type, 'kaplan_meier')
        self.assertIn('treatment', result.median_survival)
        self.assertIn('control', result.median_survival)
        self.assertIsNotNone(result.p_value)  # Log-rank test
        self.assertIsNotNone(result.plot_base64)
        
        # Treatment should have better survival
        self.assertGreater(
            result.median_survival['treatment'],
            result.median_survival['control']
        )
    
    def test_cox_regression_single_covariate(self):
        """Test 3: Simple Cox regression with one predictor."""
        result = self.analyzer.cox_regression(
            data=self.test_data,
            time_col='time',
            event_col='event',
            covariates=['age']
        )
        
        self.assertEqual(result.analysis_type, 'cox_regression')
        self.assertIn('age', result.hazard_ratios)
        self.assertIsNotNone(result.survival_table)
        self.assertIsNotNone(result.plot_base64)
    
    def test_cox_regression_multivariate(self):
        """Test 4: Multivariate Cox regression."""
        result = self.analyzer.cox_regression(
            data=self.test_data,
            time_col='time',
            event_col='event',
            covariates=['age', 'biomarker']
        )
        
        self.assertEqual(result.analysis_type, 'cox_regression')
        self.assertIn('age', result.hazard_ratios)
        self.assertIn('biomarker', result.hazard_ratios)
        self.assertEqual(len(result.hazard_ratios), 2)
    
    def test_censored_data_handling(self):
        """Test 8: Proper handling of censored observations."""
        # Create data with known censoring
        censored_data = pd.DataFrame({
            'time': [1, 2, 3, 4, 5],
            'event': [1, 0, 1, 0, 1],  # 0 = censored
            'group': ['A', 'A', 'B', 'B', 'B']
        })
        
        result = self.analyzer.kaplan_meier(
            data=censored_data,
            time_col='time',
            event_col='event',
            group_col='group'
        )
        
        self.assertEqual(result.analysis_type, 'kaplan_meier')
        # Should handle censored data without errors
        self.assertIsNotNone(result.median_survival)
    
    def test_median_survival_calculation(self):
        """Test 9: Median survival time calculation with CI."""
        result = self.analyzer.kaplan_meier(
            data=self.test_data,
            time_col='time',
            event_col='event'
        )
        
        median = result.median_survival.get('overall')
        self.assertIsNotNone(median)
        self.assertGreater(median, 0)
    
    def test_plot_generation(self):
        """Test 10: Visualization output (base64 encoded)."""
        result = self.analyzer.kaplan_meier(
            data=self.test_data,
            time_col='time',
            event_col='event',
            group_col='group'
        )
        
        self.assertIsNotNone(result.plot_base64)
        self.assertIsInstance(result.plot_base64, str)
        # Base64 should be non-empty
        self.assertGreater(len(result.plot_base64), 100)


class TestSurvivalIntegration(unittest.TestCase):
    """Test integration with StatisticalEngine and 3-tier framework."""
    
    def setUp(self):
        """Set up test data."""
        if not is_survival_available():
            self.skipTest("Survival analysis not available")
        
        self.engine = StatisticalEngine()
        
        # Sample data as list of dicts (API format)
        self.data = [
            {'time': 12, 'event': 1, 'group': 'treatment'},
            {'time': 24, 'event': 0, 'group': 'treatment'},
            {'time': 6, 'event': 1, 'group': 'control'},
            {'time': 18, 'event': 1, 'group': 'control'},
            {'time': 30, 'event': 0, 'group': 'treatment'},
            {'time': 9, 'event': 1, 'group': 'control'},
        ]
    
    def test_survival_tier1_output(self):
        """Test 5: Tier 1 (Basic) - Plain English summary."""
        result = self.engine.analyze(
            data=self.data,
            design='survival',
            tier='basic'
        )
        
        self.assertEqual(result['tier'], 'basic')
        self.assertIn('summary', result)
        self.assertIn('raw', result)
        self.assertEqual(result['raw']['type'], 'survival')
    
    def test_survival_tier2_output(self):
        """Test 6: Tier 2 (Analytical) - Diagnostics & assumptions."""
        result = self.engine.analyze(
            data=self.data,
            design='survival',
            tier='analytical'
        )
        
        self.assertEqual(result['tier'], 'analytical')
        self.assertIn('summary', result)
        self.assertIn('details', result)
    
    def test_survival_tier3_output(self):
        """Test 7: Tier 3 (Advanced) - Methodology text."""
        result = self.engine.analyze(
            data=self.data,
            design='survival',
            tier='advanced'
        )
        
        self.assertEqual(result['tier'], 'advanced')
        self.assertIn('methodology_text', result)
        self.assertIn('Kaplan-Meier', result['methodology_text'])
        self.assertIn('log-rank', result['methodology_text'])


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
