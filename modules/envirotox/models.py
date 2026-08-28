"""Environmental Fate & Ecotoxicity QSAR — screening-level estimates from RDKit descriptors.

Models (published, deliberately simplified to descriptor form):
- BCF (bioconcentration): Meylan et al. 1999 style log BCF = 0.77·logKow − 0.51 (non-ionics)
- Koc (soil adsorption): Karickhoff 1981 log Koc = 0.987·logKow − 0.346
- Fish 96h LC50: Könemann 1981 baseline narcosis log(1/LC50[mol/L]) = 0.871·logKow + 0.87
- Ready biodegradability: BIOWIN-style heuristic rule base
- PBT/vPvB screening per REACH Annex XIII criteria

These are screening estimates for prioritization — NOT regulatory submissions.
"""
import math
from typing import Dict

try:
    from rdkit import Chem
    from rdkit.Chem import Crippen, Descriptors, rdMolDescriptors
    HAS_RDKIT = True
except ImportError:
    HAS_RDKIT = False
    Chem = None

REACH_B = 2000        # log BCF 3.3 — bioaccumulative
REACH_vB = 5000       # log BCF 3.7 — very bioaccumulative
REACH_T_LC50 = 10     # mg/L — acute toxicity threshold (T criterion < 10 mg/L)


def _matches(mol, smarts: str) -> int:
    patt = Chem.MolFromSmarts(smarts)
    if patt is None:
        return 0
    try:
        return len(mol.GetSubstructMatches(patt))
    except Exception:
        return 0


def _descriptors(mol) -> Dict:
    return {
        "mw": Descriptors.MolWt(mol),
        "logp": Crippen.MolLogP(mol),
        "tpsa": rdMolDescriptors.CalcTPSA(mol),
        "hbd": rdMolDescriptors.CalcNumHBD(mol),
        "hba": rdMolDescriptors.CalcNumHBA(mol),
        "rings": rdMolDescriptors.CalcNumRings(mol),
        "aromatic_rings": rdMolDescriptors.CalcNumAromaticRings(mol),
        "rotatable": rdMolDescriptors.CalcNumRotatableBonds(mol),
        "halogens": sum(1 for a in mol.GetAtoms() if a.GetSymbol() in ("F", "Cl", "Br", "I")),
        "nitro": _matches(mol, "[N+](=O)[O-]"),
        "quaternary_n": _matches(mol, "[NX4+]"),
        "metals": sum(1 for a in mol.GetAtoms() if a.GetSymbol() in
                      ("Hg", "Pb", "Cd", "As", "Cr", "Ni", "Cu", "Zn", "Sn", "Sb", "Se")),
        "formula": rdMolDescriptors.CalcMolFormula(mol),
    }


def _logbcf(mol, d: Dict) -> float:
    """Meylan-style non-ionic estimate, clipped to sane range."""
    logbcf = 0.77 * d["logp"] - 0.51
    if d["halogens"] >= 4:
        logbcf += 0.5  # halogen correction (persistent halogenated)
    return max(-1.0, min(6.0, logbcf))


def _koc(d: Dict) -> float:
    logkoc = 0.987 * d["logp"] - 0.346
    return max(-1.0, min(7.0, logkoc))


def _fish_lc50_mg_l(mol, d: Dict) -> Dict:
    """Könemann baseline narcosis, mol/L → mg/L. Excess toxicity flags reduce it."""
    log_inv_lc50_mol = 0.871 * d["logp"] + 0.87
    log_lc50_mol = -log_inv_lc50_mol
    lc50_mol = 10 ** log_lc50_mol
    excess_factor = 1.0
    modes = ["baseline narcosis"]
    if d["nitro"] > 0:
        excess_factor = 10.0
        modes.append("reactive: nitroaromatic — possible excess toxicity")
    if _matches(mol, "[CX3]=[CX3][CX3]=[CX3]"):
        excess_factor = max(excess_factor, 100.0)
        modes.append("reactive: Michael acceptor — excess toxicity likely")
    if d["halogens"] >= 3 and d["aromatic_rings"] >= 1:
        excess_factor = max(excess_factor, 10.0)
        modes.append("halogenated aromatic — potential dioxin/PCB concern")
    lc50_mg = lc50_mol * d["mw"] * 1000 / excess_factor
    return {"lc50_mg_l": round(lc50_mg, 3), "mode_of_action": modes,
            "log_lc50_mol_l": round(log_lc50_mol, 2)}


def _biodegradability(d: Dict) -> Dict:
    """BIOWIN-like heuristic: positive and negative fragments/terms."""
    score = 0.0
    reasons = []
    if d["mw"] < 200:
        score += 0.5; reasons.append("MW < 200 (+)")
    elif d["mw"] > 400:
        score -= 1.0; reasons.append("MW > 400 (−)")
    if d["logp"] < 2.5:
        score += 0.75; reasons.append("good water solubility proxy, logP < 2.5 (+)")
    elif d["logp"] > 4:
        score -= 1.0; reasons.append("highly hydrophobic, logP > 4 (−)")
    if d["halogens"] >= 2:
        score -= 1.0 * d["halogens"] / 2; reasons.append(f"{d['halogens']} halogens (−)")
    if d["nitro"]:
        score -= 0.5; reasons.append("nitro group (−)")
    if d["quaternary_n"]:
        score -= 0.5; reasons.append("quaternary ammonium (−)")
    if d["rings"] == 0:
        score += 0.75; reasons.append("acyclic (+)")
    if d["aromatic_rings"] >= 3:
        score -= 0.5; reasons.append("≥3 aromatic rings (−)")
    if d["rotatable"] >= 5:
        score += 0.25; reasons.append("flexible aliphatic content (+)")
    if d["tpsa"] > 60:
        score += 0.25; reasons.append("polar (TPSA > 60) (+)")
    if d["metals"]:
        score -= 1.0; reasons.append("contains metal/metalloid (−)")

    if score >= 1.5:
        verdict = "readily biodegradable (likely)"
    elif score >= 0.0:
        verdict = "borderline"
    else:
        verdict = "not readily biodegradable (likely)"
    return {"verdict": verdict, "biowin_like_score": round(score, 2), "reasons": reasons}


def _pbt(bcf: float, lc50: Dict, biodeg: Dict) -> Dict:
    logbcf = math.log10(max(bcf, 1e-6))
    b = bcf >= REACH_B
    vb = bcf >= REACH_vB
    t = lc50["lc50_mg_l"] < REACH_T_LC50
    p = "not readily" in biodeg["verdict"]
    vp = p and biodeg["biowin_like_score"] <= -1.5
    classification = []
    if (p or vp) and (vb or b) and t:
        classification.append("PBT candidate (REACH Annex XIII screening)")
    if vp and vb:
        classification.append("vPvB candidate")
    return {
        "P": p, "vP": vp, "B": b, "vB": vb, "T": t,
        "log_bcf": round(logbcf, 2),
        "candidates": classification,
        "classification": classification[0] if classification else "not a PBT/vPvB candidate (screening)",
    }


def assess(smiles: str) -> Dict:
    if not HAS_RDKIT:
        return {"status": "error", "error": "RDKit is required for ecotoxicity assessment"}
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"error": f"Invalid SMILES: {smiles}"}
    d = _descriptors(mol)
    logbcf = _logbcf(mol, d)
    bcf = 10 ** logbcf
    koc = 10 ** _koc(d)
    lc50 = _fish_lc50_mg_l(mol, d)
    biodeg = _biodegradability(d)
    pbt = _pbt(bcf, lc50, biodeg)

    green_flags = []
    if d["halogens"] >= 3:
        green_flags.append(f"{d['halogens']} halogens — persistent-chemistry concern")
    if d["metals"]:
        green_flags.append("contains heavy metal/metalloid")
    if d["logp"] > 5:
        green_flags.append("very hydrophobic (logP > 5) — bioaccumulation pressure")

    return {
        "smiles": Chem.MolToSmiles(mol),
        "descriptors": {k: (round(v, 2) if isinstance(v, float) else v) for k, v in d.items()},
        "bioconcentration": {
            "log_bcf": round(logbcf, 2), "bcf_l_kg": round(bcf, 1),
            "bioaccumulative_b": bcf >= REACH_B, "very_bioaccumulative_vb": bcf >= REACH_vB,
            "model": "Meylan et al. 1999 (simplified, non-ionic)",
        },
        "soil_adsorption": {
            "log_koc": round(math.log10(koc), 2), "koc_l_kg": round(koc, 1),
            "mobility": _mobility(math.log10(koc)),
            "model": "Karickhoff 1981 (non-ionics)",
        },
        "fish_toxicity_96h": {
            **lc50, "toxic_t": lc50["lc50_mg_l"] < REACH_T_LC50,
            "model": "Könemann 1981 baseline narcosis + reactivity flags",
        },
        "biodegradability": biodeg,
        "pbt_screen": pbt,
        "green_chemistry_flags": green_flags,
        "overall_concern": "high" if pbt["candidates"]
                           else ("moderate" if (bcf >= REACH_B or lc50["lc50_mg_l"] < REACH_T_LC50 or green_flags)
                                 else "low"),
        "disclaimer": "Screening-level estimates from descriptor QSAR — not a substitute for "
                      "OECD 301/305 or 203 studies or regulatory assessment.",
    }


def _mobility(logkoc: float) -> str:
    if logkoc < 1.5:
        return "very high mobility"
    if logkoc < 2.5:
        return "high mobility"
    if logkoc < 3.5:
        return "medium mobility"
    if logkoc < 4.5:
        return "low mobility"
    return "immobile"


def batch(smiles_list: list) -> Dict:
    results = []
    for smi in smiles_list:
        r = assess(smi)
        if "error" in r:
            results.append({"smiles": smi, "error": r["error"]})
            continue
        results.append({
            "smiles": r["smiles"], "formula": r["descriptors"]["formula"],
            "logp": r["descriptors"]["logp"], "bcf_l_kg": r["bioconcentration"]["bcf_l_kg"],
            "lc50_mg_l": r["fish_toxicity_96h"]["lc50_mg_l"],
            "biodeg": r["biodegradability"]["verdict"],
            "concern": r["overall_concern"],
        })
    results.sort(key=lambda x: x.get("concern", "") != "high")
    return {"count": len(results), "results": results}
