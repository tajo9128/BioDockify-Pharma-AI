"""Multi-objective molecule scorer — drug-likeness, ADMET, diversity, synthetic accessibility.

Combines scores from multiple sources into a single ranking metric.
"""
import logging
from typing import Dict, List, Optional
from rdkit import Chem, DataStructs
from rdkit.Chem import AllChem, Descriptors, Lipinski, rdMolDescriptors
from rdkit.Chem.QED import qed

log = logging.getLogger("generative_chemistry.scorer")

# Score weights (adjustable by user)
DEFAULT_WEIGHTS = {
    "qed": 0.25,           # Drug-likeness
    "sa_score": 0.15,      # Synthetic accessibility (inverted — lower is better)
    "lipinski": 0.15,      # Lipinski compliance
    "admet": 0.20,         # ADMET prediction
    "diversity": 0.15,     # Structural diversity within set
    "novelty": 0.10,       # Distance from seed molecules
}


def score_molecule(smiles: str, weights: Optional[Dict] = None) -> Dict:
    """Score a single molecule on all objectives.

    Returns dict with individual scores and combined score.
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"error": "Invalid SMILES", "combined": 0}

    scores = {}

    # QED (0-1, higher = more drug-like)
    try:
        scores["qed"] = round(qed(mol), 4)
    except Exception:
        scores["qed"] = 0.0

    # Lipinski violations (0-4, lower is better → invert)
    violations = 0
    mw = Descriptors.MolWt(mol)
    logp = Descriptors.MolLogP(mol)
    hbd = Lipinski.NumHDonors(mol)
    hba = Lipinski.NumHAcceptors(mol)
    if mw > 500: violations += 1
    if logp > 5: violations += 1
    if hbd > 5: violations += 1
    if hba > 10: violations += 1
    scores["lipinski"] = round((4 - violations) / 4, 4)  # 0-1, higher is better
    scores["lipinski_violations"] = violations

    # Synthetic accessibility (1-10, lower is better → invert)
    sa = _compute_sa(mol)
    scores["sa_score"] = sa
    scores["sa_inverted"] = round((10 - sa) / 9, 4)  # 0-1, higher is better

    # ADMET quick screen (rule-based, like existing ADMET module)
    scores["admet"] = _quick_admet(mol)

    # Molecular properties
    scores["properties"] = {
        "mw": round(mw, 1), "logp": round(logp, 2),
        "tpsa": round(Descriptors.TPSA(mol), 1),
        "hbd": hbd, "hba": hba,
        "rotb": Lipinski.NumRotatableBonds(mol),
        "n_rings": rdMolDescriptors.CalcNumRings(mol),
        "n_aromatic_rings": rdMolDescriptors.CalcNumAromaticRings(mol),
        "formal_charge": Chem.GetFormalCharge(mol),
    }

    # Combined score (without diversity/novelty — those need a reference set)
    combined = (
        weights.get("qed", 0.25) * scores["qed"] +
        weights.get("sa_score", 0.15) * scores["sa_inverted"] +
        weights.get("lipinski", 0.15) * scores["lipinski"] +
        weights.get("admet", 0.20) * scores["admet"]
    )
    scores["combined"] = round(combined, 4)

    return scores


def score_library(molecules: List[Dict], seed_smiles: Optional[List[str]] = None,
                  weights: Optional[Dict] = None) -> List[Dict]:
    """Score a library of molecules with diversity and novelty calculations.

    Args:
        molecules: List of dicts with at least 'smiles' key
        seed_smiles: Original seed molecules for novelty calculation
        weights: Custom score weights

    Returns:
        Molecules sorted by combined score (descending)
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    # Score each molecule individually
    for mol_entry in molecules:
        smiles = mol_entry.get("smiles", "")
        scores = score_molecule(smiles, weights)
        mol_entry["scores"] = scores

    # Calculate diversity (Tanimoto distance from other molecules in set)
    mols = [Chem.MolFromSmiles(m.get("smiles", "")) for m in molecules]
    valid_mols = [(i, m) for i, m in enumerate(mols) if m is not None]

    if len(valid_mols) > 1:
        fps = []
        for idx, mol in valid_mols:
            try:
                fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
                fps.append((idx, fp))
            except Exception:
                continue

        # Calculate average Tanimoto distance for each molecule
        for i, fp_i in fps:
            distances = []
            for j, fp_j in fps:
                if i != j:
                    sim = DataStructs.TanimotoSimilarity(fp_i, fp_j)
                    distances.append(1.0 - sim)  # Distance = 1 - similarity
            avg_diversity = sum(distances) / len(distances) if distances else 0.5
            molecules[i]["scores"]["diversity"] = round(avg_diversity, 4)

    # Calculate novelty (distance from seed molecules)
    if seed_smiles:
        seed_fps = []
        for smi in seed_smiles:
            try:
                seed_mol = Chem.MolFromSmiles(smi)
                if seed_mol:
                    fp = AllChem.GetMorganFingerprintAsBitVect(seed_mol, 2, nBits=2048)
                    seed_fps.append(fp)
            except Exception:
                continue

        for i, fp_i in fps:
            if seed_fps:
                max_sim = max(DataStructs.TanimotoSimilarity(fp_i, sf) for sf in seed_fps)
                novelty = 1.0 - max_sim  # Higher novelty = more different from seeds
                molecules[i]["scores"]["novelty"] = round(novelty, 4)

    # Update combined score with diversity and novelty
    for mol_entry in molecules:
        scores = mol_entry.get("scores", {})
        base_combined = scores.get("combined", 0)
        diversity = scores.get("diversity", 0.5)
        novelty = scores.get("novelty", 0.5)
        scores["combined"] = round(
            base_combined +
            weights.get("diversity", 0.15) * diversity +
            weights.get("novelty", 0.10) * novelty, 4)

    # Sort by combined score
    molecules.sort(key=lambda m: m.get("scores", {}).get("combined", 0), reverse=True)
    return molecules


def _compute_sa(mol) -> float:
    """Estimate Synthetic Accessibility (1=easy, 10=very hard)."""
    try:
        mw = Descriptors.MolWt(mol)
        n_rings = rdMolDescriptors.CalcNumRings(mol)
        n_rotb = Lipinski.NumRotatableBonds(mol)
        n_heavy = mol.GetNumHeavyAtoms()

        score = 1.0
        score += min(n_rings * 0.5, 3.0)
        score += min(n_rotb * 0.1, 1.5)
        if mw > 500: score += 1.0
        if n_heavy > 40: score += 0.5

        ri = mol.GetRingInfo()
        for ring in ri.AtomRings():
            if len(ring) > 6:
                score += 1.0
                break

        # Check for unusual atoms
        for atom in mol.GetAtoms():
            sym = atom.GetSymbol()
            if sym in ("B", "Si", "Se", "P"):
                score += 0.3
            if atom.GetFormalCharge() != 0:
                score += 0.2

        return round(min(score, 10.0), 2)
    except Exception:
        return 5.0


def _quick_admet(mol) -> float:
    """Quick ADMET screening score (0-1, higher = better profile).

    Rule-based checks similar to the existing ADMET module.
    """
    try:
        score = 1.0
        mw = Descriptors.MolWt(mol)
        logp = Descriptors.MolLogP(mol)
        tpsa = Descriptors.TPSA(mol)
        hbd = Lipinski.NumHDonors(mol)
        hba = Lipinski.NumHAcceptors(mol)
        rotb = Lipinski.NumRotatableBonds(mol)

        # Oral bioavailability heuristics
        if mw > 500: score -= 0.2
        if logp > 5: score -= 0.15
        if logp < 0: score -= 0.1  # Too hydrophilic
        if tpsa > 140: score -= 0.15  # Poor permeability
        if tpsa < 20: score -= 0.1  # Too lipophilic
        if hbd > 5: score -= 0.1
        if hba > 10: score -= 0.1
        if rotb > 10: score -= 0.1

        # Structural alerts (PAINS-like simple checks)
        smiles = Chem.MolToSmiles(mol)
        if "N=N" in smiles: score -= 0.1  # Azo bond
        if smiles.count("c1ccccc1") > 2: score -= 0.05  # Multiple phenyls
        if "[Se]" in smiles or "[B]" in smiles: score -= 0.15

        return round(max(0, min(1, score)), 4)
    except Exception:
        return 0.5


def rank_for_docking(molecules: List[Dict], top_n: int = 10) -> List[Dict]:
    """Select top molecules for docking validation.

    Balances score with structural diversity (avoid docking 10 similar molecules).
    """
    scored = score_library(molecules)
    selected = []
    selected_fps = []

    for mol_entry in scored:
        if len(selected) >= top_n:
            break

        smiles = mol_entry.get("smiles", "")
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            continue

        try:
            fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
            # Check diversity against already selected
            if selected_fps:
                max_sim = max(DataStructs.TanimotoSimilarity(fp, sf) for sf in selected_fps)
                if max_sim > 0.85:  # Too similar to already selected
                    continue
            selected.append(mol_entry)
            selected_fps.append(fp)
        except Exception:
            continue

    return selected
