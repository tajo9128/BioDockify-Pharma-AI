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
        subprocess.run(["obabel", "-V"], capture_output=True, timeout=5)
        return True
    except Exception:
        return False


def _meeko_to_pdbqt(output_path, mol, is_ligand=True):
    """Pure Python PDB→PDBQT via Meeko — no obabel binary needed. Cross-platform."""
    try:
        from meeko import MoleculePreparation, PDBQTWriterLegacy
        from rdkit import Chem
        prep = MoleculePreparation()
        if hasattr(mol, "GetAtoms"):
            mol_setup = prep.prepare(mol)[0]
        else:
            mol_rd = Chem.MolFromPDBFile(mol) if isinstance(mol, str) else mol
            if mol_rd is None:
                return False, "Meeko: invalid molecule"
            mol_setup = prep.prepare(mol_rd)[0]
        pdbqt_str, is_ok = PDBQTWriterLegacy.write_string(mol_setup)
        if not is_ok:
            return False, "Meeko: failed to write PDBQT"
        if is_ligand:
            pdbqt_str = _sanitize_pdbqt_str(pdbqt_str, is_ligand=True)
        with open(output_path, "w") as f:
            f.write(pdbqt_str)
        return True, ""
    except ImportError:
        return False, "Meeko not installed (pip install meeko)"
    except Exception as e:
        return False, str(e)


def _sanitize_pdbqt_str(pdbqt_str, is_ligand=True):
    """Add ROOT/ENDROOT/TORSDOF markers for ligand PDBQT strings."""
    lines = pdbqt_str.split("\n")
    if is_ligand and "ROOT" not in pdbqt_str:
        lines.insert(0, "ROOT")
        lines.append("ENDROOT")
        torsions = sum(1 for l in lines if "ACTIVE_BOND" in l or "rotatable" in l.lower())
        lines.append(f"TORSDOF {max(0, torsions)}")
    return "\n".join(lines)


def _detect_format(content, filename_hint=""):
    """Detect molecular file format from content."""
    content = content.strip()
    # SMILES detection
    if not any(content.startswith(prefix) for prefix in ["HEADER", "ATOM", "HETATM", "data_", "MODEL", "@<TRIPOS>", "CRYST1", "TITLE"]):
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
    if "V2000" in content or "V3000" in content or "M  END" in content:
        return "sdf"
    # ENT (PDB variant)
    if content.strip().endswith("END"):
        return "ent"
    return filename_hint or "unknown"


def _compute_search_box(pdb_path: str):
    """Compute binding site center and auto-detected grid size from protein atom coordinates.

    Returns (center_dict, size_dict) where center is the geometric center of all atoms
    and size is the bounding box plus a 10 Å margin, capped at 30 Å per dimension.
    """
    xs, ys, zs = [], [], []
    try:
        with open(pdb_path) as f:
            for line in f:
                if line.startswith("ATOM") or line.startswith("HETATM"):
                    try:
                        xs.append(float(line[30:38].strip()))
                        ys.append(float(line[38:46].strip()))
                        zs.append(float(line[46:54].strip()))
                    except ValueError:
                        pass
    except Exception:
        pass

    if not xs:
        log.warning(f"No atoms found in receptor PDB {pdb_path}, docking grid defaults to origin + 20 Å box")
        return {"x": 0.0, "y": 0.0, "z": 0.0}, {"x": 20.0, "y": 20.0, "z": 20.0}

    # Center = geometric mean of all atom coordinates
    cx = round(sum(xs) / len(xs), 3)
    cy = round(sum(ys) / len(ys), 3)
    cz = round(sum(zs) / len(zs), 3)

    # Box = protein bounding box plus margin
    margin = 8.0
    max_dim = 30.0
    min_dim = 15.0

    dx = (max(xs) - min(xs)) + margin * 2
    dy = (max(ys) - min(ys)) + margin * 2
    dz = (max(zs) - min(zs)) + margin * 2

    sx = round(min(max(dx, min_dim), max_dim), 1)
    sy = round(min(max(dy, min_dim), max_dim), 1)
    sz = round(min(max(dz, min_dim), max_dim), 1)

    log.info(f"Auto grid: center=({cx},{cy},{cz}) size=({sx}x{sy}x{sz}) from {len(xs)} atoms")
    return {"x": cx, "y": cy, "z": cz}, {"x": sx, "y": sy, "z": sz}


class DockingPrepare(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        os.makedirs(JOBS_DIR, exist_ok=True)
        job_id = str(uuid.uuid4())[:8]
        job_dir = os.path.join(JOBS_DIR, job_id)
        os.makedirs(job_dir, exist_ok=True)

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

        smiles = None
        if ligand_format in ("smiles", "smi"):
            smiles = ligand_content.split()[0] if ligand_content.split() else ligand_content
        elif _obabel_available():
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

        # Strategy 4: Meeko — pure Python PDB→PDBQT (cross-platform fallback)
        if not ligand_prep_ok and smiles:
            try:
                from rdkit import Chem
                mol = Chem.MolFromSmiles(smiles)
                if mol:
                    mol = Chem.AddHs(mol)
                    from rdkit.Chem import AllChem
                    AllChem.EmbedMolecule(mol, AllChem.ETKDG())
                    AllChem.MMFFOptimizeMolecule(mol)
                    meeko_ok, meeko_err = _meeko_to_pdbqt(ligand_pdbqt, mol, is_ligand=True)
                    if meeko_ok: ligand_prep_ok = True
                    else: ligand_errors.append(f"Meeko: {meeko_err}")
            except Exception as e:
                ligand_errors.append(f"Meeko: {str(e)}")

        if not ligand_prep_ok:
            return {
                "error": f"Ligand preparation failed: {'; '.join(ligand_errors)}",
                "hint": "Install RDKit + OpenBabel (Docker), or pip install meeko for pure Python PDBQT conversion"
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

        if not receptor_prep_ok:
            receptor_errors.append("OpenBabel not available — cannot prepare receptor PDBQT")
            return {
                "error": f"Receptor preparation failed: {'; '.join(receptor_errors)}",
                "hint": "Install OpenBabel (apt install openbabel) for PDB→PDBQT conversion."
            }

        # === Sanitize PDBQT files (obabel can produce non-AD4 atom types) ===
        _sanitize_pdbqt(receptor_pdbqt, is_ligand=False)
        _sanitize_pdbqt(ligand_pdbqt, is_ligand=True)

        # === Validate PDBQT files after sanitization ===
        ok, msg = _validate_pdbqt(receptor_pdbqt)
        if not ok:
            return {"error": f"Receptor PDBQT validation failed: {msg}", "hint": "The protein preparation produced an invalid PDBQT file."}
        ok, msg = _validate_pdbqt(ligand_pdbqt)
        if not ok:
            return {"error": f"Ligand PDBQT validation failed: {msg}", "hint": "The ligand preparation produced an invalid PDBQT file."}
        # === Auto-detect binding site center AND grid size from protein ===
        center, size = _compute_search_box(pdb_path)

        return {
            "job_id": job_id,
            "receptor_pdbqt": receptor_pdbqt,
            "ligand_pdbqt": ligand_pdbqt,
            "ligand_name": ligand_name,
            "detected_formats": {"protein": protein_format, "ligand": ligand_format},
            "center": center,
            "size": size,
            "prep_notes": "; ".join(receptor_errors + ligand_errors) if (receptor_errors or ligand_errors) else "OK",
        }


VALID_AD_TYPES = {'C', 'A', 'N', 'NA', 'OA', 'SA', 'HD', 'H', 'F', 'Cl', 'Br', 'I', 'P', 'S', 'Z', 'G', 'GA'}


def _validate_pdbqt(filepath: str) -> tuple:
    """Validate PDBQT file before passing to Vina/GNINA."""
    import os
    try:
        if not os.path.exists(filepath):
            return False, "File does not exist"
        size = os.path.getsize(filepath)
        if size < 100:
            return False, f"File too small ({size} bytes)"
        with open(filepath, 'r') as f:
            content = f.read()
        if content.startswith("HEADER") and "REMARK" not in content and "MODEL" not in content:
            return False, "File appears to be raw PDB, not PDBQT"

        atom_count = 0
        charge_errors = 0
        type_errors = 0
        for line in content.split('\n'):
            if line.startswith('ATOM') or line.startswith('HETATM'):
                atom_count += 1
                if len(line) < 79:
                    type_errors += 1
                    continue
                charge_str = line[68:76].strip()
                if charge_str == '':
                    charge_errors += 1
                else:
                    try:
                        float(charge_str)
                    except ValueError:
                        charge_errors += 1
                atype = line[77:79].strip()
                if atype not in VALID_AD_TYPES:
                    type_errors += 1

        if atom_count == 0:
            return False, "No ATOM/HETATM records found"

        if charge_errors > 0:
            return False, f"{charge_errors}/{atom_count} atoms have invalid charges"
        if type_errors > 0:
            return False, f"{type_errors}/{atom_count} atoms have non-AutoDock4 types"

        return True, f"Valid: {atom_count} atoms, all AD4 types + charges OK"
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def _sanitize_pdbqt(filepath: str, is_ligand: bool = False) -> tuple:
    """Fix PDBQT issues: atom types, charges, ROOT/ENDROOT/TORSDOF for ligands, strip markers for receptor."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()

        lines = content.split('\n')
        fixed = 0
        out_lines = []
        AD_ELEMENTS = {
            'H': 'HD', 'C': 'C', 'N': 'NA', 'O': 'OA', 'F': 'F',
            'P': 'P', 'S': 'SA', 'Cl': 'Cl', 'Br': 'Br', 'I': 'I',
            'Na': 'Na', 'K': 'K', 'Ca': 'Ca', 'Fe': 'Fe', 'Zn': 'Zn',
            'Mg': 'Mg', 'Se': 'Se', 'B': 'B', 'Si': 'Si', 'Li': 'Li',
        }
        METAL_TYPES = {'Na', 'K', 'Ca', 'Fe', 'Zn', 'Mg', 'Se', 'B', 'Si', 'Li'}
        has_atom = False
        has_root = False
        has_endroot = False
        has_torsdof = False

        for line in lines:
            stripped = line.strip()

            if is_ligand:
                if stripped == 'ROOT':
                    has_root = True
                    out_lines.append(line)
                    continue
                if stripped == 'ENDROOT':
                    has_endroot = True
                    out_lines.append(line)
                    continue
                if stripped.startswith('TORSDOF'):
                    has_torsdof = True
                    out_lines.append(line)
                    continue
                if stripped.startswith('BRANCH') or stripped.startswith('ENDBRANCH'):
                    out_lines.append(line)
                    continue
            else:
                if stripped in ('ROOT', 'ENDROOT') or stripped.startswith('BRANCH') or stripped.startswith('ENDBRANCH'):
                    fixed += 1
                    continue
                if stripped.startswith('TORSDOF'):
                    fixed += 1
                    continue

            if line.startswith('ATOM') or line.startswith('HETATM'):
                has_atom = True
                if len(line) < 79:
                    line = line.rstrip() + ' ' * (79 - len(line.rstrip())) + '\n' if line.endswith('\n') else line.rstrip() + ' ' * (79 - len(line.rstrip()))
                    fixed += 1

                charge_str = line[68:76].strip()
                if charge_str == '':
                    line = line[:68] + '   0.000' + line[76:]
                    fixed += 1
                else:
                    try:
                        float(charge_str)
                    except ValueError:
                        line = line[:68] + '   0.000' + line[76:]
                        fixed += 1

                atype = line[77:79].strip()
                atype_valid = atype in VALID_AD_TYPES
                if not atype_valid:
                    element = line[12:16].strip()
                    if not element or element[0] not in 'CHONPSFClBrIMgZnFeCaKNaSeBSiLi':
                        element = line[76:78].strip()
                    element = (element or 'C').rstrip('0123456789')
                    if len(element) > 2:
                        element = element[:2].rstrip('0123456789')
                    default = AD_ELEMENTS.get(element, 'C')
                    line = line[:77] + default.ljust(2) + line[79:]
                    fixed += 1

            out_lines.append(line)

        if is_ligand and has_atom:
            if not has_root:
                atom_lines = [i for i, l in enumerate(out_lines) if l.startswith('ATOM') or l.startswith('HETATM')]
                if atom_lines:
                    out_lines.insert(atom_lines[0], 'ROOT')
                    fixed += 1
            if not has_endroot:
                atom_lines = [i for i, l in enumerate(out_lines) if l.startswith('ATOM') or l.startswith('HETATM')]
                if atom_lines:
                    out_lines.insert(atom_lines[-1] + 1, 'ENDROOT')
                    fixed += 1
            if not has_torsdof and has_atom:
                num_atoms = sum(1 for l in out_lines if l.startswith('ATOM') or l.startswith('HETATM'))
                torsdof = max(0, num_atoms - 5)
                out_lines.append(f'TORSDOF {torsdof}')
                fixed += 1

        with open(filepath, 'w') as f:
            f.write('\n'.join(out_lines))

        return (True, f"{fixed} fixes" if fixed else "No fixes needed", filepath)
    except Exception as e:
        return (False, f"Sanitizer error: {str(e)}", filepath)
