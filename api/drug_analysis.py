"""Enhanced Drug Analysis API — PAINS, Brenk, NIH substructure filters for drug-likeness."""
from helpers.api import ApiHandler, Request, Response
import logging

log = logging.getLogger("drug_analysis")

# PAINS substructures (Pan-Assay Interference Compounds) — SMARTS patterns
PAINS_SMARTS = {
    "ene_rhodanine": "[#6]-1-[#6](=[#8])-[#7]-[#16]-[#6]-1=[#16]",
    "anil_di_alk": "c1ccccc1-[#7](-[#6])-[#6]",
    "pyrrole_imine": "[#7]1-[#6]=[#6]-[#6](=[#6]1-[#6])-[#6]",
    "quinone_A": "[#6]1([#6](=[#8])[#6](=[#6]1[#6])[#6])=[#8]",
    "catechol_A": "c1(c(c(ccc1)-[#8])-[#8])-[#8]",
    "mannich_A": "[#7](-[#6])-[#6]-[#6]-[#7]",
    "hzone_phenol_A": "[#8]-c1ccc(cc1)-[#6]=[#7]-[#7]",
    "furan_carboxyl_A": "[#8]1-[#6]=[#6]-[#6](=[#8])-[#6]1=[#6]",
}

# Brenk unwanted fragments (toxicity/reactive groups) — SMARTS
BRENK_SMARTS = {
    "nitro": "[#7](=[#8])-[#8]",
    "sulfonyl_chloride": "[#16](=[#8])(=[#8])-[#17]",
    "acid_halide": "[#6](=[#8])-[#17,#35,#53]",
    "azide": "[#7]-[#7]#[#7]",
    "isocyanate": "[#7]=[#6]=[#8]",
    "peroxide": "[#8]-[#8]",
    "poly_halu": "[#17,#35,#53]-[#6](-[#17,#35,#53])-[#17,#35,#53]",
    "epoxide": "[#6]1-[#8]-[#6]1",
    "aldehyde": "[#6](=[#8])-[#1]",
    "bromo_aryl": "c[#35]",
}

# NIH unwanted substructures
NIH_SMARTS = {
    "alkyl_halide": "[#6]-[#17,#35,#53]",
    "anhydride": "[#6](=[#8])-[#8]-[#6](=[#8])",
    "oxime": "[#6]=[#7]-[#8]",
    "diazo": "[#6]=[#7]=[#7]",
    "sulfonate": "[#8]-[#16](=[#8])(=[#8])",
    "acyl_hydrazine": "[#6](=[#8])-[#7]-[#7]",
    "thioamide": "[#6](=[#16])-[#7]",
    "alpha_halo_carbonyl": "[#17,#35,#53]-[#6]-[#6](=[#8])",
}


def _check_smarts(smiles: str, patterns: dict):
    from rdkit import Chem
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return []
    flagged = []
    for name, smarts in patterns.items():
        pat = Chem.MolFromSmarts(smarts)
        if pat is not None and mol.HasSubstructMatch(pat):
            flagged.append(name)
    return flagged


class DrugAnalysisHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "check")

        if action == "check":
            smiles = input.get("smiles", "")
            if not smiles:
                return {"success": False, "error": "SMILES required"}

            try:
                pains = _check_smarts(smiles, PAINS_SMARTS)
                brenk = _check_smarts(smiles, BRENK_SMARTS)
                nih = _check_smarts(smiles, NIH_SMARTS)

                return {
                    "success": True,
                    "smiles": smiles,
                    "pains_flagged": pains,
                    "pains_pass": len(pains) == 0,
                    "pains_count": len(pains),
                    "brenk_flagged": brenk,
                    "brenk_pass": len(brenk) == 0,
                    "brenk_count": len(brenk),
                    "nih_flagged": nih,
                    "nih_pass": len(nih) == 0,
                    "nih_count": len(nih),
                    "overall_pass": len(pains) == 0 and len(brenk) == 0 and len(nih) == 0,
                }
            except ImportError:
                return {"success": False, "error": "RDKit not available"}
            except Exception as e:
                return {"success": False, "error": str(e)}

        if action == "filters":
            return {
                "pains": {k: v for k, v in PAINS_SMARTS.items()},
                "brenk": {k: v for k, v in BRENK_SMARTS.items()},
                "nih": {k: v for k, v in NIH_SMARTS.items()},
            }

        return {"error": f"Unknown action: {action}"}
