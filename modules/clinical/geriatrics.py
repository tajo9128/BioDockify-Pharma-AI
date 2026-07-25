"""
Geriatric Medication Safety — Beers Criteria 2023 + STOPP/START v2.

References:
- American Geriatrics Society 2023 Beers Criteria Update Expert Panel.
  J Am Geriatr Soc. 2023;71:2052-2081.
- O'Mahony D et al. Age Ageing. 2015;44(2):213-218 (STOPP/START v2).
"""

from typing import Dict, Any, List


# ── Beers Criteria 2023: Potentially Inappropriate Medications ──
BEERS_MEDS = {
    # High-risk medications in older adults
    "diphenhydramine": {
        "risk": "High",
        "issue": "Anticholinergic, sedation, confusion, falls",
        "alternative": "Loratadine, cetirizine (nonsedating antihistamines)"
    },
    "hydroxyzine": {
        "risk": "High",
        "issue": "Anticholinergic, sedation, confusion",
        "alternative": "Loratadine, cetirizine"
    },
    "amitriptyline": {
        "risk": "High",
        "issue": "Anticholinergic, cardiac arrhythmia, sedation, cognitive impairment",
        "alternative": "SSRIs (sertraline, escitalopram) for depression"
    },
    "diazepam": {
        "risk": "High",
        "issue": "Falls, cognitive impairment, prolonged half-life in elderly",
        "alternative": "Lorazepam (shorter-acting), non-pharmacologic interventions"
    },
    "lorazepam": {
        "risk": "Moderate",
        "issue": "Falls, sedation (lower risk than diazepam)",
        "alternative": "Low dose, short duration only"
    },
    "alprazolam": {
        "risk": "High",
        "issue": "Falls, cognitive impairment, dependency",
        "alternative": "Non-pharmacologic anxiety management, buspirone"
    },
    "dextromethorphan": {
        "risk": "Moderate",
        "issue": "Anticholinergic, serotonin syndrome risk with SSRIs",
        "alternative": "Honey, dextromethorphan-free cough suppressants"
    },
    "omeprazole": {
        "risk": "Moderate",
        "issue": "Long-term: C. diff infection, bone loss, hypomagnesemia, B12 deficiency",
        "alternative": "Famotidine, step-down after 8 weeks if no clear indication"
    },
    "doxazosin": {
        "risk": "High",
        "issue": "Orthostatic hypotension, falls, urinary incontinence",
        "alternative": "ARBs, ACE inhibitors for hypertension"
    },
    "metoclopramide": {
        "risk": "High",
        "issue": "Extrapyramidal symptoms, tardive dyskinesia",
        "alternative": "Domperidone (where available)"
    },
    "chlorpromazine": {
        "risk": "High",
        "issue": "Anticholinergic, sedation, QT prolongation, falls",
        "alternative": "Low-dose risperidone, behavioral interventions"
    },
    "haloperidol": {
        "risk": "Moderate",
        "issue": "EPS, QT prolongation (avoid in dementia-related psychosis)",
        "alternative": "Non-pharmacologic interventions first, low-dose atypical if needed"
    },
    "ibuprofen": {
        "risk": "Moderate",
        "issue": "GI bleed, renal impairment, cardiac risk, hypertension",
        "alternative": "Acetaminophen (first-line), topical NSAIDs"
    },
    "naproxen": {
        "risk": "Moderate",
        "issue": "GI bleed, renal impairment, cardiac risk",
        "alternative": "Acetaminophen, topical diclofenac"
    },
    "diclofenac": {
        "risk": "High",
        "issue": "GI bleed, cardiac, renal risk",
        "alternative": "Acetaminophen, topical diclofenac"
    },
    "piroxicam": {
        "risk": "High",
        "issue": "Highest GI bleed risk among NSAIDs",
        "alternative": "Avoid entirely in elderly"
    },
    "duloxetine": {
        "risk": "Moderate",
        "issue": "SSRI/SNRI — falls, hyponatremia, bleeding",
        "alternative": "Start low, go slow, monitor closely"
    },
    "venlafaxine": {
        "risk": "Moderate",
        "issue": "Hypertension, falls, hyponatremia",
        "alternative": "Start low, monitor blood pressure"
    },
    "paroxetine": {
        "risk": "High",
        "issue": "Anticholinergic SSRI, falls, hyponatremia",
        "alternative": "Sertraline, escitalopram (less anticholinergic)"
    },
    "tolterodine": {
        "risk": "High",
        "issue": "Anticholinergic — urinary retention, constipation, confusion",
        "alternative": "Mirabegron, behavioral bladder training"
    },
}


def screen_beers(medications: List[str]) -> Dict[str, Any]:
    """Screen medications against AGS Beers Criteria 2023.

    Args:
        medications: List of medication names

    Returns:
        Dict with flagged medications, risk levels, alternatives
    """
    if not medications:
        return {"status": "error", "error": "Provide list of medications"}

    results = []
    high_risk_count = 0
    moderate_risk_count = 0

    for med in medications:
        med_lower = med.strip().lower()
        if med_lower in BEERS_MEDS:
            info = BEERS_MEDS[med_lower]
            risk = info["risk"]
            flagged = True
            if risk == "High":
                high_risk_count += 1
            elif risk == "Moderate":
                moderate_risk_count += 1
        else:
            info = {"risk": "None", "issue": "Not on Beers Criteria", "alternative": "—"}
            flagged = False

        results.append({
            "medication": med,
            "flagged": flagged,
            "risk": info["risk"],
            "issue": info["issue"],
            "alternative": info["alternative"],
        })

    safe_count = len(medications) - high_risk_count - moderate_risk_count

    if high_risk_count > 0:
        recommendation = (
            f"⚠️ {high_risk_count} HIGH-risk medication(s) found. "
            f"Consider alternatives listed above. Discuss with prescriber."
        )
    elif moderate_risk_count > 0:
        recommendation = (
            f"⚠️ {moderate_risk_count} MODERATE-risk medication(s) found. "
            f"Review necessity and duration. Consider alternatives."
        )
    else:
        recommendation = "✅ No potentially inappropriate medications found."

    return {
        "status": "ok",
        "total_medications": len(medications),
        "high_risk": high_risk_count,
        "moderate_risk": moderate_risk_count,
        "safe": safe_count,
        "results": results,
        "recommendation": recommendation,
        "reference": "2023 AGS Beers Criteria Update Expert Panel. J Am Geriatr Soc. 2023;71:2052-2081",
    }


def screen_stopp_start(
    medications: List[str],
    conditions: List[str],
) -> Dict[str, Any]:
    """Screen medications against STOPP/START v2 criteria.

    STOPP: potentially inappropriate prescriptions
    START: potentially missing prescriptions

    Args:
        medications: Current medication list
        conditions: Patient conditions (e.g., ["hypertension", "diabetes", "afib"])

    Returns:
        Dict with STOPP alerts and START recommendations
    """
    if not medications:
        return {"status": "error", "error": "Provide list of medications"}

    meds = [m.strip().lower() for m in medications]
    conds = [c.strip().lower() for c in conditions] if conditions else []
    stopp_alerts = []
    start_alerts = []

    # ── STOPP: Potentially Inappropriate Prescriptions ──
    if "diazepam" in meds:
        stopp_alerts.append({
            "rule": "STOPP-2.1", "med": "diazepam",
            "issue": "Benzodiazepine >4 weeks — dependency, falls, cognitive impairment",
            "action": "Taper off; use short-acting lorazepam if needed"
        })
    if "amitriptyline" in meds:
        stopp_alerts.append({
            "rule": "STOPP-2.4", "med": "amitriptyline",
            "issue": "Tricyclic antidepressant — anticholinergic, sedation, QT prolongation",
            "action": "Switch to SSRI (sertraline, escitalopram)"
        })
    if "omeprazole" in meds:
        stopp_alerts.append({
            "rule": "STOPP-11.1", "med": "omeprazole",
            "issue": "PPI >8 weeks without documented indication",
            "action": "Step down to famotidine or discontinue"
        })
    if "ibuprofen" in meds and "hypertension" in conds:
        stopp_alerts.append({
            "rule": "STOPP-6.1", "med": "ibuprofen",
            "issue": "NSAID + hypertension — increases CV and renal risk",
            "action": "Use acetaminophen, topical NSAIDs"
        })
    if "ibuprofen" in meds and any(c in conds for c in ["ckd", "renal", "kidney"]):
        stopp_alerts.append({
            "rule": "STOPP-6.2", "med": "ibuprofen",
            "issue": "NSAID + CKD — acute kidney injury risk",
            "action": "Avoid NSAIDs; use acetaminophen"
        })
    if "metformin" in meds and any(c in conds for c in ["ckd_stage_4", "ckd_stage_5", "esrd"]):
        stopp_alerts.append({
            "rule": "STOPP-8.2", "med": "metformin",
            "issue": "Metformin with eGFR <30 — lactic acidosis risk",
            "action": "Hold metformin, use insulin or other antidiabetics"
        })
    if any(m in meds for m in ["diphenhydramine", "chlorpheniramine", "hydroxyzine"]):
        stopp_alerts.append({
            "rule": "STOPP-2.3", "med": "antihistamine",
            "issue": "First-gen antihistamine — anticholinergic, falls, confusion",
            "action": "Switch to loratadine, cetirizine"
        })

    # ── START: Potentially Missing Prescriptions ──
    if "hypertension" in conds and not any(m in meds for m in ["lisinopril", "amlodipine", "losartan", "enalapril", "ramipril"]):
        start_alerts.append({
            "rule": "START-1.1", "condition": "hypertension",
            "recommendation": "Start ACE inhibitor or ARB if BP >140/90 after lifestyle changes"
        })
    if "diabetes" in conds and not any(m in meds for m in ["metformin", "insulin", "gliclazide"]):
        start_alerts.append({
            "rule": "START-4.1", "condition": "type 2 diabetes",
            "recommendation": "Start metformin (first-line) if eGFR ≥30"
        })
    if any(c in conds for c in ["atrial_fibrillation", "afib"]) and not any(m in meds for m in ["warfarin", "apixaban", "rivaroxaban", "edoxaban"]):
        start_alerts.append({
            "rule": "START-3.1", "condition": "atrial fibrillation",
            "recommendation": "Start anticoagulant (DOAC or warfarin) if CHA2DS2-VASc ≥2"
        })
    if any(c in conds for c in ["heart_failure", "hf", "chf"]) and not any(m in meds for m in ["carvedilol", "bisoprolol", "metoprolol"]):
        start_alerts.append({
            "rule": "START-2.1", "condition": "heart failure",
            "recommendation": "Start beta-blocker (carvedilol, bisoprolol, metoprolol succinate)"
        })
    if any(c in conds for c in ["osteoporosis", "fracture"]) and not any(m in meds for m in ["alendronate", "zoledronic", "risedronate"]):
        start_alerts.append({
            "rule": "START-11.1", "condition": "osteoporosis",
            "recommendation": "Start bisphosphonate or denosumab"
        })

    return {
        "status": "ok",
        "medications": len(medications),
        "conditions": conds,
        "stopp_alerts": stopp_alerts,
        "stopp_count": len(stopp_alerts),
        "start_alerts": start_alerts,
        "start_count": len(start_alerts),
        "recommendation": (
            f"STOPP: {len(stopp_alerts)} potentially inappropriate prescription(s) found. "
            f"START: {len(start_alerts)} potentially missing prescription(s) found."
        ),
        "reference": "O'Mahony D et al. Age Ageing. 2015;44(2):213-218 (STOPP/START v2)",
    }
