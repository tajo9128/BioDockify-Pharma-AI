"""Atom Mapping — reactant-to-product atom correspondence via MCS matching.

For each reactant, finds the maximum common substructure shared with the
product and reports surviving atoms (with indices) vs. transformed atoms.
Pure RDKit, offline. (Publication-grade mapping uses ML (RXNMapper) — this
is a deterministic structural correspondence.)
"""
import logging
from typing import Dict, List

from rdkit import Chem
from rdkit.Chem import rdFMCS

log = logging.getLogger("reaction_lab.atom_map")


def map_reaction(reactants: List[str], product: str) -> Dict:
    if not reactants or not product:
        return {"error": "reactants (list) and product required"}
    pmol = Chem.MolFromSmiles(product)
    if pmol is None:
        return {"error": f"Invalid product SMILES: {product}"}

    mappings = []
    for r_idx, rsmi in enumerate(reactants):
        rmol = Chem.MolFromSmiles(rsmi)
        if rmol is None:
            return {"error": f"Invalid reactant SMILES: {rsmi}"}
        try:
            mcs = rdFMCS.FindMCS([rmol, pmol], bondCompare=rdFMCS.BondCompare.CompareOrder,
                                 atomCompare=rdFMCS.AtomCompare.CompareElements,
                                 ringMatchesRingOnly=True, completeRingsOnly=False,
                                 timeout=5)
        except Exception as e:
            return {"error": f"MCS failed: {e}"}

        if mcs.numAtoms == 0:
            mappings.append({"reactant_index": r_idx, "reactant": rsmi,
                             "conserved_atoms": 0, "reactant_atoms": rmol.GetNumAtoms(),
                             "note": "no common substructure found"})
            continue
        mcs_mol = Chem.MolFromSmarts(mcs.smartsString)
        r_match = rmol.GetSubstructMatches(mcs_mol)
        p_match = pmol.GetSubstructMatches(mcs_mol)
        pairs = []
        if r_match and p_match:
            for rm, pm in zip(r_match[0], p_match[0]):
                pairs.append({
                    "reactant_atom": rm,
                    "product_atom": pm,
                    "element": rmol.GetAtomWithIdx(rm).GetSymbol(),
                })
        mappings.append({
            "reactant_index": r_idx,
            "reactant": rsmi,
            "conserved_atoms": len(pairs),
            "reactant_atoms": rmol.GetNumAtoms(),
            "product_atoms": pmol.GetNumAtoms(),
            "conservation": round(len(pairs) / max(rmol.GetNumAtoms(), 1), 3),
            "atom_pairs": pairs,
        })

    total_conserved = sum(m.get("conserved_atoms", 0) for m in mappings)
    all_product_atoms = pmol.GetNumAtoms()
    return {
        "reactants": reactants,
        "product": product,
        "product_num_atoms": all_product_atoms,
        "mappings": mappings,
        "total_conserved_atoms": total_conserved,
        "atoms_unaccounted": max(all_product_atoms - total_conserved, 0),
        "note": "Deterministic MCS-based correspondence (not ML atom-mapping). "
                "Conserved atoms survive the reaction; unaccounted product atoms come from other reactants.",
    }
