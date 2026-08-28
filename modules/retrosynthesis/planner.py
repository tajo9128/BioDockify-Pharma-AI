"""Retrosynthesis Planner — iterative disconnection to purchasable building blocks.

Strategy:
1. BRICS disconnection (RDKit) — identifies retrosynthetically valid bonds
2. Reaction template matching — applies known retro-transforms
3. Building block lookup — checks if fragments are commercially available
4. Recursive planning — decomposes non-purchasable intermediates further

Output: a tree of synthesis routes with steps, reagents, and conditions.
"""
import logging
import re
from typing import Dict, List, Optional, Set, Tuple

try:
    from rdkit import Chem
    from rdkit.Chem import BRICS, Descriptors, rdMolDescriptors, AllChem
    from rdkit.Chem.Scaffolds import MurckoScaffold
    HAS_RDKIT = True
except ImportError:
    HAS_RDKIT = False
    Chem = None

from .reactions import REACTION_TEMPLATES, reverse_reaction

log = logging.getLogger("retrosynthesis.planner")

PURCHASABLE_MW_CUTOFF = 300.0
MAX_RECURSION_DEPTH = 4
MAX_ROUTES = 5

COMMON_BUILDING_BLOCKS: Set[str] = {
    "c1ccccc1", "c1ccncc1", "c1ccoc1", "c1ccsc1", "c1cc[nH]c1",
    "c1ccc(N)cc1", "c1ccc(O)cc1", "c1ccc(F)cc1", "c1ccc(Cl)cc1",
    "c1ccc(Br)cc1", "c1ccc(C)cc1", "c1ccc(OC)cc1",
    "CC(=O)O", "CC(N)C(=O)O", "CCCO", "CCO", "CO",
    "CC=O", "CCC=O", "c1ccc(C=O)cc1",
    "CC(=O)Cl", "ClCCCl", "BrCCBr",
    "OB(O)c1ccccc1", "OB(O)c1ccncc1",
    "NCC", "NCCN", "NCCO", "C1CCNCC1", "C1CCOCC1",
    "CC(C)(C)OC(=O)Cl", "O=C=O",
    "FC(F)(F)c1ccccc1", "Cc1ccccc1", "OCc1ccccc1",
}


def _is_purchasable(smiles: str) -> bool:
    """Heuristic: fragment is likely commercially available."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return False
    if any(atom.GetAtomicNum() == 0 for atom in mol.GetAtoms()):
        return False  # BRICS dummy-atom fragments are not real purchasable molecules
    mw = Descriptors.MolWt(mol)
    if mw > PURCHASABLE_MW_CUTOFF:
        return False
    if mw < 50:
        return True
    canonical = Chem.MolToSmiles(mol)
    if canonical in COMMON_BUILDING_BLOCKS:
        return True
    num_atoms = mol.GetNumHeavyAtoms()
    if num_atoms <= 6:
        return True
    num_rings = rdMolDescriptors.CalcNumRings(mol)
    if num_rings <= 1 and num_atoms <= 12:
        return True
    return False


def _brics_disconnection(smiles: str) -> List[Dict]:
    """BRICS-based bond disconnection — returns possible fragment sets."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return []
    try:
        fragments = list(BRICS.BRICSDecompose(mol, minFragmentSize=3))
    except Exception:
        return []
    if not fragments or len(fragments) < 2:
        return []
    clean_frags = []
    for f in fragments:
        clean = Chem.MolFromSmiles(f)
        if clean:
            clean_smi = Chem.MolToSmiles(clean)
            # cap ALL BRICS attachment points ([1*]..[16*]) with H to get real molecules
            clean_smi = re.sub(r"\[\d+\*\]", "[H]", clean_smi)
            remol = Chem.MolFromSmiles(clean_smi)
            if remol:
                clean_frags.append(Chem.MolToSmiles(remol))
    if len(clean_frags) < 2:
        return []
    return [{"fragments": clean_frags, "method": "BRICS disconnection"}]


def _template_disconnection(smiles: str) -> List[Dict]:
    """Apply retro-synthetic templates to find disconnections."""
    results = []
    for template in REACTION_TEMPLATES:
        retro_smarts = template.get("retro_smarts", "")
        if not retro_smarts:
            continue
        reactant_sets = reverse_reaction(retro_smarts, smiles)
        for reactants in reactant_sets:
            if len(reactants) >= 2:
                results.append({
                    "fragments": reactants,
                    "method": template["name"],
                    "reagents": template["reagents"],
                    "conditions": template["conditions"],
                    "reliability": template["reliability"],
                })
    results.sort(key=lambda x: x.get("reliability", 0), reverse=True)
    return results[:8]


def disconnection_analysis(smiles: str) -> Dict:
    """Analyze a molecule for possible disconnections (single step).

    Returns all possible ways to disconnect the molecule with reaction details.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"error": "Invalid SMILES"}

    canonical = Chem.MolToSmiles(mol)
    mw = Descriptors.MolWt(mol)

    brics_results = _brics_disconnection(canonical)
    template_results = _template_disconnection(canonical)

    all_disconnections = template_results + brics_results

    return {
        "target": canonical,
        "molecular_weight": round(mw, 1),
        "num_disconnections": len(all_disconnections),
        "disconnections": all_disconnections[:10],
        "is_purchasable": _is_purchasable(canonical),
    }


def _plan_recursive(smiles: str, depth: int, visited: Set[str], max_depth: int) -> Optional[Dict]:
    """Recursively plan synthesis for a molecule."""
    if depth > max_depth:
        return {"smiles": smiles, "purchasable": False, "note": "max depth reached"}
    if smiles in visited:
        return {"smiles": smiles, "purchasable": False, "note": "circular reference"}
    visited.add(smiles)

    if _is_purchasable(smiles):
        return {"smiles": smiles, "purchasable": True}

    template_results = _template_disconnection(smiles)
    brics_results = _brics_disconnection(smiles)
    all_options = template_results + brics_results

    if not all_options:
        return {"smiles": smiles, "purchasable": False, "note": "no disconnection found"}

    best = all_options[0]
    children = []
    for frag in best["fragments"]:
        child = _plan_recursive(frag, depth + 1, visited.copy(), max_depth)
        children.append(child)

    return {
        "smiles": smiles,
        "purchasable": False,
        "reaction": best.get("method", "BRICS"),
        "reagents": best.get("reagents", []),
        "conditions": best.get("conditions", ""),
        "reliability": best.get("reliability", 0.7),
        "precursors": children,
    }


def plan_synthesis(smiles: str, max_routes: int = 3, max_depth: int = MAX_RECURSION_DEPTH) -> Dict:
    """Plan complete synthesis routes from purchasable building blocks."""
    if not HAS_RDKIT:
        return {"status": "error", "error": "RDKit is required for retrosynthesis planning"}
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"error": "Invalid SMILES"}

    canonical = Chem.MolToSmiles(mol)
    mw = Descriptors.MolWt(mol)
    num_atoms = mol.GetNumHeavyAtoms()

    if _is_purchasable(canonical):
        return {
            "target": canonical,
            "molecular_weight": round(mw, 1),
            "message": "Target is commercially available — no synthesis needed.",
            "routes": [],
            "num_routes": 0,
        }

    template_results = _template_disconnection(canonical)
    brics_results = _brics_disconnection(canonical)
    all_options = (template_results + brics_results)[:max_routes]

    routes = []
    for i, option in enumerate(all_options):
        visited: Set[str] = {canonical}
        precursors = []
        all_purchasable = True
        for frag in option["fragments"]:
            child = _plan_recursive(frag, 1, visited.copy(), max_depth)
            precursors.append(child)
            if child and not child.get("purchasable", False):
                all_purchasable = False

        route = {
            "route_id": i + 1,
            "first_step": {
                "reaction": option.get("method", "BRICS"),
                "reagents": option.get("reagents", []),
                "conditions": option.get("conditions", ""),
                "reliability": option.get("reliability", 0.7),
            },
            "precursors": precursors,
            "all_purchasable": all_purchasable,
            "num_steps": _count_steps(precursors),
        }
        routes.append(route)

    routes.sort(key=lambda r: (-r["all_purchasable"], r["num_steps"]))

    return {
        "target": canonical,
        "molecular_weight": round(mw, 1),
        "num_heavy_atoms": num_atoms,
        "num_routes": len(routes),
        "routes": routes[:max_routes],
    }


def _count_steps(precursors: List) -> int:
    """Count total steps in a route tree."""
    total = 0
    for p in precursors:
        if not p:
            continue
        if not p.get("purchasable", False):
            total += 1
            children = p.get("precursors", [])
            if children:
                total += _count_steps(children)
    return total + 1


def find_building_blocks(smiles: str) -> Dict:
    """Find all purchasable building blocks needed for a target molecule."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"error": "Invalid SMILES"}

    canonical = Chem.MolToSmiles(mol)
    result = plan_synthesis(canonical, max_routes=1)

    blocks = set()
    _collect_blocks(result.get("routes", [{}])[0] if result.get("routes") else {}, blocks)

    return {
        "target": canonical,
        "building_blocks": [
            {"smiles": b, "purchasable": True, "mw": round(Descriptors.MolWt(Chem.MolFromSmiles(b)), 1)}
            for b in blocks if Chem.MolFromSmiles(b)
        ],
        "num_blocks": len(blocks),
    }


def _collect_blocks(node: Dict, blocks: Set[str]):
    """Recursively collect purchasable leaves from a route tree."""
    if not node:
        return
    if node.get("purchasable"):
        blocks.add(node["smiles"])
    for child in node.get("precursors", []):
        _collect_blocks(child, blocks)
