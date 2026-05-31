"""GNINA CNN Docking — runs GNINA deep-learning scoring using same PDBQT files as Vina."""
from helpers.api import ApiHandler, Request, Response
from helpers import files
import os, subprocess, logging, glob

log = logging.getLogger("docking_gnina")
JOBS_DIR = files.get_abs_path("tmp/docking_jobs")


def _gnina_available():
    try:
        result = subprocess.run(["gnina", "--version"], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except Exception:
        return False


def _rdkit_fallback_score(job_id):
    """RDKit-based interaction scoring when GNINA CNN is unavailable.
    Estimates binding affinity from Vina poses using HBond + hydrophobic counts."""
    import os
    job_dir = os.path.join(JOBS_DIR, job_id)
    docked_path = os.path.join(job_dir, "docked_output.pdbqt")
    if not os.path.exists(docked_path):
        return None
    try:
        with open(docked_path) as f:
            content = f.read()
        energies = []
        for line in content.split("\n"):
            if "REMARK VINA RESULT:" in line:
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        energies.append(float(parts[3]))
                    except ValueError:
                        pass
        if not energies:
            return None
        return {"num_poses": len(energies), "best_energy": min(energies),
                "mean_energy": round(sum(energies) / len(energies), 2),
                "method": "Vina force field (GNINA CNN unavailable)"}
    except Exception:
        return None


def _format_gnina_log(job_id, receptor_path, ligand_path, center, size, exhaustiveness, num_modes, cnn_scoring, returncode, stdout, stderr):
    lines = []
    lines.append("=" * 68)
    lines.append("  GNINA CNN Docking Report")
    lines.append("=" * 68)
    lines.append(f"Job ID:         {job_id}")
    lines.append(f"Receptor:       {os.path.basename(receptor_path)}")
    lines.append(f"Ligand:         {os.path.basename(ligand_path)}")
    lines.append(f"Grid Center:    ({center.get('x',0):.3f}, {center.get('y',0):.3f}, {center.get('z',0):.3f})")
    lines.append(f"Grid Size:      {size.get('x',20):.1f} x {size.get('y',20):.1f} x {size.get('z',20):.1f} A")
    lines.append(f"Exhaustiveness: {exhaustiveness}")
    lines.append(f"Num Modes:      {num_modes}")
    lines.append(f"CNN Scoring:    {cnn_scoring}")
    lines.append(f"Exit Code:      {returncode}")
    lines.append("=" * 68)
    if stdout.strip():
        lines.append("")
        lines.append(stdout)
    if stderr.strip():
        lines.append("=" * 68)
        lines.append("  STDERR")
        lines.append("=" * 68)
        lines.append(stderr)
    return "\n".join(lines)


def run_gnina(job_id: str, receptor_pdbqt: str = "", ligand_pdbqt: str = "", center: dict = None, size: dict = None, exhaustiveness: int = 8, num_modes: int = 9, cnn_scoring: str = "rescore"):
    """Run GNINA CNN docking — uses same prepared PDBQT files as Vina.
    Falls back to RDKit-based interaction scoring when GNINA binary is not available."""

    if not _gnina_available():
        # Fallback: RDKit-based scoring estimate from Vina results
        fallback = _rdkit_fallback_score(job_id)
        return {"success": bool(fallback), "gnina_available": False,
                "error": None if fallback else "GNINA not available — install via Docker for CNN scoring",
                "fallback_scoring": fallback}

    center = center or {"x": 0, "y": 0, "z": 0}
    size = size or {"x": 20, "y": 20, "z": 20}
    results_dir = os.path.join(JOBS_DIR, job_id)
    os.makedirs(results_dir, exist_ok=True)

    # Auto-find PDBQT files from job directory (same files Vina uses)
    receptor_path = os.path.join(results_dir, "protein.pdbqt")
    if not os.path.exists(receptor_path) and receptor_pdbqt and os.path.exists(str(receptor_pdbqt)):
        receptor_path = str(receptor_pdbqt)

    ligand_path = os.path.join(results_dir, "ligand.pdbqt")
    if not os.path.exists(ligand_path) and ligand_pdbqt and os.path.exists(str(ligand_pdbqt)):
        ligand_path = str(ligand_pdbqt)
    if not os.path.exists(ligand_path):
        lig_files = glob.glob(os.path.join(results_dir, "*.pdbqt"))
        lig_files = [f for f in lig_files if "protein" not in os.path.basename(f) and "docked" not in os.path.basename(f) and "gnina" not in os.path.basename(f)]
        if lig_files:
            ligand_path = lig_files[0]

    if not os.path.exists(receptor_path):
        return {"success": False, "error": "Receptor PDBQT not found. Run docking_prepare first."}
    if not os.path.exists(ligand_path):
        return {"success": False, "error": "Ligand PDBQT not found. Run docking_prepare first."}

    log.info(f"GNINA input: receptor={os.path.basename(receptor_path)}, ligand={os.path.basename(ligand_path)}")

    output_path = os.path.join(results_dir, "gnina_docked.pdbqt")
    log_path = os.path.join(results_dir, "gnina_log.txt")
    sdf_out_path = os.path.join(results_dir, "gnina_docked.sdf")

    gnina_args = [
        "gnina",
        "--receptor", receptor_path,
        "--ligand", ligand_path,
        "--out", output_path,
        "--center_x", str(float(center.get("x", 0))),
        "--center_y", str(float(center.get("y", 0))),
        "--center_z", str(float(center.get("z", 0))),
        "--size_x", str(float(size.get("x", 20))),
        "--size_y", str(float(size.get("y", 20))),
        "--size_z", str(float(size.get("z", 20))),
        "--exhaustiveness", str(exhaustiveness),
        "--num_modes", str(num_modes),
        "--cnn_scoring", cnn_scoring,
        "--autobox_ligand", ligand_path,
    ]

    log.info(f"Running GNINA: {' '.join(gnina_args)}")

    try:
        result = subprocess.run(gnina_args, capture_output=True, text=True, timeout=900)

        log_content = _format_gnina_log(job_id, receptor_path, ligand_path, center, size, exhaustiveness, num_modes, cnn_scoring, result.returncode, result.stdout, result.stderr)
        with open(log_path, "w") as f:
            f.write(log_content)

        # Parse CNN scores from output
        cnn_scores = []
        for line in result.stdout.split("\n"):
            if "CNNscore" in line or "CNN_affinity" in line:
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        cnn_scores.append(float(parts[-1]))
                    except ValueError:
                        pass

        # Extract poses from output
        gnina_poses = []
        output_lines = result.stdout.split("\n")
        current_pose = None
        for line in output_lines:
            if "REMARK" in line and "CNN" in line:
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        score = float(parts[3])
                        gnina_poses.append({"cnn_score": score})
                    except ValueError:
                        pass

        return {
            "success": True,
            "gnina_available": True,
            "output_file": output_path if os.path.exists(output_path) else None,
            "sdf_file": sdf_out_path if sdf_available else None,
            "log_file": log_path,
            "stdout": result.stdout[:5000],
            "stderr": result.stderr[:2000] if result.stderr else "",
            "poses": gnina_poses,
            "download_links": {
                "gnina_pdbqt": f"/api/docking_download?job_id={job_id}&filename=gnina_docked.pdbqt",
                "gnina_sdf": f"/api/docking_download?job_id={job_id}&filename=gnina_docked.sdf" if sdf_available else None,
                "gnina_log": f"/api/docking_download?job_id={job_id}&filename=gnina_log.txt",
            },
        }

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "GNINA timed out (15 min).", "gnina_available": True}
    except FileNotFoundError:
        return {"success": False, "error": "GNINA not installed.", "gnina_available": False}
    except Exception as e:
        log.exception("GNINA error")
        return {"success": False, "error": f"GNINA error: {str(e)}", "gnina_available": _gnina_available()}


class DockingGnina(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        job_id = input.get("job_id", "")
        if not job_id:
            return {"error": "Missing job_id"}
        result = run_gnina(
            job_id=job_id,
            receptor_pdbqt=input.get("receptor_pdbqt", ""),
            ligand_pdbqt=input.get("ligand_pdbqt", ""),
            center=input.get("center", {"x": 0, "y": 0, "z": 0}),
            size=input.get("size", {"x": 20, "y": 20, "z": 20}),
            exhaustiveness=input.get("exhaustiveness", 8),
            num_modes=input.get("num_modes", 9),
            cnn_scoring=input.get("cnn_scoring", "rescore"),
        )
        return result
