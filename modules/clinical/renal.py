"""
Renal Dose Adjustment — CKD-EPI 2021 + dose adjustment calculator.

Reference: Inker et al. NEJM 2021;385:1804-1813 (race-free CKD-EPI)
"""

import math
from typing import Dict, Any, Optional


def calculate_ckd_epi(serum_creatinine_mg_dl: float, age: int, sex: str) -> Dict[str, Any]:
    """Calculate eGFR using CKD-EPI 2021 equation (race-free).

    Args:
        serum_creatinine_mg_dl: Serum creatinine in mg/dL
        age: Patient age in years
        sex: "male" or "female"

    Returns:
        Dict with eGFR, CKD stage
    """
    scr = serum_creatinine_mg_dl
    if scr <= 0 or age <= 0:
        return {"status": "error", "error": "Creatinine and age must be > 0"}

    # CKD-EPI 2021 (race-free)
    kappa = 0.7 if sex.lower() == "female" else 0.9
    alpha = -0.241 if sex.lower() == "female" else -0.302
    sex_modifier = 1.018 if sex.lower() == "female" else 1.0
    scr_ratio = scr / kappa

    gfr = 142 * min(scr_ratio, 1) ** alpha * max(scr_ratio, 1) ** (-1.200) * 0.9938 ** age * sex_modifier

    # CKD staging
    if gfr >= 90: stage = "G1 (Normal)"
    elif gfr >= 60: stage = "G2 (Mild)"
    elif gfr >= 45: stage = "G3a (Mild-Moderate)"
    elif gfr >= 30: stage = "G3b (Moderate-Severe)"
    elif gfr >= 15: stage = "G4 (Severe)"
    else: stage = "G5 (Kidney Failure)"

    return {
        "status": "ok",
        "gfr_ml_min": round(gfr, 1),
        "ckd_stage": stage,
        "reference": "CKD-EPI 2021 (Inker et al., NEJM 385:1804-1813)"
    }


def calculate_renal_adjust(
    serum_creatinine_mg_dl: float,
    age: int,
    sex: str,
    drug: Optional[str] = None,
    dose_mg: Optional[float] = None,
) -> Dict[str, Any]:
    """Calculate renal dose adjustment for drugs cleared renally.

    Args:
        serum_creatinine_mg_dl: Serum creatinine in mg/dL
        age: Patient age
        sex: "male" or "female"
        drug: Optional drug name for specific guidance
        dose_mg: Optional current dose to calculate adjusted dose

    Returns:
        Dict with eGFR, CKD stage, dose adjustment factors
    """
    eGFR_result = calculate_ckd_epi(serum_creatinine_mg_dl, age, sex)
    if "error" in eGFR_result:
        return eGFR_result

    gfr = eGFR_result["gfr_ml_min"]
    stage = eGFR_result["ckd_stage"]

    # General dose adjustment factors by eGFR
    if gfr >= 60:
        factor = 1.0
        advice = "No dose adjustment needed"
        frequency = "Normal dosing"
    elif gfr >= 30:
        factor = 0.75
        advice = "Consider 75% dose reduction or extend interval"
        frequency = "Dose-reduce or extend interval"
    elif gfr >= 15:
        factor = 0.5
        advice = "Reduce dose by 50% or extend interval"
        frequency = "Dose-reduce by 50% or extend interval"
    else:
        factor = 0.25
        advice = "Reduce dose by 75% or extend interval. Consider drug discontinuation."
        frequency = "Max dose 25% of normal"

    result = {
        "status": "ok",
        "gfr_ml_min": round(gfr, 1),
        "ckd_stage": stage,
        "adjustment_factor": factor,
        "advice": advice,
        "frequency_adjustment": frequency,
        "reference": "Clinical Pharmacology and Therapeutics guidance",
    }

    if dose_mg and dose_mg > 0:
        adjusted_dose = round(dose_mg * factor)
        result["current_dose_mg"] = dose_mg
        result["adjusted_dose_mg"] = adjusted_dose
        # Alias for Clinical UI (reads suggested_dose_mg)
        result["suggested_dose_mg"] = adjusted_dose

    # Drug-specific guidance
    if drug:
        drug_lower = drug.strip().lower()
        drug_guidance = _get_drug_renal_guidance(drug_lower, gfr)
        if drug_guidance:
            result["drug_specific"] = drug_guidance

    return result


def _get_drug_renal_guidance(drug: str, gfr: float) -> Optional[str]:
    """Drug-specific renal dosing guidance."""
    guidance = {
        "metformin": f"{'No dose change' if gfr >= 60 else 'Dose-reduce' if gfr >= 30 else 'STOP — contraindicated if eGFR < 30'}",
        "gabapentin": f"{'Normal dosing' if gfr >= 60 else 'Start 300mg QD' if gfr >= 30 else 'Start 100mg QD'}",
        "acyclovir": f"{'Normal dosing' if gfr >= 60 else 'Dose-reduce or extend interval' if gfr >= 30 else 'Dose-reduce by 75%'}",
        "vancomycin": "Use AUC-guided dosing (Rybak 2020). Avoid trough-only monitoring.",
        "digoxin": "Digoxin is 70% renally cleared. Reduce dose if eGFR < 30. Target 0.5-0.9 ng/mL for heart failure.",
        "colistin": "Dose per CLcr. Avoid if eGFR < 10.",
    }
    return guidance.get(drug)
