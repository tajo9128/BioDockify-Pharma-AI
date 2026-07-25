"""
Therapeutic Drug Monitoring (TDM) — Bayesian-style calculator.

Reference: Winter ME. Basic Clinical Pharmacokinetics. 5th ed. 2010.
"""

import math
from typing import Dict, Any, Optional


# Reference ranges for common TDM drugs
DRUG_RANGES = {
    "vancomycin": {
        "trough": (10, 20), "unit": "µg/mL",
        "half_life": (4, 12), "vd": 0.7, "route": "iv",
        "note": "AUC-guided dosing preferred (Rybak 2020). Target trough 15-20 for MRSA.",
        "reference": "Rybak MJ et al. Therapeutic Drug Monitoring. 2020;42(2):245-253"
    },
    "gentamicin": {
        "trough": (0.5, 2.0), "peak": (5, 12), "unit": "µg/mL",
        "half_life": (2, 3), "vd": 0.25, "route": "iv",
        "note": "Extended-interval dosing preferred. Monitor renal function.",
        "reference": "Begg EJ et al. Clin Pharmacokinet. 1999"
    },
    "phenytoin": {
        "total_range": (10, 20), "free_range": (1, 2), "unit": "µg/mL",
        "half_life": (7, 42), "vd": 0.7, "route": "oral",
        "note": "Michaelis-Menten kinetics. Free phenytoin more clinically relevant.",
        "reference": "Winter ME. Basic Clinical Pharmacokinetics. 2010"
    },
    "carbamazepine": {
        "range": (4, 12), "unit": "µg/mL",
        "half_life": (12, 17), "vd": 1.0, "route": "oral",
        "note": "Auto-induction: half-life decreases over time. Monitor weekly initially.",
        "reference": "Winter ME. Basic Clinical Pharmacokinetics. 2010"
    },
    "valproate": {
        "range": (50, 100), "unit": "µg/mL",
        "half_life": (9, 16), "vd": 0.15, "route": "oral",
        "note": "Free valproate more relevant with low albumin or renal failure.",
        "reference": "Patsalos PN et al. Epilepsia. 2018"
    },
    "lithium": {
        "range": (0.6, 1.2), "unit": "mEq/L",
        "half_life": (18, 24), "vd": 0.7, "route": "oral",
        "note": "Narrow therapeutic index. Monitor renal and thyroid function.",
        "reference": "Malhi GS et al. Bipolar Disord. 2017"
    },
    "digoxin": {
        "range": (0.8, 2.0), "unit": "ng/mL",
        "half_life": (36, 48), "vd": 7, "route": "oral",
        "note": "Target 0.5-0.9 ng/mL for heart failure (DIG trial). Higher levels for A-fib.",
        "reference": "DIG Trial Group. NEJM 1997"
    },
    "theophylline": {
        "range": (10, 20), "unit": "µg/mL",
        "half_life": (3, 8), "vd": 0.5, "route": "oral",
        "note": "Narrow therapeutic index. Many drug interactions.",
        "reference": "Hendeles L et al. Chest. 1985"
    },
    "tacrolimus": {
        "range": (5, 15), "unit": "ng/mL",
        "half_life": (12, 15), "vd": 1, "route": "oral",
        "note": "Therapeutic range varies by transplant type and time post-transplant.",
        "reference": "Andrews PA et al. Transplantation. 2014"
    },
    "cyclosporine": {
        "range": (100, 400), "unit": "ng/mL",
        "half_life": (5, 18), "vd": 4, "route": "oral",
        "note": "Whole blood trough level. Range varies by transplant type.",
        "reference": "Oellerich M et al. Ther Drug Monit. 2004"
    },
}


def calculate_tdm(
    drug: str,
    dose_mg: float,
    interval_h: float,
    route: str = "iv",
    infusion_time_h: float = 0.0,
    steady_state_peak: Optional[float] = None,
    steady_state_trough: Optional[float] = None,
    patient_weight_kg: float = 70,
    renal_function: Optional[float] = None,
) -> Dict[str, Any]:
    """Therapeutic Drug Monitoring calculator.

    Estimates PK parameters from dosing + optional measured levels,
    and provides dosing recommendations.

    Args:
        drug: Drug name (must be in DRUG_RANGES)
        dose_mg: Current dose in mg
        interval_h: Dosing interval in hours
        route: "iv" or "oral"
        infusion_time_h: IV infusion time (0 for bolus)
        steady_state_peak: Optional measured peak level
        steady_state_trough: Optional measured trough level
        patient_weight_kg: Patient weight (for Vd estimation)
        renal_function: Optional GFR mL/min (for renally cleared drugs)

    Returns:
        Dict with PK parameters, therapeutic range, dosing recommendation
    """
    if not dose_mg or dose_mg <= 0:
        return {"status": "error", "error": "Dose must be > 0"}
    if interval_h <= 0:
        return {"status": "error", "error": "Interval must be > 0"}

    drug_lower = drug.strip().lower()
    if drug_lower not in DRUG_RANGES:
        available = list(DRUG_RANGES.keys())
        return {"status": "error", "error": f"Drug '{drug}' not in TDM database. Available: {available}"}

    ref = DRUG_RANGES[drug_lower]
    vd_per_kg = ref.get("vd", 0.7)
    vd = vd_per_kg * patient_weight_kg
    half_life_est = sum(ref.get("half_life", (8, 8))) / 2
    therapeutic_range = ref.get("range", ref.get("trough", (0, 100)))

    # Estimate clearance
    clearance = (0.693 * vd) / half_life_est if half_life_est > 0 else 1  # L/h
    if renal_function and renal_function < 60:
        # Rough renal adjustment
        renal_factor = renal_function / 120
        clearance = clearance * max(renal_factor, 0.3)

    # Estimate steady-state levels
    if route == "iv":
        ss_peak = dose_mg / vd
        ss_trough = ss_peak * math.exp(-0.693 * interval_h / half_life_est)
    else:
        # Oral: assume 80% bioavailability
        bioavailability = 0.8
        ss_peak = (dose_mg * bioavailability) / vd
        ss_trough = ss_peak * math.exp(-0.693 * interval_h / half_life_est)

    # Time to steady state (4-5 half-lives)
    steady_state_time_h = half_life_est * 5
    steady_state_time_d = steady_state_time_h / 24

    # Accumulation factor
    accumulation = 1 / (1 - math.exp(-0.693 * interval_h / half_life_est))

    result = {
        "drug": drug_lower,
        "therapeutic_range": therapeutic_range,
        "unit": ref.get("unit", "µg/mL"),
        "dose": f"{dose_mg}mg q{interval_h}h {route}",
        "vd_L": round(vd, 2),
        "vd_L_per_kg": vd_per_kg,
        "half_life_h": round(half_life_est, 1),
        "clearance_L_h": round(clearance, 2),
        "steady_state_peak_est": round(ss_peak, 2),
        "steady_state_trough_est": round(ss_trough, 2),
        "accumulation_factor": round(accumulation, 2),
        "time_to_steady_state_h": round(steady_state_time_h, 1),
        "time_to_steady_state_d": round(steady_state_time_d, 1),
        "note": ref.get("note", ""),
        "reference": ref.get("reference", ""),
    }

    # If actual measured levels are provided, compare
    if steady_state_peak is not None and steady_state_peak > 0:
        result["measured_peak"] = steady_state_peak
        if ss_peak > 0:
            result["peak_ratio"] = round(steady_state_peak / ss_peak, 2)

    if steady_state_trough is not None and steady_state_trough > 0:
        result["measured_trough"] = steady_state_trough
        result["in_range"] = therapeutic_range[0] <= steady_state_trough <= therapeutic_range[1]
        result["trough_status"] = (
            "Below range — consider increasing dose" if steady_state_trough < therapeutic_range[0]
            else "Above range — consider reducing dose" if steady_state_trough > therapeutic_range[1]
            else "Within therapeutic range"
        )

    return {"status": "ok", **result}
