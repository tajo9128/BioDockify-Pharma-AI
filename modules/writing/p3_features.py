"""P3 features: pharmacophore export, fed-batch bioprocess, phytochem user DB,
literature RIS export, statistics Holm correction, pediatric dosing, BCPNN signals.

All additive — new file, no core changes.
"""
from __future__ import annotations

import json
import math
import os
from typing import Any, Dict, List

# ══ P3-1: Pharmacophore export formats ═══════════════════════════════════════


def export_pharmacophore(features: List[Dict], fmt: str = "json") -> Dict[str, Any]:
    """Export pharmacophore features to Pharmer .ph4, Mol2 query, or JSON."""
    if not features:
        return {"error": "no features to export"}
    pts = []
    for f in features:
        pts.append({
            "type": f.get("type", "HBA"),
            "x": f.get("x", 0), "y": f.get("y", 0), "z": f.get("z", 0),
            "radius": f.get("radius", 1.5),
        })
    if fmt == "ph4":
        lines = ["# Pharmacophore export (Pharmer format)"]
        for p in pts:
            lines.append(f"{p['type']}\t{p['x']:.3f}\t{p['y']:.3f}\t{p['z']:.3f}\t{p['radius']:.2f}")
        return {"format": "ph4", "content": "\n".join(lines), "download_name": "pharmacophore.ph4"}
    elif fmt == "mol2":
        lines = ["@<TRIPOS>MOLECULE", "pharmacophore", f"{len(pts)} 0 0 0 0", "QUERY", "", "@<TRIPOS>ATOM"]
        for i, p in enumerate(pts, 1):
            lines.append(f"{i}\t{p['type']}_P\t{p['x']:.4f}\t{p['y']:.4f}\t{p['z']:.4f}\t{p['type']}\t1\tUNL")
        lines.append("@<TRIPOS>BOND")
        return {"format": "mol2", "content": "\n".join(lines), "download_name": "pharmacophore.mol2"}
    else:
        return {"format": "json", "content": json.dumps({"features": pts}, indent=2),
                "download_name": "pharmacophore.json"}


# ══ P3-2: Fed-batch bioreactor simulation ════════════════════════════════════


def fedbatch_simulation(mu_max: float, ks: float, s0: float, yxs: float,
                         feed_rate: float = 0.5, feed_conc: float = 100.0,
                         hours: int = 30, x0: float = 0.5, v0: float = 1.0) -> Dict[str, Any]:
    """Fed-batch Monod simulation with exponential feed."""
    if min(mu_max, ks, s0, yxs, feed_rate) <= 0:
        return {"error": "all parameters must be > 0"}
    dt = hours / 200
    x, s, v = x0, s0, v0
    times, biomass, substrate, volume, product = [], [], [], [], []
    for i in range(201):
        t = i * dt
        mu = mu_max * s / (ks + s) if (ks + s) > 0 else 0
        # feed adds substrate at feed_rate * feed_conc
        ds_feed = feed_rate * feed_conc * dt / v
        dx = mu * x * dt
        ds = (-dx / yxs + ds_feed - s * feed_rate * dt / v)
        dv = feed_rate * dt
        x = max(0, x + dx - x * feed_rate * dt / v * 0.01)  # dilution loss small
        s = max(0, s + ds)
        v = v + dv
        times.append(round(t, 2))
        biomass.append(round(x, 4))
        substrate.append(round(s, 4))
        volume.append(round(v, 4))
        product.append(round(x * 0.1, 4))  # simplified product ∝ biomass
    return {"time_h": times, "biomass_g_L": biomass, "substrate_g_L": substrate,
            "volume_L": volume, "product_g_L": product,
            "final_biomass": round(x, 3), "final_volume": round(v, 3),
            "final_substrate": round(s, 3),
            "note": "Fed-batch Monod with constant feed. Product ∝ biomass (simplified)."}


# ══ P3-3: Phytochem user-extensible plant DB ═════════════════════════════════

_USER_DB = os.environ.get("PHYTO_DB", "/a0/tmp/phyto_plants.json" if os.name != "nt" else "tmp/phyto_plants.json")


def add_plant(plant: Dict[str, str]) -> Dict[str, Any]:
    """Add a user-defined plant to the persistent ethnobotany DB."""
    required = ("name", "common", "family", "part", "markers", "traditional_uses", "class_of_compounds")
    if not all(plant.get(k, "").strip() for k in required):
        return {"error": f"all fields required: {', '.join(required)}"}
    db = _load_user_plants()
    entry = {k: str(plant[k]).strip()[:200] for k in required}
    db.append(entry)
    os.makedirs(os.path.dirname(_USER_DB), exist_ok=True)
    with open(_USER_DB, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=1, ensure_ascii=False)
    return {"success": True, "added": entry["name"], "total_user_plants": len(db)}


def _load_user_plants() -> List[Dict]:
    if os.path.exists(_USER_DB):
        try:
            return json.loads(open(_USER_DB, encoding="utf-8").read())
        except Exception:
            pass
    return []


def list_user_plants() -> Dict[str, Any]:
    return {"plants": _load_user_plants(), "total": len(_load_user_plants()),
            "note": "User-added plants (persistent). Combine with the built-in 12-plant seed DB."}


# ══ P3-4: Literature RIS export ═════════════════════════════════════════════


def export_ris(papers: List[Dict]) -> Dict[str, Any]:
    """Export papers to RIS format (RefWorks/EndNote/Zotero compatible)."""
    if not papers:
        return {"error": "no papers to export"}
    lines = []
    for p in papers:
        lines.append("TY  - JOUR")
        if p.get("title"): lines.append(f"TI  - {p['title']}")
        if p.get("author"):
            authors = p["author"] if isinstance(p["author"], list) else [p["author"]]
            for a in authors:
                lines.append(f"AU  - {a}")
        if p.get("journal") or p.get("container_title"):
            lines.append(f"JO  - {p.get('journal') or p.get('container_title')}")
        if p.get("year"): lines.append(f"PY  - {p['year']}")
        if p.get("doi"): lines.append(f"DO  - {p['doi']}")
        if p.get("pmid"): lines.append(f"ID  - PMID:{p['pmid']}")
        if p.get("url"): lines.append(f"UR  - {p['url']}")
        if p.get("abstract"): lines.append(f"AB  - {str(p['abstract'])[:2000]}")
        lines.append("ER  - ")
        lines.append("")
    return {"format": "ris", "content": "\n".join(lines), "count": len(papers),
            "note": "Import into Zotero, EndNote, Mendeley, or RefWorks."}


def export_bibtex(papers: List[Dict]) -> Dict[str, Any]:
    """Export papers to BibTeX format."""
    if not papers:
        return {"error": "no papers"}
    lines = []
    for i, p in enumerate(papers):
        key = (p.get("author", "anon").split(",")[0].strip() or "anon") + str(p.get("year", "")) + str(i)
        key = "".join(c for c in key if c.isalnum())
        lines.append(f"@article{{{key},")
        if p.get("title"): lines.append(f"  title = {{{p['title']}}},")
        if p.get("author"):
            authors = p["author"] if isinstance(p["author"], list) else [p["author"]]
            lines.append(f"  author = {{{' and '.join(authors)}}},")
        if p.get("journal"): lines.append(f"  journal = {{{p['journal']}}},")
        if p.get("year"): lines.append(f"  year = {{{p['year']}}},")
        if p.get("volume"): lines.append(f"  volume = {{{p['volume']}}},")
        if p.get("pages"): lines.append(f"  pages = {{{p['pages']}}},")
        if p.get("doi"): lines.append(f"  doi = {{{p['doi']}}},")
        lines.append("}")
        lines.append("")
    return {"format": "bibtex", "content": "\n".join(lines), "count": len(papers)}


# ══ P3-5: Statistics multi-test Holm correction ═════════════════════════════


def holm_bonferroni(p_values: List[float], alpha: float = 0.05) -> Dict[str, Any]:
    """Holm-Bonferroni step-down correction for multiple comparisons."""
    if not p_values:
        return {"error": "no p-values provided"}
    n = len(p_values)
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    adjusted = [0.0] * n
    rejected = [False] * n
    for rank, (orig_idx, p) in enumerate(indexed):
        adj_p = min(1.0, p * (n - rank))
        adjusted[orig_idx] = round(adj_p, 6)
        rejected[orig_idx] = adj_p < alpha
    # enforce monotonicity (step-down)
    prev = 0
    for orig_idx, _ in indexed:
        adjusted[orig_idx] = max(adjusted[orig_idx], prev)
        prev = adjusted[orig_idx]
    sig_count = sum(rejected)
    return {"n_tests": n, "adjusted_p": adjusted, "rejected": rejected,
            "significant_count": sig_count,
            "alpha": alpha,
            "method": "Holm-Bonferroni (step-down)",
            "note": f"{sig_count}/{n} tests significant after correction."}


# ══ P3-6: Pediatric dosing calculator ═══════════════════════════════════════

_PEDIATRIC_DOSES = {
    # drug: {mg_per_kg_per_dose, max_single_mg, interval_h, notes}
    "paracetamol": {"mg_per_kg": 15, "max_single": 1000, "interval_h": 6, "max_daily": 75,
                    "note": "Max 4 doses/24h. Neonate: 10-15 mg/kg q8-12h."},
    "ibuprofen": {"mg_per_kg": 10, "max_single": 400, "interval_h": 8, "max_daily": 40,
                  "note": "≥6 months only. Avoid in dehydration/GI bleeding."},
    "amoxicillin": {"mg_per_kg": 15, "max_single": 500, "interval_h": 8, "max_daily": 90,
                    "note": "High-dose OTitis media: 80-90 mg/kg/day divided TID."},
    "azithromycin": {"mg_per_kg": 10, "max_single": 500, "interval_h": 24, "max_daily": 10,
                     "note": "Once daily × 3-5 days. 10 mg/kg day 1, then 5 mg/kg."},
    "ceftriaxone": {"mg_per_kg": 50, "max_single": 2000, "interval_h": 24, "max_daily": 100,
                    "note": "IV/IM. Meningitis: 100 mg/kg/day divided q12h."},
    "gentamicin": {"mg_per_kg": 2.5, "max_single": 120, "interval_h": 8, "max_daily": 7.5,
                   "note": "Monitor levels. Extended interval: 5-7 mg/kg q24h."},
    "morphine": {"mg_per_kg": 0.1, "max_single": 5, "interval_h": 4, "max_daily": 0.6,
                 "note": "IV. Neonate: 0.05 mg/kg. Monitor respiratory depression."},
    "salbutamol": {"mg_per_kg": 0.15, "max_single": 5, "interval_h": 6, "max_daily": 0.6,
                   "note": "Oral. Inhaled: 2-4 puffs (100mcg) PRN."},
}


def pediatric_dose(drug: str, weight_kg: float, age_months: int = None) -> Dict[str, Any]:
    """Calculate weight-based pediatric dose."""
    drug = drug.lower().strip()
    info = _PEDIATRIC_DOSES.get(drug)
    if not info:
        return {"error": f"drug not in pediatric list. Available: {', '.join(sorted(_PEDIATRIC_DOSES))}"}
    if weight_kg <= 0 or weight_kg > 100:
        return {"error": "weight_kg must be 0-100"}
    dose_mg = info["mg_per_kg"] * weight_kg
    capped = min(dose_mg, info["max_single"])
    daily_max = min(info["max_daily"] * weight_kg, info["max_single"] * (24 // info["interval_h"]))
    # BSA method (Mosteller) for chemotherapy-type dosing reference
    if weight_kg > 0:
        height_m = (weight_kg * 3.6 + 0.15) ** 0.5 if weight_kg < 30 else 1.5  # rough estimate
        bsa = math.sqrt(height_m * weight_kg / 3600)
    else:
        bsa = 0
    age_warn = ""
    if age_months is not None and age_months < 6 and drug == "ibuprofen":
        age_warn = "⚠ CONTRAINDICATED: ibuprofen < 6 months"
    return {"drug": drug.title(), "weight_kg": weight_kg,
            "dose_per_administration_mg": round(capped, 1),
            "interval_hours": info["interval_h"],
            "max_daily_mg": round(daily_max, 1),
            "estimated_bsa_m2": round(bsa, 2),
            "age_warning": age_warn,
            "clinical_note": info["note"],
            "formula": f"{info['mg_per_kg']} mg/kg × {weight_kg} kg = {round(dose_mg, 1)} mg"
                       + (f" (capped at {info['max_single']} mg)" if dose_mg > info["max_single"] else ""),
            "disclaimer": "Educational calculator — always verify against institutional guidelines and drug monographs."}


# ══ P3-7: BCPNN Bayesian signal detection ═══════════════════════════════════


def bcpnn_signal(a: int, b: int, c: int, d: int) -> Dict[str, Any]:
    """Bayesian Confidence Propagation Neural Network (BCPNN) signal detection.
    Returns IC (Information Component) with credibility interval.
    Reference: Bate A et al. Br J Clin Pharmacol. 1998;45:313-322.
    """
    if min(a, b, c, d) < 0:
        return {"error": "contingency cells must be ≥ 0"}
    n = a + b + c + d
    if n == 0 or (a + c) == 0 or (a + b) == 0:
        return {"error": "marginal totals must be > 0"}

    # Beta prior parameters
    alpha1, beta1 = 0.5, 0.5
    # Expected probability under independence
    p11_exp = (a + b) / n * (a + c) / n
    # Observed with Bayesian smoothing
    p11_obs = (a + alpha1) / (a + b + alpha1 + beta1)
    p1_exp = (a + c) / n

    # Information Component: log2(P(drug,event) / (P(drug) × P(event)))
    try:
        ic = math.log2(p11_obs / p11_exp) if p11_exp > 0 and p11_obs > 0 else 0.0
    except (ValueError, ZeroDivisionError):
        ic = 0.0

    # Variance approximation
    var_ic = (1.0 / max(a, 1)) + (1.0 / max(a + c, 1)) + (1.0 / max(a + b, 1)) - (1.0 / max(n, 1))
    se = math.sqrt(max(var_ic, 1e-10))
    ic_lower = ic - 1.96 * se
    ic_upper = ic + 1.96 * se

    # Signal criteria: IC025 (lower 95% CI) > 0
    signal = ic_lower > 0
    return {
        "IC": round(ic, 3),
        "IC_95_ci": [round(ic_lower, 3), round(ic_upper, 3)],
        "IC025": round(ic_lower, 3),
        "signal": "signal_detected" if signal else "no_signal",
        "criteria": "IC025 > 0 (lower 95% credibility bound of Information Component)",
        "cells": {"a": a, "b": b, "c": c, "d": d},
        "note": "BCPNN/IC method used by WHO-UMC (VigiBase). IC > 0 suggests disproportionate reporting.",
        "reference": "Bate 1998; Noren 2008 (scaled IC)",
    }


# ══ P3-8: FAERS data format parser ══════════════════════════════════════════


def parse_faers_csv(text: str) -> Dict[str, Any]:
    """Parse FAERS quarterly CSV data (demo+drug+reaction joined) into contingency tables.

    Input: CSV with columns [case_id, drug_name, reaction_medDRA_pt] (one row per case-drug-reaction).
    Output: drug-event contingency table cells ready for PRR/ROR/BCPNN analysis.
    """
    import csv
    import io
    from collections import defaultdict

    if not text.strip():
        return {"error": "no data provided"}
    reader = csv.DictReader(io.StringIO(text))
    # Detect column names (FAERS uses various formats)
    rows = list(reader)
    if not rows:
        return {"error": "no rows parsed"}
    cols = list(rows[0].keys())
    # Map to canonical names
    col_map = {}
    for c in cols:
        cl = c.lower().strip()
        if "case" in cl and "id" in cl: col_map[c] = "case_id"
        elif "drug" in cl and ("name" in cl or "ingred" in cl): col_map[c] = "drug"
        elif "reaction" in cl or "pt" in cl or "meddra" in cl: col_map[c] = "reaction"

    if "case_id" not in col_map.values() or "drug" not in col_map.values() or "reaction" not in col_map.values():
        return {"error": f"need columns with case_id, drug_name, reaction — found: {cols}"}

    # Build case → drugs set, case → reactions set
    case_drugs = defaultdict(set)
    case_reactions = defaultdict(set)
    for row in rows:
        cid = row[[k for k, v in col_map.items() if v == "case_id"][0]]
        drug = row[[k for k, v in col_map.items() if v == "drug"][0]].lower().strip()
        rxn = row[[k for k, v in col_map.items() if v == "reaction"][0]].upper().strip()
        if cid and drug:
            case_drugs[cid].add(drug)
        if cid and rxn:
            case_reactions[cid].add(rxn)

    all_cases = set(case_drugs.keys()) | set(case_reactions.keys())
    # Get most common drugs and reactions
    drug_counts = defaultdict(int)
    rxn_counts = defaultdict(int)
    for cid, drugs in case_drugs.items():
        for d in drugs:
            drug_counts[d] += 1
    for cid, rxns in case_reactions.items():
        for r in rxns:
            rxn_counts[r] += 1

    top_drugs = sorted(drug_counts.items(), key=lambda x: -x[1])[:10]
    top_rxns = sorted(rxn_counts.items(), key=lambda x: -x[1])[:10]

    # Build contingencies for top drug-reaction pairs
    contingencies = []
    for drug, d_count in top_drugs[:5]:
        for rxn, r_count in top_rxns[:5]:
            a = sum(1 for cid in all_cases if drug in case_drugs.get(cid, set()) and rxn in case_reactions.get(cid, set()))
            b = d_count - a
            c = r_count - a
            d = len(all_cases) - a - b - c
            if a >= 3:  # minimum cases
                contingencies.append({"label": f"{drug} → {rxn}", "a": a, "b": b, "c": c, "d": d})

    return {"total_cases": len(all_cases), "total_drugs": len(drug_counts),
            "total_reactions": len(rxn_counts),
            "top_drugs": [{"name": d, "cases": c} for d, c in top_drugs],
            "top_reactions": [{"name": r, "cases": c} for r, c in top_rxns],
            "contingencies": contingencies,
            "note": "Ready for PRR/ROR/BCPNN analysis via pharmacovigilance API."}
