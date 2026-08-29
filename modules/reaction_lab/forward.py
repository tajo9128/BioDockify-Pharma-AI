"""Forward Reaction Executor — apply named reaction templates to reactants.

Reuses the 12 curated templates from modules/retrosynthesis/reactions.py
(amide coupling, Suzuki, reductive amination, Buchwald, SNAr, ...) plus
supports arbitrary reaction SMARTS. Combinatorial enumeration supported.
"""
import logging
from typing import Dict, List

from rdkit import Chem
from rdkit.Chem import rdChemReactions

from ..retrosynthesis.reactions import REACTION_TEMPLATES

log = logging.getLogger("reaction_lab.forward")


def list_reactions() -> List[Dict]:
    return [
        {"name": t["name"], "category": t["category"], "reagents": t["reagents"],
         "conditions": t["conditions"], "reliability": t["reliability"],
         "example": t.get("example", "")}
        for t in REACTION_TEMPLATES
    ]


def run_forward(reaction_name: str, reactants: List[str]) -> Dict:
    """Apply a named template to a list of reactant SMILES."""
    template = next((t for t in REACTION_TEMPLATES if t["name"].lower() == reaction_name.lower()), None)
    if template is None:
        return {"error": f"Unknown reaction '{reaction_name}'. Use list_reactions / templates."}
    return _apply_smarts(template["forward_smarts"], reactants,
                         name=template["name"], reagents=template["reagents"],
                         conditions=template["conditions"], reliability=template["reliability"])


def run_smarts(reaction_smarts: str, reactants: List[str]) -> Dict:
    """Apply arbitrary reaction SMARTS ('reactants>>product')."""
    if ">>" not in reaction_smarts:
        return {"error": "reaction_smarts must contain '>>'"}
    return _apply_smarts(reaction_smarts, reactants, name="custom SMARTS")


def _apply_smarts(smarts: str, reactants: List[str], name: str = "",
                  reagents=None, conditions: str = "", reliability=None) -> Dict:
    if not reactants or not isinstance(reactants, list):
        return {"error": "reactants required (list of SMILES)"}
    try:
        rxn = rdChemReactions.ReactionFromSmarts(smarts)
        if rxn is None:
            return {"error": "Invalid reaction SMARTS"}
    except Exception as e:
        return {"error": f"SMARTS parse failed: {e}"}

    mols = []
    for smi in reactants:
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            return {"error": f"Invalid reactant SMILES: {smi}"}
        mols.append(Chem.AddHs(mol))  # templates use explicit [H] in patterns

    # try the whole list as one reactant set; if template expects fewer reactants,
    # try the first N in order.
    expected = rxn.GetNumReactantTemplates()
    if len(mols) < expected:
        return {"error": f"Reaction expects {expected} reactants, got {len(mols)}"}

    products = []
    tried_sets = []
    if len(mols) == expected:
        tried_sets.append(mols)
    else:
        # greedy: first 'expected' mols, plus best-effort singles if 1-template
        tried_sets.append(mols[:expected])

    for molset in tried_sets:
        try:
            outcomes = rxn.RunReactants(tuple(molset))
        except Exception as e:
            return {"error": f"Reaction execution failed: {e}"}
        seen = set()
        for outcome in outcomes:
            for pm in outcome:
                try:
                    Chem.SanitizeMol(pm)
                    pm = Chem.RemoveHs(pm)
                    Chem.SanitizeMol(pm)
                    smi = Chem.MolToSmiles(pm)
                except Exception:
                    continue
                if smi not in seen:
                    seen.add(smi)
                    products.append({"smiles": smi, "molblock": Chem.MolToMolBlock(pm)})

    result = {
        "reaction": name or smarts,
        "reactants": reactants,
        "num_products": len(products),
        "products": products[:50],
    }
    if reagents:
        result["reagents"] = reagents
    if conditions:
        result["conditions"] = conditions
    if reliability is not None:
        result["reliability"] = reliability
    if not products:
        result["note"] = "No products formed — reactants may not match the template pattern."
    return result


def enumerate_library(reaction_name: str, building_block_sets: List[List[str]], max_products: int = 200) -> Dict:
    """Combinatorial enumeration: one SMILES list per reactant slot."""
    template = next((t for t in REACTION_TEMPLATES if t["name"].lower() == reaction_name.lower()), None)
    if template is None:
        return {"error": f"Unknown reaction '{reaction_name}'"}
    if not building_block_sets:
        return {"error": "building_block_sets required (list of SMILES lists)"}

    import itertools
    rxn = rdChemReactions.ReactionFromSmarts(template["forward_smarts"])
    expected = rxn.GetNumReactantTemplates()
    if len(building_block_sets) != expected:
        return {"error": f"Reaction expects {expected} reactant slots, got {len(building_block_sets)}"}

    combos = list(itertools.product(*building_block_sets))
    products, seen = [], set()
    for combo in combos:
        mols = [Chem.AddHs(Chem.MolFromSmiles(s)) for s in combo]
        if any(m is None for m in mols):
            continue
        try:
            outcomes = rxn.RunReactants(tuple(mols))
        except Exception:
            continue
        for outcome in outcomes:
            for pm in outcome:
                try:
                    Chem.SanitizeMol(pm)
                    pm = Chem.RemoveHs(pm)
                    Chem.SanitizeMol(pm)
                    smi = Chem.MolToSmiles(pm)
                except Exception:
                    continue
                if smi not in seen:
                    seen.add(smi)
                    products.append({"smiles": smi, "from": list(combo)})
                    if len(products) >= max_products:
                        return {"reaction": template["name"], "num_combinations": len(combos),
                                "num_products": len(products), "products": products,
                                "truncated": True,
                                "reagents": template["reagents"], "conditions": template["conditions"]}
    return {"reaction": template["name"], "num_combinations": len(combos),
            "num_products": len(products), "products": products,
            "reagents": template["reagents"], "conditions": template["conditions"]}
