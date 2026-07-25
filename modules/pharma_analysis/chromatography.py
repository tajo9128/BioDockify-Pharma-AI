"""
HPLC Chromatography — system suitability calculations (USP <621>).
"""

import numpy as np
from typing import Dict, Any


def calculate_theoretical_plates(retention_time: float, peak_width_at_half: float) -> Dict[str, Any]:
    """Calculate theoretical plates (N) per USP method.

    N = 5.54 × (tR / W0.5)²

    Args:
        retention_time: Retention time (minutes)
        peak_width_at_half: Peak width at half height (minutes)

    Returns:
        Dict with theoretical plates count
    """
    if peak_width_at_half <= 0:
        return {"status": "error", "error": "Peak width at half height must be > 0"}

    n = 5.54 * (retention_time / peak_width_at_half) ** 2

    if n >= 2000:
        assessment = "PASS — adequate for most analyses"
    elif n >= 1000:
        assessment = "MARGINAL — consider column optimization"
    else:
        assessment = "FAIL — insufficient resolution"

    return {
        "status": "ok",
        "theoretical_plates": round(n, 0),
        "assessment": assessment,
        "pass": n >= 2000,
        "reference": "USP <621> Chromatography"
    }


def calculate_tailing_factor(peak: Dict[str, float]) -> Dict[str, Any]:
    """Calculate tailing factor (T) per USP method.

    T = (a + b) / 2a
    where a = peak width at 5% height (front), b = peak width at 5% height (back)

    Args:
        peak: Dict with 'width_front' and 'width_back' at 5% height

    Returns:
        Dict with tailing factor
    """
    a = peak.get("width_front", 0)
    b = peak.get("width_back", 0)

    if a <= 0:
        return {"status": "error", "error": "Front width must be > 0"}

    t = (a + b) / (2 * a)

    if t <= 2.0:
        assessment = "PASS — acceptable peak shape"
    elif t <= 3.0:
        assessment = "MARGINAL — tailing present"
    else:
        assessment: str = "FAIL — severe tailing"

    return {
        "status": "ok",
        "tailing_factor": round(t, 2),
        "assessment": assessment,
        "pass": t <= 2.0,
        "reference": "USP <621> Chromatography"
    }


def calculate_resolution(retention_time1: float, retention_time2: float,
                         peak_width1: float, peak_width2: float) -> Dict[str, Any]:
    """Calculate resolution (Rs) between two peaks.

    Rs = 2(tR2 - tR1) / (W1 + W2)

    Args:
        retention_time1: Retention time of first peak
        retention_time2: Retention time of second peak
        peak_width1: Width of first peak at base
        peak_width2: Width of second peak at base

    Returns:
        Dict with resolution value
    """
    rs = 2 * abs(retention_time2 - retention_time1) / (peak_width1 + peak_width2) if (peak_width1 + peak_width2) > 0 else 0

    if rs >= 2.0:
        assessment = "PASS — baseline resolved"
    elif rs >= 1.5:
        assessment = "MARGINAL — partially resolved"
    else:
        assessment = "FAIL — co-eluting peaks"

    return {
        "status": "ok",
        "resolution": round(rs, 2),
        "assessment": assessment,
        "pass": rs >= 2.0,
        "reference": "USP <621> Chromatography"
    }
