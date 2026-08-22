"""Route Utilities — scoring, ranking, complexity estimation, serialization."""
import logging
from typing import Dict, List

from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors

log = logging.getLogger("retrosynthesis.routes")


def estimate_complexity(smiles: str) -> Dict:
    """Estimate synthetic complexity of a molecule (Bertz/SA score inspired).

    Returns a score from 1 (trivial) to 10 (very complex).
    Factors: rings, stereocenters, heteroatoms, molecular weight, sp3 fraction.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"error": "Invalid SMILES", "score": 0}

    mw = Descriptors.MolWt(mol)
    num_rings = rdMolDescriptors.CalcNumRings(mol)
    num_stereo = rdMolDescriptors.CalcNumAtomStereoCenters(mol)
    num_hetero = rdMolDescriptors.CalcNumHeteroatoms(mol)
    num_rotatable = rdMolDescriptors.CalcNumRotatableBonds(mol)
    num_atoms = mol.GetNumHeavyAtoms()
    fsp3 = rdMolDescriptors.CalcFractionCSP3(mol)

    score = 1.0
    score += min(num_rings * 0.8, 4.0)
    score += min(num_stereo * 1.2, 3.0)
    score += min(num_hetero * 0.15, 1.5)
    score += min(mw / 200.0, 2.0)
    score += min(num_rotatable * 0.1, 1.0)
    if fsp3 > 0.5:
        score += 0.5

    score = min(10.0, max(1.0, score))

    difficulty = "trivial"
    if score >= 7:
        difficulty = "very complex"
    elif score >= 5:
        difficulty = "moderate"
    elif score >= 3:
        difficulty = "straightforward"

    return {
        "smiles": Chem.MolToSmiles(mol),
        "complexity_score": round(score, 1),
        "difficulty": difficulty,
        "factors": {
            "rings": num_rings,
            "stereocenters": num_stereo,
            "heteroatoms": num_hetero,
            "rotatable_bonds": num_rotatable,
            "molecular_weight": round(mw, 1),
            "fraction_sp3": round(fsp3, 2),
            "heavy_atoms": num_atoms,
        },
    }


def rank_routes(routes: List[Dict]) -> List[Dict]:
    """Rank synthesis routes by desirability.

    Criteria (weighted):
      - Fewer steps preferred (40%)
      - All purchasable building blocks (30%)
      - Higher average reliability (30%)
    """
    for route in routes:
        steps = route.get("num_steps", 99)
        purchasable = 1.0 if route.get("all_purchasable") else 0.0
        reliability = route.get("first_step", {}).get("reliability", 0.5)

        step_score = max(0, 1.0 - (steps - 1) * 0.2)
        route["rank_score"] = round(
            step_score * 0.4 + purchasable * 0.3 + reliability * 0.3, 3
        )

    routes.sort(key=lambda r: r["rank_score"], reverse=True)
    for i, route in enumerate(routes):
        route["rank"] = i + 1
    return routes


def route_to_dict(route: Dict, flat: bool = False) -> Dict:
    """Convert a route tree to a serializable dict.

    If flat=True, flatten into a linear list of steps (for simple display).
    """
    if not flat:
        return route

    steps = []
    _flatten_route(route, steps, step_num=1)
    return {"steps": steps, "total_steps": len(steps)}


def _flatten_route(node: Dict, steps: List, step_num: int) -> int:
    """Recursively flatten route tree into ordered steps list."""
    if not node or node.get("purchasable"):
        return step_num

    precursors = node.get("precursors", [])
    for child in precursors:
        step_num = _flatten_route(child, steps, step_num)

    first_step = node.get("first_step") or node
    reactants = [p.get("smiles", "?") for p in precursors] if precursors else []

    steps.append({
        "step": step_num,
        "reaction": first_step.get("reaction", node.get("reaction", "Unknown")),
        "reagents": first_step.get("reagents", node.get("reagents", [])),
        "conditions": first_step.get("conditions", node.get("conditions", "")),
        "reactants": reactants,
        "product": node.get("smiles", node.get("target", "?")),
        "reliability": first_step.get("reliability", node.get("reliability", 0.0)),
    })
    return step_num + 1
