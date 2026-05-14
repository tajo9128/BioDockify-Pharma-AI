from helpers.api import ApiHandler, Request, Response
from helpers import files
import os
import subprocess
import uuid
import json


JOBS_DIR = files.get_abs_path("tmp/docking_jobs")


class DockingPrepare(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        os.makedirs(JOBS_DIR, exist_ok=True)
        job_id = str(uuid.uuid4())[:8]
        job_dir = os.path.join(JOBS_DIR, job_id)
        os.makedirs(job_dir, exist_ok=True)

        pdb_content = input.get("protein_pdb", "")
        ligand_smiles = input.get("ligand_smiles", "").strip()
        ligand_name = input.get("ligand_name", "ligand").strip()

        if not pdb_content or not ligand_smiles:
            return {"error": "Protein PDB and ligand SMILES required"}

        pdb_path = os.path.join(job_dir, "protein.pdb")
        with open(pdb_path, "w") as f:
            f.write(pdb_content)

        smi_path = os.path.join(job_dir, f"{ligand_name}.smi")
        with open(smi_path, "w") as f:
            f.write(f"{ligand_smiles} {ligand_name}")

        try:
            from rdkit import Chem
            from rdkit.Chem import AllChem
            mol = Chem.MolFromSmiles(ligand_smiles)
            if mol is None:
                return {"error": "Invalid ligand SMILES"}
            mol = Chem.AddHs(mol)
            AllChem.EmbedMolecule(mol, AllChem.ETKDG())
            AllChem.MMFFOptimizeMolecule(mol)
            sdf_path = os.path.join(job_dir, f"{ligand_name}.sdf")
            writer = Chem.SDWriter(sdf_path)
            writer.write(mol)
            writer.close()
        except ImportError:
            return {"error": "RDKit not available for ligand preparation"}

        receptor_pdbqt = os.path.join(job_dir, "protein.pdbqt")
        try:
            subprocess.run(
                ["obabel", pdb_path, "-O", receptor_pdbqt, "--gen3D"],
                capture_output=True, text=True, timeout=120
            )
        except Exception as e:
            return {"error": f"Receptor prep failed: {str(e)}"}

        ligand_pdbqt = os.path.join(job_dir, f"{ligand_name}.pdbqt")
        try:
            subprocess.run(
                ["obabel", sdf_path, "-O", ligand_pdbqt],
                capture_output=True, text=True, timeout=60
            )
        except Exception as e:
            return {"error": f"Ligand prep failed: {str(e)}"}

        center_x, center_y, center_z = 0, 0, 0
        atom_count = 0
        try:
            with open(pdb_path) as f:
                for line in f:
                    if line.startswith("ATOM") or line.startswith("HETATM"):
                        try:
                            center_x += float(line[30:38].strip())
                            center_y += float(line[38:46].strip())
                            center_z += float(line[46:54].strip())
                            atom_count += 1
                        except ValueError:
                            pass
            if atom_count > 0:
                center_x /= atom_count
                center_y /= atom_count
                center_z /= atom_count
        except Exception:
            pass

        return {
            "job_id": job_id,
            "receptor_pdbqt": receptor_pdbqt,
            "ligand_pdbqt": ligand_pdbqt,
            "ligand_name": ligand_name,
            "center": {"x": round(center_x, 2), "y": round(center_y, 2), "z": round(center_z, 2)},
            "size": {"x": 20, "y": 20, "z": 20},
        }
