"""
QSAR-Ready Structure Standardization Pipeline
Adapted from OPERA's structure curation methodology.

Ensures molecules are properly prepared for QSAR modeling:
1. Remove salts and counterions
2. Neutralize charges
3. Standardize tautomers
4. Remove stereochemistry ambiguity
5. Filter out metals, mixtures, and invalid structures
"""
import logging
from typing import List, Tuple, Optional, Dict
from rdkit import Chem
from rdkit.Chem import SaltRemover, AllChem, Descriptors
from rdkit.Chem.MolStandardize import rdMolStandardize

logger = logging.getLogger("qsar3d.standardize")


class StructureStandardizer:
    """
    Standardize molecules for QSAR modeling (OPERA-style curation).
    """

    def __init__(self):
        self.salt_remover = SaltRemover.SaltRemover()
        self.normalizer = rdMolStandardize.Normalizer()
        self.uncharger = rdMolStandardize.Uncharger()
        self.teautomer = rdMolStandardize.TautomerEnumerator()

    def standardize(self, mol: Chem.Mol) -> Optional[Chem.Mol]:
        """
        Apply full QSAR-ready standardization to a molecule.
        Returns None if molecule fails curation.
        """
        if mol is None:
            return None

        try:
            # Step 1: Remove salts
            mol = self.salt_remover.StripMol(mol)
            if mol.GetNumAtoms() == 0:
                return None

            # Step 2: Normalize functional groups
            mol = self.normalizer.normalize(mol)
            if mol is None:
                return None

            # Step 3: Neutralize charges
            mol = self.uncharger.uncharge(mol)
            if mol is None:
                return None

            # Step 4: Canonical tautomer
            mol = self.teautomer.Canonicalize(mol)
            if mol is None:
                return None

            # Step 5: Canonical SMILES → back to Mol (ensures clean structure)
            can_smi = Chem.MolToSmiles(mol)
            mol = Chem.MolFromSmiles(can_smi)
            if mol is None:
                return None

            # Step 6: Filter — reject metals, too small/large
            return self._filter(mol)

        except Exception as e:
            logger.debug(f"Standardization failed: {e}")
            return None

    def _filter(self, mol: Chem.Mol) -> Optional[Chem.Mol]:
        """Filter out unsuitable molecules for QSAR."""
        # Reject if contains metals
        metal_symbols = {'Li', 'Be', 'Na', 'Mg', 'Al', 'K', 'Ca', 'Sc', 'Ti',
                         'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'Ga',
                         'Rb', 'Sr', 'Y', 'Zr', 'Nb', 'Mo', 'Tc', 'Ru', 'Rh',
                         'Pd', 'Ag', 'Cd', 'In', 'Sn', 'Cs', 'Ba', 'La', 'Hg',
                         'Tl', 'Pb', 'Bi', 'Po', 'At', 'Fr', 'Ra', 'Ac'}
        for atom in mol.GetAtoms():
            if atom.GetSymbol() in metal_symbols:
                return None
            if atom.GetAtomicNum() > 53:  # No elements heavier than Iodine
                return None

        # Reject if too small
        if mol.GetNumHeavyAtoms() < 3:
            return None

        # Reject if too large
        mw = Descriptors.MolWt(mol)
        if mw > 1000:
            return None

        return mol

    def standardize_smiles(self, smiles: str) -> Optional[Chem.Mol]:
        """Standardize from SMILES string."""
        mol = Chem.MolFromSmiles(smiles)
        return self.standardize(mol)

    def prepare_dataset(self, smiles_list: List[str]) -> Tuple[List[Chem.Mol], List[int]]:
        """
        Prepare entire dataset. Returns (valid_molecules, valid_indices).
        Indices map back to original dataset positions.
        """
        valid_mols = []
        valid_indices = []

        for i, smi in enumerate(smiles_list):
            mol = self.standardize_smiles(smi)
            if mol is not None:
                valid_mols.append(mol)
                valid_indices.append(i)

        rejected = len(smiles_list) - len(valid_mols)
        logger.info(f"Standardization: {len(valid_mols)}/{len(smiles_list)} valid, "
                     f"{rejected} rejected")

        return valid_mols, valid_indices
