"""Impurity / Degradation Prediction — ICH Q1A-aligned stress-degradation rules.

SMARTS rule base covering hydrolysis, oxidation, photolysis, dehydration,
dimerization, decarboxylation and rearrangement susceptibilities common in
pharma stress studies. Screening-level: flags likely degradants with
plausible structures where a transform can be applied.
"""
import logging
from typing import Dict, List

try:
    from rdkit import Chem
    from rdkit.Chem import AllChem, Descriptors
    from rdkit import RDLogger
    HAS_RDKIT = True
except ImportError:
    HAS_RDKIT = False
    Chem = None

log = logging.getLogger("reaction_lab.impurity")

# Each rule: name, condition (ICH stress type), susceptibility SMARTS, optional transform.
DEGRADATION_RULES = [
    {"name": "Ester hydrolysis", "condition": "acid/base + water (hydrolytic)",
     "smarts": "[CX3](=O)[OX2][#6]", "transform": "C(=O)O[C:1]>>C(=O)O.[H][C:1]"},
    {"name": "Amide hydrolysis", "condition": "strong acid/base (hydrolytic)",
     "smarts": "[CX3](=O)[NX3]", "transform": "C(=O)[NX3:1]>>C(=O)O.[NX3:1]"},
    {"name": "Lactone ring opening", "condition": "base (hydrolytic)",
     "smarts": "[CX3](=O)[OX2][CX4]", "transform": None},
    {"name": "Benzylic oxidation", "condition": "oxidative (H2O2, AIBN)",
     "smarts": "[c][CH2,CH3]", "transform": "[c][CH2:1]>>[c][CH2][OX2H]"},
    {"name": "Thioether → sulfoxide", "condition": "oxidative",
     "smarts": "[#6][SX2][#6]", "transform": "[#6][S;X2:1][#6]>>[#6][S(=O)][#6]"},
    {"name": "Aromatic amine oxidation", "condition": "oxidative / photolytic",
     "smarts": "[c][NX2H2]", "transform": None},
    {"name": "Nitroaromatic impurity risk", "condition": "photolytic / reductive",
     "smarts": "[c][N+](=O)[O-]", "transform": None},
    {"name": "Phenol oxidation (quinone)", "condition": "oxidative",
     "smarts": "c[OX2H]c", "transform": None},
    {"name": "Aldehyde → acid (autoxidation)", "condition": "oxidative (air)",
     "smarts": "[CX3H1](=O)[#6]", "transform": "[CX3H1:1](=O)>>[CX3:1](=O)[OX2H]"},
    {"name": "Primary alcohol → aldehyde", "condition": "oxidative",
     "smarts": "[#6][CH2][OX2H]", "transform": None},
    {"name": "Dehydration (β-hydroxy)", "condition": "acid / heat",
     "smarts": "[#6][CH1]([OX2H])[CH2]", "transform": "[CH1:1]([OX2H])[CH2:2]>>[CH1:1]=[CH2:2]"},
    {"name": "Decarboxylation risk", "condition": "heat",
     "smarts": "[#6][CX3](=O)[OX2H]", "transform": None},
    {"name": "Michael acceptor dimerization", "condition": "pH stress",
     "smarts": "[CX3]=[CX3][CX3]=[CX3]", "transform": None},
    {"name": "Imine hydrolysis", "condition": "acid + water",
     "smarts": "[CX3]=[NX2]", "transform": "[CX3:1]=[NX2:2]>>[CX3:1]=O.[NX2H2:2]"},
    {"name": "Acetal hydrolysis", "condition": "acid + water",
     "smarts": "[CX4]([OX2][#6])([OX2][#6])", "transform": None},
    {"name": "N-oxide formation (tertiary amine)", "condition": "oxidative",
     "smarts": "[NX3;!$(N[C=O]);!$(N*=[*])]", "transform": "[NX3;H0:1]([#6])([#6])[#6]>>[NX4+:1]([O-])([#6])([#6])[#6]"},
]


def predict_impurities(smiles, conditions: List[str] = None) -> Dict:
    """Flag degradation susceptibilities; generate plausible degradant structures."""
    if not HAS_RDKIT:
        return {"status": "error", "error": "RDKit is required for impurity prediction"}
    if isinstance(smiles, list):
        smiles = ".".join(smiles)
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"error": f"Invalid SMILES: {smiles}"}
    conditions = [c.lower() for c in (conditions or [])]

    RDLogger.DisableLog("rdApp.warning")

    findings = []
    for rule in DEGRADATION_RULES:
        patt = Chem.MolFromSmarts(rule["smarts"])
        if patt is None:
            continue
        matches = mol.GetSubstructMatches(patt)
        if not matches:
            continue
        if conditions and not any(c in rule["condition"].lower() for c in conditions):
            continue

        entry = {
            "impurity": rule["name"],
            "condition": rule["condition"],
            "sites": len(matches),
            "site_atoms_1based": sorted({a + 1 for m in matches[:5] for a in m})[:12],
        }
        # try to draw an actual degradant
        degradants = []
        if rule.get("transform"):
            try:
                from rdkit.Chem import rdChemReactions
                rxn = rdChemReactions.ReactionFromSmarts(rule["transform"])
                outcomes = rxn.RunReactants((mol,))
                seen = set()
                for outcome in outcomes[:4]:
                    for pm in outcome:
                        try:
                            Chem.SanitizeMol(pm)
                            smi = Chem.MolToSmiles(pm)
                            if smi not in seen:
                                seen.add(smi)
                                degradants.append(smi)
                        except Exception:
                            continue
            except Exception as e:
                log.debug("transform failed for %s: %s", rule["name"], e)
        entry["predicted_degradants"] = degradants[:4]
        findings.append(entry)

    risk_score = min(100, sum(10 + 5 * f["sites"] for f in findings))
    return {
        "smiles": Chem.MolToSmiles(mol),
        "num_findings": len(findings),
        "findings": findings,
        "degradation_risk_score": risk_score,
        "risk_level": "high" if risk_score >= 60 else ("moderate" if risk_score >= 30 else "low"),
        "ich_context": "ICH Q1A(R2) stress testing: hydrolysis (acid/base), oxidation, photolysis, thermal. "
                       "Screening-level SMARTS rules — confirm with forced-degradation studies.",
    }
