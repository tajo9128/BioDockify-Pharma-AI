"""Phytochemistry Deep-Dive — additive module (Pharmacognosy department).

  · Chromatographic fingerprint similarity (cosine / Pearson / range-normalized)
  · Marker-compound assay calculator (calibration regression + LOD/LOQ + assay %)
  · Limits checker (heavy metals & aflatoxins vs WHO / API / AYUSH limits)
  · Ethnobotany quick-reference database (seeded, offline)
"""
from __future__ import annotations

import math
from typing import Any, Dict, List

# ── Fingerprint similarity ─────────────────────────────────────────────────────

def fingerprint_similarity(profile_a: List[float], profile_b: List[float],
                           rts_a: List[float] = None, rts_b: List[float] = None) -> Dict[str, Any]:
    """Compare two chromatographic area profiles (aligned peak lists)."""
    a = [float(x) for x in (profile_a or [])]
    b = [float(x) for x in (profile_b or [])]
    if len(a) < 3 or len(b) < 3:
        return {"error": "need ≥3 peak areas per profile"}
    if len(a) != len(b):
        # pad shorter with zeros (missing peaks = absent)
        n = max(len(a), len(b))
        a += [0.0] * (n - len(a))
        b += [0.0] * (n - len(b))
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    cos = dot / (na * nb) if na and nb else 0.0
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    sa = math.sqrt(sum((x - ma) ** 2 for x in a))
    sb = math.sqrt(sum((y - mb) ** 2 for y in b))
    pearson = cov / (sa * sb) if sa and sb else 0.0
    total_a, total_b = sum(a), sum(b)
    rel_a = [x / total_a for x in a] if total_a else a
    rel_b = [y / total_b for y in b] if total_b else b
    # EU/Ph.Eur-style: number of matched peaks + their % of total area
    matched = sum(1 for x, y in zip(a, b) if x > 0 and y > 0)
    verdict = ("similar — cos ≥ 0.95, all key peaks present" if cos >= 0.95 and matched >= max(3, int(0.8 * len(a)))
               else "probably similar — review key-peak table" if cos >= 0.85
               else "different profile")
    return {"cosine_similarity": round(cos, 4),
            "pearson_r": round(pearson, 4),
            "matched_peaks": f"{matched}/{len(a)}",
            "relative_areas_A": [round(x, 4) for x in rel_a],
            "relative_areas_B": [round(y, 4) for y in rel_b],
            "verdict": verdict,
            "note": "Align peaks by Rt before comparison (common-marker windows). Regulators typically want ≥ 0.90–0.95 similarity."}


# ── Marker assay calculator ───────────────────────────────────────────────────

def marker_assay(calibration_conc: List[float], calibration_area: List[float],
                 sample_area: float, sample_weight_mg: float, dilution: float = 1.0,
                 volume_ml: float = 10.0) -> Dict[str, Any]:
    """Linear calibration → sample concentration, assay % w/w, LOD/LOQ (ICH)."""
    xs = [float(x) for x in (calibration_conc or [])]
    ys = [float(y) for y in (calibration_area or [])]
    if len(xs) < 4 or len(xs) != len(ys):
        return {"error": "need ≥4 calibration points (conc, area) — equal length"}
    if not sample_area or not sample_weight_mg:
        return {"error": "provide sample_area and sample_weight_mg"}
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    syy = sum((y - my) ** 2 for y in ys)
    slope = sxy / sxx if sxx else 0
    intercept = my - slope * mx
    r2 = (sxy * sxy) / (sxx * syy) if sxx and syy else 0
    if slope <= 0:
        return {"error": "calibration slope invalid"}
    conc = (float(sample_area) - intercept) / slope  # µg/mL (as given)
    total_in_vial = conc * float(volume_ml) * float(dilution)  # µg
    assay_pct = total_in_vial / 1000.0 / float(sample_weight_mg) * 100.0  # mg/mg %
    sy = math.sqrt(max(syy - slope * sxy, 0.0) / (n - 2)) if n > 2 else 0.0
    lod = 3.3 * sy / slope
    loq = 10 * sy / slope
    return {"regression": {"slope": round(slope, 4), "intercept": round(intercept, 2), "r2": round(r2, 5)},
            "sample_conc_ug_ml": round(conc, 3),
            "total_marker_ug": round(total_in_vial, 1),
            "assay_percent_w_w": round(assay_pct, 2),
            "lod_ug_ml": round(lod, 4), "loq_ug_ml": round(loq, 4),
            "validation_hint": ("r² ≥ 0.999 — excellent" if r2 >= 0.999 else
                                "r² ≥ 0.995 — acceptable (ICH Q2)" if r2 >= 0.995 else
                                "r² < 0.995 — recalibrate / check range"),
            "note": "Linearity per ICH Q2(R2). LOD/LOQ from σ/slope (3.3σ / 10σ)."}


# ── Limits checker — heavy metals & mycotoxins ─────────────────────────────────

LIMITS = [
    # (analyte, limits dict of standard→ppm or ppb, class)
    {"analyte": "Lead (Pb)", "unit": "ppm", "limits": {"WHO/API herbal": 10, "EU traditional herbal": 3.0, "AYUSH (India)": 10, "USP <232> oral": 5}},
    {"analyte": "Cadmium (Cd)", "unit": "ppm", "limits": {"WHO/API herbal": 0.3, "EU traditional herbal": 0.3, "AYUSH (India)": 0.3, "USP <232> oral": 0.5}},
    {"analyte": "Mercury (Hg)", "unit": "ppm", "limits": {"WHO/API herbal": 0.1, "EU traditional herbal": 0.1, "AYUSH (India)": 1.0, "USP <232> oral": 3}},
    {"analyte": "Arsenic (As, inorganic)", "unit": "ppm", "limits": {"WHO/API herbal": 0.1, "EU traditional herbal": 0.5, "AYUSH (India)": 3.0, "USP <232> oral": 3}},
    {"analyte": "Aflatoxin B1", "unit": "ppb", "limits": {"Ph.Eur/API": 2, "USP": 2, "FSSAI total": 30, "EU food": 2}},
    {"analyte": "Aflatoxins total (B1+B2+G1+G2)", "unit": "ppb", "limits": {"Ph.Eur/API": 4, "USP": 4, "EU food": 4, "FSSAI": 30}},
    {"analyte": "Ochratoxin A", "unit": "ppb", "limits": {"EU food (herbs)": 10, "Ph.Eur (some)": 10}},
]


def check_limits(analyte: str, value: float, standard: str = "WHO/API herbal") -> Dict[str, Any]:
    key = analyte.lower()
    row = next((r for r in LIMITS if r["analyte"].lower().startswith(key[:6])), None)
    if not row:
        return {"error": f"known analytes: {', '.join(r['analyte'] for r in LIMITS)}"}
    lim = row["limits"].get(standard)
    if lim is None:
        lim = list(row["limits"].values())[0]
        std_used = list(row["limits"].keys())[0]
    else:
        std_used = standard
    status = "PASS" if value <= lim else "FAIL"
    return {"analyte": row["analyte"], "value": value, "unit": row["unit"],
            "standard": std_used, "limit": lim,
            "status": status,
            "margin_pct": round((lim - value) / lim * 100, 1) if lim else None,
            "action": "release-compatible" if status == "PASS" else "reject lot / re-test confirmed method; investigate source (soil, drying, storage)"}


def limits_reference() -> Dict[str, Any]:
    return {"tables": LIMITS,
            "note": "Educational summary. Always work from the current official pharmacopoeial monograph."}


# ── Ethnobotany quick-reference (seeded, offline) ─────────────────────────────

PLANTS = [
    {"name": "Withania somnifera", "common": "Ashwagandha", "family": "Solanaceae",
     "part": "root", "markers": "withanolides (withaferin A)", "traditional_uses": "adaptogen, rasayana; stress, vitality",
     "class_of_compounds": "steroidal lactones"},
    {"name": "Bacopa monnieri", "common": "Brahmi", "family": "Plantaginaceae",
     "part": "whole plant/leaf", "markers": "bacosides A & B", "traditional_uses": "memory, cognition (medhya rasayana)",
     "class_of_compounds": "triterpenoid saponins"},
    {"name": "Curcuma longa", "common": "Turmeric", "family": "Zingiberaceae",
     "part": "rhizome", "markers": "curcuminoids (curcumin ≥ 3%)", "traditional_uses": "anti-inflammatory, wound healing",
     "class_of_compounds": "diarylheptanoids"},
    {"name": "Ocimum tenuiflorum", "common": "Tulsi / Holy basil", "family": "Lamiaceae",
     "part": "leaf", "markers": "eugenol, ursolic acid", "traditional_uses": "cough/cold, adaptogen, immune",
     "class_of_compounds": "phenylpropanoids, triterpenes"},
    {"name": "Gymnema sylvestre", "common": "Gurmar", "family": "Apocynaceae",
     "part": "leaf", "markers": "gymnemic acids", "traditional_uses": "diabetes (madhumeha), sugar-craving",
     "class_of_compounds": "triterpenoid saponins"},
    {"name": "Rauwolfia serpentina", "common": "Sarpagandha", "family": "Apocynaceae",
     "part": "root", "markers": "reserpine", "traditional_uses": "hypertension, insanity (historical); CITES/regulated",
     "class_of_compounds": "indole alkaloids"},
    {"name": "Phyllanthus emblica", "common": "Amla", "family": "Phyllanthaceae",
     "part": "fruit", "markers": "emblicanin, vitamin C, tannins", "traditional_uses": "rasayana, antioxidant, digestive",
     "class_of_compounds": "hydrolysable tannins"},
    {"name": "Commiphora mukul", "common": "Guggul", "family": "Burseraceae",
     "part": "oleo-gum resin", "markers": "guggulsterones E & Z", "traditional_uses": "hyperlipidemia, arthritis",
     "class_of_compounds": "steroidal ketones"},
    {"name": "Azadirachta indica", "common": "Neem", "family": "Meliaceae",
     "part": "leaf/bark", "markers": "azadirachtin, nimbin", "traditional_uses": "antimicrobial, skin, pesticide",
     "class_of_compounds": "limonoids"},
    {"name": "Picrorhiza kurroa", "common": "Kutki", "family": "Plantaginaceae",
     "part": "root/rhizome", "markers": "picroside I & kutkoside", "traditional_uses": "hepatoprotective (yakrit)",
     "class_of_compounds": "iridoid glycosides"},
    {"name": "Silybum marianum", "common": "Milk thistle", "family": "Asteraceae",
     "part": "seed", "markers": "silymarin (silybin A/B)", "traditional_uses": "liver protection (western herbal)",
     "class_of_compounds": "flavonolignans"},
    {"name": "Cinchona officinalis", "common": "Cinchona", "family": "Rubiaceae",
     "part": "bark", "markers": "quinine, quinidine", "traditional_uses": "malaria (historical), tonics",
     "class_of_compounds": "quinoline alkaloids"},
]


def search_plants(query: str) -> Dict[str, Any]:
    q = (query or "").lower().strip()
    rows = [p for p in PLANTS if not q or q in p["name"].lower() or q in p["common"].lower()
            or q in p["traditional_uses"].lower() or q in p["class_of_compounds"].lower()
            or q in p["markers"].lower()]
    return {"results": rows, "total_db": len(PLANTS),
            "note": "Seed reference for study — verify with API/AYUSH monographs and primary literature."}
