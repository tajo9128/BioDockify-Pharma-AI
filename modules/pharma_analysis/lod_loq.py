"""
LOD and LOQ Calculations — ICH Q2(R2) / USP <1225>.

Methods:
  1. Signal-to-Noise (S/N = 3 for LOD, S/N = 10 for LOQ)
  2. Standard Deviation of Response (3.3σ/S for LOD, 10σ/S for LOQ)

Reference: ICH Q2(R2) Validation of Analytical Procedures (2023)
"""

import numpy as np
from typing import Dict, Any, List, Optional


def calculate_lod_loq(
    method: str,
    blank_measurements: Optional[List[float]] = None,
    slope: Optional[float] = None,
    signal_to_noise_ratio: Optional[float] = None,
) -> Dict[str, Any]:
    """Calculate LOD and LOQ.

    Args:
        method: "signal_to_noise" or "standard_deviation"
        blank_measurements: List of blank/sample measurements (for std dev method)
        slope: Calibration curve slope (for std dev method)
        signal_to_noise_ratio: Measured S/N ratio (for S/N method)

    Returns:
        Dict with LOD and LOQ values
    """
    if method == "signal_to_noise":
        if not signal_to_noise_ratio or signal_to_noise_ratio <= 0:
            return {"status": "error", "error": "Provide signal_to_noise_ratio > 0 for S/N method"}

        lod = 3 * signal_to_noise_ratio
        loq = 10 * signal_to_noise_ratio

        return {
            "status": "ok",
            "method": "Signal-to-Noise (S/N)",
            "lod": round(lod, 4),
            "loq": round(loq, 4),
            "lod_formula": "LOD = 3 × S/N",
            "loq_formula": "LOQ = 10 × S/N",
            "interpretation": f"LOD = {lod:.4f}, LOQ = {loq:.4f}",
            "reference": "ICH Q2(R2) Validation of Analytical Procedures (2023)"
        }

    elif method == "standard_deviation":
        if not blank_measurements or not slope or slope <= 0:
            return {"status": "error", "error": "Provide blank_measurements and slope > 0 for std dev method"}

        blanks = np.array(blank_measurements, dtype=float)
        sd = float(np.std(blanks, ddof=1))

        lod = (3.3 * sd) / slope
        loq = (10 * sd) / slope

        return {
            "status": "ok",
            "method": "Standard Deviation of Response",
            "lod": round(lod, 4),
            "loq": round(loq, 4),
            "lod_formula": "LOD = 3.3 × σ / S",
            "loq_formula": "LOQ = 10 × σ / S",
            "blank_std": round(sd, 4),
            "slope": slope,
            "n_blank_measurements": len(blanks),
            "interpretation": f"LOD = {lod:.4f}, LOQ = {loq:.4f}",
            "reference": "ICH Q2(R2) Validation of Analytical Procedures (2023)"
        }

    else:
        return {"status": "error", "error": f"Unknown method: {method}. Use 'signal_to_noise' or 'standard_deviation'"}
