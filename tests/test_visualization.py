"""
Test Suite for Statistical Visualization Module

Tests Q-Q plots, forest plots, publication tables, and bootstrap CI.
"""

import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
from modules.statistics.visualization import StatisticalVisualizer, is_visualization_available


class TestQQPlots(unittest.TestCase):
    """Test suite for Q-Q plot and normality testing."""
    
    def setUp(self):
        """Set up test data."""
        np.random.seed(42)
        self.visualizer = StatisticalVisualizer()
        
        # Normal data
        self.normal_data = np.random.normal(100, 15, 100)
        
        # Non-normal data (exponential)
        self.skewed_data = np.random.exponential(5, 100)
    
    def test_qq_normal_data(self):
        """Test 1: Normal data should pass normality test."""
        plot, result = self.visualizer.qq_plot(self.normal_data)
        
        self.assertTrue(result.is_normal)
        self.assertGreater(result.shapiro_pvalue, 0.05)
    
    def test_qq_skewed_data(self):
        """Test 2: Skewed data should fail normality test."""
        plot, result = self.visualizer.qq_plot(self.skewed_data)
        
        self.assertFalse(result.is_normal)
        self.assertLess(result.shapiro_pvalue, 0.05)
    
    def test_qq_plot_generated(self):
        """Test 3: Q-Q plot should be generated."""
        if not is_visualization_available():
            self.skipTest("matplotlib not available")
        
        plot, result = self.visualizer.qq_plot(self.normal_data)
        
        self.assertIsNotNone(plot)
        self.assertIsInstance(plot, str)
        self.assertGreater(len(plot), 100)  # Base64 should be substantial
    
    def test_normality_interpretation(self):
        """Test 4: Interpretation text should be generated."""
        plot, result = self.visualizer.qq_plot(self.normal_data)
        
        self.assertIsNotNone(result.interpretation)
        self.assertGreater(len(result.interpretation), 10)


class TestForestPlots(unittest.TestCase):
    """Test suite for forest plot generation."""
    
    def setUp(self):
        """Set up test data."""
        self.visualizer = StatisticalVisualizer()
        
        self.estimates = {
            'Age': 1.5,
            'Biomarker': 0.8,
            'Treatment': 2.1
        }
        
        self.cis = {
            'Age': (1.2, 1.9),
            'Biomarker': (0.5, 1.3),
            'Treatment': (1.5, 2.8)
        }
    
    def test_forest_plot_generated(self):
        """Test 5: Forest plot should be generated."""
        if not is_visualization_available():
            self.skipTest("matplotlib not available")
        
        plot = self.visualizer.forest_plot(
            estimates=self.estimates,
            confidence_intervals=self.cis
        )
        
        self.assertIsNotNone(plot)
        self.assertIsInstance(plot, str)


class TestPublicationTables(unittest.TestCase):
    """Test suite for publication table generation."""
    
    def setUp(self):
        """Set up test data."""
        np.random.seed(42)
        self.visualizer = StatisticalVisualizer()
        
        self.test_data = pd.DataFrame({
            'group': ['A', 'A', 'A', 'B', 'B', 'B'],
            'value1': [10, 12, 11, 20, 22, 21],
            'value2': [5, 6, 5.5, 8, 9, 8.5]
        })
    
    def test_summary_table_overall(self):
        """Test 6: Summary table without groups."""
        result = self.visualizer.create_summary_table(self.test_data)
        
        self.assertIn('formatted_table', result)
        self.assertIn('markdown', result)
        self.assertIn('latex', result)
    
    def test_summary_table_grouped(self):
        """Test 7: Summary table with groups."""
        result = self.visualizer.create_summary_table(
            self.test_data,
            group_col='group'
        )
        
        self.assertIn('formatted_table', result)
        self.assertGreater(len(result['formatted_table']), 0)
    
    def test_results_table(self):
        """Test 8: Results table generation."""
        estimates = {'Age': 1.5, 'Treatment': 2.0}
        cis = {'Age': (1.2, 1.8), 'Treatment': (1.5, 2.5)}
        pvals = {'Age': 0.02, 'Treatment': 0.001}
        
        result = self.visualizer.create_results_table(estimates, cis, pvals)
        
        self.assertIn('markdown', result)
        self.assertIn('p-value', result['markdown'])


class TestBootstrap(unittest.TestCase):
    """Test suite for bootstrap confidence intervals."""
    
    def setUp(self):
        """Set up test data."""
        np.random.seed(42)
        self.visualizer = StatisticalVisualizer()
        self.data = np.random.normal(100, 15, 50)
    
    def test_bootstrap_mean(self):
        """Test 9: Bootstrap CI for mean."""
        result = self.visualizer.bootstrap_ci(
            self.data,
            statistic='mean',
            n_bootstrap=500
        )
        
        self.assertIsNotNone(result.estimate)
        self.assertLess(result.ci_lower, result.estimate)
        self.assertGreater(result.ci_upper, result.estimate)
    
    def test_bootstrap_median(self):
        """Test 10: Bootstrap CI for median."""
        result = self.visualizer.bootstrap_ci(
            self.data,
            statistic='median',
            n_bootstrap=500
        )
        
        self.assertIsNotNone(result.estimate)
        self.assertEqual(result.n_bootstrap, 500)


if __name__ == '__main__':
    unittest.main(verbosity=2)
