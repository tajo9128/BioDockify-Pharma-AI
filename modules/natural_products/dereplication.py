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


# ─── Formula analysis + reference matching (ported from biodockify-web) ─────

import math

# Monoisotopic masses of the most abundant isotope (Da) — IUPAC (Meija 2016)
_MONO_MASSES = {
    "C": 12.000000, "H": 1.0078250319, "N": 14.0030740052, "O": 15.9949146221,
    "S": 31.97207069, "P": 30.97376151, "F": 18.99840320, "Cl": 34.96885271,
    "Br": 78.9183376, "I": 126.904473, "Si": 27.9769265327, "B": 11.0093055,
    "Na": 22.98976967, "K": 38.9637069, "Se": 79.9165196,
}
_PROTON = 1.00727646688
_ELECTRON = 0.00054857990

ADDUCTS = {
    "[M+H]+": {"shift": _PROTON, "charge": 1},
    "[M+Na]+": {"shift": _MONO_MASSES["Na"] - _ELECTRON, "charge": 1},
    "[M+K]+": {"shift": _MONO_MASSES["K"] - _ELECTRON, "charge": 1},
    "[M+NH4]+": {"shift": 18.033823, "charge": 1},
    "[M-H]-": {"shift": -_PROTON, "charge": 1},
    "[M+Cl]-": {"shift": _MONO_MASSES["Cl"] + _ELECTRON, "charge": 1},
    "[M+2H]2+": {"shift": 2 * _PROTON, "charge": 2},
}


def _parse_strict(formula: str) -> dict:
    import re
    text = str(formula or "").strip().replace(" ", "")
    if not text or len(text) > 200:
        raise ValueError("Provide a molecular formula, e.g. C20H24O5N2")
    if not re.match(r"^(?:[A-Z][a-z]?\d*)+$", text):
        raise ValueError("Formula must be element symbols with optional counts, e.g. C21H30O2")
    elements = {}
    for symbol, count in re.findall(r"([A-Z][a-z]?)(\d*)", text):
        if symbol not in _MONO_MASSES:
            raise ValueError(f"Unsupported element: {symbol}")
        elements[symbol] = elements.get(symbol, 0) + (int(count) if count else 1)
    if sum(elements.values()) > 2000:
        raise ValueError("Formula exceeds the supported atom count")
    return elements


def _mono_mass(elements: dict) -> float:
    return sum(_MONO_MASSES[s] * n for s, n in elements.items())


def rdbe(elements: dict) -> float:
    """Ring plus double-bond equivalents: C - (H+X)/2 + N/2 + 1."""
    halogens = sum(elements.get(x, 0) for x in ("F", "Cl", "Br", "I"))
    return (elements.get("C", 0) - (elements.get("H", 0) + halogens) / 2.0
            + elements.get("N", 0) / 2.0 + 1.0)


def classify_natural_product(elements: dict) -> dict:
    """Heuristic NP class screen (overlapping rules, not diagnostic)."""
    c, h, o, n = (elements.get(x, 0) for x in "CHON")
    if c <= 0:
        return {"candidate_classes": [], "basis": "No carbon present"}
    h_to_c, o_to_c, unsat = h / c, o / c, rdbe(elements)
    candidates = []
    if n >= 1 and h_to_c >= 1.0:
        candidates.append("alkaloid")
    if c >= 15 and o >= 4 and unsat >= 7:
        candidates.append("flavonoid")
    if c % 5 == 0 and c >= 10 and h_to_c >= 1.4 and o <= 3:
        candidates.append("terpenoid")
    if c >= 17 and 1.2 <= h_to_c <= 1.9 and o <= 5 and unsat >= 4:
        candidates.append("steroid")
    if o >= 2 and n == 0 and unsat >= 4 and c <= 20:
        candidates.append("phenolic")
    if n >= 2 and o >= 3 and h_to_c >= 1.4:
        candidates.append("peptide")
    if o >= 6 and c >= 10 and o_to_c >= 0.4:
        candidates.append("glycoside")
    if c >= 12 and h_to_c >= 1.8 and o <= 2:
        candidates.append("fatty acid or lipid")
    return {
        "candidate_classes": candidates,
        "h_to_c_ratio": round(h_to_c, 3), "o_to_c_ratio": round(o_to_c, 3),
        "basis": "Compositional heuristics only — confirm with MS/MS, NMR, authentic standard.",
    }


def adduct_targets(neutral_mass: float, adducts=None) -> list:
    names = list(adducts) if adducts else list(ADDUCTS)
    out = []
    for name in names:
        spec = ADDUCTS.get(name)
        if not spec:
            raise ValueError(f"Unsupported adduct: {name}")
        out.append({"adduct": name, "charge": int(spec["charge"]),
                    "mz": round((neutral_mass + spec["shift"]) / spec["charge"], 5)})
    return out


def analyze_formula(formula: str) -> dict:
    """Full compositional profile: mass, RDBE, NP class hints, adduct m/z table."""
    elements = _parse_strict(formula)
    mass = _mono_mass(elements)
    unsat = rdbe(elements)
    warnings = []
    if unsat < 0:
        warnings.append("Negative RDBE — composition not valid as a neutral molecule.")
    if unsat % 1 != 0:
        warnings.append("Half-integer RDBE — odd-electron/radical/charged formula.")
    return {
        "formula": "".join(f"{s}{elements[s] if elements[s] > 1 else ''}"
                           for s in sorted(elements, key=lambda x: (x != "C", x != "H", x))),
        "elements": elements,
        "monoisotopic_mass": round(mass, 5),
        "rdbe": round(unsat, 1),
        "classification": classify_natural_product(elements),
        "adduct_targets": adduct_targets(mass),
        "warnings": warnings,
        "reference": "IUPAC atomic masses (Meija 2016); RDBE per Pellegrin 1983",
    }


def match_candidates(observed_mz: float, references: list, tolerance_ppm: float = 5.0,
                     adduct: str = "[M+H]+") -> dict:
    """Match observed m/z against user-supplied reference compounds (name + formula/mass)."""
    try:
        mz = float(observed_mz)
        ppm = float(tolerance_ppm)
    except (TypeError, ValueError):
        return {"error": "observed_mz and tolerance_ppm must be numbers"}
    if mz <= 0 or mz > 100000:
        return {"error": "observed_mz outside supported range"}
    if ppm <= 0 or ppm > 500:
        return {"error": "tolerance_ppm must be 0-500"}
    if not references:
        return {"error": "references required: [{name, formula | monoisotopic_mass}]"}
    spec = ADDUCTS.get(adduct)
    if not spec:
        return {"error": f"Unsupported adduct: {adduct}. Use: {', '.join(ADDUCTS)}"}

    matches, skipped = [], []
    for i, rec in enumerate(references[:2000]):
        if not isinstance(rec, dict):
            skipped.append({"index": i, "reason": "not an object"}); continue
        name = str(rec.get("name", "")).strip()
        if not name:
            skipped.append({"index": i, "reason": "missing name"}); continue
        neutral = None
        if rec.get("formula"):
            try:
                neutral = _mono_mass(_parse_strict(str(rec["formula"])))
            except ValueError as e:
                skipped.append({"index": i, "reason": f"{name}: {e}"}); continue
        elif rec.get("monoisotopic_mass") is not None:
            try:
                neutral = float(rec["monoisotopic_mass"])
            except (TypeError, ValueError):
                skipped.append({"index": i, "reason": f"{name}: invalid mass"}); continue
        if not neutral or neutral <= 0:
            skipped.append({"index": i, "reason": f"{name}: no usable mass"}); continue
        expected = (neutral + spec["shift"]) / spec["charge"]
        if expected <= 0:
            continue
        err = (mz - expected) / expected * 1e6
        if abs(err) <= ppm:
            matches.append({"name": name[:120],
                            "formula": rec.get("formula"),
                            "neutral_mass": round(neutral, 5),
                            "expected_mz": round(expected, 5),
                            "error_ppm": round(err, 2),
                            "absolute_error_ppm": round(abs(err), 2)})
    matches.sort(key=lambda m: m["absolute_error_ppm"])
    return {
        "observed_mz": round(mz, 5), "adduct": adduct, "tolerance_ppm": ppm,
        "references_supplied": len(references), "match_count": len(matches),
        "matches": matches[:50], "skipped": skipped[:50],
        "verdict": (f"{len(matches)} reference(s) match within {ppm:g} ppm - candidates "
                    "needing MS/MS confirmation." if matches else
                    f"No reference matched within {ppm:g} ppm - does NOT establish novelty; "
                    "coverage limited to supplied references."),
    }
