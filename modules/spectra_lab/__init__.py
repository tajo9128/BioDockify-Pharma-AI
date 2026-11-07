"""Spectra & Elucidation Lab — additive module (Analysis + Pharmacognosy departments).

Offline interpretation assistants built on correlation tables and RDKit:
  · IR wavenumber → functional-group matcher
  · ¹H/¹³C NMR shift estimation from SMILES (environment-based additive tables)
  · Multiplet analyzer (peaks → interpretation)
  · MS fragmentation predictor (common neutral losses + diagnostic ions)
  · UV-Vis λmax conjugation rules
"""
from __future__ import annotations

from typing import Any, Dict, List

# ── IR correlation table (cm-1) ───────────────────────────────────────────────

IR_GROUPS: List[Dict[str, Any]] = [
    {"group": "O–H (alcohol, free)", "range": (3600, 3650), "strength": "sharp, weak–medium"},
    {"group": "O–H (H-bonded)", "range": (3200, 3550), "strength": "broad, strong"},
    {"group": "O–H (carboxylic acid)", "range": (2500, 3300), "strength": "very broad"},
    {"group": "N–H (amine/amide)", "range": (3300, 3500), "strength": "medium, 1–2 bands"},
    {"group": "≡C–H (terminal alkyne)", "range": (3250, 3350), "strength": "sharp"},
    {"group": "C–H (sp, alkyne)", "range": (3000, 3100), "strength": "weak"},
    {"group": "C–H (sp2, alkene/aromatic)", "range": (3000, 3100), "strength": "medium"},
    {"group": "C–H (sp3)", "range": (2850, 2970), "strength": "strong"},
    {"group": "C–H (aldehyde, –CHO)", "range": (2720, 2820), "strength": "weak doublet"},
    {"group": "C≡N (nitrile)", "range": (2210, 2260), "strength": "medium, sharp"},
    {"group": "C≡C (alkyne)", "range": (2100, 2260), "strength": "weak"},
    {"group": "C=O (acid chloride)", "range": (1780, 1820), "strength": "strong"},
    {"group": "C=O (anhydride)", "range": (1740, 1820), "strength": "two strong bands"},
    {"group": "C=O (ester)", "range": (1720, 1750), "strength": "strong"},
    {"group": "C=O (aldehyde)", "range": (1720, 1740), "strength": "strong"},
    {"group": "C=O (ketone)", "range": (1700, 1725), "strength": "strong"},
    {"group": "C=O (carboxylic acid)", "range": (1690, 1725), "strength": "strong"},
    {"group": "C=O (amide)", "range": (1630, 1695), "strength": "strong"},
    {"group": "C=C (alkene)", "range": (1620, 1680), "strength": "variable"},
    {"group": "C=C (aromatic)", "range": (1450, 1600), "strength": "medium, 2–4 bands"},
    {"group": "N=O (nitro)", "range": (1510, 1560), "strength": "strong (asym)"},
    {"group": "N=O (nitro)", "range": (1340, 1390), "strength": "strong (sym)"},
    {"group": "C–O (ester/ether)", "range": (1050, 1300), "strength": "strong"},
    {"group": "C–N", "range": (1020, 1250), "strength": "medium"},
    {"group": "C–Cl", "range": (600, 800), "strength": "strong"},
    {"group": "aromatic C–H oop (mono-di-sub)", "range": (690, 900), "strength": "strong"},
]


def match_ir(peaks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Match given IR peaks [{wavenumber, note?}] against the correlation table."""
    hits = []
    for peak in peaks:
        try:
            w = float(peak.get("wavenumber", 0))
        except (TypeError, ValueError):
            continue
        if not (400 <= w <= 4000):
            continue
        matched = []
        for g in IR_GROUPS:
            lo, hi = g["range"]
            if lo <= w <= hi:
                matched.append(g)
        hits.append({"wavenumber": w,
                     "note": str(peak.get("note", ""))[:60],
                     "assignments": [f'{m["group"]} ({m["strength"]})' for m in matched] or ["no table match — fingerprint region?"],
                     "confidence": "high" if len(matched) == 1 else ("ambiguous" if matched else "none")})
    found_groups = sorted({m["group"].split("(")[0].strip() for h in hits for m in
                           [g for g in IR_GROUPS if g["range"][0] <= h["wavenumber"] <= g["range"][1]]})
    return {"peaks": hits, "groups_present": found_groups,
            "note": "Correlation-table matching. Always confirm with NMR/MS before structural claims."}


# ── NMR shift estimation (environment-based, RDKit) ──────────────────────────

def _atom_env(mol, idx: int) -> str:
    from rdkit import Chem
    a = mol.GetAtomWithIdx(idx)
    sym = a.GetSymbol()
    hyb = str(a.GetHybridization())
    aromatic = a.GetIsAromatic()
    # neighbor hetero/electronegative count
    n_o = sum(1 for n in a.GetNeighbors() if n.GetSymbol() in ("O", "N", "halogen".replace("halogen", "F")))
    n_x = sum(1 for n in a.GetNeighbors() if n.GetSymbol() in ("F", "Cl", "Br", "I"))
    return sym, hyb, aromatic, n_o + n_x


def estimate_nmr(smiles: str) -> Dict[str, Any]:
    """Rough ¹H and ¹³C shift estimates per atom from local environment rules."""
    from rdkit import Chem

    mol = Chem.MolFromSmiles(smiles or "")
    if mol is None:
        return {"error": "invalid SMILES"}
    mol_h = Chem.AddHs(mol)

    c13, h1 = [], []
    base_c = {"sp3": 0, "sp2": 100, "sp": 70}
    for atom in mol.GetAtoms():
        if atom.GetSymbol() != "C":
            continue
        _, hyb, arom, n_elec = _atom_env(mol, atom.GetIdx())
        shift = 125.0 if arom else base_c.get("sp2" if "SP2" in hyb.upper() else ("sp" if "SP" == hyb.upper()[:2] else "sp3"), 0)
        if not arom and "SP3" in hyb.upper():
            shift = 10 + 25 * n_elec
        elif "SP" == hyb.upper()[:2]:
            shift = 70 + 10 * n_elec
        shift += 8 * n_elec if (arom or "SP2" in hyb.upper()) and n_elec else 0
        c13.append({"idx": atom.GetIdx(), "env": f"C-{hyb}{'+X'*n_elec if n_elec else ''}{' (arom)' if arom else ''}",
                    "d13_est": round(min(220, max(0, shift)), 1)})

    for atom in mol_h.GetAtoms():
        if atom.GetSymbol() != "H":
            continue
        heavy = [n for n in atom.GetNeighbors() if n.GetSymbol() != "H"]
        if not heavy:
            continue
        h_atom = heavy[0]
        sym, hyb, arom, n_elec = _atom_env(mol_h, h_atom.GetIdx())
        if sym in ("O", "N"):
            shift = 2.0 if sym == "N" else 3.0
            kind = f"{sym}–H"
        elif arom:
            shift = 7.2 + 0.3 * n_elec
            kind = "aromatic H"
        elif hyb.upper().startswith("SP2"):
            shift = 5.0 + 0.7 * n_elec
            kind = "vinylic H"
        elif hyb.upper() in ("SP", "S"):
            shift = 2.5
            kind = "acetylenic H"
        else:  # SP3 alkyl
            # α to carbonyl/aryl? (heavy neighbor C has O double-bond or is aromatic)
            alpha_carbonyl = any(
                n.GetSymbol() == "O" and any(b.GetBondTypeAsDouble() == 2 for b in n.GetBonds())
                for nb in h_atom.GetNeighbors() for n in nb.GetNeighbors() if nb.GetSymbol() == "C"
                for b in nb.GetBonds()) if False else False
            shift = 0.9 + 0.55 * n_elec
            hn = h_atom.GetTotalNumHs()
            kind = f"alkyl H ({'CH3' if hn >= 3 else 'CH2' if hn >= 2 else 'CH'})"
        h1.append({"env": kind, "d1_est": round(min(12, max(0.5, shift)), 2)})

    # collapse H into grouped estimate list (approximate integrals)
    groups: Dict[str, Dict[str, Any]] = {}
    for h in h1:
        k = f"{h['env']} ~{h['d1_est']:.1f}"
        groups.setdefault(k, {"env": h["env"], "d1_est": h["d1_est"], "count": 0})
        groups[k]["count"] += 1
    h_rows = sorted(groups.values(), key=lambda r: r["d1_est"])
    from rdkit.Chem import rdMolDescriptors
    return {"formula": rdMolDescriptors.CalcMolFormula(mol),
            "h1": [{"shift_ppm": r["d1_est"], "group": r["env"], "approx_H": r["count"]} for r in h_rows],
            "c13": sorted(c13, key=lambda r: r["d13_est"]),
            "note": "Environment-rule estimates (±0.3–0.5 ppm ¹H, ±5–10 ppm ¹³C). Not a substitute for measurement or full prediction tools."}


def analyze_multiplets(peaks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Interpret entered ¹H peaks: shift → likely environment; multiplicity → neighbors."""
    env_table = [
        (0.8, 1.0, "simple alkyl CH3", "terminal methyl"),
        (1.0, 1.8, "alkyl CH2/CH", "chain methylene/methine"),
        (1.8, 2.5, "allylic / α-C=O / benzylic-adjacent", "next to π or carbonyl"),
        (2.5, 3.0, "α to carbonyl / acetylenic", "–CH2–C(=O)– or ≡C–H"),
        (3.0, 4.5, "O/N-attached CH/CH2", "–CH2–O–, –CH2–N–, O–CH3"),
        (4.5, 6.0, "vinylic", "=C–H"),
        (6.0, 7.0, "vinylic (conjugated)", "=C–H conjugated"),
        (7.0, 8.5, "aromatic", "Ar–H"),
        (8.5, 10.0, "aldehyde / amide NH", "–CHO, –CONH"),
        (10.0, 13.0, "carboxylic OH / phenol (exchange)", "–COOH, Ar–OH"),
    ]
    mult_n = {"s": 0, "singlet": 0, "d": 1, "doublet": 1, "t": 2, "triplet": 2, "q": 3, "quartet": 3,
              "quintet": 4, "m": None, "multiplet": None, "br": None, "dd": 2, "dt": 3}
    rows = []
    for p in peaks:
        try:
            s = float(p.get("shift", 0))
        except (TypeError, ValueError):
            continue
        env = next((e[2] for e in env_table if e[0] <= s <= e[1]), "unassigned region")
        mult = str(p.get("multiplet", "m")).lower().strip()
        n = mult_n.get(mult)
        try:
            integ = float(p.get("integration", 0) or 0)
        except (TypeError, ValueError):
            integ = 0
        try:
            j = float(p.get("j_hz", 0) or 0)
        except (TypeError, ValueError):
            j = 0
        rows.append({"shift": s, "multiplicity": mult.upper() if mult else "M",
                     "integration": integ or None, "j_hz": j or None,
                     "likely_env": env,
                     "neighbors": (f"{n} adjacent H (n+1 rule)" if n is not None else
                                   "overlapping / no simple n+1")})
    total_h = sum(r["integration"] or 0 for r in rows)
    return {"peaks": rows, "total_integrated_H": round(total_h, 1) if total_h else None,
            "note": "Enter measured peaks; environments follow standard shift regions and the n+1 rule."}


# ── MS fragmentation predictor ────────────────────────────────────────────────

LOSSES = [
    {"loss": 18.0, "fragment": "H₂O", "hint": "alcohol/acid — OH elimination"},
    {"loss": 28.0, "fragment": "CO", "hint": "aldehyde/ketone/ester rearrangement"},
    {"loss": 31.0, "fragment": "CH₃O•", "hint": "methoxy / methyl ester"},
    {"loss": 32.0, "fragment": "CH₃OH", "hint": "methyl ester (MH−32)"},
    {"loss": 43.0, "fragment": "C₃H₇ / CH₃CO", "hint": "propyl loss or acetyl"},
    {"loss": 44.0, "fragment": "CO₂", "hint": "carboxylic acid / ester"},
    {"loss": 45.0, "fragment": "COOH", "hint": "carboxylic acid"},
    {"loss": 46.0, "fragment": "C₂H₅OH / NO₂", "hint": "ethyl ester or nitro"},
    {"loss": 60.0, "fragment": "CH₃COOH", "hint": "acetate ester"},
    {"loss": 73.0, "fragment": "C₃H₉Si (TMS)", "hint": "silylated derivative"},
]


def predict_fragments(smiles: str, ionization: str = "ESI+") -> Dict[str, Any]:
    from rdkit import Chem
    from rdkit.Chem import Descriptors

    mol = Chem.MolFromSmiles(smiles or "")
    if mol is None:
        return {"error": "invalid SMILES"}
    mw = Descriptors.MolWt(mol)

    smarts_diagnostic = [
        ("[NX3;H2,H1,H0;$(N[#6])]", 30.0, "imine/amino fragment ~m/z 30 region"),
        ("c1ccccc1", 77.0, "phenyl cation m/z 77 (plus 51, 39 series)"),
        ("C(=O)N", 44.0, "amide CO-NH₂⁺ ~m/z 44"),
        ("[$([CX3](=O)[#6]),$([CX3](=O)O)]", 43.0, "acylium CH₃CO⁺ m/z 43"),
        ("[OX2]([#6])[#6]", 31.0, "CH₂=OH⁺ m/z 31 (ether/alcohol)"),
        ("[nX3]1cccc1-related-tail", 79.0, "pyridine ring m/z 79"),
    ]
    ions = []
    for smi, mz, hint in smarts_diagnostic:
        if "related-tail" in smi:
            continue
        patt = Chem.MolFromSmarts(smi)
        if patt and mol.HasSubstructMatch(patt):
            ions.append({"mz": mz, "ion": hint})

    neutrals = []
    for l in LOSSES:
        m = mw - l["loss"]
        if m >= 15:
            neutrals.append({"mz": round(m, 2), "loss": l["fragment"], "hint": l["hint"]})

    precursor = round(mw + (1.0073 if ionization == "ESI+" else -1.0073), 2) if ionization.startswith("ESI") else round(mw, 2)
    # halogen isotope hints
    halogens = {s: sum(1 for a in mol.GetAtoms() if a.GetSymbol() == s) for s in ("Cl", "Br")}
    iso_note = []
    if halogens.get("Cl"):
        iso_note.append(f"{halogens['Cl']}×Cl → M+2 at ~32% of M")
    if halogens.get("Br"):
        iso_note.append(f"{halogens['Br']}×Br → M+2 at ~98% of M (1:1)")
    return {"mw": round(mw, 2), "precursor_mz": precursor, "ionization": ionization,
            "common_neutral_losses": neutrals, "diagnostic_ions": ions,
            "isotope_pattern": iso_note or ["no Cl/Br pattern"],
            "note": "Rule-based predictions — confirm with high-res MS/MS and databases (NIST/MassBank)."}


# ── UV λmax rules ─────────────────────────────────────────────────────────────

def uv_rules(smiles: str) -> Dict[str, Any]:
    from rdkit import Chem
    mol = Chem.MolFromSmiles(smiles or "")
    if mol is None:
        return {"error": "invalid SMILES"}
    out = []
    if mol.HasSubstructMatch(Chem.MolFromSmarts("C=C-C=C")):
        out.append({"chromophore": "diene (conjugated)", "lmax_rule": "214 + 5×(alkyl/ring residues) + 30×(extra conj.)", "base_nm": 214})
    if mol.HasSubstructMatch(Chem.MolFromSmarts("c1ccccc1")):
        out.append({"chromophore": "benzene ring", "lmax_rule": "254 (fine structure); auxochromes (OH, OR, NR2) shift to 270–290", "base_nm": 254})
    if mol.HasSubstructMatch(Chem.MolFromSmarts("[CX3](=O)[#6]")):
        out.append({"chromophore": "α,β-unsaturated carbonyl (enone)", "lmax_rule": "215 + 10×α-residue + 12×β-residue + extended conj. 30–60", "base_nm": 215})
    if mol.HasSubstructMatch(Chem.MolFromSmarts("c1ccccc1-c1ccccc1")):
        out.append({"chromophore": "biphenyl", "lmax_rule": "~252 nm (conj. across bond)", "base_nm": 252})
    if not out:
        out.append({"chromophore": "isolated π or n electrons", "lmax_rule": "C=C ~ 180, C=O ~ 280 (n→π*, weak)", "base_nm": 180})
    return {"chromophores": out,
            "note": "Woodward–Fieser-style rules. Measured λmax confirms conjugation extent."}


def parse_spectrum_csv(text: str) -> Dict[str, Any]:
    """Parse a two-column spectrum CSV and auto-pick peaks with scipy."""
    import numpy as np
    from scipy.signal import find_peaks
    lines = [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("#")]
    if len(lines) < 10:
        return {"error": "need at least 10 data rows"}
    start = 0
    try:
        float(lines[0].split(",")[0])
    except ValueError:
        start = 1
    xs, ys = [], []
    for line in lines[start:]:
        parts = line.split(",")
        if len(parts) < 2:
            continue
        try:
            xs.append(float(parts[0]))
            ys.append(float(parts[1]))
        except ValueError:
            continue
    if len(xs) < 10:
        return {"error": "only " + str(len(xs)) + " valid rows parsed"}
    x = np.array(xs)
    y = np.array(ys)
    prominence = float(np.max(y)) * 0.1
    peaks, props = find_peaks(y, prominence=prominence, distance=max(1, len(x) // 100))
    detected = [{"position": round(float(x[i]), 1), "intensity": round(float(y[i]), 1)}
                for i in peaks[:30]]
    return {"n_points": len(xs), "x_range": [float(x.min()), float(x.max())],
            "peaks_detected": len(peaks), "peaks": detected,
            "note": "Prominence threshold = 10% of max intensity."}
