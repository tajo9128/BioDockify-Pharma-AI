"""Drug Properties API v2 — MW, LogP, TPSA, HBA/HBD, hERG, AMES, pKa,
BBB score, Melting Point, Drug-likeness Score.

Inspired by MolSoft ICM-Pro (ML LogP/LogS/DrugLikeness), DeepPurpose (DL encodings)."""
from helpers.api import ApiHandler, Request
import re


def _kb_store(title, content, tags=None):
    try:
        from modules.knowledge.auto_store import auto_store
        auto_store("drug_properties", title, content, source="Drug Properties",
                   tags=tags or ["drug_properties"], category="drug_analysis")
    except Exception:
        pass

DRUG_LIBRARY = {
    "aspirin": {"smiles": "CC(=O)Oc1ccccc1C(=O)O", "name": "Aspirin"},
    "caffeine": {"smiles": "Cn1cnc2c1c(=O)n(c(=O)n2C)C", "name": "Caffeine"},
    "ibuprofen": {"smiles": "CC(C)Cc1ccc(cc1)C(C)C(=O)O", "name": "Ibuprofen"},
    "metformin": {"smiles": "CN(C)C(=N)N=C(N)N", "name": "Metformin"},
    "morphine": {"smiles": "CN1CCc2c(O)ccc(c2C1)C(O)=O", "name": "Morphine"},
    "warfarin": {"smiles": "CC(=O)OC(Cc1c(O)c2ccccc2oc1=O)C(c1ccccc1)=O", "name": "Warfarin"},
    "sildenafil": {"smiles": "CCCC1=C2N(C(=O)N1CCC)CCCC2c3ccc(cc3)S(=O)(=O)N", "name": "Sildenafil"},
    "glucose": {"smiles": "OC[C@H]1OC(O)[C@H](O)[C@@H](O)[C@@H]1O", "name": "Glucose"},
    "paracetamol": {"smiles": "CC(=O)Nc1ccc(O)cc1", "name": "Paracetamol"},
    "captopril": {"smiles": "CC(CS)C(=O)N1CCCC1C(=O)O", "name": "Captopril"},
}

ATOMIC_WEIGHTS = {"H":1.008,"C":12.011,"N":14.007,"O":15.999,"F":18.998,"P":30.974,"S":32.065,"Cl":35.453,"Br":79.904,"I":126.904,"Na":22.990,"K":39.098,"Ca":40.078,"Fe":55.845,"Zn":65.380}

# ── hERG SMARTS structural alerts (cardiotoxicity) ──
HERG_ALERTS = [
    ("tertiary_amine_pharmacophore", "[NX3;H0;!$(NC=O)]"),
    ("aromatic_ring_hydrophobic", "a(-[Cl,Br,I,F])"),
    ("sulfonamide", "S(=O)(=O)N"),
    ("alkoxy_benzene_long", "cOCCCN"),
    ("fluoro_alkane", "C(F)(F)"),
    ("tetrazole", "c1nnn[nH]1"),
    ("nitrile", "C#N"),
    ("imidazole_basic", "c1ncnc1"),
    ("piperazine_like", "C1CNCCN1"),
    ("diphenylmethane", "C(c1ccccc1)c1ccccc1"),
]

# ── AMES mutagenicity SMARTS alerts (Kazius-Hansen) ──
AMES_ALERTS = [
    ("nitro_group", "[N+](=O)[O-]"),
    ("nitroso", "N=O"),
    ("aromatic_amine", "c[NH2]"),
    ("epoxide", "C1OC1"),
    ("alkyl_halide", "[Cl,Br,I][CX4;CH,CH2,CH3]"),
    ("aziridine", "C1CN1"),
    ("n_nitroso", "CN=O"),
    ("hydrazine", "NN"),
    ("polycyclic_aromatic", "c1ccc2c(c1)ccc1ccccc12"),
    ("acyl_halide", "C(=O)[Cl,Br,I]"),
    ("sulfonate_ester", "S(=O)(=O)O[CX4]"),
    ("quinone", "O=c1ccc(=O)cc1"),
    ("diazo", "[N]=[N]"),
    ("hydroxylamine", "NO"),
    ("mustard", "ClCCN"),
]

# ── pKa SMARTS patterns with approximate pKa values ──
PKA_ACIDIC = [
    ("carboxylic_acid", "C(=O)O", 4.2),
    ("sulfonic_acid", "S(=O)(=O)O", -2.0),
    ("phenol", "cO", 9.9),
    ("tetrazole", "c1nn[nH]n1", 4.9),
    ("imide", "C(=O)NC(=O)", 9.0),
    ("thiol", "CS", 10.0),
]
PKA_BASIC = [
    ("aliphatic_amine_primary", "[CX4]N", 10.5),
    ("aliphatic_amine_secondary", "[CX4]N[CX4]", 11.0),
    ("aliphatic_amine_tertiary", "[CX4]N([CX4])[CX4]", 10.0),
    ("aniline", "cN", 4.6),
    ("pyridine", "c1ncccc1", 5.2),
    ("imidazole", "c1ncnc1", 7.0),
    ("guanidine", "NC(=N)N", 13.0),
    ("amidine", "NC(=N)", 11.5),
    ("piperidine", "C1CCNCC1", 11.1),
    ("morpholine", "C1COCCN1", 8.5),
]


def _substructure_match(mol, smarts):
    try:
        from rdkit import Chem
        pat = Chem.MolFromSmarts(smarts)
        return pat is not None and mol.HasSubstructMatch(pat)
    except Exception:
        return False


def _count_matches(mol, smarts):
    try:
        from rdkit import Chem
        pat = Chem.MolFromSmarts(smarts)
        return len(mol.GetSubstructMatches(pat)) if pat is not None else 0
    except Exception:
        return 0


def _predict_herg(mol):
    """hERG cardiotoxicity prediction: SMARTS structural alerts → risk level."""
    count = sum(1 for _, s in HERG_ALERTS if _substructure_match(mol, s))
    if count >= 3: return "High risk", count
    if count >= 1: return "Moderate risk", count
    return "Low risk", 0


def _predict_ames(mol):
    """AMES mutagenicity prediction: SMARTS structural alerts → risk level."""
    count = sum(1 for _, s in AMES_ALERTS if _substructure_match(mol, s))
    if count >= 2: return "Likely mutagenic", count
    if count >= 1: return "Possible mutagen", count
    return "Probably non-mutagenic", 0


def _predict_pka(mol):
    """Predict acidic and basic pKa via substructure matching."""
    acidic = []
    for name, smarts, pka in PKA_ACIDIC:
        if _substructure_match(mol, smarts):
            acidic.append({"group": name, "pka": pka})
    basic = []
    for name, smarts, pka in PKA_BASIC:
        if _substructure_match(mol, smarts):
            basic.append({"group": name, "pka": pka})
    strongest_acidic = min(a["pka"] for a in acidic) if acidic else None
    strongest_basic = max(b["pka"] for b in basic) if basic else None
    return {
        "acidic_pka": strongest_acidic,
        "basic_pka": strongest_basic,
        "acidic_groups": acidic,
        "basic_groups": basic,
    }


def _predict_bbb(mol, wlogp, tpsa, mw, rot, hbd, hba):
    """BBB permeability score (Clark's model + supplementary rules)."""
    score = 0.0
    if wlogp > 1 and wlogp < 4: score += 0.3
    elif wlogp >= 4: score += 0.15
    if tpsa < 60: score += 0.3
    elif tpsa < 90: score += 0.15
    if mw < 400: score += 0.2
    elif mw < 500: score += 0.1
    if hbd <= 1: score += 0.1
    if hba <= 6: score += 0.05
    if rot <= 5: score += 0.05
    # Nitrogen count penalty
    n_count = 0
    try:
        n_count = sum(1 for a in mol.GetAtoms() if a.GetSymbol() == "N")
    except Exception:
        pass
    if n_count > 3: score -= 0.2
    score = round(min(1.0, max(0.0, score)), 2)
    label = "High" if score >= 0.7 else ("Moderate" if score >= 0.4 else "Low")
    return {"score": score, "label": label}


def _predict_melting_point(mol, mw, rot):
    """Melting point via Joback group contribution (RDKit fragments)."""
    contributions = {
        "ring": 5.0, "methyl": -5.10, "methylene": 11.27,
        "hydroxyl": 44.45, "carbonyl": 61.20, "carboxyl": 155.50,
        "amino_primary": 66.85, "amino_secondary": 50.17, "nitro": 127.24,
        "ether": 22.42, "halogen": 15.0, "amide": 128.22,
        "sulfonamide": 140.0, "nitrile": 59.89,
    }
    mp = 122.5  # base melting point
    try:
        from rdkit import Chem
        fragments = {
            "ring": "[R]",
            "methyl": "[CH3]",
            "hydroxyl": "[OH]",
            "carbonyl": "[CX3](=O)[#6]",
            "carboxyl": "C(=O)O",
            "amino_primary": "[NH2]",
            "nitro": "[N+](=O)[O-]",
            "amide": "C(=O)N",
        }
        for name, smarts in fragments.items():
            n = _count_matches(mol, smarts)
            mp += contributions.get(name, 0) * n
    except Exception:
        pass
    mp += rot * 2.0
    return round(mp, 1)


def _compute_druglikeness_score(mol, mw, logp, hbd, hba, tpsa, rot, formula):
    """MolSoft-style drug-likeness score (0-1 continuous).
    Weighted composite of 6 rule-of-thumb filters + fragment penalties."""
    from rdkit import Chem
    score = 1.0
    violations = []
    if mw < 200 or mw > 650: score -= 0.15; violations.append("MW")
    if logp < -2 or logp > 6: score -= 0.12; violations.append("LogP")
    if hbd > 6: score -= 0.1; violations.append("HBD")
    if hba > 12: score -= 0.1; violations.append("HBA")
    if tpsa > 160: score -= 0.1; violations.append("TPSA")
    if rot > 12: score -= 0.08; violations.append("RotBonds")
    # Fragment penalties
    try:
        n_aromatic = sum(1 for a in mol.GetAtoms() if a.GetIsAromatic())
        if n_aromatic > 18: score -= 0.08; violations.append("aromatic>18")
        n_halogen = sum(1 for a in mol.GetAtoms() if a.GetSymbol() in ("F","Cl","Br","I"))
        if n_halogen > 4: score -= 0.05; violations.append("halogen>4")
    except Exception:
        pass
    score = round(max(0.0, score), 2)
    label = "Excellent" if score >= 0.9 else ("Good" if score >= 0.7 else ("Moderate" if score >= 0.5 else "Poor"))
    return {"score": score, "label": label, "violations": violations}


def _calc_lipinski(mw, logp, hbd, hba):
    rules = {"MW < 500": mw < 500, "LogP < 5": logp < 5, "HBD < 5": hbd < 5, "HBA < 10": hba < 10}
    v = sum(1 for p in rules.values() if not p)
    return {"passed": v <= 1, "violations": v, "rules": rules}


class DrugProperties(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        smiles = (input.get("smiles", "") or "").strip()
        preset = (input.get("preset", "") or "").strip()
        if preset and preset in DRUG_LIBRARY:
            smiles = DRUG_LIBRARY[preset]["smiles"]
        if not smiles:
            return {"error": "", "library": {k:v["name"] for k,v in DRUG_LIBRARY.items()}, "hint": "Enter a SMILES string or select a preset drug"}

        try:
            from rdkit import Chem
            from rdkit.Chem import Descriptors, Crippen, rdMolDescriptors
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return {"error": "Invalid SMILES string"}

            mw = round(Descriptors.MolWt(mol), 2)
            logp = round(Crippen.MolLogP(mol), 2)
            wlogp = logp
            hbd = Descriptors.NumHDonors(mol)
            hba = Descriptors.NumHAcceptors(mol)
            tpsa = round(Descriptors.TPSA(mol), 2)
            rot = Descriptors.NumRotatableBonds(mol)
            formula = rdMolDescriptors.CalcMolFormula(mol)

            # ── Extended Properties ──
            herg_risk, herg_alerts = _predict_herg(mol)
            ames_risk, ames_alerts = _predict_ames(mol)
            pka_data = _predict_pka(mol)
            bbb = _predict_bbb(mol, wlogp, tpsa, mw, rot, hbd, hba)
            mp = _predict_melting_point(mol, mw, rot)
            dl_score = _compute_druglikeness_score(mol, mw, logp, hbd, hba, tpsa, rot, formula)
            lipinski = _calc_lipinski(mw, logp, hbd, hba)

            result = {
                "smiles": smiles,
                "formula": formula,
                # Flat keys (frontend compat)
                "molecular_weight": mw, "logp": logp, "hbd": hbd, "hba": hba, "tpsa": tpsa,
                "rotatable_bonds": rot, "lipinski_pass": lipinski["passed"],
                # New extended properties
                "druglikeness_score": dl_score,
                "herg": {"risk": herg_risk, "alerts_triggered": herg_alerts, "alerts_total": len(HERG_ALERTS)},
                "ames": {"risk": ames_risk, "alerts_triggered": ames_alerts, "alerts_total": len(AMES_ALERTS)},
                "pka": pka_data,
                "bbb_permeability": bbb,
                "melting_point": mp,
                "lipinski": lipinski,
                "drug_likeness": "Pass" if lipinski["passed"] else "Fail",
                "properties": {
                    "molecular_weight": {"value": mw, "unit": "g/mol"},
                    "logp": {"value": logp, "unit": ""},
                    "h_bond_donors": {"value": hbd, "unit": ""},
                    "h_bond_acceptors": {"value": hba, "unit": ""},
                    "tpsa": {"value": tpsa, "unit": "Å²"},
                    "rotatable_bonds": {"value": rot, "unit": ""},
                    "melting_point": {"value": mp, "unit": "°C"},
                },
            }
            # Auto-store to Knowledge Base
            name = preset or smiles[:30]
            _kb_store(f"Drug Properties — {name}", result, ["drug_properties", formula])
            return result
        except ImportError:
            return {"error": "RDKit not available"}
        except Exception as e:
            import logging; logging.getLogger("drug_properties").warning(f"Failed: {e}")
            return {"error": str(e)}
