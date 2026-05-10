"""
Test Suite for Power Analysis Module

Tests power calculations, sample size estimation, and effect size interpretation.
"""

import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from modules.statistics.power import PowerAnalyzer, is_power_available


class TestPowerAnalysis(unittest.TestCase):
    """Test suite for power analysis functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = PowerAnalyzer()
    
    def test_power_ttest_two_sample(self):
        """Test 1: Power calculation for two-sample t-test."""
        result = self.analyzer.calculate_power(
            effect_size=0.5,  # Medium effect
            n=64,  # Per group
            alpha=0.05,
            test_type='two_sample'
        )
        
        self.assertEqual(result.test_type, 'two_sample')
        self.assertGreater(result.power, 0.7)  # Should be ~0.8
        self.assertLess(result.power, 0.95)
        self.assertIn('Adequate', result.interpretation)
    
    def test_power_anova(self):
        """Test 2: Power calculation for ANOVA."""
        result = self.analyzer.calculate_power(
            effect_size=0.25,  # Cohen's f
            n=30,  # Per group
            alpha=0.05,
            test_type='anova',
            n_groups=3
        )
        
        self.assertEqual(result.test_type, 'anova')
        self.assertGreater(result.power, 0)
        self.assertLessEqual(result.power, 1)
    
    def test_power_correlation(self):
        """Test 3: Power calculation for correlation."""
        result = self.analyzer.calculate_power(
            effect_size=0.3,  # r = 0.3
            n=100,
            alpha=0.05,
            test_type='correlation'
        )
        
        self.assertEqual(result.test_type, 'correlation')
        self.assertGreater(result.power, 0.5)
    
    def test_sample_size_ttest(self):
        """Test 4: Sample size calculation for t-test."""
        result = self.analyzer.calculate_sample_size(
            effect_size=0.5,  # Medium effect
            power=0.8,
            alpha=0.05,
            test_type='two_sample'
        )
        
        self.assertEqual(result.test_type, 'two_sample')
        self.assertGreater(result.required_n, 0)
        self.assertIsNotNone(result.per_group_n)
        self.assertIn('participants', result.interpretation.lower())
    
    def test_sample_size_anova(self):
        """Test 5: Sample size calculation for ANOVA."""
        result = self.analyzer.calculate_sample_size(
            effect_size=0.25,
            power=0.8,
            alpha=0.05,
            test_type='anova',
            n_groups=4
        )
        
        self.assertIsNotNone(result.per_group_n)
        self.assertEqual(result.required_n, result.per_group_n * 4)
    
    def test_effect_size_from_data(self):
        """Test 6: Calculate effect size from raw data."""
        # Create groups with known difference
        np.random.seed(42)
        group1 = np.random.normal(100, 15, 50)
        group2 = np.random.normal(110, 15, 50)  # Difference of ~10
        
        result = self.analyzer.effect_size_from_data(
            group1=group1.tolist(),
            group2=group2.tolist()
        )
        
        self.assertIn('cohens_d', result)
        self.assertIn('hedges_g', result)
        self.assertIn('interpretation', result)
        # Should be medium to large effect (~0.67, but can vary)
        self.assertGreater(result['cohens_d'], 0.3)
        self.assertLess(result['cohens_d'], 1.5)
    
    def test_power_curve_generation(self):
        """Test 7: Generate power curve data."""
        result = self.analyzer.generate_power_curve(
            effect_size=0.5,
            alpha=0.05,
            test_type='two_sample',
            n_range=(10, 100)
        )
        
        self.assertIn('n', result)
        self.assertIn('power', result)
        self.assertEqual(len(result['n']), len(result['power']))
        
        # Power should increase with N
        self.assertLess(result['power'][0], result['power'][-1])
    
    def test_effect_size_interpretation(self):
        """Test 8: Effect size interpretation."""
        # Small effect
        result_small = self.analyzer.calculate_power(
            effect_size=0.2, n=50, test_type='two_sample'
        )
        
        # Large effect
        result_large = self.analyzer.calculate_power(
            effect_size=0.8, n=50, test_type='two_sample'
        )
        
        # Large effect should have higher power
        self.assertGreater(result_large.power, result_small.power)
    
    def test_underpowered_detection(self):
        """Test 9: Detect underpowered study."""
        result = self.analyzer.calculate_power(
            effect_size=0.2,  # Small effect
            n=10,  # Too few
            alpha=0.05,
            test_type='two_sample'
        )
        
        self.assertLess(result.power, 0.5)
        self.assertIn('underpowered', result.interpretation.lower())
    
    def test_adequate_power_recommendation(self):
        """Test 10: Recommendations for adequate power."""
        result = self.analyzer.calculate_power(
            effect_size=0.5,
            n=64,
            alpha=0.05,
            test_type='two_sample'
        )
        
        self.assertIsNotNone(result.recommendation)
        # Should mention sample size
        self.assertTrue(
            'adequate' in result.recommendation.lower() or 
            'increase' in result.recommendation.lower()
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)
