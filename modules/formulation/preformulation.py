"""Preformulation & drug-delivery calculators (additive — formulation package).

Pure-computation helpers for the Preformulation & Drug Delivery Designer:
  · preformulation profile from SMILES (RDKit descriptors + rule-based flags)
  · drug–excipient compatibility matrix (incompatibility chemistry rules)
  · delivery-system calculators: liposome loading, nanoparticle dose/PDI,
    mucoadhesion factors, transdermal Fick's-law flux, first-order release t
"""
from __future__ import annotations

from typing import Any, Dict, List

# ── Preformulation profile ────────────────────────────────────────────────────

_LIPINSKI_NOTE = "Lipinski Ro5: MW ≤ 500, logP ≤ 5, HBD ≤ 5, HBA ≤ 10"


def preformulation_profile(smiles: str, drug_name: str = "") -> Dict[str, Any]:
    """Descriptor panel + rule-based preformulation flags from a SMILES."""
    from rdkit import Chem
    from rdkit.Chem import Crippen, Descriptors, rdMolDescriptors

    mol = Chem.MolFromSmiles(smiles or "")
    if mol is None:
        return {"error": "invalid SMILES"}

    mw = Descriptors.MolWt(mol)
    logp = Crippen.MolLogP(mol)
    hbd = rdMolDescriptors.CalcNumHBD(mol)
    hba = rdMolDescriptors.CalcNumHBA(mol)
    tpsa = rdMolDescriptors.CalcTPSA(mol)
    rotb = rdMolDescriptors.CalcNumRotatableBonds(mol)
    aromatics = rdMolDescriptors.CalcNumAromaticRings(mol)
    pka_basic = max((Crippen._GetAtomContribs and 0) or 0, 0)  # placeholder, rule-based below

    # rule-of-thumb ionization class (pharma heuristic, not a pKa predictor)
    from rdkit.Chem import rdMolDescriptors as rdmd
    has_amide = mol.HasSubstructMatch(Chem.MolFromSmarts("C(=O)N"))
    has_amine = mol.HasSubstructMatch(Chem.MolFromSmarts("[NX3;H2,H1,H0;!$(NC=O)]"))
    has_acid = mol.HasSubstructMatch(Chem.MolFromSmarts("C(=O)[OX2H1]"))
    has_tertamine = mol.HasSubstructMatch(Chem.MolFromSmarts("[NX3;H0](C)(C)C"))
    if has_acid and has_amine:
        ion_class = "ampholyt (zwitterionic near pI)"
    elif has_acid:
        ion_class = "weak acid (pKa ~ 3–5 typical)"
    elif has_tertamine:
        ion_class = "basic — salts likely (pKa ~ 8–10 typical)"
    elif has_amine:
        ion_class = "weak base (pKa ~ 7–9 typical)"
    else:
        ion_class = "essentially neutral"

    # solubility heuristic: ESOL-style (Delaney) without needing the full model
    esol_logs = 0.16 - 0.63 * logp - 0.0062 * mw + 0.066 * has_acid - 0.74 * (rotb > 6)
    logs_class = ("high" if esol_logs > -1 else "moderate" if esol_logs > -3 else "low" if esol_logs > -5 else "very low")

    bdd_flag = "likely BBB-permeable" if tpsa < 90 and logp < 3.5 else "BBD restricted (TPSA ≥ 90 or logP ≥ 3.5)"
    gi_flag = "good passive-absorption outlook" if mw <= 500 and logp <= 5 and hbd <= 5 else "Ro5 violation — poor passive absorption risk"
    hygro_note = "hygroscopicity risk if HBD+HBA ≥ 8" if (hbd + hba) >= 8 else "hygroscopicity risk low"
    polymorph_note = ("high polymorph risk (rigid, aromatic, H-bonding)" if aromatics >= 1 and (hbd + hba) >= 3
                      else "moderate polymorph risk — screen anyway (XRPD/DSC)")

    excipient_risk = []
    if has_acid:
        excipient_risk.append("acidic API: avoid alkaline excipients (Na-CMC, Mg-stearate at scale)")
    if has_amine:
        excipient_risk.append("amine API: avoid lactose (Maillard) with primary amines; avoid anhydrous citric acid blends")
    if logp > 4:
        excipient_risk.append("high logP: watch adsorption onto crospovidone/silica; solubilizers (Surfactants/ cyclodextrin) likely needed")

    return {
        "drug": drug_name or smiles[:40],
        "descriptors": {"MW": round(mw, 1), "logP": round(logp, 2), "HBD": hbd, "HBA": hba,
                        "TPSA": round(tpsa, 1), "rotatable_bonds": rotb, "aromatic_rings": aromatics,
                        "formula": rdmd.CalcMolFormula(mol)},
        "estimated_solubility": {"class": logs_class, "logS_est": round(float(esol_logs), 2),
                                 "basis": "Delaney-style heuristic (not a measured value)"},
        "ionization": ion_class,
        "flags": {"absorption": gi_flag, "bddd": bdd_flag, "hygroscopicity": hygro_note, "polymorph": polymorph_note},
        "excipient_alerts": excipient_risk or ["no specific incompatibility rule triggered — run compatibility studies"],
        "note": _LIPINSKI_NOTE,
    }


# ── Excipient compatibility matrix (rule-based chemistry) ─────────────────────

_RULES: List[Dict[str, Any]] = [
    {"excipient": "lactose", "risk": ["primary amine (Maillard browning)", "acidic pH"], "manage": "control moisture, low temp; consider mannitol/starch"},
    {"excipient": "magnesium stearate", "risk": ["weak acid APIs (ion-pair, dissolution slowdown)", "strong bases"], "manage": "limit 0.5–1%, lub-time short; use stearic acid"},
    {"excipient": "starch", "risk": ["hygroscopic APIs", "enzymatic degradation of esters"], "manage": "dried starch, low moisture products"},
    {"excipient": "povidone (PVP)", "risk": ["oxidizable APIs (peroxide residues)"], "manage": "low-peroxide grade PVP; add antioxidant"},
    {"excipient": "crospovidone", "risk": ["adsorption of lipophilic APIs"], "manage": "check dissolution; alternative: sodium starch glycolate"},
    {"excipient": "sodium CMC", "risk": ["acidic API (precipitation of free acid)", "Al3+/Ca2+ salts"], "manage": "pH microenvironment control"},
    {"excipient": "citric acid / tartaric acid", "risk": ["base/amine APIs (salt formation, instability)", "saccharose inversion"], "manage": "microenvironment pH study; keep RH low"},
    {"excipient": "talc", "risk": [], "manage": "generally inert — good default glidant"},
    {"excipient": "MCC (avicel)", "risk": ["hygroscopic moisture-sensitive APIs (water sorption)"], "manage": "silicified MCC or anhydrous lactose alternative"},
    {"excipient": "gelatin capsule shells", "risk": ["hygroscopic/lipophilic liquids (brittleness/softening)", "aldehyde crosslinking"], "manage": "HPMC capsules; low RH packaging"},
    {"excipient": "propylene glycol / glycerin", "risk": ["hydrolysis-prone esters"], "manage": "anhydrous systems, antioxidants"},
    {"excipient": "sodium lauryl sulfate", "risk": ["strongly pH-dependent solubility of weak acids"], "manage": "wetting-study; binary blend screen"},
]


def compatibility_screen(flags: List[str]) -> Dict[str, Any]:
    """Rank excipient incompatibility risks for a list of API feature flags
    (as produced by preformulation_profile / analyst input)."""
    text = " ".join(str(f).lower() for f in flags)
    rows = []
    for rule in _RULES:
        triggered = [r for r in rule["risk"] if any(k in text for k in _keywords(r))]
        if triggered:
            rows.append({"excipient": rule["excipient"], "triggered": triggered, "management": rule["manage"], "risk": "high"})
        elif rule["risk"]:
            rows.append({"excipient": rule["excipient"], "triggered": [], "management": rule["manage"], "risk": "check"})
        else:
            rows.append({"excipient": rule["excipient"], "triggered": [], "management": rule["manage"], "risk": "low"})
    rows.sort(key=lambda r: {"high": 0, "check": 1, "low": 2}[r["risk"]])
    return {"rows": rows,
            "note": "Rule-based screen — always confirm with binary blends (DSC/TGA/iso thermal stress, 40°C/75% RH 4 weeks)."}


def _keywords(risk: str) -> List[str]:
    kmap = {
        "primary amine (maillard browning)": ["amine", "basic", "salt"],
        "acidic ph": ["acid"],
        "weak acid": ["acid"],
        "strong bases": ["basic", "amine", "salt"],
        "hygroscopic": ["hygroscopicity risk", "hbd", "hba"],
        "adsorption": ["high logp", "lipophilic"],
        "oxidizable": ["oxid"],
    }
    for k, v in kmap.items():
        if k in risk.lower():
            return v
    return [risk.lower().split("(")[0].strip()]


# ── Delivery-system calculators ───────────────────────────────────────────────

def liposome_calculator(drug_mg: float, lipid_conc_mmol: float, volume_ml: float,
                        entrapment_pct: float = 80.0, lipid_mw: float = 750.0) -> Dict[str, Any]:
    """Loading, capacity and concentration summary for a liposomal batch."""
    if min(drug_mg, lipid_conc_mmol, volume_ml) <= 0:
        return {"error": "all inputs must be > 0"}
    total_lipid_mmol = lipid_conc_mmol * volume_ml / 1000.0
    total_lipid_mg = total_lipid_mmol * lipid_mw
    entrapped = drug_mg * entrapment_pct / 100.0
    drug_lipid_ratio = drug_mg / total_lipid_mg if total_lipid_mg else 0
    capacity_flag = "within typical capacity (< 0.3 w/w)" if drug_lipid_ratio <= 0.3 else "high loading — check stability/leakage"
    return {"total_lipid_mg": round(total_lipid_mg, 1), "entrapped_drug_mg": round(entrapped, 2),
            "free_drug_mg": round(drug_mg - entrapped, 2),
            "drug_lipid_w_w": round(drug_lipid_ratio, 3),
            "entrapped_conc_mg_ml": round(entrapped / volume_ml, 2),
            "flag": capacity_flag,
            "note": "post-sizing (extrusion/sonication) typically reduces entrapment 10–25% — measure by SEC/ultrafiltration."}


def nanoparticle_dose(mg_kg: float, bodyweight_kg: float, conc_mg_ml: float,
                      pdi: float = 0.2) -> Dict[str, Any]:
    """Volume to administer + quality read on PDI."""
    if min(mg_kg, bodyweight_kg, conc_mg_ml) <= 0:
        return {"error": "all inputs must be > 0"}
    total_mg = mg_kg * bodyweight_kg
    vol_ml = total_mg / conc_mg_ml
    pdi_read = ("monodisperse (PDI ≤ 0.2)" if pdi <= 0.2 else "acceptable (PDI ≤ 0.3)" if pdi <= 0.3 else "heterogeneous — re-optimize")
    return {"total_dose_mg": round(total_mg, 1), "volume_ml": round(vol_ml, 2),
            "pdi_assessment": pdi_read,
            "note": "IV-distribution scales with size 80–200 nm (protein corona, RES uptake)."}


def mucoadhesion_score(polymer: str, conc_pct: float, mw_band: str = "high") -> Dict[str, Any]:
    """Semi-quantitative mucoadhesion potential (literature factors)."""
    p = polymer.lower()
    base, factors, notes = 1.0, [], []
    table = {
        "chitosan": (8, "cationic — electrostatic mucus binding; pH < 6.5 protonated"),
        "carbopol": (9, "strong H-bonding + swelling; neutralize partially to cut irritation"),
        "hpmc": (5, "moderate H-bonding, gentle"),
        "sodium cmc": (6, "anionic H-bonding; Ca2+ crosslinks boost"),
        "alginate": (6, "gel-forming, Ca2+ beads"),
        "pectin": (5, "mucus-mimic; Ca2+ network"),
        "gelatin": (4, "weak; often blended"),
        "hyaluronic acid": (7, "CD44 targeting + mucoadhesion"),
    }
    for key, (score, note) in table.items():
        if key in p:
            base = score
            notes.append(note)
            break
    else:
        notes.append("polymer not in table — generic H-bonding assumed")
        base = 5
    if conc_pct >= 1:
        factors.append(f"concentration {conc_pct}% (↑ viscosity ↑ adhesion)")
    if mw_band.lower().startswith("high"):
        factors.append("high-MW chain interpenetration (+)")
    score = min(10, base + (1 if conc_pct >= 2 else 0) + (1 if mw_band.lower().startswith("high") else 0))
    return {"polymer": polymer, "score_10": score,
            "verdict": "strong" if score >= 8 else "moderate" if score >= 6 else "weak",
            "factors": factors, "notes": notes}


def transdermal_flux(area_cm2: float, concentration_mg_ml: float, thickness_cm: float,
                     partition_k: float = 1.0, diffusion_cm2_s: float = 1e-9) -> Dict[str, Any]:
    """Steady-state Fick's first law across a membrane/skin model."""
    if min(area_cm2, thickness_cm) <= 0 or concentration_mg_ml <= 0:
        return {"error": "inputs must be > 0"}
    j_per_area = diffusion_cm2_s * partition_k * concentration_mg_ml / thickness_cm  # mg/(cm2·s)
    j_per_area_day = j_per_area * 86400
    total_day = j_per_area_day * area_cm2
    lag_time_h = thickness_cm ** 2 / (6 * diffusion_cm2_s) / 3600 if diffusion_cm2_s else None
    return {"flux_mg_cm2_day": round(j_per_area_day, 4),
            "total_daily_mg": round(total_day, 3),
            "lag_time_hours": round(lag_time_h, 1) if lag_time_h else None,
            "assumption": f"D={diffusion_cm2_s:g} cm²/s, K={partition_k}, h={thickness_cm} cm",
            "note": "SC D ~ 1e-9–1e-11; enhancers raise D; always confirm in Franz cells."}


def release_half_life(rate_constant: float, order: str = "first") -> Dict[str, Any]:
    """t½ / t90 for zero- or first-order release/degradation."""
    if rate_constant <= 0:
        return {"error": "k must be > 0"}
    if order == "zero":
        return {"order": "zero", "t50_factor": "0.5/k (with C0=1)", "formula": "t = fraction/k",
                "note": "needs C0 — use release_kinetics module for real fits"}
    t_half = 0.693 / rate_constant
    t90 = -0.105 / rate_constant if rate_constant > 0 else None
    return {"order": "first", "t_half": round(t_half, 3), "t90": round(abs(t90), 3) if t90 else None}
