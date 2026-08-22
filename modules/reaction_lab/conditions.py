"""Condition Recommendation — reaction lookup by class/functional group.

Recommends reagent systems, solvents, temperatures and workups from the
curated template database plus a functional-group decision table.
"""
import logging
from typing import Dict, List

from rdkit import Chem

from ..retrosynthesis.reactions import REACTION_TEMPLATES

log = logging.getLogger("reaction_lab.conditions")

# functional-group → recommended reaction conditions decision table
FG_TABLE = [
    {"group": "carboxylic acid + amine (amide)", "smarts_a": "[CX3](=O)[OX2H]", "smarts_b": "[NX3;H2,H1;!$(N[CX3]=O)]",
     "reaction": "Amide Coupling", "recommendation": "HATU (1.1 eq) + DIPEA (2-3 eq) in DMF, RT, 2-12 h; or EDCI/HOBt"},
    {"group": "aryl bromide + boronic acid", "smarts_a": "[c][Br]", "smarts_b": "[c][B](O)O",
     "reaction": "Suzuki Coupling", "recommendation": "Pd(dppf)Cl2 (2-5 mol%), K2CO3 (2 eq), dioxane/H2O 4:1, 80°C, N2, 4-16 h"},
    {"group": "aryl chloride + amine", "smarts_a": "[c][Cl]", "smarts_b": "[NX3;H1,H2]",
     "reaction": "Buchwald-Hartwig", "recommendation": "Pd2(dba)3 (1-2 mol%) + BrettPhos (4 mol%), NaOtBu, toluene or dioxane, 100°C, N2"},
    {"group": "aldehyde/ketone + amine", "smarts_a": "[CX3]=[OX1]", "smarts_b": "[NX3;H1,H2]",
     "reaction": "Reductive Amination", "recommendation": "NaBH(OAc)3 (1.5 eq), AcOH cat., DCE or MeOH, RT, 4-24 h"},
    {"group": "aryl fluoride + amine (SNAr)", "smarts_a": "[c][F]", "smarts_b": "[NX3;H2]",
     "reaction": "SNAr", "recommendation": "K2CO3 or DIPEA, DMF/DMSO, 60-100°C"},
    {"group": "alcohol activation", "smarts_a": "[#6][OX2H]", "smarts_b": None,
     "reaction": "Mitsunobu / Mesylation", "recommendation": "MsCl + Et3N, DCM, 0°C→RT (mesylate); or PPh3/DIAD (Mitsunobu)"},
]


def recommend_conditions(reactant_smiles: List[str]) -> Dict:
    if not reactant_smiles:
        return {"error": "reactant_smiles (list) required"}
    mols = []
    for smi in reactant_smiles:
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            return {"error": f"Invalid SMILES: {smi}"}
        mols.append(mol)

    matches = []
    for row in FG_TABLE:
        pa = Chem.MolFromSmarts(row["smarts_a"])
        pb = Chem.MolFromSmarts(row["smarts_b"]) if row["smarts_b"] else None
        has_a = any(m.HasSubstructMatch(pa) for m in mols)
        has_b = all(m.HasSubstructMatch(pb) for m in mols) if pb else True
        if has_a and (has_b or pb is None):
            matches.append({
                "detected": row["group"],
                "reaction": row["reaction"],
                "recommendation": row["recommendation"],
            })

    # also surface any named template matching these reactants
    from .forward import run_forward
    template_suggestions = []
    for t in REACTION_TEMPLATES:
        r = run_forward(t["name"], reactant_smiles)
        if isinstance(r, dict) and r.get("num_products", 0) > 0:
            template_suggestions.append({
                "reaction": t["name"],
                "example_product": r["products"][0]["smiles"],
                "reagents": t["reagents"], "conditions": t["conditions"],
            })

    return {
        "reactants": reactant_smiles,
        "condition_matches": matches,
        "productive_reactions": template_suggestions[:8],
        "note": "Curated med-chem conditions. Verify against literature (Reaxys/SciFinder) before execution.",
    }
