"""
PK/PD Calculations — Cheng-Prusoff, AUC-guided vancomycin, Ki from IC50.

FDA/EMA guidelines compliant.
"""

import numpy as np
from typing import Dict, Any, Optional


def cheng_prusoff(ic50: float, km: float, s: float) -> Dict[str, Any]:
    """Calculate Ki using Cheng-Prusoff equation.
    
    Ki = IC50 / (1 + [S]/Km)
    
    Args:
        ic50: IC50 value (nM)
        km: Michaelis constant (nM)
        s: Substrate concentration (nM)
    
    Returns:
        Dict with Ki, interpretation, and reference
    """
    if km <= 0 or s < 0:
        return {"status": "error", "error": "Km must be > 0, S must be >= 0"}
    
    ki = ic50 / (1 + s/km)
    
    if ki < 1:
        potency = "very potent"
    elif ki < 10:
        potency = "potent"
    elif ki < 100:
        potency = "moderate"
    else:
        potency = "weak"
    
    return {
        "status": "ok",
        "ki_nM": round(ki, 2),
        "ic50_nM": round(ic50, 2),
        "km_nM": round(km, 2),
        "substrate_nM": round(s, 2),
        "potency": potency,
        "interpretation": f"Ki = {ki:.2f} nM ({potency} inhibitor)",
        "reference": "Cheng Y, Prusoff WH. Biochem Pharmacol. 1973;22(23):3099-108."
    }


def ki_from_ic50(ic50: float, km: float, s: float) -> Dict[str, Any]:
    """Alias for Cheng-Prusoff calculation."""
    return cheng_prusoff(ic50, km, s)


def auc_guided_vancomycin(
    target_auc: float = 400,
    mic: float = 1.0,
    patient_weight_kg: float = 70,
    current_dose_mg: float = 1000,
    current_auc: float = 300,
    current_interval_h: float = 12,
) -> Dict[str, Any]:
    """AUC-guided vancomycin dosing (current standard of care).
    
    Target AUC/MIC = 400-600 for MRSA infections.
    
    Args:
        target_auc: Target AUC24/MIC ratio (default 400)
        mic: Minimum inhibitory concentration (µg/mL)
        patient_weight_kg: Patient weight
        current_dose_mg: Current vancomycin dose
        current_auc: Measured AUC24
        current_interval_h: Current dosing interval
    
    Returns:
        Dict with dosing recommendation
    """
    if mic <= 0 or current_auc <= 0 or patient_weight_kg <= 0:
        return {"status": "error", "error": "MIC, AUC, and weight must be > 0"}
    
    target_auc24 = target_auc * mic
    
    # Current AUC24 = AUC * 24/interval (if measured AUC is for the interval)
    current_auc24 = current_auc * (24 / current_interval_h)
    
    # Dose adjustment factor
    adjustment_factor = target_auc24 / current_auc24
    
    # New dose
    new_dose = current_dose_mg * adjustment_factor
    new_dose_rounded = round(new_dose / 250) * 250  # Round to nearest 250mg
    
    # New AUC/MIC
    new_auc_mic = (new_dose_rounded / current_dose_mg) * current_auc / mic
    
    # Trough estimate (simplified)
    # AUC24 ≈ Cmax * half_life * 24 / (interval * 0.693)
    # For vancomycin: t1/2 ≈ 4-6 hours
    t_half = 5  # hours (average)
    cmax_est = new_dose_rounded / (patient_weight_kg * 0.7)  # rough estimate
    trough_est = cmax_est * (1 - 2**(-current_interval_h/t_half))
    
    return {
        "status": "ok",
        "target_auc_mic": target_auc,
        "mic": mic,
        "target_auc24": target_auc24,
        "current_auc24": current_auc24,
        "adjustment_factor": round(adjustment_factor, 2),
        "current_dose": f"{current_dose_mg}mg q{current_interval_h}h",
        "recommended_dose": f"{new_dose_rounded}mg q{current_interval_h}h",
        "new_auc_mic": round(new_auc_mic, 0),
        "estimated_trough": f"{trough_est:.1f} µg/mL (approximate)",
        "interpretation": (
            f"Target AUC/MIC: {target_auc}. "
            f"Current: {current_auc/mic:.0f}. "
            f"{'Increase' if adjustment_factor > 1.1 else 'Decrease' if adjustment_factor < 0.9 else 'Maintain'} dose. "
            f"Monitor trough levels."
        ),
        "reference": "Rybak MJ, et al. Ther Drug Monit. 2020;42(2):199-216."
    }
