"""
BioDockify Clinical Pharmacy Module — extracted calculation logic.

This module provides pure-function calculations for clinical pharmacy
tools. The api/clinical.py handler is a thin wrapper that calls these
functions and handles HTTP/JSON concerns.

Functions:
    check_drug_interaction — DDI lookup from curated database
    calculate_tdm — Therapeutic Drug Monitoring calculations
    calculate_renal_adjust — CKD-EPI GFR + dose adjustment
    calculate_hepatic_adjust — Child-Pugh scoring + dose adjustment
    calculate_naranjo — ADR causality assessment
    calculate_ckd_epi — Standalone CKD-EPI GFR
    calculate_vancomycin_auc — AUC-guided vancomycin dosing
    screen_beers — AGS Beers Criteria 2023 screening
    screen_stopp_start — STOPP/START v2 criteria
"""

from .drug_interactions import check_drug_interaction, DRUG_INTERACTIONS
from .tdm import calculate_tdm, DRUG_RANGES
from .renal import calculate_renal_adjust, calculate_ckd_epi
from .hepatic import calculate_hepatic_adjust
from .adr import calculate_naranjo, NARANJO_QUESTIONS
from .vancomycin import calculate_vancomycin_auc
from .geriatrics import screen_beers, screen_stopp_start

__all__ = [
    "check_drug_interaction", "DRUG_INTERACTIONS",
    "calculate_tdm", "DRUG_RANGES",
    "calculate_renal_adjust", "calculate_ckd_epi",
    "calculate_hepatic_adjust",
    "calculate_naranjo", "NARANJO_QUESTIONS",
    "calculate_vancomycin_auc",
    "screen_beers", "screen_stopp_start",
]
