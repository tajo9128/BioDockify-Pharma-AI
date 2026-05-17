from helpers.api import ApiHandler, Request, Response
from helpers import files
import os
import subprocess
import uuid
import json
import logging
import tempfile

log = logging.getLogger("docking_prepare")

JOBS_DIR = files.get_abs_path("tmp/docking_jobs")


def _run_obabel(args, timeout=60, label="conversion"):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            stderr = result.stderr.strip()
            log.warning(f"obabel {label} failed: {stderr}")
            return False, result.stdout, stderr
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
    try:
        result = subprocess.run(["obabel", "-V"], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except Exception:
        return False


def _detect_format(content, filename_hint=""):
    """Detect molecular file format from content."""
    content = content.strip()
    # SMILES detection
    if not any(content.startswith(prefix) for prefix in ["HEADER", "ATOM", "HETATM", "data_", "MODEL", "@<TRIPOS>", "CRYST1", "TITLE"]):
        # Likely SMILES or name
        if len(content.split()) == 1 and len(content) < 500:
            return "smiles"
    # PDB detection
    if "ATOM  " in content or "HETATM" in content or content.startswith("HEADER"):
        return "pdb"
    # PDBQT detection
    if content.startswith("MODEL") or "REMARK VINA" in content:
        return "pdbqt"
    # CIF detection
    if content.startswith("data_") or "_atom_site." in content:
        return "cif"
    # MOL2 detection
    if "@<TRIPOS>" in content:
        return "mol2"
    # SDF/MOL detection
    if "V2000" in content or "V3000" in content or content.startswith("M  END"):
        return "sdf"
    # ENT (PDB variant)
    if "END" in content.split("\n")[-3:]:
        return "ent"
    return filename_hint or "unknown"


class DockingPrepare(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        os.makedirs(JOBS_DIR, exist_ok=True)
        job_id = str(uuid.uuid4())[:8]
        job_dir = os.path.join(JOBS_DIR, job_id)
        os.makedirs(job_dir, exist_ok=True)

        # Accept both old field names and new field names
        protein_content = input.get("protein_content") or input.get("protein_pdb", "")
        protein_format = input.get("protein_format", "").lower() or "pdb"
        ligand_content = input.get("ligand_content") or input.get("ligand_smiles", "").strip()
        ligand_format = input.get("ligand_format", "").lower() or "smiles"
        ligand_name = input.get("ligand_name", "ligand").strip()

        if not protein_content or not ligand_content:
            return {"error": "Protein and ligand data required"}

        # Auto-detect formats if not provided
        if not protein_format or protein_format == "unknown":
            protein_format = _detect_format(protein_content, "pdb")
        if not ligand_format or ligand_format == "unknown":
            ligand_format = _detect_format(ligand_content, "smiles")

        log.info(f"Docking prepare: protein={protein_format}, ligand={ligand_format}")

        # === Save raw input files ===
        pdb_path = os.path.join(job_dir, "protein.pdb")
        lig_input_path = os.path.join(job_dir, f"ligand_raw.{'smi' if ligand_format == 'smiles' else ligand_format}")
        with open(lig_input_path, "w") as f:
            f.write(ligand_content)

        # === Protein preparation: convert to PDB if needed ===
        if protein_format in ("pdb", "ent", "pdbqt"):
            with open(pdb_path, "w") as f:
                f.write(protein_content)
        elif _obabel_available():
            # Convert non-PDB formats to PDB
            tmp_input = os.path.join(job_dir, f"protein_input.{protein_format}")
            with open(tmp_input, "w") as f:
                f.write(protein_content)
            ok, stdout, stderr = _run_obabel(
                ["obabel", tmp_input, "-O", pdb_path],
                timeout=30, label=f"protein {protein_format}→PDB"
            )
            if not ok:
                return {
                    "error": f"Failed to convert protein from {protein_format.upper()} to PDB: {stderr}",
                    "hint": "Try pasting the content in PDB format directly"
                }
        else:
            return {
                "error": f"Protein format '{protein_format}' requires OpenBabel for conversion. Install: apt install openbabel",
                "hint": "Paste PDB format content directly"
            }

        # === Ligand preparation ===
        ligand_pdbqt = os.path.join(job_dir, f"{ligand_name}.pdbqt")
        sdf_path = os.path.join(job_dir, f"{ligand_name}.sdf")
        ligand_prep_ok = False
        ligand_errors = []

        # Strategy: try to get SMILES first (if not already SMILES)
        smiles = None
        if ligand_format in ("smiles", "smi"):
            smiles = ligand_content.split()[0] if ligand_content.split() else ligand_content
        elif _obabel_available():
            # Try SMILES extraction from other formats
            ok, stdout, stderr = _run_obabel(
                ["obabel", lig_input_path, "-osmi"],
                timeout=15, label="extract SMILES"
            )
            if ok and stdout.strip():
                smiles = stdout.strip().split()[0] if stdout.strip().split() else stdout.strip()

        # Strategy 1: RDKit SMILES → SDF → PDBQT
        if smiles:
            try:
                from rdkit import Chem
                from rdkit.Chem import AllChem
                mol = Chem.MolFromSmiles(smiles)
                if mol is None:
                    ligand_errors.append(f"Invalid SMILES: {smiles[:50]}")
                else:
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
                            ligand_errors.append(f"SDF→PDBQT: {stderr}")
                    else:
                        ligand_errors.append("obabel not available for PDBQT conversion")
            except ImportError:
                ligand_errors.append("RDKit not available")
            except Exception as e:
                ligand_errors.append(f"RDKit prep: {str(e)}")

        # Strategy 2: obabel direct conversion (for SDF/MOL/PDB/MOL2 input formats)
        if not ligand_prep_ok and _obabel_available() and ligand_format in ("sdf", "mol", "pdb", "mol2", "pdbqt"):
            ok, stdout, stderr = _run_obabel(
                ["obabel", lig_input_path, "-O", ligand_pdbqt, "--gen3D"],
                timeout=30, label=f"ligand {ligand_format}→PDBQT"
            )
            if ok:
                ligand_prep_ok = True
            else:
                ligand_errors.append(f"{ligand_format}→PDBQT: {stderr}")

        # Strategy 3: obabel from SMILES directly
        if not ligand_prep_ok and smiles and _obabel_available():
            tmp_smi = os.path.join(job_dir, "temp.smi")
            with open(tmp_smi, "w") as f:
                f.write(f"{smiles} ligand")
            ok, stdout, stderr = _run_obabel(
                ["obabel", tmp_smi, "-O", ligand_pdbqt, "--gen3D"],
                timeout=30, label="SMILES→PDBQT"
            )
            if ok:
                ligand_prep_ok = True
            else:
                ligand_errors.append(f"SMILES→PDBQT: {stderr}")

        if not ligand_prep_ok:
            return {
                "error": f"Ligand preparation failed ({ligand_format.upper()}): {'; '.join(ligand_errors)}",
                "hint": "Install RDKit and OpenBabel, or provide SMILES string"
            }

        # === Receptor PDB → PDBQT conversion ===
        receptor_pdbqt = os.path.join(job_dir, "protein.pdbqt")
        receptor_prep_ok = False
        receptor_errors = []

        if _obabel_available():
            ok, stdout, stderr = _run_obabel(
                ["obabel", pdb_path, "-O", receptor_pdbqt, "-xr"],
                timeout=60, label="receptor PDB→PDBQT"
            )
            if ok:
                receptor_prep_ok = True
            else:
                receptor_errors.append(f"obabel: {stderr.strip()}")

        # Fallback: raw PDB as PDBQT
        if not receptor_prep_ok:
            receptor_errors.append("Using raw PDB as fallback")
            try:
                with open(pdb_path) as src:
                    with open(receptor_pdbqt, "w") as dst:
                        dst.write(src.read())
                receptor_prep_ok = True
            except Exception as e:
                receptor_errors.append(f"PDB copy fallback: {str(e)}")

        if not receptor_prep_ok:
            return {
                "error": f"Receptor preparation failed: {'; '.join(receptor_errors)}",
                "hint": "Install OpenBabel (apt install openbabel) or try a smaller PDB file."
            }

        # === Compute binding site center ===
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
            "detected_formats": {"protein": protein_format, "ligand": ligand_format},
            "center": {"x": round(center_x, 2), "y": round(center_y, 2), "z": round(center_z, 2)},
            "size": {"x": 20, "y": 20, "z": 20},
            "prep_notes": "; ".join(receptor_errors + ligand_errors) if (receptor_errors or ligand_errors) else "OK",
        }
