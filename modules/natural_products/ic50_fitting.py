"""
IC50/EC50 Fitting — 4-parameter logistic regression + linear interpolation.

Reference: Sebaugh JL. Pharm Stat. 2011;10(2):128-134.
"""

import numpy as np
from typing import Dict, Any, List, Optional


def fit_dose_response(doses: List[float], responses: List[float]) -> Dict[str, Any]:
    """Fit dose-response data to 4-parameter logistic (4PL) model.

    y = Bottom + (Top - Bottom) / (1 + (x/IC50)^HillSlope)

    Args:
        doses: List of dose/concentration values
        responses: List of response values (e.g., % inhibition, cell viability)

    Returns:
        Dict with IC50, Hill slope, top, bottom, R-squared
    """
    dose_arr = np.array(doses, dtype=float)
    resp_arr = np.array(responses, dtype=float)

    if len(dose_arr) < 4:
        return {"status": "error", "error": "Need ≥4 data points for 4PL fit"}

    try:
        from scipy.optimize import curve_fit

        def logistic_4pl(x, top, bottom, ic50, hill):
            return bottom + (top - bottom) / (1 + (x / ic50) ** hill)

        # Initial estimates
        top_est = float(np.max(resp_arr))
        bottom_est = float(np.min(resp_arr))
        mid_resp = (top_est + bottom_est) / 2
        ic50_est = float(dose_arr[np.argmin(np.abs(resp_arr - mid_resp))])
        hill_est = 1.0

        p0 = [top_est, bottom_est, ic50_est, hill_est]
        popt, pcov = curve_fit(logistic_4pl, dose_arr, resp_arr, p0=p0, maxfev=10000)
        top, bottom, ic50, hill = popt

        # R²
        resp_pred = logistic_4pl(dose_arr, *popt)
        ss_res = np.sum((resp_arr - resp_pred) ** 2)
        ss_tot = np.sum((resp_arr - np.mean(resp_arr)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # EC90, EC50, EC10 from Hill equation
        def ec_from_inhibition(pct):
            if pct <= 0 or pct >= 100:
                return None
            ratio = pct / (100 - pct)
            return ic50 * ratio ** (1 / hill)

        ec10 = ec_from_inhibition(10)
        ec90 = ec_from_inhibition(90)

        return {
            "status": "ok",
            "ic50": round(float(ic50), 4),
            "ec50": round(float(ic50), 4),
            "ec10": round(float(ec10), 4) if ec10 else None,
            "ec90": round(float(ec90), 4) if ec90 else None,
            "hill_slope": round(float(hill), 4),
            "top": round(float(top), 4),
            "bottom": round(float(bottom), 4),
            "r_squared": round(float(r2), 4),
            "method": "4-parameter logistic regression (scipy.optimize.curve_fit)",
            "reference": "Sebaugh JL. Pharm Stat. 2011;10(2):128-134"
        }

    except ImportError:
        # Fallback: linear interpolation without scipy
        return _linear_interpolation(dose_arr, resp_arr)
    except Exception as e:
        return {"status": "error", "error": f"Curve fit failed: {str(e)}. Try linear interpolation."}


def fit_4pl(doses: List[float], responses: List[float]) -> Dict[str, Any]:
    """Alias for fit_dose_response."""
    return fit_dose_response(doses, responses)


def _linear_interpolation(doses: np.ndarray, responses: np.ndarray) -> Dict[str, Any]:
    """Linear interpolation fallback when scipy is unavailable."""
    sorted_pairs = sorted(zip(doses, responses), key=lambda x: x[0])
    d_sorted = np.array([p[0] for p in sorted_pairs])
    r_sorted = np.array([p[1] for p in sorted_pairs])

    mid_resp = (float(np.max(responses)) + float(np.min(responses))) / 2
    idx = np.argmin(np.abs(r_sorted - mid_resp))

    if idx == 0:
        ic50 = float(d_sorted[0])
    elif idx == len(d_sorted) - 1:
        ic50 = float(d_sorted[-1])
    else:
        x1, x2 = d_sorted[idx - 1], d_sorted[idx + 1]
        y1, y2 = r_sorted[idx - 1], r_sorted[idx + 1]
        if y2 != y1:
            ic50 = float(x1 + (mid_resp - y1) * (x2 - x1) / (y2 - y1))
        else:
            ic50 = float(d_sorted[idx])

    return {
        "status": "ok",
        "ic50": round(ic50, 4),
        "ec50": round(ic50, 4),
        "method": "Linear interpolation (scipy unavailable)",
        "note": "Install scipy for 4-parameter logistic regression"
    }
