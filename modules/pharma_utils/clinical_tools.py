"""
Clinical Tools — Beers Criteria, STOPP/START, drug safety screening.

AGS Beers Criteria: https://doi.org/10.1093/gerona/glab023
STOPP/START v2: https://doi.org/10.1093/ageing/afu145
"""

from typing import List, Dict, Any


# AGS Beers Criteria 2023 — Potentially Inappropriate Medications (PIMs) for Older Adults
BEERS_CRITERIA = {
    "anticholinergics": {
        "severity": "HIGH",
        "drugs": ["diphenhydramine", "dimenhydrinate", "chlorpheniramine", "hydroxyzine", "amitriptyline", "doxepin", "imipramine", "paroxetine"],
        "risks": "Confusion, constipation, urinary retention, dry mouth, blurred vision",
        "alternative": "Loratadine, cetirizine (for allergies); nortriptyline (for depression); sertraline (for depression)",
        "rationale": "Highly anticholinergic; risk of cognitive decline and delirium in older adults"
    },
    "benzodiazepines": {
        "severity": "HIGH",
        "drugs": ["diazepam", "lorazepam", "alprazolam", "clonazepam", "temazepam", "triazolam"],
        "risks": "Falls, fractures, cognitive impairment, delirium, motor vehicle accidents",
        "alternative": "Melatonin, trazodone, CBT-I for insomnia; buspirone for anxiety",
        "rationale": "Increased sensitivity to benzodiazepines in older adults; slower metabolism"
    },
    "antipsychotics": {
        "severity": "HIGH",
        "drugs": ["haloperidol", "risperidone", "olanzapine", "quetiapine", "aripiprazole"],
        "risks": "Stroke, cognitive decline, mortality, extrapyramidal symptoms",
        "alternative": "Behavioral interventions first; if needed, lowest dose shortest duration",
        "rationale": "FDA black box warning: increased risk of death in elderly with dementia"
    },
    "opioids": {
        "severity": "HIGH",
        "drugs": ["morphine", "oxycodone", "hydrocodone", "fentanyl", "tramadol", "codeine"],
        "risks": "Respiratory depression, falls, constipation, cognitive impairment, addiction",
        "alternative": "Acetaminophen, NSAIDs (short-term), physical therapy, nerve blocks",
        "rationale": "Increased sensitivity to CNS depression; higher risk of falls"
    },
    "nsaids": {
        "severity": "MODERATE",
        "drugs": ["ibuprofen", "naproxen", "diclofenac", "piroxicam", "indomethacin", "ketorolac"],
        "risks": "GI bleeding, renal impairment, cardiovascular events, hypertension",
        "alternative": "Acetaminophen (first-line), topical NSAIDs, physical therapy",
        "rationale": "GI bleed risk 4-5x higher in older adults; renal impairment risk"
    },
    "antidiabetics": {
        "severity": "MODERATE",
        "drugs": ["glibenclamide", "glipizide", "glyburide"],
        "risks": "Severe hypoglycemia, falls, cognitive impairment",
        "alternative": "Metformin (first-line), DPP-4 inhibitors (sitagliptin, linagliptin)",
        "rationale": "Long-acting sulfonylureas cause prolonged hypoglycemia in elderly"
    },
    "antihypertensives": {
        "severity": "MODERATE",
        "drugs": ["doxazosin", "prazosin", "terazosin", "alpha-methyldopa", "clonidine"],
        "risks": "Orthostatic hypotension, falls, syncope, bradycardia",
        "alternative": "ACE inhibitors, ARBs, low-dose thiazides, amlodipine",
        "rationale": "Alpha-blockers cause orthostatic hypotension; high fall risk"
    },
    "proton_pump_inhibitors": {
        "severity": "LOW",
        "drugs": ["omeprazole", "esomeprazole", "lansoprazole", "pantoprazole", "rabeprazole"],
        "risks": "C. difficile infection, bone fractures, hypomagnesemia, B12 deficiency",
        "alternative": "H2 blockers (famotidine), antacids, taper after 8 weeks",
        "rationale": "Long-term PPI use (>8 weeks) associated with multiple adverse effects"
    },
    "muscle_relaxants": {
        "severity": "HIGH",
        "drugs": ["carisoprodol", "cyclobenzaprine", "metaxalone", "methocarbamol", "tizanidine"],
        "risks": "Sedation, weakness, falls, confusion, constipation",
        "alternative": "Physical therapy, stretching, heat/cold therapy",
        "rationale": "Anticholinergic effects, sedation, increased fall risk"
    },
    "antispasmodics": {
        "severity": "MODERATE",
        "drugs": ["oxybutynin", "tolterodine", "solifenacin", "trospium", "darifenacin"],
        "risks": "Urinary retention, constipation, confusion, dry mouth",
        "alternative": "Behavioral therapy, pelvic floor exercises, mirabegron",
        "rationale": "Anticholinergic burden; risk of urinary retention in men with BPH"
    }
}


def beers_criteria_screen(medications: List[str]) -> Dict[str, Any]:
    """Screen medications against AGS Beers Criteria 2023.
    
    Args:
        medications: List of medication names to screen
    
    Returns:
        Dict with screening results and recommendations
    """
    if not medications:
        return {"status": "error", "error": "Provide list of medications to screen"}
    
    results = []
    high_risk_count = 0
    moderate_risk_count = 0
    
    for med in medications:
        med_lower = med.strip().lower()
        found = False
        
        for category, criteria in BEERS_CRITERIA.items():
            if med_lower in criteria["drugs"]:
                results.append({
                    "medication": med,
                    "category": [category],
                    "severity": criteria["severity"],
                    "risks": criteria["risks"],
                    "alternative": criteria["alternative"],
                    "rationale": criteria["rationale"]
                })
                
                if criteria["severity"] == "HIGH":
                    high_risk_count += 1
                elif criteria["severity"] == "MODERATE":
                    moderate_risk_count += 1
                
                found = True
                break
        
        if not found:
            results.append({
                "medication": med,
                "categories": [],
                "severity": "NONE",
                "risks": "Not on Beers Criteria list",
                "alternative": "",
                "rationale": ""
            })
    
    return {
        "status": "ok",
        "total_medications": len(medications),
        "high_risk_count": high_risk_count,
        "moderate_risk_count": moderate_risk_count,
        "safe_count": len(medications) - high_risk_count - moderate_risk_count,
        "results": results,
        "recommendation": (
            f"Found {high_risk_count} HIGH-risk and {moderate_risk_count} MODERATE-risk medications. "
            f"{'Review alternatives with prescriber.' if high_risk_count > 0 else 'Current medications are within Beers Criteria guidelines.'}"
        ),
        "reference": "2023 American Geriatrics Society Beers Criteria Update Expert Panel. J Am Geriatr Soc. 2023."
    }
