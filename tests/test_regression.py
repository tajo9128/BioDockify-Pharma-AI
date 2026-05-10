"""
Test Suite for Enhanced Regression Module

Tests logistic regression, ROC curves, odds ratios, and model diagnostics.
"""

import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
from modules.statistics.regression import RegressionAnalyzer, is_regression_available


class TestLogisticRegression(unittest.TestCase):
    """Test suite for logistic regression functionality."""
    
    def setUp(self):
        """Set up test data."""
        np.random.seed(42)
        n = 100
        
        # Create sample data with known relationship
        self.test_data = pd.DataFrame({
            'outcome': np.random.binomial(1, 0.5, n),
            'age': np.random.normal(50, 10, n),
            'biomarker': np.random.normal(100, 20, n),
            'treatment': np.random.binomial(1, 0.5, n)
        })
        
        # Create correlated outcome for better testing
        prob = 1 / (1 + np.exp(-(self.test_data['age'] - 50) / 10))
        self.test_data['outcome_correlated'] = np.random.binomial(1, prob)
        
        self.analyzer = RegressionAnalyzer()
    
    def test_logistic_single_predictor(self):
        """Test 1: Logistic regression with single predictor."""
        result = self.analyzer.logistic_regression(
            data=self.test_data,
            outcome_col='outcome',
            predictors=['age']
        )
        
        self.assertIn('age', result.odds_ratios)
        self.assertIn('intercept', result.coefficients)
        self.assertGreater(result.auc, 0)
        self.assertLessEqual(result.auc, 1)
    
    def test_logistic_multiple_predictors(self):
        """Test 2: Logistic regression with multiple predictors."""
        result = self.analyzer.logistic_regression(
            data=self.test_data,
            outcome_col='outcome',
            predictors=['age', 'biomarker', 'treatment']
        )
        
        self.assertEqual(len(result.odds_ratios), 4)  # 3 predictors + intercept
        self.assertIn('age', result.odds_ratios)
        self.assertIn('biomarker', result.odds_ratios)
        self.assertIn('treatment', result.odds_ratios)
    
    def test_odds_ratios_positive(self):
        """Test 3: Odds ratios should always be positive."""
        result = self.analyzer.logistic_regression(
            data=self.test_data,
            outcome_col='outcome',
            predictors=['age', 'biomarker']
        )
        
        for name, or_val in result.odds_ratios.items():
            self.assertGreater(or_val, 0)
    
    def test_confidence_intervals(self):
        """Test 4: Confidence intervals should contain odds ratio."""
        if not is_regression_available():
            self.skipTest("sklearn not available")
        
        result = self.analyzer.logistic_regression(
            data=self.test_data,
            outcome_col='outcome_correlated',
            predictors=['age']
        )
        
        # CI should contain the point estimate
        or_age = result.odds_ratios['age']
        ci = result.confidence_intervals['age']
        
        if not np.isnan(ci[0]):
            self.assertLessEqual(ci[0], or_age * 1.1)  # Allow some tolerance
            self.assertGreaterEqual(ci[1], or_age * 0.9)
    
    def test_auc_range(self):
        """Test 5: AUC should be between 0 and 1."""
        result = self.analyzer.logistic_regression(
            data=self.test_data,
            outcome_col='outcome',
            predictors=['age']
        )
        
        self.assertGreaterEqual(result.auc, 0)
        self.assertLessEqual(result.auc, 1)
    
    def test_model_summary_generated(self):
        """Test 6: Model summary text should be generated."""
        result = self.analyzer.logistic_regression(
            data=self.test_data,
            outcome_col='outcome',
            predictors=['age']
        )
        
        self.assertIsNotNone(result.model_summary)
        self.assertIn('AUC', result.model_summary)


class TestROCAnalysis(unittest.TestCase):
    """Test suite for ROC curve analysis."""
    
    def setUp(self):
        """Set up test data."""
        np.random.seed(42)
        self.analyzer = RegressionAnalyzer()
        
        # Perfect separation
        self.y_true_perfect = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1])
        self.y_prob_perfect = np.array([0.1, 0.2, 0.3, 0.4, 0.45, 0.55, 0.6, 0.7, 0.8, 0.9])
        
        # Random
        self.y_true_random = np.random.binomial(1, 0.5, 100)
        self.y_prob_random = np.random.uniform(0, 1, 100)
    
    def test_roc_perfect_auc(self):
        """Test 7: Perfect separation should have high AUC."""
        result = self.analyzer.calculate_roc(
            y_true=self.y_true_perfect,
            y_prob=self.y_prob_perfect
        )
        
        self.assertGreater(result.auc, 0.9)
    
    def test_roc_random_auc(self):
        """Test 8: Random predictions should have AUC near 0.5."""
        result = self.analyzer.calculate_roc(
            y_true=self.y_true_random,
            y_prob=self.y_prob_random
        )
        
        self.assertGreater(result.auc, 0.3)
        self.assertLess(result.auc, 0.7)
    
    def test_optimal_threshold(self):
        """Test 9: Optimal threshold should be between 0 and 1."""
        result = self.analyzer.calculate_roc(
            y_true=self.y_true_perfect,
            y_prob=self.y_prob_perfect
        )
        
        self.assertGreaterEqual(result.optimal_threshold, 0)
        self.assertLessEqual(result.optimal_threshold, 1)
    
    def test_sensitivity_specificity_range(self):
        """Test 10: Sensitivity and specificity should be 0-1."""
        result = self.analyzer.calculate_roc(
            y_true=self.y_true_perfect,
            y_prob=self.y_prob_perfect
        )
        
        self.assertGreaterEqual(result.sensitivity, 0)
        self.assertLessEqual(result.sensitivity, 1)
        self.assertGreaterEqual(result.specificity, 0)
        self.assertLessEqual(result.specificity, 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
