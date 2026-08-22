"""Molecular Fingerprints and Descriptors for bioactivity prediction."""
import logging
import numpy as np
from typing import Dict, List, Optional

from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors, MACCSkeys, rdMolDescriptors

log = logging.getLogger("bioactivity_predictor.fingerprints")


def compute_ecfp4(smiles: str, n_bits: int = 2048) -> Optional[np.ndarray]:
    """Compute ECFP4 (Morgan radius=2) fingerprint as bit vector."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius=2, nBits=n_bits)
    return np.array(fp, dtype=np.uint8)


def compute_maccs(smiles: str) -> Optional[np.ndarray]:
    """Compute MACCS keys fingerprint (166 bits)."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    fp = MACCSkeys.GenMACCSKeys(mol)
    return np.array(fp, dtype=np.uint8)


def compute_descriptors(smiles: str) -> Optional[Dict]:
    """Compute physicochemical descriptors for ML models.

    Returns 12 key descriptors used as features alongside fingerprints.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return {
        "mw": Descriptors.MolWt(mol),
        "logp": Descriptors.MolLogP(mol),
        "tpsa": Descriptors.TPSA(mol),
        "hbd": rdMolDescriptors.CalcNumHBD(mol),
        "hba": rdMolDescriptors.CalcNumHBA(mol),
        "rotatable_bonds": rdMolDescriptors.CalcNumRotatableBonds(mol),
        "aromatic_rings": rdMolDescriptors.CalcNumAromaticRings(mol),
        "heavy_atoms": mol.GetNumHeavyAtoms(),
        "fraction_sp3": rdMolDescriptors.CalcFractionCSP3(mol),
        "num_rings": rdMolDescriptors.CalcNumRings(mol),
        "num_heteroatoms": rdMolDescriptors.CalcNumHeteroatoms(mol),
        "formal_charge": Chem.GetFormalCharge(mol),
    }


def batch_fingerprints(smiles_list: List[str], fp_type: str = "ecfp4",
                       n_bits: int = 2048) -> np.ndarray:
    """Compute fingerprints for a batch of molecules.

    Returns matrix of shape (n_valid_molecules, n_bits).
    Invalid SMILES are silently skipped.
    """
    fps = []
    for smi in smiles_list:
        if fp_type == "ecfp4":
            fp = compute_ecfp4(smi, n_bits)
        elif fp_type == "maccs":
            fp = compute_maccs(smi)
        else:
            fp = compute_ecfp4(smi, n_bits)
        if fp is not None:
            fps.append(fp)
    if not fps:
        return np.empty((0, n_bits), dtype=np.uint8)
    return np.vstack(fps)
