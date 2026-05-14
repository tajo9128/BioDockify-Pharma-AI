from helpers.api import ApiHandler, Request, Response
from helpers import files
import os
import subprocess


JOBS_DIR = files.get_abs_path("tmp/docking_jobs")


class DockingRun(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        job_id = input.get("job_id", "")
        receptor = input.get("receptor_pdbqt", "")
        ligand = input.get("ligand_pdbqt", "")
        center = input.get("center", {"x": 0, "y": 0, "z": 0})
        size = input.get("size", {"x": 20, "y": 20, "z": 20})

        if not job_id or not receptor or not ligand:
            return {"error": "Missing job parameters"}

        results_dir = os.path.join(JOBS_DIR, job_id)
        os.makedirs(results_dir, exist_ok=True)
        output_path = os.path.join(results_dir, "docking_results.pdbqt")

        try:
            result = subprocess.run(
                [
                    "vina",
                    "--receptor", receptor,
                    "--ligand", ligand,
                    "--out", output_path,
                    "--center_x", str(center.get("x", 0)),
                    "--center_y", str(center.get("y", 0)),
                    "--center_z", str(center.get("z", 0)),
                    "--size_x", str(size.get("x", 20)),
                    "--size_y", str(size.get("y", 20)),
                    "--size_z", str(size.get("z", 20)),
                    "--exhaustiveness", "8",
                    "--num_modes", "9",
                ],
                capture_output=True, text=True, timeout=600
            )

            poses = []
            for line in result.stdout.split("\n"):
                if line.strip().startswith("REMARK VINA RESULT:"):
                    parts = line.strip().split()
                    if len(parts) >= 4:
                        try:
                            energy = float(parts[3])
                            poses.append({"energy": energy})
                        except ValueError:
                            pass

            if not poses:
                with open(output_path) as f:
                    for line in f:
                        if line.startswith("MODEL"):
                            poses.append({"energy": None})
                        elif line.strip().startswith("REMARK VINA RESULT:") and poses:
                            parts = line.strip().split()
                            if len(parts) >= 4:
                                try:
                                    poses[-1]["energy"] = float(parts[3])
                                except ValueError:
                                    pass

            return {
                "status": "complete",
                "job_id": job_id,
                "poses": poses,
                "num_poses": len(poses),
                "stdout": result.stdout[:2000],
                "stderr": result.stderr[:1000] if result.stderr else "",
            }

        except subprocess.TimeoutExpired:
            return {"status": "error", "error": "Docking timed out (10 min limit)"}
        except FileNotFoundError:
            return {"status": "error", "error": "AutoDock Vina not installed"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
