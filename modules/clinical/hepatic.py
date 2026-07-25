"""
Hepatic Dose Adjustment — Child-Pugh Classification + drug-specific guidance.

Reference: Child CG, Turcotte JG. Surgery and Portal Hypertension. 1964.
Pugh RN et al. Br J Surg. 1973.
"""

from typing import Dict, Any, Optional


def calculate_hepatic_adjust(
    bilirubin_mg_dl: float,
    albumin_g_dl: float,
    inr: float,
    ascites: str,  # "none", "mild", "moderate_severe"
    encephalopathy: str,  # "none", "grade_1_2", "grade_3_4"
    drug: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculate Child-Pugh score and hepatic dose adjustment.

    Args:
        bilirubin_mg_dl: Serum bilirubin (mg/dL)
        albumin_g_dl: Serum albumin (g/dL)
        inr: International normalized ratio
        ascites: "none", "mild", or "moderate_severe"
        encephalopathy: "none", "grade_1_2", or "grade_3_4"
        drug: Optional drug name for specific guidance

    Returns:
        Dict with Child-Pugh score, class, dose adjustment guidance
    """
    # Score bilirubin
    if bilirubin_mg_dl < 2:
        bp_score = 1
    elif bilirubin_mg_dl <= 3:
        bp_score = 2
    else:
        bp_score = 3

    # Score albumin
    if albumin_g_dl > 3.5:
        al_score = 1
    elif albumin_g_dl >= 2.8:
        al_score = 2
    else:
        al_score = 3

    # Score INR
    if inr < 1.7:
        inr_score = 1
    elif inr <= 2.3:
        inr_score = 2
    else:
        inr_score = 3

    # Score ascites
    asc_score = {"none": 1, "mild": 2, "moderate_severe": 3}.get(ascites.lower().replace(" ", "_"), 1)

    # Score encephalopathy
    enc_score = {"none": 1, "grade_1_2": 2, "grade_3_4": 3}.get(encephalopathy.lower().replace(" ", "_").replace("/", "_"), 1)

    total = bp_score + al_score + inr_score + asc_score + enc_score

    if total <= 6:
        child_pugh_class = "A"
        severity = "Mild hepatic impairment"
        adjustment = "No dose adjustment needed in most cases"
    elif total <= 9:
        child_pugh_class = "B"
        severity = "Moderate hepatic impairment"
        adjustment = "Dose-reduce 25-50% for hepatically cleared drugs"
    else:
        child_pugh_class = "C"
        severity = "Severe hepatic impairment"
        adjustment = "Dose-reduce 50-75% or avoid hepatotoxic drugs"

    return {
        "status": "ok",
        "total_score": total,
        "child_pugh_class": child_pugh_class,
        "severity": severity,
        "adjustment": adjustment,
        "components": {
            "bilirubin": {"score": bp_score, "value": bilirubin_mg_dl},
            "albumin": {"score": al_score, "value": albumin_g_dl},
            "inr": {"score": inr_score, "value": inr},
            "ascites": {"score": asc_score, "value": ascites},
            "encephalopathy": {"score": enc_score, "value": encephalopathy},
        },
        "reference": "Child CG, Turcotte JG. Surgery and Portal Hypertension. 1964; Pugh RN et al. Br J Surg. 1973"
    }
