"""
BioDockify Pharma Utilities — Shared calculations across departments.

Provides:
- Shared dissolution f2/f1 calculation (consolidates duplicate)
- Cheng-Prusoff correction (Ki from IC50)
- AUC-guided vancomycin dosing
- System Suitability Testing (SST) calculator
- Content Uniformity calculator (USP <905>)
- Beers Criteria screening
- DOE design generator (full factorial, fractional factorial, Taguchi)
- Chou-Talalay Combination Index (drug synergy)
- SAR table generator
- Ki calculator from IC50

All calculations follow FDA/EMA/ICH/USP guidelines.
"""

from .dissolution import calculate_f2, calculate_f1
from .pk_calculations import cheng_prusoff, auc_guided_vancomycin, ki_from_ic50
from .quality_control import system_suitability, content_uniformity
from .clinical_tools import beers_criteria_screen
from .experimental_design import full_factorial, fractional_factorial, taguchi_design
from .synergy_analysis import chou_talalay_index
from .sar_analysis import generate_sar_table

__all__ = [
    "calculate_f2", "calculate_f1",
    "cheng_prusoff", "auc_guided_vancomycin", "ki_from_ic50",
    "system_suitability", "content_uniformity",
    "beers_criteria_screen",
    "full_factorial", "fractional_factorial", "taguchi_design",
    "chou_talalay_index",
    "generate_sar_table",
]
