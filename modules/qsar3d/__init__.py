"""
BioDockify 3D-QSAR Engine
Merges Open3DQSAR's field-based approach (MIF calculation, PLS, validation)
with Py-CoMFA's Python implementation patterns.

Based on:
- Open3DQSAR (Tosco & Balle, GPL v3) — C algorithms for MIF, PLS, validation
- Py-CoMFA / 3d-qsar.com (Ragno, Sapienza University) — Python CoMFA validation

Key innovations:
- Pure Python (RDKit + NumPy + scikit-learn) — no C compilation
- Multiple force fields (TRIPOS 5.2, MMFF94, Merck)
- Multiple field types (steric, electrostatic, hydrophobic)
- Full validation suite (LOO, L5O, Y-scrambling)
- 3D contour visualization data export
"""
from .mif import MIFCalculator
from .pls import PLSModel
from .validation import ModelValidator
from .alignment import MolecularAligner
from .builder import QSAR3DBuilder

__all__ = [
    "MIFCalculator",
    "PLSModel",
    "ModelValidator",
    "MolecularAligner",
    "QSAR3DBuilder",
]
