"""
ADR Causality Assessment — Naranjo Scale (1981).

Reference: Naranjo CA et al. Clin Pharmacol Ther. 1981;30(1):239-245.
"""

from typing import Dict, Any, List


# Naranjo 10-question scale
NARANJO_QUESTIONS = [
    {"q": "Are there previous conclusive reports on this reaction?", "yes": 1, "no": 0, "unknown": 0},
    {"q": "Did the adverse event appear after the suspected drug was administered?", "yes": 2, "no": -1, "unknown": 0},
    {"q": "Did the adverse reaction improve when the drug was discontinued?", "yes": 1, "no": 0, "unknown": 0},
    {"q": "Did the adverse reaction reappear when the drug was re-administered?", "yes": 2, "no": -1, "unknown": 0},
    {"q": "Are there alternative causes that could have caused the reaction?", "yes": -1, "no": 2, "unknown": 0},
    {"q": "Did the reaction reappear when a placebo was given?", "yes": -1, "no": 1, "unknown": 0},
    {"q": "Was the drug detected in the blood (or other fluids) in toxic concentrations?", "yes": 1, "no": 0, "unknown": 0},
    {"q": "Was the reaction more severe when the dose was increased?", "yes": 1, "no": 0, "unknown": 0},
    {"q": "Did the patient have a similar reaction to the same or similar drugs?", "yes": 1, "no": 0, "unknown": 0},
    {"q": "Was the adverse event confirmed by objective evidence?", "yes": 1, "no": 0, "unknown": 0},
]


def calculate_naranjo(answers: List[str]) -> Dict[str, Any]:
    """Calculate Naranjo ADR causality score.

    Args:
        answers: List of 10 answers ("yes", "no", "unknown") for each Naranjo question

    Returns:
        Dict with total score, causality category, and per-question breakdown
    """
    if len(answers) != 10:
        return {"status": "error", "error": "Provide exactly 10 answers (yes/no/unknown)"}

    total = 0
    breakdown = []
    for i, ans in enumerate(answers):
        ans_lower = ans.strip().lower()
        q = NARANJO_QUESTIONS[i]
        if ans_lower in ("yes", "y", "1"):
            pts = q["yes"]
        elif ans_lower in ("no", "n", "0"):
            pts = q["no"]
        else:
            pts = q["unknown"]
        total += pts
        breakdown.append({"question": q["q"], "answer": ans, "points": pts})

    # Causality category
    if total >= 9:
        category = "Definite"
    elif total >= 5:
        category = "Probable"
    elif total >= 1:
        category = "Possible"
    else:
        category = "Doubtful"

    return {
        "status": "ok",
        "total_score": total,
        "category": category,
        "breakdown": breakdown,
        "interpretation": f"Score: {total} → {category} ADR causality",
        "reference": "Naranjo CA et al. Clin Pharmacol Ther. 1981;30(1):239-245"
    }
