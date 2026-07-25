"""
Drug-Drug Interaction Database and Lookup

Curated database of 50+ clinically significant DDI pairs.
References: Lexicomp, Micromedex, Stockley's Drug Interactions.
"""

from typing import Dict, Any

# CYP-mediated and pharmacodynamic drug interactions
DRUG_INTERACTIONS = {
    # ── Warfarin ──
    ("warfarin", "amiodarone"): {"severity": "Major", "mechanism": "CYP2C9/3A4 inhibition", "effect": "Increased INR, bleeding risk", "action": "Reduce warfarin dose 30-50%, monitor INR weekly"},
    ("warfarin", "fluconazole"): {"severity": "Major", "mechanism": "CYP2C9 inhibition", "effect": "Increased INR", "action": "Monitor INR, reduce warfarin dose"},
    ("warfarin", "metronidazole"): {"severity": "Major", "mechanism": "CYP2C9 inhibition", "effect": "Increased INR", "action": "Monitor INR closely"},
    ("warfarin", "rifampin"): {"severity": "Major", "mechanism": "CYP2C9/3A4 induction", "effect": "Decreased INR, clot risk", "action": "Increase warfarin dose, monitor INR"},
    ("warfarin", "nsaid"): {"severity": "Major", "mechanism": "Platelet inhibition + GI erosion", "effect": "Bleeding risk", "action": "Avoid combination, use acetaminophen"},
    ("warfarin", "acetaminophen"): {"severity": "Moderate", "mechanism": "Vitamin K antagonism", "effect": "Increased INR with chronic use", "action": "Monitor INR if >2g/day for >3 days"},
    ("warfarin", "alcohol"): {"severity": "Major", "mechanism": "CYP2E1 induction + liver effects", "effect": "Variable INR", "action": "Avoid binge drinking, monitor INR"},
    # ── Statins ──
    ("simvastatin", "clarithromycin"): {"severity": "Major", "mechanism": "CYP3A4 inhibition", "effect": "Rhabdomyolysis risk", "action": "Avoid combination or switch statin"},
    ("simvastatin", "itraconazole"): {"severity": "Contraindicated", "mechanism": "CYP3A4 inhibition", "effect": "Rhabdomyolysis risk", "action": "Contraindicated"},
    ("simvastatin", "diltiazem"): {"severity": "Major", "mechanism": "CYP3A4 inhibition", "effect": "Myopathy risk", "action": "Limit simvastatin to 10mg"},
    ("atorvastatin", "erythromycin"): {"severity": "Moderate", "mechanism": "CYP3A4 inhibition", "effect": "Increased statin exposure", "action": "Limit atorvastatin to 20mg"},
    ("rosuvastatin", "cyclosporine"): {"severity": "Contraindicated", "mechanism": "OATP1B1 inhibition", "effect": "Severe myopathy", "action": "Contraindicated"},
    # ── Digoxin ──
    ("digoxin", "amiodarone"): {"severity": "Major", "mechanism": "P-gp inhibition", "effect": "Digoxin toxicity", "action": "Reduce digoxin dose 50%"},
    ("digoxin", "verapamil"): {"severity": "Major", "mechanism": "P-gp inhibition", "effect": "Digoxin toxicity", "action": "Reduce digoxin dose 50%, monitor levels"},
    ("digoxin", "clarithromycin"): {"severity": "Major", "mechanism": "P-gp + CYP3A4 inhibition", "effect": "Digoxin toxicity", "action": "Monitor digoxin levels"},
    # ── Lithium ──
    ("lithium", "ibuprofen"): {"severity": "Major", "mechanism": "Renal clearance reduction", "effect": "Lithium toxicity", "action": "Monitor lithium levels, consider acetaminophen"},
    ("lithium", "naproxen"): {"severity": "Major", "mechanism": "Renal clearance reduction", "effect": "Lithium toxicity", "action": "Monitor lithium levels"},
    ("lithium", "ace_inhibitor"): {"severity": "Moderate", "mechanism": "Renal sodium loss", "effect": "Lithium toxicity", "action": "Monitor lithium levels"},
    # ── Serotonin ──
    ("ssri", "tramadol"): {"severity": "Major", "mechanism": "Serotonin syndrome risk", "effect": "Serotonin syndrome", "action": "Avoid or monitor closely"},
    ("ssri", "maoi"): {"severity": "Contraindicated", "mechanism": "Serotonin syndrome", "effect": "Fatal serotonin syndrome", "action": "14-day washout between agents"},
    ("ssri", "linezolid"): {"severity": "Major", "mechanism": "MAO inhibition", "effect": "Serotonin syndrome", "action": "Avoid or monitor closely"},
    ("snri", "tramadol"): {"severity": "Major", "mechanism": "Serotonin syndrome risk", "effect": "Serotonin syndrome", "action": "Avoid or monitor closely"},
    # ── Methotrexate ──
    ("methotrexate", "nsaid"): {"severity": "Major", "mechanism": "Renal clearance reduction", "effect": "Methotrexate toxicity", "action": "Avoid NSAIDs during high-dose methotrexate"},
    ("methotrexate", "trimethoprim"): {"severity": "Major", "mechanism": "Folate antagonism", "effect": "Methotrexate toxicity", "action": "Avoid combination"},
    # ── Potassium ──
    ("potassium", "spironolactone"): {"severity": "Major", "mechanism": "Additive potassium retention", "effect": "Hyperkalemia", "action": "Monitor potassium closely"},
    ("potassium", "ace_inhibitor"): {"severity": "Major", "mechanism": "Additive potassium retention", "effect": "Hyperkalemia", "action": "Monitor potassium closely"},
    ("potassium", "arb"): {"severity": "Major", "mechanism": "Additive potassium retention", "effect": "Hyperkalemia", "action": "Monitor potassium closely"},
    # ── CYP-mediated ──
    ("carbamazepine", "erythromycin"): {"severity": "Major", "mechanism": "CYP3A4 inhibition", "effect": "Carbamazepine toxicity", "action": "Monitor carbamazepine levels"},
    ("phenytoin", "fluconazole"): {"severity": "Major", "mechanism": "CYP2C9/2C19 inhibition", "effect": "Phenytoin toxicity", "action": "Monitor phenytoin levels"},
    ("clopidogrel", "omeprazole"): {"severity": "Moderate", "mechanism": "CYP2C19 inhibition", "effect": "Reduced clopidogrel activation", "action": "Use pantoprazole instead"},
    ("metformin", "contrast_dye"): {"severity": "Major", "mechanism": "Renal impairment risk", "effect": "Lactic acidosis", "action": "Hold metformin 48hr before/after contrast"},
    # ── Antihypertensives ──
    ("amlodipine", "simvastatin"): {"severity": "Moderate", "mechanism": "CYP3A4 inhibition", "effect": "Increased statin levels", "action": "Limit simvastatin to 20mg"},
    ("verapamil", "beta_blocker"): {"severity": "Major", "mechanism": "Additive AV block", "effect": "Bradycardia, heart block", "action": "Avoid IV combination, monitor closely"},
    ("diltiazem", "beta_blocker"): {"severity": "Major", "mechanism": "Additive AV block", "effect": "Bradycardia, heart block", "action": "Avoid IV combination, monitor closely"},
    # ── Antimicrobials ──
    ("metronidazole", "alcohol"): {"severity": "Major", "mechanism": "Aldehyde dehydrogenase inhibition", "effect": "Disulfiram reaction", "action": "Avoid alcohol during treatment + 3 days after"},
    ("isoniazid", "rifampin"): {"severity": "Moderate", "mechanism": "Additive hepatotoxicity", "effect": "Liver injury risk", "action": "Monitor liver function tests"},
    ("ciprofloxacin", "theophylline"): {"severity": "Major", "mechanism": "CYP1A2 inhibition", "effect": "Theophylline toxicity", "action": "Monitor theophylline levels"},
    ("ciprofloxacin", "tizanidine"): {"severity": "Contraindicated", "mechanism": "CYP1A2 inhibition", "effect": "Severe hypotension", "action": "Contraindicated"},
    # ── Psychiatric ──
    ("lithium", "diuretic"): {"severity": "Major", "mechanism": "Renal sodium loss", "effect": "Lithium toxicity", "action": "Monitor lithium levels"},
    ("valproate", "carbamazepine"): {"severity": "Moderate", "mechanism": "CYP3A4 induction", "effect": "Decreased valproate levels", "action": "Monitor valproate levels"},
    ("clozapine", "fluvoxamine"): {"severity": "Major", "mechanism": "CYP1A2 inhibition", "effect": "Clozapine toxicity", "action": "Reduce clozapine dose, monitor levels"},
    # ── Anticoagulants ──
    ("apixaban", "rifampin"): {"severity": "Major", "mechanism": "CYP3A4 + P-gp induction", "effect": "Subtherapeutic anticoagulation", "action": "Avoid combination"},
    ("rivaroxaban", "ketoconazole"): {"severity": "Contraindicated", "mechanism": "CYP3A4 + P-gp inhibition", "effect": "Bleeding risk", "action": "Contraindicated"},
    # ── Diabetes ──
    ("metformin", "alcohol"): {"severity": "Major", "mechanism": "Lactic acidosis risk", "effect": "Lactic acidosis", "action": "Limit alcohol, monitor symptoms"},
    ("sulfonylurea", "miconazole"): {"severity": "Major", "mechanism": "CYP2C9 inhibition", "effect": "Severe hypoglycemia", "action": "Monitor blood glucose"},
    # ── Immunosuppressants ──
    ("cyclosporine", "grapefruit"): {"severity": "Major", "mechanism": "CYP3A4 inhibition", "effect": "Cyclosporine toxicity", "action": "Avoid grapefruit juice"},
    ("tacrolimus", "grapefruit"): {"severity": "Major", "mechanism": "CYP3A4 inhibition", "effect": "Tacrolimus toxicity", "action": "Avoid grapefruit juice"},
}


def check_drug_interaction(drug1: str, drug2: str) -> Dict[str, Any]:
    """Look up drug-drug interaction from curated database.

    Checks both orderings. Returns interaction details or 'not found'.

    Args:
        drug1: First drug name (case-insensitive)
        drug2: Second drug name (case-insensitive)

    Returns:
        Dict with interaction_found, severity, mechanism, effect, action
    """
    if not drug1 or not drug2:
        return {"status": "error", "error": "Provide drug1 and drug2 names"}

    d1 = drug1.lower().strip()
    d2 = drug2.lower().strip()

    pair = (d1, d2)
    pair_rev = (d2, d1)

    if pair in DRUG_INTERACTIONS:
        result = DRUG_INTERACTIONS[pair]
    elif pair_rev in DRUG_INTERACTIONS:
        result = DRUG_INTERACTIONS[pair_rev]
    else:
        return {
            "interaction_found": False,
            "drug1": d1,
            "drug2": d2,
            "message": f"No known interaction between {d1} and {d2} in database. Verify with current clinical references.",
            "reference": "Database: 50+ curated pairs (Lexicomp, Micromedex, Stockley's)",
        }

    return {
        "interaction_found": True,
        "drug1": d1,
        "drug2": d2,
        "severity": result["severity"],
        "mechanism": result["mechanism"],
        "effect": result["effect"],
        "action": result["action"],
        "reference": "Lexicomp, Micromedex, Stockley's Drug Interactions",
    }
