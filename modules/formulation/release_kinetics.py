"""
Release Kinetics Fitting — 5 pharmacokinetic release models.

Fits dissolution/release data to: Zero-order, First-order, Higuchi,
Korsmeyer-Peppas, Weibull. Uses least-squares regression.

References:
- Costa P, Lobo JM. Eur J Pharm Sci. 2001;13(2):123-133.
- Ritger PL, Peppas NA. J Controlled Release. 1987;5(1):37-42.
"""

import numpy as np
from typing import Dict, Any, List, Tuple


def fit_release_kinetics(time_points: List[float], release_pcts: List[float]) -> Dict[str, Any]:
    """Fit dissolution/release data to 5 kinetic models.

    Args:
        time_points: List of time values (hours)
        release_pcts: List of cumulative % released at each time point

    Returns:
        Dict with best-fit model, R-squared, equation, parameters
    """
    t = np.array(time_points, dtype=float)
    r = np.array(release_pcts, dtype=float)

    if len(t) < 3 or len(t) != len(r):
        return {"status": "error", "error": "Need ≥3 matched time/release pairs"}

    results = {}

    # 1. Zero-order: R = k*t
    # Linear: y = k*t  (y = release, t = time)
    try:
        coeffs = np.polyfit(t, r, 1)
        k0 = coeffs[0]
        r_pred = k0 * t
        ss_res = np.sum((r - r_pred) ** 2)
        ss_tot = np.sum((r - np.mean(r)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        results["zero_order"] = {
            "model": "Zero-order",
            "equation": "R = k₀ × t",
            "parameters": {"k0": round(k0, 4)},
            "r_squared": round(r2, 4),
            "description": "Constant release rate over time",
        }
    except Exception:
        results["zero_order"] = {"model": "Zero-order", "r_squared": 0, "fit_error": True}

    # 2. First-order: ln(100-R) = -k*t + ln(100)
    # Linear: ln(100-R) = -k*t + b
    try:
        r_safe = np.clip(r, 0.01, 99.99)
        y_log = np.log(100 - r_safe)
        coeffs = np.polyfit(t, y_log, 1)
        k1 = -coeffs[0]
        b = coeffs[1]
        r_pred_log = -k1 * t + b
        ss_res = np.sum((y_log - r_pred_log) ** 2)
        ss_tot = np.sum((y_log - np.mean(y_log)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        results["first_order"] = {
            "model": "First-order",
            "equation": "ln(100-R) = -k₁ × t + ln(100)",
            "parameters": {"k1": round(k1, 4)},
            "r_squared": round(r2, 4),
            "description": "Exponential decay; release slows as drug depletes",
        }
    except Exception:
        results["first_order"] = {"model": "First-order", "r_squared": 0, "fit_error": True}

    # 3. Higuchi: R = k_H × √t
    try:
        sqrt_t = np.sqrt(t)
        coeffs = np.polyfit(sqrt_t, r, 1)
        kH = coeffs[0]
        r_pred = kH * sqrt_t
        ss_res = np.sum((r - r_pred) ** 2)
        ss_tot = np.sum((r - np.mean(r)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        results["higuchi"] = {
            "model": "Higuchi",
            "equation": "R = k_H × √t",
            "parameters": {"kH": round(kH, 4)},
            "r_squared": round(r2, 4),
            "description": "Fickian diffusion from matrix; R ∝ √t",
        }
    except Exception:
        results["higuchi"] = {"model": "Higuchi", "r_squared": 0, "fit_error": True}

    # 4. Korsmeyer-Peppas: R = k_KP × t^n
    # log(R) = n × log(t) + log(k_KP)
    try:
        t_safe = np.clip(t, 0.01, None)
        r_safe = np.clip(r, 0.01, None)
        log_t = np.log(t_safe)
        log_r = np.log(r_safe)
        coeffs = np.polyfit(log_t, log_r, 1)
        n = coeffs[0]
        kKP = np.exp(coeffs[1])
        r_pred_log = n * log_t + coeffs[1]
        ss_res = np.sum((log_r - r_pred_log) ** 2)
        ss_tot = np.sum((log_r - np.mean(log_r)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # n interpretation
        if n < 0.43:
            release_mechanism = "Fickian diffusion"
        elif n < 0.85:
            release_mechanism = "Anomalous transport (non-Fickian)"
        elif n == 0.85:
            release_mechanism = "Case-II transport"
        else:
            release_mechanism = "Super case-II transport"

        results["korsmeyer_peppas"] = {
            "model": "Korsmeyer-Peppas",
            "equation": "R = k_KP × t^n",
            "parameters": {"k_KP": round(kKP, 4), "n": round(n, 4)},
            "r_squared": round(r2, 4),
            "release_mechanism": release_mechanism,
            "description": "Power-law model; n indicates release mechanism",
        }
    except Exception:
        results["korsmeyer_peppas"] = {"model": "Korsmeyer-Peppas", "r_squared": 0, "fit_error": True}

    # 5. Weibull: R = 100 × (1 - exp(-(t/b)^β))
    # Note: simplified fit using linearized form
    try:
        t_safe = np.clip(t, 0.01, None)
        r_safe = np.clip(r, 0.01, 99.99)
        # R/100 = 1 - exp(-(t/b)^β)
        # ln(-ln(1 - R/100)) = β × ln(t) - β × ln(b)
        y_weibull = np.log(-np.log(1 - r_safe / 100))
        log_t = np.log(t_safe)
        coeffs = np.polyfit(log_t, y_weibull, 1)
        beta = coeffs[0]
        b_exp = -coeffs[1] / beta if beta != 0 else 1.0
        b_val = np.exp(b_exp)

        # R² on transformed scale
        r_pred = beta * log_t - beta * b_exp
        ss_res = np.sum((y_weibull - r_pred) ** 2)
        ss_tot = np.sum((y_weibull - np.mean(y_weibull)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        results["weibull"] = {
            "model": "Weibull",
            "equation": "R = 100 × (1 - exp(-(t/b)^β))",
            "parameters": {"beta": round(beta, 4), "b": round(b_val, 4)},
            "r_squared": round(r2, 4),
            "description": "Empirical model; β shape parameter",
        }
    except Exception:
        results["weibull"] = {"model": "Weibull", "r_squared": 0, "fit_error": True}

    # Find best-fit model
    valid = {k: v for k, v in results.items() if v.get("r_squared", 0) > 0}
    if valid:
        best_key = max(valid, key=lambda k: valid[k]["r_squared"])
        best = valid[best_key]
    else:
        best_key = "none"
        best = {"model": "None", "r_squared": 0}

    return {
        "status": "ok",
        "models": results,
        "best_fit": best["model"],
        "best_r_squared": best.get("r_squared", 0),
        "best_equation": best.get("equation", ""),
        "best_parameters": best.get("parameters", {}),
        "release_mechanism": results.get("korsmeyer_peppas", {}).get("release_mechanism"),
        "total_points": len(t),
        "reference": "Costa P, Lobo JM. Eur J Pharm Sci. 2001;13(2):123-133; Ritger PL, Peppas NA. J Controlled Release. 1987;5(1):37-42",
    }
