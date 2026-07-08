"""
Molecular Alignment for 3D-QSAR
Based on Open3DQSAR alignment and Py-CoMFA pre-alignment requirements.

"Alignment, alignment, alignment" — the 3 rules of 3D-QSAR.
"""
import numpy as np
import logging
from typing import List, Optional, Tuple
from rdkit import Chem
from rdkit.Chem import AllChem, rdMolAlign
from rdkit.Chem import rdFMCS

logger = logging.getLogger("qsar3d.alignment")


class MolecularAligner:
    """
    Align molecules for 3D-QSAR using multiple strategies.

    Methods:
    - scaffold: Maximum Common Substructure (MCS) based alignment
    - reference: Align to a reference ligand
    - pharmacophore: Align using pharmacophore features (via existing module)
    """

    def __init__(self, method: str = 'scaffold', max_iters: int = 200):
        self.method = method
        self.max_iters = max_iters

    def generate_3d(self, mol: Chem.Mol) -> Chem.Mol:
        """Generate 3D coordinates using ETKDG."""
        mol = Chem.AddHs(mol)
        params = AllChem.ETKDGv3()
        params.randomSeed = 42
        AllChem.EmbedMolecule(mol, params)
        try:
            AllChem.MMFFOptimizeMolecule(mol, maxIters=self.max_iters)
        except Exception:
            try:
                AllChem.UFFOptimizeMolecule(mol, maxIters=self.max_iters)
            except Exception:
                pass
        return mol

    def align_to_scaffold(self, mols: List[Chem.Mol]) -> List[Chem.Mol]:
        """
        Align all molecules to their maximum common substructure (MCS).
        This is the standard alignment method for ligand-based 3D-QSAR.
        """
        if len(mols) < 2:
            return mols

        # Find MCS
        mcs = rdFMCS.FindMCS(
            mols,
            timeout=10,
            atomCompare=rdFMCS.AtomCompare.CompareElements,
            bondCompare=rdFMCS.BondCompare.CompareOrder,
            ringMatchesRingOnly=True,
            completeRingsOnly=True,
            matchValences=False,
        )

        if mcs.numAtoms < 3:
            logger.warning(f"MCS too small ({mcs.numAtoms} atoms), skipping alignment")
            return mols

        logger.info(f"MCS found: {mcs.numAtoms} atoms, {mcs.numBonds} bonds, "
                    f"smarts: {mcs.smartsString[:80]}...")

        mcs_mol = Chem.MolFromSmarts(mcs.smartsString)

        # Align each molecule to the first one via MCS
        reference = mols[0]
        aligned = [reference]

        for mol in mols[1:]:
            try:
                # Get atom mappings between reference and mol via MCS
                ref_match = reference.GetSubstructMatch(mcs_mol)
                mol_match = mol.GetSubstructMatch(mcs_mol)

                if len(ref_match) < 3 or len(mol_match) < 3:
                    logger.warning("Insufficient atoms for alignment, skipping")
                    aligned.append(mol)
                    continue

                # Map atom indices
                atom_map = list(zip(mol_match, ref_match))

                # Perform RMSD-based alignment
                rdMolAlign.AlignMol(
                    mol, reference,
                    atomMap=atom_map,
                )
                aligned.append(mol)
            except Exception as e:
                logger.warning(f"Alignment failed for molecule: {e}")
                aligned.append(mol)

        return aligned

    def align_to_reference(self, mols: List[Chem.Mol],
                           reference: Chem.Mol) -> List[Chem.Mol]:
        """Align all molecules to a specific reference molecule."""
        aligned = [reference]

        for mol in mols:
            if mol is reference:
                continue

            # Find common substructure between mol and reference
            mcs = rdFMCS.FindMCS(
                [mol, reference],
                timeout=10,
                atomCompare=rdFMCS.AtomCompare.CompareElements,
                bondCompare=rdFMCS.BondCompare.CompareOrder,
                ringMatchesRingOnly=True,
                completeRingsOnly=True,
            )

            if mcs.numAtoms < 3:
                aligned.append(mol)
                continue

            mcs_mol = Chem.MolFromSmarts(mcs.smartsString)
            ref_match = reference.GetSubstructMatch(mcs_mol)
            mol_match = mol.GetSubstructMatch(mcs_mol)

            try:
                atom_map = list(zip(mol_match, ref_match))
                rdMolAlign.AlignMol(mol, reference, atomMap=atom_map)
            except Exception as e:
                logger.warning(f"Alignment failed: {e}")

            aligned.append(mol)

        return aligned

    def prepare_dataset(self, smiles_list: List[str],
                        activity_list: List[float],
                        reference_smiles: str = None) -> Tuple[List[Chem.Mol], List[float]]:
        """
        Full dataset preparation: generate 3D, align.

        Returns: (aligned_molecules, activities)
        """
        mols = []
        activities = []

        for smi, act in zip(smiles_list, activity_list):
            mol = Chem.MolFromSmiles(smi)
            if mol is None:
                logger.warning(f"Invalid SMILES: {smi}")
                continue
            mol = self.generate_3d(mol)
            mols.append(mol)
            activities.append(float(act))

        if len(mols) < 5:
            raise ValueError(f"Need at least 5 molecules for 3D-QSAR, got {len(mols)}")

        # Align
        if reference_smiles:
            ref_mol = Chem.MolFromSmiles(reference_smiles)
            if ref_mol:
                ref_mol = self.generate_3d(ref_mol)
                mols = self.align_to_reference(mols, ref_mol)
        else:
            mols = self.align_to_scaffold(mols)

        return mols, activities
