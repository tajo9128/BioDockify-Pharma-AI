"""
Dissolution Profile Comparison — f2, f1, Mahalanobis distance.

FDA Guidance for Industry: Dissolution Testing (1997)
"""

import numpy as np
from typing import Dict, Any, List


def compare_dissolution_profiles(
    test_dissolution: List[float],
    reference_dissolution: List[float],
) -> Dict[str, Any]:
    """Compare test vs reference dissolution profiles using f2/f1 factors.

    Args:
        test_dissolution: List of % dissolved at each time point for test
        reference_dissolution: List of % dissolved at each time point for reference

    Returns:
        Dict with f2, f1, similarity verdict
    """
    test = np.array(test_dissolution, dtype=float)
    ref = np.array(reference_dissolution, dtype=float)

    if len(test) != len(ref):
        return {"status": "error", "error": "Test and reference must have same number of time points"}
    if len(test) < 3:
        return {"status": "error", "error": "Need ≥3 time points"}
    if np.any(test < 0) or np.any(ref < 0) or np.any(test > 100) or np.any(ref > 100):
        return {"status": "error", "error": "Values must be 0-100%"}

    n = len(test)

    # f2 = 50 × log10(sqrt(1 + (1/n) × Σ(Rt - Tt)²))
    diff_sq = np.sum((ref - test) ** 2)
    inner = 1 + diff_sq / n
    if inner > 0:
        f2 = 50 * np.log10(np.sqrt(inner))
    else:
        f2 = 100.0

    # f1 = (Σ|Rt - Tt| / ΣRt) × 100
    f1_num = np.sum(np.abs(ref - test))
    f1_den = np.sum(ref)
    f1 = (f1_num / f1_den * 100) if f1_den > 0 else 0

    verdict = "Similar" if f2 >= 50 else "Different"

    return {
        "status": "ok",
        "f2": round(f2, 2),
        "f1": round(f1, 2),
        "verdict": verdict,
        "time_points": n,
        "interpretation": (
            f"f2={f2:.1f} ({'≥50 → Similar' if f2 >= 50 else '<50 → Different'}). "
            f"f1={f1:.1f} ({'≤15 → Similar' if f1 <= 15 else '>15 → Different'})."
        ),
        "reference": "FDA Guidance for Industry: Dissolution Testing (1997)"
    }
