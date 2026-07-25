"""
Dissolution Profile Comparison — f2/f1 calculations.

FDA Guidance: https://www.fda.gov/regulatory-information/search-fda-guidance-documents/dissolution-testing-and-acceptance-criteria-immediate-release-solid-oral-dosage-forms
EMA Guideline: https://www.ema.europa.eu/en/investigation-bioavailability-bioequivalence
"""

import numpy as np
from typing import List, Dict, Any


def calculate_f2(test_dissolution: List[float], reference_dissolution: List[float]) -> Dict[str, Any]:
    """Calculate f2 similarity factor (FDA 1997 guidance).
    
    f2 = 50 * log10(sqrt(1 + (1/n) * Σ(Rt - Tt)²))
    
    Args:
        test_dissolution: List of % dissolved at each time point for test
        reference_dissolution: List of % dissolved at each time point for reference
    
    Returns:
        Dict with f2 value, interpretation, and guidance reference
    """
    if len(test_dissolution) != len(reference_dissolution):
        return {"status": "error", "error": "Test and reference must have same number of time points"}
    
    if len(test_dissolution) < 3:
        return {"status": "error", "error": "Need at least 3 time points for f2 calculation"}
    
    test = np.array(test_dissolution, dtype=float)
    ref = np.array(reference_dissolution, dtype=float)
    
    # Check for trivial case (100% dissolved)
    if np.any(test > 100) or np.any(ref > 100):
        return {"status": "error", "error": "Dissolution values must be 0-100%"}
    
    # f2 = 50 * log10(sqrt(1 + (1/n) * sum((Rt - Tt)^2)))
    # where Rt = reference, Tt = test
    diff_squared = np.sum((ref - test) ** 2)
    n = len(test)
    
    inner = 1 + (1/n) * diff_squared
    if inner <= 0:
        f2 = 0.0
    else:
        f2 = 50 * np.log10(np.sqrt(inner))
    
    # f1 difference factor (FDA 1997)
    f1_num = np.sum(np.abs(ref - test))
    f1_den = np.sum(ref)
    f1 = (f1_num / f1_den) * 100 if f1_den > 0 else 0
    
    # Interpretation
    if f2 >= 50:
        interpretation = "Dissolution profiles are SIMILAR (f2 ≥ 50)"
        similarity = "Similar"
    else:
        interpretation = "Dissolution profiles are DIFFERENT (f2 < 50)"
        similarity = "Different"
    
    return {
        "status": "ok",
        "f2": round(f2, 2),
        "f1": round(f1, 2),
        "similarity": similarity,
        "interpretation": interpretation,
        "time_points": n,
        "reference_mean_dissolution": round(float(np.mean(ref)), 1),
        "test_mean_dissolution": round(float(np.mean(test)), 1),
        "guideline": "FDA Guidance for Industry: Dissolution Testing and Acceptance Criteria for Immediate-Release Solid Oral Dosage Forms (1997)"
    }


def calculate_f1(test_dissolution: List[float], reference_dissolution: List[float]) -> Dict[str, Any]:
    """Calculate f1 difference factor (FDA 1997 guidance).
    
    f1 = (Σ|Rt - Tt| / ΣRt) * 100
    
    Args:
        test_dissolution: List of % dissolved at each time point for test
        reference_dissolution: List of % dissolved at each time point for reference
    
    Returns:
        Dict with f1 value and interpretation
    """
    if len(test_dissolution) != len(reference_dissolution):
        return {"status": "error", "error": "Test and reference must have same number of time points"}
    
    test = np.array(test_dissolution, dtype=float)
    ref = np.array(reference_dissolution, dtype=float)
    
    f1_num = np.sum(np.abs(ref - test))
    f1_den = np.sum(ref)
    f1 = (f1_num / f1_den) * 100 if f1_den > 0 else 0
    
    if f1 <= 15:
        interpretation = "Dissolution profiles are SIMILAR (f1 ≤ 15)"
    else:
        interpretation = "Dissolution profiles are DIFFERENT (f1 > 15)"
    
    return {
        "status": "ok",
        "f1": round(f1, 2),
        "interpretation": interpretation,
        "time_points": len(test),
        "guideline": "FDA Guidance for Industry (1997)"
    }
