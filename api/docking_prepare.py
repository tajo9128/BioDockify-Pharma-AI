from helpers.api import ApiHandler, Request, Response
from helpers import files
import os
import subprocess
import uuid
import json
import logging

log = logging.getLogger("docking_prepare")

JOBS_DIR = files.get_abs_path("tmp/docking_jobs")


def _run_obabel(args, timeout=60, label="conversion"):
    """Run obabel with timeout and return (success, stdout, stderr)."""
    try:
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout
        )
        if result.returncode != 0:
            log.warning(f"obabel {label} failed: {result.stderr.strip()}")
            return False, result.stdout, result.stderr
        return True, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        log.warning(f"obabel {label} timed out after {timeout}s")
        return False, "", f"Timed out after {timeout}s"
    except FileNotFoundError:
        log.warning("obabel not found in PATH")
        return False, "", "obabel not installed"
    except Exception as e:
        return False, "", str(e)


def _obabel_available():
    """Check if obabel is available in PATH."""
    try:
        result = subprocess.run(
            ["obabel", "-V"], capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


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

        # Save input files
        pdb_path = os.path.join(job_dir, "protein.pdb")
        with open(pdb_path, "w") as f:
            f.write(pdb_content)

        smi_path = os.path.join(job_dir, f"{ligand_name}.smi")
        with open(smi_path, "w") as f:
            f.write(f"{ligand_smiles} {ligand_name}")

        # === Ligand preparation (RDKit first, then obabel fallback) ===
        ligand_pdbqt = os.path.join(job_dir, f"{ligand_name}.pdbqt")
        ligand_prep_ok = False
        ligand_errors = []

        # Strategy 1: RDKit for SMILES → SDF, then obabel SDF → PDBQT
        sdf_path = os.path.join(job_dir, f"{ligand_name}.sdf")
        try:
            from rdkit import Chem
            from rdkit.Chem import AllChem
            mol = Chem.MolFromSmiles(ligand_smiles)
            if mol is None:
                return {"error": "Invalid ligand SMILES"}
            mol = Chem.AddHs(mol)
            AllChem.EmbedMolecule(mol, AllChem.ETKDG())
            AllChem.MMFFOptimizeMolecule(mol)
            writer = Chem.SDWriter(sdf_path)
            writer.write(mol)
            writer.close()

            if _obabel_available():
                ok, stdout, stderr = _run_obabel(
                    ["obabel", sdf_path, "-O", ligand_pdbqt],
                    timeout=30, label="ligand SDF→PDBQT"
                )
                if ok:
                    ligand_prep_ok = True
                else:
                    ligand_errors.append(f"obabel SDF→PDBQT: {stderr}")
            else:
                ligand_errors.append("obabel not available for ligand PDBQT conversion")
        except ImportError:
            ligand_errors.append("RDKit not available")
        except Exception as e:
            ligand_errors.append(f"RDKit ligand prep: {str(e)}")

        # Strategy 2: obabel directly from SMILES → PDBQT
        if not ligand_prep_ok and _obabel_available():
            ok, stdout, stderr = _run_obabel(
                ["obabel", smi_path, "-O", ligand_pdbqt, "--gen3D"],
                timeout=30, label="ligand SMILES→PDBQT"
            )
            if ok:
                ligand_prep_ok = True
            else:
                ligand_errors.append(f"obabel SMILES→PDBQT: {stderr}")

        if not ligand_prep_ok:
            return {
                "error": f"Ligand preparation failed. {'; '.join(ligand_errors)}",
                "hint": "Ensure RDKit or OpenBabel is installed. For SMILES, RDKit is recommended."
            }

        # === Receptor preparation ===
        receptor_pdbqt = os.path.join(job_dir, "protein.pdbqt")
        receptor_prep_ok = False
        receptor_errors = []

        if _obabel_available():
            # Strategy 1: obabel PDB → PDBQT (no 3D gen, proteins already have coords)
            ok, stdout, stderr = _run_obabel(
                ["obabel", pdb_path, "-O", receptor_pdbqt, "-xr"],
                timeout=60, label="receptor PDB→PDBQT"
            )
            if ok:
                receptor_prep_ok = True
            else:
                receptor_errors.append(f"obabel: {stderr.strip()}")

        # Strategy 2: Copy PDB as PDBQT (some tools accept this)
        if not receptor_prep_ok:
            receptor_errors.append("obabel not available; using raw PDB as fallback")
            try:
                with open(pdb_path) as src:
                    with open(receptor_pdbqt, "w") as dst:
                        dst.write(src.read())
                receptor_prep_ok = True
            except Exception as e:
                receptor_errors.append(f"PDB copy fallback: {str(e)}")

        if not receptor_prep_ok:
            return {
                "error": f"Receptor preparation failed. {'; '.join(receptor_errors)}",
                "hint": "Install OpenBabel (apt install openbabel) or try a smaller PDB file."
            }

        # === Compute binding site center from PDB atoms ===
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
            "prep_notes": "; ".join(receptor_errors + ligand_errors) if (receptor_errors or ligand_errors) else "OK",
        }
