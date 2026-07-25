"""
Quality Control Calculations — SST, Content Uniformity.

USP <621> Chromatography, USP <905> Uniformity of Dosage Units.
"""

import numpy as np
from typing import Dict, Any, List, Optional


def system_suitability(
    retention_times: List[float],
    peak_areas: List[float],
    theoretical_plates: Optional[List[float]] = None,
    tailing_factors: Optional[List[float]] = None,
    reference_rt: Optional[float] = None,
) -> Dict[str, Any]:
    """System Suitability Testing (SST) calculator.
    
    USP <621> Chromatography requirements:
    - Retention time reproducibility (RSD < 1%)
    - Peak area reproducibility (RSD < 2%)
    - Theoretical plates (N ≥ 2000 for most methods)
    - Tailing factor (T ≤ 2.0)
    - Resolution (Rs ≥ 2.0)
    
    Args:
        retention_times: List of retention times for repeated injections
        peak_areas: List of peak areas for repeated injections
        theoretical_plates: Optional list of theoretical plate counts
        tailing_factors: Optional list of tailing factors
        reference_rt: Reference retention time for RT shift calculation
    
    Returns:
        Dict with SST results and pass/fail status
    """
    rt = np.array(retention_times, dtype=float)
    pa = np.array(peak_areas, dtype=float)
    
    rt_rsd = (np.std(rt) / np.mean(rt)) * 100 if np.mean(rt) > 0 else 0
    pa_rsd = (np.std(pa) / np.mean(pa)) * 100 if np.mean(pa) > 0 else 0
    
    # RT shift from reference
    rt_shift_pct = 0
    if reference_rt and reference_rt > 0:
        rt_shift_pct = abs(np.mean(rt) - reference_rt) / reference_rt * 100
    
    # Check criteria
    rt_pass = rt_rsd < 1.0
    pa_pass = pa_rsd < 2.0
    
    # Theoretical plates check
    plates_pass = True
    plates_mean = None
    if theoretical_plates:
        plates = np.array(theoretical_plates, dtype=float)
        plates_mean = float(np.mean(plates))
        plates_pass = plates_mean >= 2000
    
    # Tailing factor check
    tailing_pass = True
    tailing_mean = None
    if tailing_factors:
        tf = np.array(tailing_factors, dtype=float)
        tailing_mean = float(np.mean(tf))
        tailing_pass = tailing_mean <= 2.0
    
    overall_pass = rt_pass and pa_pass and plates_pass and tailing_pass
    
    return {
        "status": "ok",
        "rt_rsd_pct": round(rt_rsd, 2),
        "pa_rsd_pct": round(pa_rsd, 2),
        "rt_mean": round(float(np.mean(rt)), 3),
        "rt_shift_pct": round(rt_shift_pct, 2),
        "plates_mean": round(plates_mean, 0) if plates_mean else None,
        "tailing_mean": round(tailing_mean, 2) if tailing_mean else None,
        "rt_pass": rt_pass,
        "pa_pass": pa_pass,
        "plates_pass": plates_pass,
        "tailing_pass": tailing_pass,
        "overall_pass": overall_pass,
        "criteria": {
            "rt_rsd": "< 1%",
            "pa_rsd": "< 2%",
            "theoretical_plates": "≥ 2000",
            "tailing_factor": "≤ 2.0",
        },
        "reference": "USP <621> Chromatography"
    }


def content_uniformity(
    assay_values: List[float],
    target_mg: float,
    method: str = "acceptance_value",
) -> Dict[str, Any]:
    """Content Uniformity calculator (USP <905>).
    
    USP <905> Uniformity of Dosage Units:
    - Acceptance Value (AV) method
    - Label Claim method
    - Individual Content method
    
    Args:
        assay_values: List of individual assay results (mg or %)
        target_mg: Target content per unit (mg)
        method: "acceptance_value" or "label_claim"
    
    Returns:
        Dict with uniformity results
    """
    values = np.array(assay_values, dtype=float)
    n = len(values)
    
    if n < 10:
        return {"status": "error", "error": "USP <905> requires at least 10 units"}
    
    mean_val = float(np.mean(values))
    std_val = float(np.std(values, ddof=1))
    rsd = (std_val / mean_val) * 100 if mean_val > 0 else 0
    
    # Label Claim method (USP <905>)
    if method == "label_claim":
        # Individual content limits
        lower_limit = target_mg * 0.85
        upper_limit = target_mg * 1.15
        
        within_limits = np.sum((values >= lower_limit) & (values <= upper_limit))
        
        # Acceptance Value (AV)
        # AV = |M - X̄| + ks  where M = target, k = 2.4 (n=10), s = sample std
        k = 2.4 if n == 10 else (2.0 if n <= 30 else 1.9)
        av = abs(target_mg - mean_val) + k * std_val
        
        # USP limits: AV ≤ 15.0 for L1 (n=10), AV ≤ 25.0 for L2 (n=30)
        l1_pass = av <= 15.0
        l2_pass = av <= 25.0
        
        return {
            "status": "ok",
            "method": "Label Claim (USP <905>)",
            "n_units": n,
            "target_mg": target_mg,
            "mean_mg": round(mean_val, 2),
            "std_mg": round(std_val, 2),
            "rsd_pct": round(rsd, 1),
            "acceptance_value": round(av, 2),
            "l1_pass": l1_pass,
            "l2_pass": l2_pass,
            "within_85_115_pct": int(within_limits),
            "all_within_limits": within_limits == n,
            "units_outside_limits": int(n - within_limits),
            "interpretation": (
                f"AV = {av:.2f} {'≤ 15 (PASS)' if l1_pass else '> 15 (FAIL)'}. "
                f"{within_limits}/{n} units within 85-115% of label claim."
            ),
            "reference": "USP <905> Uniformity of Dosage Units"
        }
    
    # Acceptance Value method
    k = 2.4
    av = abs(target_mg - mean_val) + k * std_val
    
    return {
        "status": "ok",
        "method": "Acceptance Value",
        "n_units": n,
        "target_mg": target_mg,
        "mean_mg": round(mean_val, 2),
        "std_mg": round(std_val, 2),
        "acceptance_value": round(av, 2),
        "l1_pass": av <= 15.0,
        "interpretation": f"AV = {av:.2f} {'≤ 15 (PASS)' if av <= 15.0 else '> 15 (FAIL)'}",
        "reference": "USP <905>"
    }
