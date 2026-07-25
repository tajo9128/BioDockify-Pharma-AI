"""
ICH Q2(R2) Method Validation — linearity, accuracy, precision.

Reference: ICH Q2(R2) Validation of Analytical Procedures (2023)
"""

import numpy as np
from typing import Dict, Any, List


def calculate_linearity(concentrations: List[float], responses: List[float]) -> Dict[str, Any]:
    """Calculate linearity parameters per ICH Q2(R2).

    Args:
        concentrations: List of known concentrations
        responses: List of measured responses

    Returns:
        Dict with slope, intercept, R-squared, linearity assessment
    """
    conc = np.array(concentrations, dtype=float)
    resp = np.array(responses, dtype=float)

    if len(conc) < 3:
        return {"status": "error", "error": "Need ≥3 concentration levels"}

    # Linear regression
    slope, intercept = np.polyfit(conc, resp, 1)
    resp_pred = slope * conc + intercept

    # R-squared
    ss_res = np.sum((resp - resp_pred) ** 2)
    ss_tot = np.sum((resp - np.mean(resp)) ** 2)
    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    # Residuals
    residuals = resp - resp_pred
    max_residual_pct = np.max(np.abs(residuals / resp_pred * 100)) if np.all(resp_pred != 0) else 0

    return {
        "status": "ok",
        "slope": round(float(slope), 4),
        "intercept": round(float(intercept), 4),
        "r_squared": round(float(r2), 4),
        "residuals": [round(float(r), 2) for r in residuals],
        "max_residual_pct": round(float(max_residual_pct), 2),
        "linearity_pass": r2 >= 0.999,
        "concentration_range": f"{float(min(conc))} - {float(max(conc))}",
        "n_points": len(conc),
        "interpretation": f"R² = {r2:.4f} {'PASS' if r2 >= 0.999 else 'FAIL'} (threshold ≥ 0.999)",
        "reference": "ICH Q2(R2) Validation of Analytical Procedures (2023)"
    }


def calculate_accuracy(known_concentrations: List[float], measured_concentrations: List[float]) -> Dict[str, Any]:
    """Calculate accuracy (% recovery) per ICH Q2(R2).

    Args:
        known_concentrations: List of known (spiked) concentrations
        measured_concentrations: List of measured concentrations

    Returns:
        Dict with mean recovery, RSD, pass/fail
    """
    known = np.array(known_concentrations, dtype=float)
    measured = np.array(measured_concentrations, dtype=float)

    if len(known) != len(measured):
        return {"status": "error", "error": "Known and measured must have same length"}

    recovery = (measured / known) * 100
    mean_recovery = float(np.mean(recovery))
    sd_recovery = float(np.std(recovery, ddof=1))
    rsd = (sd_recovery / mean_recovery) * 100 if mean_recovery > 0 else 0

    return {
        "status": "ok",
        "mean_recovery_pct": round(mean_recovery, 2),
        "sd_recovery": round(sd_recovery, 2),
        "rsd_pct": round(rsd, 2),
        "recovery_per_level": [round(float(r), 2) for r in recovery],
        "accuracy_pass": 80 <= mean_recovery <= 120 and rsd <= 10,
        "n_points": len(known),
        "interpretation": f"Mean recovery: {mean_recovery:.1f}% (RSD {rsd:.1f}%) — {'PASS' if 80 <= mean_recovery <= 120 and rsd <= 10 else 'FAIL'}",
        "reference": "ICH Q2(R2) Validation of Analytical Procedures (2023)"
    }


def calculate_precision(measurements: List[float]) -> Dict[str, Any]:
    """Calculate precision (repeatability) per ICH Q2(R2).

    Args:
        measurements: List of repeated measurements at same concentration

    Returns:
        Dict with mean, SD, RSD, pass/fail
    """
    data = np.array(measurements, dtype=float)
    n = len(data)
    mean = float(np.mean(data))
    sd = float(np.std(data, ddof=1))
    rsd = (sd / mean) * 100 if mean > 0 else 0

    return {
        "status": "ok",
        "n_measurements": n,
        "mean": round(mean, 4),
        "sd": round(sd, 4),
        "rsd_pct": round(rsd, 2),
        "precision_pass": rsd <= 2.0,
        "interpretation": f"RSD = {rsd:.2f}% {'PASS' if rsd <= 2.0 else 'FAIL'} (threshold ≤ 2.0%)",
        "reference": "ICH Q2(R2) Validation of Analytical Procedures (2023)"
    }
