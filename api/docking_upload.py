"""Upload external docking results for deep analysis.

Accepts receptor (PDB/PDBQT) + docked ligand (PDBQT/SDF) from any platform
(AutoDock Vina, Glide, GOLD, AutoDock-GPU, etc.) and creates a job directory
compatible with the deep analysis pipeline.
"""
from helpers.api import ApiHandler, Request, Response
from helpers import files
import os, uuid, logging

log = logging.getLogger("docking_upload")
JOBS_DIR = files.get_abs_path("tmp/docking_jobs")


class DockingUpload(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        try:
            return self._process_upload(input, request)
        except Exception as e:
            log.exception(f"Upload error: {e}")
            return {"error": str(e)}

    def _process_upload(self, input: dict, request: Request) -> dict:
        MAX_RECEPTOR_SIZE = 50_000_000  # 50 MB
        MAX_LIGAND_SIZE = 10_000_000    # 10 MB

        # Get file contents from request
        receptor_content = input.get("receptor_content", "").strip()
        receptor_filename = input.get("receptor_filename", "receptor.pdb")
        ligand_content = input.get("ligand_content", "").strip()
        ligand_filename = input.get("ligand_filename", "docked_output.pdbqt")

        if not receptor_content:
            return {"error": "Receptor structure file required (PDB or PDBQT)"}
        if not ligand_content:
            return {"error": "Docked ligand file required (PDBQT or SDF with poses)"}
        if len(receptor_content) > MAX_RECEPTOR_SIZE:
            return {"error": f"Receptor file too large (max {MAX_RECEPTOR_SIZE // 1_000_000} MB)"}
        if len(ligand_content) > MAX_LIGAND_SIZE:
            return {"error": f"Ligand file too large (max {MAX_LIGAND_SIZE // 1_000_000} MB)"}

        # Create job directory
        job_id = f"ext-{uuid.uuid4().hex[:6]}"
        job_dir = os.path.join(JOBS_DIR, job_id)
        os.makedirs(job_dir, exist_ok=True)

        # Determine receptor format and save
        receptor_ext = receptor_filename.rsplit(".", 1)[-1].lower() if "." in receptor_filename else "pdb"
        if receptor_ext in ("pdbqt",):
            receptor_path = os.path.join(job_dir, "protein.pdbqt")
        else:
            receptor_path = os.path.join(job_dir, "protein.pdb")
        with open(receptor_path, "w", encoding="utf-8") as f:
            f.write(receptor_content)

        # If receptor is PDB, also save a copy for analysis
        if receptor_ext in ("pdb", "ent"):
            pdb_copy = os.path.join(job_dir, "protein.pdb")
            if receptor_path != pdb_copy:
                with open(pdb_copy, "w", encoding="utf-8") as f:
                    f.write(receptor_content)

        # Determine ligand format and save
        ligand_ext = ligand_filename.rsplit(".", 1)[-1].lower() if "." in ligand_filename else "pdbqt"
        if ligand_ext == "sdf":
            ligand_path = os.path.join(job_dir, "docked_poses.sdf")
        else:
            ligand_path = os.path.join(job_dir, "docked_output.pdbqt")
        with open(ligand_path, "w", encoding="utf-8") as f:
            f.write(ligand_content)

        # Parse pose count and energies
        poses = []
        if ligand_ext == "pdbqt":
            for line in ligand_content.split("\n"):
                if "REMARK VINA RESULT:" in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        try:
                            poses.append(float(parts[3]))
                        except ValueError:
                            pass
            # Also try MODEL/ENDMDL counting
            if not poses:
                model_count = ligand_content.count("MODEL")
                if model_count > 0:
                    poses = [0.0] * model_count
        elif ligand_ext == "sdf":
            model_count = ligand_content.count("$$$$")
            if model_count == 0 and "V2000" in ligand_content:
                model_count = 1
            poses = [0.0] * max(model_count, 1)

        return {
            "success": True,
            "job_id": job_id,
            "receptor_file": receptor_filename,
            "ligand_file": ligand_filename,
            "num_poses": len(poses),
            "energies": poses,
            "message": f"Uploaded {len(poses)} poses. Use Job ID '{job_id}' for deep analysis.",
        }
