"""Scaffold extraction, hopping, and R-group analysis using RDKit Murcko scaffolds."""
import logging
from typing import Dict, List, Optional
from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold
from rdkit.Chem import BRICS

log = logging.getLogger("generative_chemistry.scaffolds")


def extract_scaffold(smiles: str) -> Optional[str]:
    """Extract the Murcko scaffold from a molecule."""
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        scaffold = MurckoScaffold.MurckoScaffoldSmiles(mol=mol)
        return scaffold if scaffold else None
    except Exception:
        return None


def extract_scaffolds(seed_smiles: List[str]) -> List[Dict]:
    """Extract all unique scaffolds from a list of molecules.

    Returns list of dicts with scaffold SMILES, count, and source molecules.
    """
    scaffold_map = {}

    for smi in seed_smiles:
        scaffold = extract_scaffold(smi)
        if not scaffold:
            continue
        if scaffold not in scaffold_map:
            scaffold_map[scaffold] = {
                "scaffold": scaffold,
                "count": 0,
                "sources": [],
            }
        scaffold_map[scaffold]["count"] += 1
        scaffold_map[scaffold]["sources"].append(smi)

    scaffolds = sorted(scaffold_map.values(), key=lambda x: x["count"], reverse=True)
    return scaffolds


def scaffold_hop(smiles: str, n_hops: int = 10) -> List[Dict]:
    """Find alternative scaffolds for a molecule (scaffold hopping).

    Generates molecules with similar properties but different core scaffolds.
    Uses bioisosteric scaffold replacements common in medicinal chemistry.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return []

    original_scaffold = extract_scaffold(smiles)
    if not original_scaffold:
        return []

    # Common scaffold bioisosteres (ring replacements)
    scaffold_replacements = {
        "c1ccccc1": ["c1ccncc1", "c1cccnc1", "c1cc(F)ccc1", "c1cc(Cl)ccc1",
                     "C1CCCCC1", "c1cc2ccccc2cc1", "c1cc[nH]c1"],
        "c1ccncc1": ["c1ccccc1", "c1cccnc1", "c1cc[nH]c1", "C1CCNCC1"],
        "C1CCCCC1": ["c1ccccc1", "C1CCC(F)CC1", "C1CCC(Cl)CC1"],
        "c1ccnc c1": ["c1ccncc1", "c1ccccc1"],
        "c1cc2[nH]ccc2cc1": ["c1cc2ccccc2cc1", "c1ccc2[nH]ccc2c1"],
        "C(=O)N": ["S(=O)(=O)N", "c1nn[nH]n1"],
        "C(=O)O": ["C(=O)N", "S(=O)(=O)O", "P(=O)(O)O"],
    }

    hops = []
    for old, replacements in scaffold_replacements.items():
        if old in original_scaffold:
            for new in replacements:
                hopped_smiles = original_scaffold.replace(old, new, 1)
                try:
                    mol = Chem.MolFromSmiles(hopped_smiles)
                    if mol is not None:
                        hops.append({
                            "smiles": Chem.MolToSmiles(mol),
                            "original_scaffold": original_scaffold,
                            "new_scaffold": extract_scaffold(hopped_smiles),
                            "replacement": f"{old} → {new}",
                            "method": "scaffold_hop",
                        })
                except Exception:
                    continue

    return hops[:n_hops]


def get_r_groups(smiles: str) -> List[Dict]:
    """Analyze R-groups (substituents) on a molecule's scaffold.

    Decomposes the molecule into scaffold + R-groups for SAR analysis.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return []

    scaffold = extract_scaffold(smiles)
    if not scaffold:
        return []

    # Use BRICS to find the fragments that differ from the scaffold
    try:
        frags = list(BRICS.BRICSDecompose(mol, minFragmentSize=3))
    except Exception:
        frags = []

    r_groups = []
    for frag in frags:
        # If fragment is not part of the scaffold, it's an R-group
        if frag and frag not in scaffold:
            try:
                frag_mol = Chem.MolFromSmiles(frag)
                if frag_mol is not None and frag_mol.GetNumAtoms() >= 1:
                    r_groups.append({
                        "fragment": frag,
                        "n_atoms": frag_mol.GetNumAtoms(),
                        "type": _classify_fragment(frag),
                    })
            except Exception:
                continue

    return r_groups


def _classify_fragment(frag: str) -> str:
    """Classify a fragment by its medicinal chemistry role."""
    frag_lower = frag.lower()

    if any(x in frag for x in ["F", "Cl", "Br", "I"]):
        return "halogen"
    if "C(=O)O" in frag or "COOH" in frag:
        return "carboxylic_acid"
    if "C(=O)N" in frag or "CONH" in frag:
        return "amide"
    if "N" in frag and "C(=O)" not in frag:
        return "amine"
    if "O" in frag and "N" not in frag:
        return "ether/hydroxyl"
    if "c1cc" in frag_lower or "c1nc" in frag_lower:
        return "aromatic"
    if "S" in frag:
        return "sulfur"
    if "P" in frag:
        return "phosphorus"
    return "alkyl"


def fragment_library(seed_smiles: List[str]) -> List[Dict]:
    """Build a fragment library from seed molecules for recombination.

    Returns fragments with their frequency and properties.
    """
    all_fragments = {}

    for smi in seed_smiles:
        try:
            mol = Chem.MolFromSmiles(smi)
            if mol is None:
                continue
            frags = BRICS.BRICSDecompose(mol, minFragmentSize=4)
            for frag in frags:
                if frag not in all_fragments:
                    all_fragments[frag] = {
                        "fragment": frag,
                        "count": 0,
                        "sources": [],
                    }
                all_fragments[frag]["count"] += 1
                if smi not in all_fragments[frag]["sources"]:
                    all_fragments[frag]["sources"].append(smi)
        except Exception:
            continue

    fragments = sorted(all_fragments.values(), key=lambda x: x["count"], reverse=True)
    return fragments
