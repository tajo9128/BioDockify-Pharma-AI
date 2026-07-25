"""
BioDockify Pharmaceutics / Formulation Lab Module

Calculations for drug formulation, stability, dissolution modeling.
All pure functions, no Flask/Agent Zero deps.
"""

from .release_kinetics import fit_release_kinetics
from .stability import predict_shelf_life
from .dissolution_profile import compare_dissolution_profiles
from .excipient_db import get_excipients, search_excipients

__all__ = [
    "fit_release_kinetics",
    "predict_shelf_life",
    "compare_dissolution_profiles",
    "get_excipients",
    "search_excipients",
]
