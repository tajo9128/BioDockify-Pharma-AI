from helpers.api import ApiHandler, Request, Response
from helpers import files
import os
import subprocess


class PoseGet(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        job_id = input.get("job_id", "")
        pose_index = input.get("pose", 0)

        if not job_id:
            return {"error": "job_id required"}

        # Look for docking results
        results_dir = files.get_abs_path(f"tmp/docking_jobs/{job_id}")
        pdbqt_path = os.path.join(results_dir, "docking_results.pdbqt")
        lig_pdbqt = os.path.join(results_dir, f"{input.get('ligand_name', 'ligand')}.pdbqt")

        if not os.path.exists(pdbqt_path):
            return {"error": "Results not found"}

        try:
            # Extract the requested pose from multi-model PDBQT
            pose_pdbqt = os.path.join(results_dir, f"pose_{pose_index}.pdbqt")
            with open(pdbqt_path) as f:
                content = f.read()

            models = content.split("MODEL")
            if pose_index + 1 < len(models):
                pose_content = "MODEL" + models[pose_index + 1]
                # Get only this pose
                parts = pose_content.split("ENDMDL")
                if len(parts) > 0:
                    pose_content = parts[0] + "ENDMDL"
            else:
                pose_content = content

            with open(pose_pdbqt, "w") as f:
                f.write(pose_content)

            # Convert to PDB for NGL Viewer
            pose_pdb = os.path.join(results_dir, f"pose_{pose_index}.pdb")
            subprocess.run(
                ["obabel", pose_pdbqt, "-O", pose_pdb],
                capture_output=True, text=True, timeout=30
            )

            # Also convert ligand to SDF for better display
            lig_sdf = os.path.join(results_dir, "ligand.sdf")
            if os.path.exists(lig_pdbqt) and not os.path.exists(lig_sdf):
                subprocess.run(
                    ["obabel", lig_pdbqt, "-O", lig_sdf],
                    capture_output=True, text=True, timeout=30
                )

            # Read PDB content
            pdb_content = ""
            if os.path.exists(pose_pdb):
                with open(pose_pdb) as f:
                    pdb_content = f.read()

            sdf_content = ""
            if os.path.exists(lig_sdf):
                with open(lig_sdf) as f:
                    sdf_content = f.read()

            return {
                "pdb": pdb_content,
                "sdf": sdf_content,
                "pose": pose_index,
                "job_id": job_id,
            }

        except Exception as e:
            return {"error": str(e)}
