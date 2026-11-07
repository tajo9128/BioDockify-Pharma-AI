"""Bioprocess & Protein Studio — additive module (Biotechnology department).

Pure-python/biopython helpers:
  · protein properties (MW, pI, extinction coefficient, GRAVY, instability)
  · peptide antigenicity scoring (hydrophilicity/flexibility/surface rules)
  · bioreactor growth kinetics (Monod, yield, dilution/cell-washout)
  · fermentation media C:N calculator
  · plasmid helper (copy/mass conversions, insert:vector molar ratio)
"""
from __future__ import annotations

from typing import Any, Dict

AA = "ACDEFGHIKLMNPQRSTVWY"
MW = {"A": 89.09, "C": 121.16, "D": 133.10, "E": 147.13, "F": 165.19, "G": 75.07,
      "H": 155.16, "I": 131.17, "K": 146.19, "L": 131.17, "M": 149.21, "N": 132.12,
      "P": 115.13, "Q": 146.15, "R": 174.20, "S": 105.09, "T": 119.12, "V": 117.15,
      "W": 204.23, "Y": 181.19}
PKA = {"Cterm": 3.55, "Nterm": 7.50, "C": 9.0, "D": 4.05, "E": 4.45, "H": 5.98,
       "K": 10.0, "R": 12.0, "Y": 10.0}
HYDRO = {"I": 4.5, "V": 4.2, "L": 3.8, "F": 2.8, "C": 2.5, "M": 1.9, "A": 1.8,
         "G": -0.4, "T": -0.7, "S": -0.8, "W": -0.9, "Y": -1.3, "P": -1.6,
         "H": -3.2, "E": -3.5, "Q": -3.5, "D": -3.5, "N": -3.5, "K": -3.9, "R": -4.5}
# Trp/Tyr extinction at 280 nm (M-1 cm-1)
EPS = {"W": 5500, "Y": 1490, "C": 125}  # C = cystine only (approximate)


def protein_properties(sequence: str, name: str = "") -> Dict[str, Any]:
    seq = "".join(c for c in str(sequence or "").upper() if c in AA)
    if len(seq) < 2:
        return {"error": "provide a protein sequence (single-letter codes, ≥2 residues)"}
    n = len(seq)
    mw_total = sum(MW[c] for c in seq) - 18.02 * (n - 1)

    # pI by bisection on net charge
    def net_charge(pH: float) -> float:
        import math
        pos = 1.0 / (1 + 10 ** (pH - PKA["Nterm"]))
        pos += sum(1 / (1 + 10 ** (pH - PKA[c])) for c in seq if c in ("K", "R", "H"))
        neg = 1.0 / (1 + 10 ** (PKA["Cterm"] - pH))
        neg += sum(1 / (1 + 10 ** (PKA[c] - pH)) for c in seq if c in ("D", "E", "C", "Y"))
        return pos - neg

    lo, hi = 0.0, 14.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if net_charge(mid) > 0:
            lo = mid
        else:
            hi = mid
    pi = round((lo + hi) / 2, 2)

    gravy = round(sum(HYDRO[c] for c in seq) / n, 3)
    eps280 = sum(EPS.get(c, 0) for c in seq)
    aromatic = {"W": seq.count("W"), "Y": seq.count("Y"), "F": seq.count("F")}
    charged = {"D+E": seq.count("D") + seq.count("E"), "K+R+H": seq.count("K") + seq.count("R") + seq.count("H")}
    extinction_note = "A280 valid (has Trp/Tyr)" if eps280 > 0 else "A280 weak — use Bradford/BCA"

    return {
        "name": name or f"{n}-residue protein",
        "length": n,
        "molecular_weight_kDa": round(mw_total / 1000, 2),
        "isoelectric_point_pI": pi,
        "extinction_coeff_280": eps280,
        "extinction_note": extinction_note,
        "gravy_hydropathy": gravy,
        "hydropathy_verdict": "hydrophobic/membrane倾向" if gravy > 0.4 else "amphipathic" if gravy > -0.4 else "hydrophilic/soluble",
        "aromatics": aromatic, "charged_groups": charged,
        "stability_hint": "Cys pairs: check for disulfides" if seq.count("C") >= 2 else "no disulfide likely",
        "formula_hint": f"A280=1 → {round(mw_total/eps280, 2) if eps280 else '?'} mg/mL" if eps280 else "",
    }


def antigenicity_score(sequence: str) -> Dict[str, Any]:
    """Semi-quantitative B-cell epitope potential over windows."""
    seq = "".join(c for c in str(sequence or "").upper() if c in AA)
    if len(seq) < 8:
        return {"error": "need ≥8 residues"}
    flexible = {"G": 1, "S": 0.9, "P": 0.85, "N": 0.8, "D": 0.8, "T": 0.7, "E": 0.6, "K": 0.6, "A": 0.6}
    best_windows = []
    for i in range(len(seq) - 7):
        w = seq[i:i + 8]
        hydro = sum(HYDRO[c] for c in w) / 8
        flex = sum(flexible.get(c, 0.5) for c in w) / 8
        score = flex * 10 - hydro * 2  # higher flex + lower hydro = better epitope
        best_windows.append((round(score, 2), i + 1, w, round(hydro, 2)))
    best_windows.sort(reverse=True)
    top = [{"start": s, "window": w, "score": sc, "hydropathy": h}
           for sc, s, w, h in best_windows[:5]]
    return {"top_epitope_candidates": top,
            "advice": "Best 8-mers: flexible + hydrophilic. Verify with in-silico servers (BepiPred/IEDB) and peptide synthesis.",
            "note": "Rule-based screen for B-cell linear epitope potential."}


def bioreactor_kinetics(mu_max: float, ks: float, s0: float, yxs: float,
                        f_rate: float = 0.0, volume: float = 1.0) -> Dict[str, Any]:
    """Monod growth, chemostat critical dilution, biomass & product outlook."""
    if min(mu_max, ks, s0, yxs) <= 0:
        return {"error": "mu_max, ks, s0, yxs must be > 0"}
    d = f_rate / volume if volume > 0 and f_rate >= 0 else 0.0
    d_crit = mu_max * s0 / (ks + s0)
    washout = d >= d_crit
    # chemostat steady state (if not washed out)
    if not washout and d > 0:
        s_ss = d * ks / (mu_max - d) if mu_max > d else None
        x_ss = yxs * (s0 - s_ss) if s_ss is not None and s_ss < s0 else None
    else:
        s_ss = x_ss = None
    doubling_min = 0.693 / mu_max * 60
    return {
        "max_specific_growth_rate_h": mu_max,
        "doubling_time_min": round(doubling_min, 1),
        "critical_dilution_rate_per_h": round(d_crit, 3),
        "operating_dilution_rate_per_h": round(d, 3),
        "washout_risk": "WASHOUT — D ≥ Dcrit" if washout else ("marginal — D within 10% of Dcrit" if d > 0.9 * d_crit else "safe"),
        "steady_state": {"substrate_g_L": round(s_ss, 3) if s_ss is not None else None,
                         "biomass_g_L": round(x_ss, 3) if x_ss is not None else None},
        "batch_biomass_potential_g_L": round(yxs * s0, 2),
        "note": "Monod chemostat model (no maintenance/death). Validate with batch/respirometry.",
    }


def media_cn(carbon_source: str, carbon_g_l: float, nitrogen_source: str, nitrogen_g_l: float) -> Dict[str, Any]:
    """C:N molar ratio helper for fermentation media design."""
    comp = {
        "glucose": {"c_frac": 0.40, "n_frac": 0.0},
        "glycerol": {"c_frac": 0.39, "n_frac": 0.0},
        "methanol": {"c_frac": 0.375, "n_frac": 0.0},
        "yeast extract": {"c_frac": 0.43, "n_frac": 0.085},
        "peptone": {"c_frac": 0.45, "n_frac": 0.13},
        "ammonium sulfate": {"c_frac": 0.0, "n_frac": 0.212},
        "ammonium chloride": {"c_frac": 0.0, "n_frac": 0.262},
        "urea": {"c_frac": 0.20, "n_frac": 0.467},
        "corn steep liquor": {"c_frac": 0.40, "n_frac": 0.045},
    }
    c = comp.get(carbon_source.lower())
    n = comp.get(nitrogen_source.lower())
    if not c or not n:
        return {"error": f"known sources: {', '.join(comp)}"}
    c_mol = carbon_g_l * c["c_frac"] / 12.011
    n_mol = (carbon_g_l * c["n_frac"] + nitrogen_g_l * n["n_frac"]) / 14.007
    if n_mol <= 0:
        return {"error": "no nitrogen in inputs"}
    ratio = c_mol / n_mol
    verdict = ("C-limited (ratio < 6)" if ratio < 6 else
               "balanced (6–10, typical microbial)" if ratio <= 10 else
               "N-limited (> 10) — good for secondary metabolites/antibiotics")
    return {"carbon_mmol_L": round(c_mol * 1000, 1), "nitrogen_mmol_L": round(n_mol * 1000, 1),
            "C_N_ratio": round(ratio, 1), "verdict": verdict,
            "note": "Elemental fractions are typical values — check your supplier's COA."}


def cloning_calculator(insert_bp: int, vector_bp: int, insert_mass_ng: float,
                       vector_mass_ng: float, ratio: int = 3) -> Dict[str, Any]:
    """Ligation molar-insert:vector calculation + plasmid conversions."""
    if min(insert_bp, vector_bp, insert_mass_ng, vector_mass_ng) <= 0:
        return {"error": "all inputs must be > 0"}
    ins_pmol = insert_mass_ng * 1000 / (insert_bp * 660)
    vec_pmol = vector_mass_ng * 1000 / (vector_bp * 660)
    needed_ins_ng = vec_pmol * ratio * insert_bp * 660 / 1000
    return {"insert_pmol": round(ins_pmol, 4), "vector_pmol": round(vec_pmol, 4),
            "current_ratio": round(ins_pmol / vec_pmol, 1) if vec_pmol else None,
            "target_ratio": ratio,
            "insert_ng_needed_for_target": round(needed_ins_ng, 1),
            "plasmid_size_bp": insert_bp + vector_bp,
            "note": "660 g/mol per bp dsDNA; typical ligation ratios 3:1–5:1."}
