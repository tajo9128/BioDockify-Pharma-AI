"""
Stability Prediction — ICH Q1E Shelf-life Estimation.

Uses Arrhenius equation to extrapolate accelerated stability data
to predict shelf-life at target (ambient) temperature.

Reference: ICH Q1E Statistical Evaluation of Stability Data (2003)
"""

import math
from typing import Dict, Any, List


def predict_shelf_life(
    temperatures_c: List[float],
    degradation_pcts: List[float],
    months: List[int],
    target_temp_c: float = 25.0,
    threshold_pct: float = 10.0,
    activation_energy_kcal: float = 15.0,
) -> Dict[str, Any]:
    """Predict shelf-life at target temperature using Arrhenius extrapolation.

    Args:
        temperatures_c: List of stability storage temperatures (°C)
        degradation_pcts: List of degradation % at each temperature/time
        months: List of months at each temperature
        target_temp_c: Target (ambient) temperature for shelf-life (°C)
        threshold_pct: Maximum acceptable degradation % (ICH default: 10%)
        activation_energy_kcal: Estimated activation energy (kcal/mol)

    Returns:
        Dict with predicted shelf-life, degradation rates, Arrhenius fit
    """
    if len(temperatures_c) < 2:
        return {"status": "error", "error": "Need ≥2 temperature points"}

    R = 1.987e-3  # kcal/(mol·K)

    # Convert to Kelvin
    temps_K = [t + 273.15 for t in temperatures_c]
    target_K = target_temp_c + 273.15

    # Calculate degradation rates (k = %/month) for each condition
    rates = []
    for i in range(len(temperatures_c)):
        if months[i] > 0:
            k = degradation_pcts[i] / months[i]
        else:
            k = 0
        rates.append(k)

    # Arrhenius: k = A × exp(-Ea/RT)
    # ln(k) = ln(A) - Ea/(R × T)
    # If we have Ea, we can predict k at target T
    # If not, fit Ea from the data

    if len(temperatures_c) >= 2 and activation_energy_kcal > 0:
        # Use provided Ea to extrapolate
        Ea = activation_energy_kcal
        # Fit ln(A) from first data point
        if rates[0] > 0:
            lnA = math.log(rates[0]) + Ea / (R * temps_K[0])
        else:
            lnA = 0

        # Predict rate at target temperature
        k_target = math.exp(lnA - Ea / (R * target_K))
    else:
        # Linear fit of ln(k) vs 1/T to estimate Ea
        try:
            valid_points = [(1/t, math.log(k)) for t, k in zip(temps_K, rates) if k > 0]
            if len(valid_points) < 2:
                return {"status": "error", "error": "Need ≥2 valid degradation rates for Arrhenius fit"}
            xs, ys = zip(*valid_points)
            n = len(xs)
            sum_x = sum(xs)
            sum_y = sum(ys)
            sum_xy = sum(x*y for x, y in zip(xs, ys))
            sum_x2 = sum(x*x for x in xs)
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
            intercept = (sum_y - slope * sum_x) / n
            Ea = -slope * R
            k_target = math.exp(intercept + Ea / (R * target_K))
        except Exception:
            return {"status": "error", "error": "Arrhenius fit failed"}

    # Predict shelf-life: months until degradation reaches threshold
    if k_target > 0:
        shelf_life_months = threshold_pct / k_target
        shelf_life_years = shelf_life_months / 12
    else:
        shelf_life_months = float('inf')
        shelf_life_years = float('inf')

    # t90 (time to 10% degradation)
    if k_target > 0:
        t90_months = 10 / k_target
    else:
        t90_months = float('inf')

    return {
        "status": "ok",
        "shelf_life_months": round(shelf_life_months, 1),
        "shelf_life_years": round(shelf_life_years, 1),
        "t90_months": round(t90_months, 1),
        "target_temp_c": target_temp_c,
        "threshold_pct": threshold_pct,
        "degradation_rate_per_month": round(k_target, 4),
        "activation_energy_kcal_mol": round(Ea, 2),
        "data_points": len(temperatures_c),
        "interpretation": (
            f"Predicted shelf-life: {shelf_life_years:.1f} years "
            f"({shelf_life_months:.0f} months) at {target_temp_c}°C "
            f"before reaching {threshold_pct}% degradation."
        ),
        "reference": "ICH Q1E Statistical Evaluation of Stability Data (2003)"
    }
