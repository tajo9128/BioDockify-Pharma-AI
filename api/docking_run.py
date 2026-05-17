from helpers.api import ApiHandler, Request, Response
from helpers import files
import os
import subprocess
import json
import logging

log = logging.getLogger("docking_run")

JOBS_DIR = files.get_abs_path("tmp/docking_jobs")


class DockingRun(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        job_id = input.get("job_id", "")
        receptor = input.get("receptor_pdbqt", "") or input.get("receptor", "")
        ligand = input.get("ligand_pdbqt", "") or input.get("ligand", "")
        center = input.get("center", {"x": 0, "y": 0, "z": 0})
        size = input.get("size", {"x": 20, "y": 20, "z": 20})
        exhaustiveness = input.get("exhaustiveness", 8)
        num_modes = input.get("num_modes", 9)

        if not job_id:
            return {"error": "Missing job_id"}

        results_dir = os.path.join(JOBS_DIR, job_id)

        # Auto-find receptor/ligand PDBQT files from job directory if not specified
        if not receptor or not os.path.exists(receptor):
            candidate = os.path.join(results_dir, "protein.pdbqt")
            if os.path.exists(candidate):
                receptor = candidate
        if not ligand or not os.path.exists(ligand):
            import glob
            lig_files = glob.glob(os.path.join(results_dir, "*.pdbqt"))
            lig_files = [f for f in lig_files if "protein" not in os.path.basename(f)]
            if lig_files:
                ligand = lig_files[0]

        if not receptor or not os.path.exists(receptor):
            return {"error": "Receptor PDBQT not found. Run docking_prepare first."}
        if not ligand or not os.path.exists(ligand):
            return {"error": "Ligand PDBQT not found. Run docking_prepare first."}

        os.makedirs(results_dir, exist_ok=True)
        output_path = os.path.join(results_dir, "docked_output.pdbqt")
        log_path = os.path.join(results_dir, "vina_log.txt")
        sdf_output_path = os.path.join(results_dir, "docked_poses.sdf")

        # Build Vina command
        vina_args = [
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
            "--exhaustiveness", str(exhaustiveness),
            "--num_modes", str(num_modes),
        ]

        log.info(f"Running Vina: {' '.join(vina_args)}")

        try:
            result = subprocess.run(
                vina_args,
                capture_output=True, text=True, timeout=600
            )

            # Save log file
            log_content = []
            log_content.append("=" * 60)
            log_content.append("  AutoDock Vina Docking Log")
            log_content.append("=" * 60)
            log_content.append(f"Job ID: {job_id}")
            log_content.append(f"Receptor: {receptor}")
            log_content.append(f"Ligand: {ligand}")
            log_content.append(f"Grid Center: ({center.get('x',0)}, {center.get('y',0)}, {center.get('z',0)})")
            log_content.append(f"Grid Size: ({size.get('x',20)}x{size.get('y',20)}x{size.get('z',20)})")
            log_content.append(f"Exhaustiveness: {exhaustiveness}")
            log_content.append(f"Num Modes: {num_modes}")
            log_content.append(f"Return Code: {result.returncode}")
            log_content.append("-" * 60)
            log_content.append("STDOUT:")
            log_content.append(result.stdout)
            if result.stderr:
                log_content.append("-" * 60)
                log_content.append("STDERR:")
                log_content.append(result.stderr)
            log_content.append("=" * 60)

            with open(log_path, "w") as f:
                f.write("\n".join(log_content))

            # Check for Vina errors
            if result.returncode != 0:
                error_msg = result.stderr or "Vina exited with non-zero code"
                return {"status": "error", "error": f"Vina failed: {error_msg[:500]}", "stdout": result.stdout[:1000]}

            # Parse poses from stdout
            poses = []
            for line in result.stdout.split("\n"):
                line_stripped = line.strip()
                if line_stripped.startswith("REMARK VINA RESULT:"):
                    parts = line_stripped.split()
                    if len(parts) >= 4:
                        try:
                            energy = float(parts[3])
                            # RMSD values if available
                            rmsd_lb = float(parts[4]) if len(parts) >= 5 else None
                            rmsd_ub = float(parts[5]) if len(parts) >= 6 else None
                            poses.append({
                                "energy": energy,
                                "rmsd_lb": rmsd_lb,
                                "rmsd_ub": rmsd_ub,
                            })
                        except (ValueError, IndexError):
                            pass

            # If no REMARK lines, parse from output file
            if not poses:
                try:
                    with open(output_path) as f:
                        current_pose = None
                        for line in f:
                            if line.startswith("MODEL"):
                                current_pose = {"energy": None}
                            elif line.strip().startswith("REMARK VINA RESULT:") and current_pose is not None:
                                parts = line.strip().split()
                                if len(parts) >= 4:
                                    try:
                                        current_pose["energy"] = float(parts[3])
                                        current_pose["rmsd_lb"] = float(parts[4]) if len(parts) >= 5 else None
                                        current_pose["rmsd_ub"] = float(parts[5]) if len(parts) >= 6 else None
                                    except (ValueError, IndexError):
                                        pass
                            elif line.startswith("ENDMDL") and current_pose is not None:
                                poses.append(current_pose)
                                current_pose = None
                except Exception:
                    pass

            # Try converting to SDF for better compatibility
            sdf_available = False
            try:
                conv = subprocess.run(
                    ["obabel", output_path, "-O", sdf_output_path],
                    capture_output=True, text=True, timeout=30
                )
                sdf_available = conv.returncode == 0 and os.path.exists(sdf_output_path)
            except Exception:
                pass

            return {
                "status": "complete",
                "job_id": job_id,
                "poses": poses,
                "num_poses": len(poses),
                "output_file": output_path if os.path.exists(output_path) else None,
                "sdf_file": sdf_output_path if sdf_available else None,
                "log_file": log_path if os.path.exists(log_path) else None,
                "stdout": result.stdout[:3000],
                "stderr": result.stderr[:1000] if result.stderr else "",
                "download_links": {
                    "pdbqt": f"/api/docking_download/{job_id}/docked_output.pdbqt",
                    "sdf": f"/api/docking_download/{job_id}/docked_poses.sdf" if sdf_available else None,
                    "log": f"/api/docking_download/{job_id}/vina_log.txt",
                },
            }

        except subprocess.TimeoutExpired:
            msg = "Docking timed out (10 min). Try a smaller grid or protein."
            with open(log_path, "w") as f:
                f.write(msg)
            return {"status": "error", "error": msg}
        except FileNotFoundError:
            msg = "AutoDock Vina (vina) not installed. Run: apt install autodock-vina"
            return {"status": "error", "error": msg}
        except Exception as e:
            msg = f"Docking error: {str(e)}"
            log.exception(msg)
            return {"status": "error", "error": msg}
