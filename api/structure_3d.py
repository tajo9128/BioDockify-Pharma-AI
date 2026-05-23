"""Structure 3D API — generates 3D conformer SDF from SMILES for 3Dmol.js."""
from helpers.api import ApiHandler, Request
import logging

log = logging.getLogger("structure_3d")


class Structure3d(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        smiles = (input.get("smiles") or "").strip()
        if not smiles:
            return {"success": False, "error": "smiles required"}

        try:
            from rdkit import Chem
            from rdkit.Chem import AllChem

            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return {"success": False, "error": "Invalid SMILES"}

            mol = Chem.AddHs(mol)
            status = AllChem.EmbedMolecule(mol, AllChem.ETKDG())
            if status != 0:
                return {"success": False, "error": "Could not generate 3D coordinates"}

            AllChem.MMFFOptimizeMolecule(mol)
            sdf = Chem.MolToMolBlock(mol)
            return {
                "success": True,
                "sdf": sdf,
                "num_atoms": mol.GetNumAtoms(),
                "num_bonds": mol.GetNumBonds(),
            }
        except ImportError:
            return {"success": False, "error": "RDKit not available"}
        except Exception as e:
            log.exception("structure_3d failed")
            return {"success": False, "error": str(e)}
