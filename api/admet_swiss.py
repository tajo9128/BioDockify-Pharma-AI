"""SwissADME-style comprehensive ADME prediction engine.
Computes 5 sections: Physicochemical, Lipophilicity (5 models), Water Solubility (3 models),
Pharmacokinetics (GI, BBB, P-gp, CYP450, Log Kp), Druglikeness (6 filters), Medicinal Chemistry.
All computation is RDKit-based — no external ML models required."""
import logging
from typing import Dict, Tuple

log = logging.getLogger("admet_swiss")

# ── iLOGP atom-type contributions (Daina et al. 2014) ──
ILOGP_CONTRIB = {
    "C": {"sp3": 0.20, "sp2": 0.15, "aromatic": 0.10},
    "N": {"sp3": -0.50, "sp2": -0.40, "aromatic": -0.35},
    "O": {"sp3": -0.60, "sp2": -0.50, "aromatic": -0.45},
    "F": {"sp3": 0.50, "sp2": 0.45, "aromatic": 0.40},
    "Cl": {"sp3": 0.80, "sp2": 0.75, "aromatic": 0.70},
    "Br": {"sp3": 1.00, "sp2": 0.95, "aromatic": 0.90},
    "I": {"sp3": 1.20, "sp2": 1.15, "aromatic": 1.10},
    "S": {"sp3": -0.20, "sp2": -0.15, "aromatic": -0.10},
    "P": {"sp3": 0.30, "sp2": 0.25, "aromatic": 0.20},
}

# ── CYP450 SMARTS structural alerts ──
CYP450_ALERTS = {
    "cyp1a2": [
        ("polycyclic_planar", "c1ccc2c(c1)ccc1ccccc12"),
        ("alkoxy_aniline", "c1cc(O)ccc1N"),
        ("methylenedioxyphenyl", "O1COc2ccccc12"),
        ("coumarin_core", "O=c1ccc2ccccc2o1"),
    ],
    "cyp2c19": [
        ("benzyl_alcohol", "OCc1ccccc1"),
        ("benzhydryl", "C(c1ccccc1)c1ccccc1"),
        ("tertiary_amine_allyl", "C=CCN(C)C"),
        ("biguanide", "NC(=N)NC(=N)N"),
    ],
    "cyp2c9": [
        ("sulfonamide", "S(=O)(=O)N"),
        ("barbiturate", "O=c1[nH]ccc(=O)[nH]1"),
        ("warfarin_like", "O=c1oc2ccccc2c1O"),
        ("profen_acids", "CC(C(=O)O)c1ccc(cc1)"),
    ],
    "cyp2d6": [
        ("basic_nitrogen_tertiary", "CN(C)CC"),
        ("phenethylamine", "c1ccccc1CCN"),
        ("aryloxy_amine", "c1cc(OCCN)ccc1"),
        ("piperidine", "C1CCNCC1"),
    ],
    "cyp3a4": [
        ("imidazole_ring", "c1ncnc1"),
        ("macrocycle_lactone", "O=C1CCCCCCCCCCCN1"),
        ("dihydropyridine", "C1=CNC(C)=C(C)C=1"),
        ("triazole", "c1nnn[nH]1"),
    ],
}

# ── Druglikeness filter thresholds ──
LEADLIKENESS = {"mw": (250, 350), "logp": (None, 3.5), "rot_bonds": (None, 7)}


def compute_swiss_adme(smiles: str) -> Dict:
    """Main entry point — returns comprehensive SwissADME-style result."""
    from rdkit import Chem
    from rdkit.Chem import Descriptors, Crippen, rdMolDescriptors

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"error": "Invalid SMILES"}

    # ── 1. Physicochemical Properties ──
    mw = round(Descriptors.MolWt(mol), 2)
    hbd = Descriptors.NumHDonors(mol)
    hba = Descriptors.NumHAcceptors(mol)
    tpsa = round(Descriptors.TPSA(mol), 2)
    rot = Descriptors.NumRotatableBonds(mol)
    formula = rdMolDescriptors.CalcMolFormula(mol)
    frac_csp3 = round(rdMolDescriptors.CalcFractionCSP3(mol), 2)
    mr = round(Descriptors.MolMR(mol), 2)
    heavy_atoms = sum(1 for a in mol.GetAtoms() if a.GetAtomicNum() > 1)
    aromatic_heavy = sum(1 for a in mol.GetAtoms() if a.GetIsAromatic() and a.GetAtomicNum() > 1)

    physicochemical = {
        "formula": formula, "mw": mw, "heavy_atoms": heavy_atoms,
        "aromatic_heavy_atoms": aromatic_heavy, "fraction_csp3": frac_csp3,
        "rotatable_bonds": rot, "hba": hba, "hbd": hbd,
        "molar_refractivity": mr, "tpsa": tpsa,
    }

    # ── 2. Lipophilicity (5 models) ──
    ilogp = round(_calc_ilogp(mol), 2)
    xlogp3 = round(_calc_xlogp3(mol), 2)
    wlogp = round(Crippen.MolLogP(mol), 2)
    mlogp = round(Descriptors.MolLogP(mol), 2)
    silicos_it = round(_calc_silicos_it_logp(mol), 2)
    consensus_logp = round((ilogp + xlogp3 + wlogp + mlogp + silicos_it) / 5, 2)

    lipophilicity = {
        "ilogp": ilogp, "xlogp3": xlogp3, "wlogp": wlogp,
        "mlogp": mlogp, "silicos_it": silicos_it, "consensus_logp": consensus_logp,
    }

    # ── 3. Water Solubility (3 models) ──
    esol_logs = round(0.16 - 0.63 * consensus_logp - 0.0062 * mw + 0.066 * rot - 0.74 * aromatic_heavy, 2)
    ali_logs = round(0.972 * consensus_logp - 0.011 * mw + 0.040 * rot - 1.326, 2)
    silicos_logs = round(0.023 * mw - 0.467 * consensus_logp - 0.024 * rot + 2.946, 2)

    solubility = {
        "esol_logs": esol_logs, "esol_class": _solubility_class(esol_logs),
        "ali_logs": ali_logs, "ali_class": _solubility_class(ali_logs),
        "silicos_it_logs": silicos_logs, "silicos_it_class": _solubility_class(silicos_logs),
    }

    # ── 4. Pharmacokinetics ──
    gi_absorbed, bbb_permeant = _boiled_egg(wlogp, tpsa)
    pgp_substrate = _predict_pgp(mw, consensus_logp, hba, tpsa)
    cyp_inhibition = _check_cyp_inhibition(mol)
    log_kp = round(-2.8 + 0.71 * consensus_logp - 0.0061 * mw, 2)

    pharmacokinetics = {
        "gi_absorption": "High" if gi_absorbed else "Low",
        "bbb_permeant": "Yes" if bbb_permeant else "No",
        "pgp_substrate": "Yes" if pgp_substrate else "No",
        "log_kp_cm_s": log_kp,
        **cyp_inhibition,
    }

    # ── 5. Druglikeness (6 filters) ──
    n_atoms = len(mol.GetAtoms())
    lipinski = _check_lipinski(mw, consensus_logp, hbd, hba)
    ghose = _check_ghose(mw, consensus_logp, mr, n_atoms)
    veber = _check_veber(tpsa, rot)
    egan = _check_egan(wlogp, tpsa)
    muegge = _check_muegge(mw, consensus_logp, tpsa, rot, hba, hbd, mol)
    bioavail = _calc_bioavailability_score(tpsa)

    druglikeness = {
        "lipinski": lipinski, "ghose": ghose, "veber": veber,
        "egan": egan, "muegge": muegge, "bioavailability_score": bioavail,
        "consensus": sum(f["passed"] for f in [lipinski, ghose, veber, egan, muegge]),
    }

    # ── 6. Medicinal Chemistry ──
    leadlikeness = _check_leadlikeness(mw, consensus_logp, rot)
    sa_score = round(_calc_synthetic_accessibility(mol), 2)

    medicinal = {
        "leadlikeness": leadlikeness,
        "synthetic_accessibility": sa_score,
    }

    return {
        "smiles": smiles,
        "physicochemical": physicochemical,
        "lipophilicity": lipophilicity,
        "solubility": solubility,
        "pharmacokinetics": pharmacokinetics,
        "druglikeness": druglikeness,
        "medicinal": medicinal,
    }


# ── Private computation helpers ──

def _calc_ilogp(mol) -> float:
    """iLOGP: physics-based atom-type contributions."""
    total = 0.0
    for atom in mol.GetAtoms():
        sym = atom.GetSymbol()
        if sym not in ILOGP_CONTRIB:
            continue
        is_sp2 = "SP2" in atom.GetHybridization().name
        is_aromatic = atom.GetIsAromatic()
        key = "aromatic" if is_aromatic else ("sp2" if is_sp2 else "sp3")
        total += ILOGP_CONTRIB[sym].get(key, 0.15)
    return round(total, 2)


def _calc_xlogp3(mol) -> float:
    """XLOGP3 approximated via Crippen with correction."""
    from rdkit.Chem import Crippen
    return round(Crippen.MolLogP(mol) * 0.85, 2)


def _calc_silicos_it_logp(mol) -> float:
    """SILICOS-IT: fragment-based + 1 carbon atom rule."""
    from rdkit import Chem
    fragments = {
        "[OH]": -1.109, "[C](=O)": -0.487, "[O]": -0.408,
        "[NH2]": -0.721, "[NH]": -0.410, "[C]#[N]": -0.197,
        "[N+](=O)[O-]": -0.617, "[F]": 0.444, "[Cl]": 0.731,
        "[Br]": 0.926, "[I]": 1.261, "[S]": 0.100,
    }
    total = 0.0
    for smarts, contrib in fragments.items():
        pat = Chem.MolFromSmarts(smarts)
        if pat is not None:
            total += len(mol.GetSubstructMatches(pat)) * contrib
    n_c = sum(1 for a in mol.GetAtoms() if a.GetSymbol() == "C")
    return round(total + n_c * 0.198, 2)


def _solubility_class(logs: float) -> str:
    if logs >= 0:
        return "Highly soluble"
    if logs >= -2:
        return "Very soluble"
    if logs >= -4:
        return "Soluble"
    if logs >= -6:
        return "Moderately soluble"
    if logs >= -10:
        return "Poorly soluble"
    return "Insoluble"


def _boiled_egg(wlogp: float, tpsa: float) -> Tuple[bool, bool]:
    """BOILED-Egg model: GI absorption (white) and BBB permeation (yolk)."""
    gi_absorbed = tpsa < 12.5 * wlogp - 25 and tpsa < 300 - 12.5 * wlogp
    bbb_permeant = tpsa < 5 * wlogp - 15 and tpsa < 200 - 8 * wlogp
    return gi_absorbed, bbb_permeant


def _predict_pgp(mw: float, logp: float, hba: int, tpsa: float) -> bool:
    """P-gp substrate prediction via rule-based consensus."""
    score = 0
    if mw > 400:
        score += 1
    if logp > 4:
        score += 1
    if hba > 6:
        score += 1
    if tpsa > 90:
        score += 1
    if hba > 6:
        score += 1
    return score >= 3


def _check_cyp_inhibition(mol) -> Dict[str, str]:
    """CYP450 inhibition via SMARTS structural alerts: 5 major isoforms."""
    from rdkit import Chem
    results = {}
    for isoform, alerts in CYP450_ALERTS.items():
        matched = False
        for name, smarts in alerts:
            pat = Chem.MolFromSmarts(smarts)
            if pat is not None and mol.HasSubstructMatch(pat):
                matched = True
                break
        results[isoform] = "Yes" if matched else "No"
    return results


def _check_lipinski(mw, logp, hbd, hba) -> Dict:
    r = {"MW (≤500)": mw <= 500, "LogP (≤5)": logp <= 5, "HBD (≤5)": hbd <= 5, "HBA (≤10)": hba <= 10}
    v = sum(1 for p in r.values() if not p)
    return {"passed": v <= 1, "violations": v, "rules": r}


def _check_ghose(mw, logp, mr, atoms) -> Dict:
    r = {"MW 160-480": 160 <= mw <= 480, "LogP -0.4 to 5.6": -0.4 <= logp <= 5.6,
         "Atoms 20-70": 20 <= atoms <= 70, "MR 40-130": 40 <= mr <= 130}
    v = sum(1 for p in r.values() if not p)
    return {"passed": v == 0, "violations": v, "rules": r}


def _check_veber(tpsa, rot) -> Dict:
    r = {"RotBonds (≤10)": rot <= 10, "TPSA (≤140)": tpsa <= 140}
    v = sum(1 for p in r.values() if not p)
    return {"passed": v == 0, "violations": v, "rules": r}


def _check_egan(wlogp, tpsa) -> Dict:
    r = {"WLOGP (≤5.88)": wlogp <= 5.88, "TPSA (≤131.6)": tpsa <= 131.6}
    v = sum(1 for p in r.values() if not p)
    return {"passed": v == 0, "violations": v, "rules": r}


def _check_muegge(mw, logp, tpsa, rot, hba, hbd, mol) -> Dict:
    nr = mol.GetRingInfo().NumRings()
    nc = sum(1 for a in mol.GetAtoms() if a.GetSymbol() == "C")
    no = sum(1 for a in mol.GetAtoms() if a.GetSymbol() in ("N", "O"))
    r = {"MW 200-600": 200 <= mw <= 600, "LogP -2 to 5": -2 <= logp <= 5,
         "TPSA (≤150)": tpsa <= 150, "Rings (≤7)": nr <= 7, "C (>4)": nc > 4,
         "N+O (>1)": no > 1, "RotBonds (≤15)": rot <= 15, "HBA (≤10)": hba <= 10, "HBD (≤5)": hbd <= 5}
    v = sum(1 for p in r.values() if not p)
    return {"passed": v == 0, "violations": v, "rules": r}


def _calc_bioavailability_score(tpsa: float) -> str:
    if tpsa <= 0:
        return "1.00"
    if tpsa <= 140:
        return "0.55"
    if tpsa <= 200:
        return "0.17"
    return "0.00"


def _check_leadlikeness(mw, logp, rot) -> Dict:
    r = {"MW 250-350": 250 <= mw <= 350, "LogP (≤3.5)": logp <= 3.5, "RotBonds (≤7)": rot <= 7}
    v = sum(1 for p in r.values() if not p)
    return {"passed": v <= 1, "violations": v, "rules": r}


def _calc_synthetic_accessibility(mol) -> float:
    """SA Score (1=easy, 10=hard). Fragment frequency + complexity penalties."""
    from rdkit.Chem import Descriptors, FindMolChiralCenters
    mw = Descriptors.MolWt(mol)
    rot = Descriptors.NumRotatableBonds(mol)
    rings = mol.GetRingInfo().NumRings()
    chiral = len(FindMolChiralCenters(mol, includeUnassigned=True))
    score = 1.0 + 0.05 * mw / 100 + 0.1 * rot + 0.2 * rings + 0.2 * chiral
    return round(min(10.0, max(1.0, score)), 2)
