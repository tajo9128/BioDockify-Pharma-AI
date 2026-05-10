
# Test suite for multiplicity_control module
import sys
sys.path.insert(0, '/a0/usr/projects/biodockify_ai')

import numpy as np
from modules.statistics.multiplicity_control import MultiplicityControl

def test_basic_functionality():
    """Test basic functionality of MultiplicityControl"""
    mc = MultiplicityControl(alpha=0.05)
    pvalues = np.array([0.012, 0.023, 0.045, 0.089, 0.156])
    test_names = [f"Test {i+1}" for i in range(len(pvalues))]

    # Test all 10 methods
    methods = [
        'bonferroni_correction',
        'holm_bonferroni_correction',
        'benjamini_hochberg_fdr',
        'benjamini_yekutieli_fdr',
        'sidak_correction',
        'hochberg_correction',
        'hommel_correction',
        'calculate_adjusted_pvalues',
        'family_wise_error_rate',
        'compare_correction_methods'
    ]

    print("Testing all 10 methods...")
    for method in methods:
        try:
            if method == 'calculate_adjusted_pvalues':
                result = getattr(mc, method)(pvalues, method='holm', test_names=test_names)
            elif method == 'family_wise_error_rate':
                result = getattr(mc, method)(pvalues, method='holm', test_names=test_names)
            elif method == 'compare_correction_methods':
                result = getattr(mc, method)(pvalues, test_names)
            else:
                result = getattr(mc, method)(pvalues, test_names)
            print(f"  OK {method}")
        except Exception as e:
            print(f"  FAIL {method}: {e}")
            return False

    return True

if __name__ == "__main__":
    success = test_basic_functionality()
    if success:
        print("All tests passed!")
    else:
        print("Some tests failed!")
