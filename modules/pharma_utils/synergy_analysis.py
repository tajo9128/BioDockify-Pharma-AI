"""
Drug Synergy Analysis — Chou-Talalay Combination Index.

Reference: Chou TC. Pharmacol Rev. 2006;58(3):621-81.
"""

import numpy as np
from typing import Dict, Any, List
from scipy import optimize


def chou_talalay_index(
    drug1_alone: List[Dict[str, float]],
    drug2_alone: List[Dict[str, float]],
    combination: List[Dict[str, float]],
    drug1_name: str = "Drug A",
    drug2_name: str = "Drug B",
) -> Dict[str, Any]:
    """Calculate Chou-Talalay Combination Index (CI).
    
    CI < 1: Synergy
    CI = 1: Additive
    CI > 1: Antagonism
    
    Args:
        drug1_alone: List of {dose, effect} for drug 1 alone
        drug2_alone: List of {dose, effect} for drug 2 alone
        combination: List of {dose_ratio, effect} for combination
        drug1_name: Name of drug 1
        drug2_name: Name of drug 2
    
    Returns:
        Dict with CI values and synergy assessment
    """
    try:
        # Fit dose-response curves for each drug alone
        d1_doses = np.array([d["dose"] for d in drug1_alone], dtype=float)
        d1_effects = np.array([d["effect"] for d in drug1_alone], dtype=float)
        
        d2_doses = np.array([d["dose"] for d in drug2_alone], dtype=float)
        d2_effects = np.array([d["effect"] for d in drug2_alone], dtype=float)
        
        # 4-parameter logistic fit: y = bottom + (top - bottom) / (1 + (x/EC50)^slope)
        def logistic_4p(x, top, bottom, ec50, slope):
            return bottom + (top - bottom) / (1 + (x / ec50) ** slope)
        
        # Fit drug 1
        p0_d1 = [np.max(d1_effects), np.min(d1_effects), np.median(d1_doses), 1.0]
        try:
            popt_d1, _ = optimize.curve_fit(logistic_4p, d1_doses, d1_effects, p0=p0_d1, maxfev=5000)
            ec50_d1 = popt_d1[2]
            slope_d1 = popt_d1[3]
        except:
            # Fallback: use 50% effect level
            ec50_d1 = np.median(d1_doses)
            slope_d1 = 1.0
        
        # Fit drug 2
        p0_d2 = [np.max(d2_effects), np.min(d2_effects), np.median(d2_doses), 1.0]
        try:
            popt_d2, _ = optimize.curve_fit(logistic_4p, d2_doses, d2_effects, p0=p0_d2, maxfev=5000)
            ec50_d2 = popt_d2[2]
            slope_d2 = popt_d2[3]
        except:
            ec50_d2 = np.median(d2_doses)
            slope_d2 = 1.0
        
        # Calculate CI for each combination dose
        ci_values = []
        for combo in combination:
            dose_ratio = combo.get("dose_ratio", 1.0)
            effect = combo.get("effect", 50)
            
            # Find doses that would produce this effect alone
            # From logistic: x = ec50 * ((top-bottom)/(y-bottom) - 1)^(1/slope)
            try:
                # Drug 1 dose for this effect level
                d1_effective_dose = ec50_d1 * ((popt_d1[0] - popt_d1[1]) / (effect - popt_d1[1]) - 1) ** (1/slope_d1)
                # Drug 2 dose for this effect level
                d2_effective_dose = ec50_d2 * ((popt_d2[0] - popt_d2[1]) / (effect - popt_d2[1]) - 1) ** (1/slope_d2)
                
                # Actual doses in combination
                d1_actual = dose_ratio * ec50_d1
                d2_actual = (1 - dose_ratio) * ec50_d2 if dose_ratio < 1 else ec50_d2
                
                # CI = (d1_actual / d1_effective) + (d2_actual / d2_effective)
                ci = (d1_actual / d1_effective_dose) + (d2_actual / d2_effective_dose) if d1_effective_dose > 0 and d2_effective_dose > 0 else float('inf')
                
                ci_values.append({
                    "effect_level": effect,
                    "dose_ratio": dose_ratio,
                    "ci": round(ci, 3),
                    "interpretation": "Synergy" if ci < 0.9 else ("Additive" if ci <= 1.1 else "Antagonism"),
                })
            except:
                ci_values.append({"effect_level": effect, "dose_ratio": dose_ratio, "ci": None, "interpretation": "Calculation error"})
        
        # Average CI
        valid_cis = [c["ci"] for c in ci_values if c["ci"] is not None]
        avg_ci = np.mean(valid_cis) if valid_cis else None
        
        if avg_ci and avg_ci < 0.9:
            verdict = "SYNERGISTIC"
        elif avg_ci and avg_ci <= 1.1:
            verdict = "ADDITIVE"
        else:
            verdict = "ANTAGONISTIC"
        
        return {
            "status": "ok",
            "drug1": drug1_name,
            "drug2": drug2_name,
            "ec50_drug1": round(ec50_d1, 2),
            "ec50_drug2": round(ec50_d2, 2),
            "ci_values": ci_values,
            "average_ci": round(avg_ci, 3) if avg_ci else None,
            "verdict": verdict,
            "interpretation": f"{drug1_name} + {drug2_name}: {verdict} (CI = {avg_ci:.2f})" if avg_ci else "Insufficient data",
            "reference": "Chou TC. Pharmacol Rev. 2006;58(3):621-81."
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
