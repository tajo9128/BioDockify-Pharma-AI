"""
Dereplication — molecular formula parsing and exact mass estimation.

Molecular formula → exact mass, DBE (degree of unsaturation), compound class.
"""

import re
from typing import Dict, Any


# Standard atomic masses (Da)
ATOMIC_MASSES = {
    'C': 12.0000, 'H': 1.00783, 'O': 15.9949, 'N': 14.0031,
    'S': 31.9721, 'P': 30.9738, 'F': 18.9984, 'Cl': 34.9689,
    'Br': 78.9183, 'I': 126.9045, 'Si': 27.9769, 'B': 10.0129,
}

# Natural product classes by C:H:O ratio (simplified)
NP_CLASSES = {
    "Alkaloid": lambda c, h, o, n: n >= 1 and h/c > 1,
    "Flavonoid": lambda c, h, o, n: c >= 15 and o >= 4 and c/h < 0.8,
    "Terpenoid": lambda c, h, o, n: c >= 10 and o <= 3 and h/c > 1.5,
    "Phenolic": lambda c, h, o, n: o >= 2 and c/h < 1 and n == 0,
    "Peptide": lambda c, h, o, n: n >= 2 and o >= 2,
    "Steroid": lambda c, h, o, n: c >= 17 and h/c > 1.5 and o <= 4,
    "Lipid": lambda c, h, o, n: c >= 12 and h/c > 1.8 and o <= 2,
    "Glycoside": lambda c, h, o, n: o >= 6 and c >= 10,
}


def parse_molecular_formula(formula: str) -> Dict[str, Any]:
    """Parse a molecular formula string into element counts and computed properties.

    Args:
        formula: Molecular formula (e.g., "C20H24O5N2")

    Returns:
        Dict with element counts, exact mass, DBE, compound class
    """
    if not formula or not formula.strip():
        return {"status": "error", "error": "Provide molecular formula (e.g., C20H24O5N2)"}

    elements = {}
    for match in re.finditer(r'([A-Z][a-z]?)(\d*)', formula):
        elem = match.group(1)
        count = int(match.group(2)) if match.group(2) else 1
        elements[elem] = elements.get(elem, 0) + count

    if not elements:
        return {"status": "error", "error": f"Could not parse formula: {formula}"}

    # Exact mass
    total_mass = 0
    for elem, count in elements.items():
        mass = ATOMIC_MASSES.get(elem)
        if mass is None:
            return {"status": "error", "error": f"Unknown element: {elem}"}
        total_mass += mass * count

    # Degree of unsaturation (DBE) = (2C + 2 + N - H) / 2
    c = elements.get('C', 0)
    h = elements.get('H', 0)
    n = elements.get('N', 0)
    o = elements.get('O', 0)
    halogens = elements.get('F', 0) + elements.get('Cl', 0) + elements.get('Br', 0) + elements.get('I', 0)

    dbe = (2 * c + 2 + n - h - halogens) / 2.0

    # Compound class guess
    compound_class = "Unknown"
    for class_name, check_fn in NP_CLASSES.items():
        try:
            if check_fn(c, h, o, n):
                compound_class = class_name
                break
        except Exception:
            pass

    return {
        "status": "ok",
        "formula": formula,
        "elements": elements,
        "exact_mass": round(total_mass, 4),
        "dbe": round(dbe, 1),
        "compound_class": compound_class,
        "interpretation": f"Formula: {formula}, Exact mass: {total_mass:.4f} Da, DBE: {dbe:.1f}, Class: {compound_class}",
    }


def estimate_exact_mass(formula: str) -> Dict[str, Any]:
    """Estimate exact mass from molecular formula."""
    result = parse_molecular_formula(formula)
    if "error" in result:
        return result
    return {
        "status": "ok",
        "exact_mass": result["exact_mass"],
        "formula": result["formula"],
    }
