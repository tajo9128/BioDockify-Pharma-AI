from helpers.api import ApiHandler, Request, Response
from helpers import files
import os
import subprocess
import json
import logging
import re

log = logging.getLogger("docking_run")

JOBS_DIR = files.get_abs_path("tmp/docking_jobs")


def _compute_consensus_score(poses, gnina_result=None):
    """Combine Vina + GNINA CNN scores into Z-score normalized consensus."""
    import numpy as np
    vina_scores = np.array([p.get("energy", 0) for p in poses], dtype=np.float64)
    gnina_scores = None
    if gnina_result and gnina_result.get("success") and gnina_result.get("poses"):
        gnina_scores = np.array([p.get("cnn_score", 0) for p in gnina_result.get("poses", [])], dtype=np.float64)
    n_poses = len(vina_scores)
    consensus = []
    for i in range(n_poses):
        ze = (vina_scores[i] - vina_scores.mean()) / (vina_scores.std() + 1e-10) if n_poses > 1 else 0
        zgn = 0
        if gnina_scores is not None and i < len(gnina_scores):
            zgn = (gnina_scores[i] - gnina_scores.mean()) / (gnina_scores.std() + 1e-10) if len(gnina_scores) > 1 else 0
        consensus_z = float(0.6 * ze + 0.4 * zgn) if gnina_scores is not None else float(ze)
        consensus.append({"pose_index": i, "vina_energy": float(vina_scores[i]),
            "gnina_cnn": float(gnina_scores[i]) if gnina_scores is not None and i < len(gnina_scores) else None,
            "consensus_z": round(consensus_z, 4), "vina_z": round(float(ze), 4),
            "gnina_z": round(float(zgn), 4) if gnina_scores is not None else None})
    consensus.sort(key=lambda c: c["consensus_z"])
    return {"num_poses": n_poses, "per_pose": consensus, "best_consensus_z": consensus[0]["consensus_z"] if consensus else None}


def _parse_energy_table(stdout: str):
    """Parse Vina's detailed energy table (mode | affinity | rmsd l.b. | rmsd u.b.) from stdout."""
    lines = stdout.split("\n")
    table_start = -1
    for i, line in enumerate(lines):
        if "mode" in line.lower() and "affinity" in line.lower():
            table_start = i + 1
            break
        if "-----+" in line:
            table_start = i + 1
            break

    entries = []
    if table_start >= 0:
        for line in lines[table_start:]:
            stripped = line.strip()
            if not stripped:
                break
            parts = stripped.split()
            if len(parts) >= 2:
                try:
                    mode = int(parts[0])
                    affinity = float(parts[1])
                    rmsd_lb = float(parts[2]) if len(parts) >= 3 else None
                    rmsd_ub = float(parts[3]) if len(parts) >= 4 else None
                    entries.append({
                        "mode": mode,
                        "affinity": affinity,
                        "rmsd_lb": rmsd_lb,
                        "rmsd_ub": rmsd_ub,
                    })
                except (ValueError, IndexError):
                    pass
    return entries


def _format_log(
    job_id: str,
    receptor: str,
    ligand: str,
    center: dict,
    size: dict,
    exhaustiveness: int,
    num_modes: int,
    returncode: int,
    stdout: str,
    stderr: str,
    table_entries: list,
) -> str:
    lines = []
    lines.append("=" * 68)
    lines.append("  AutoDock Vina — Molecular Docking Report")
    lines.append("=" * 68)
    lines.append("")
    lines.append("Job ID:         " + job_id)
    lines.append("Receptor:       " + os.path.basename(receptor))
    lines.append("Ligand:         " + os.path.basename(ligand))
    lines.append(f"Grid Center:    ({center.get('x',0):.3f}, {center.get('y',0):.3f}, {center.get('z',0):.3f})")
    lines.append(f"Grid Size:      {size.get('x',20):.1f} x {size.get('y',20):.1f} x {size.get('z',20):.1f} \u00c5")
    lines.append(f"Exhaustiveness: {exhaustiveness}")
    lines.append(f"Num Modes:      {num_modes}")
    lines.append(f"Exit Code:      {returncode}")
    lines.append("")

    if table_entries:
        lines.append("-" * 68)
        lines.append(f"{'Mode':>5}  {'Affinity (kcal/mol)':>22}  {'RMSD l.b.':>10}  {'RMSD u.b.':>10}")
        lines.append("-" * 68)
        for e in table_entries:
            rmsd_lb = f"{e.get('rmsd_lb',0):.3f}" if e.get('rmsd_lb') is not None else "  ---"
            rmsd_ub = f"{e.get('rmsd_ub',0):.3f}" if e.get('rmsd_ub') is not None else "  ---"
            lines.append(f"{e['mode']:>5}  {e['affinity']:>22.2f}  {rmsd_lb:>10}  {rmsd_ub:>10}")
        lines.append("-" * 68)
        lines.append("")
        if table_entries:
            best = table_entries[0]
            lines.append(f"Best Binding Affinity:  {best['affinity']:.2f} kcal/mol  (mode {best['mode']})")
        lines.append(f"Total Poses Found:      {len(table_entries)}")
        lines.append("")

    lines.append("=" * 68)
    lines.append("  Raw Vina STDOUT")
    lines.append("=" * 68)
    lines.append(stdout)

    if stderr.strip():
        lines.append("=" * 68)
        lines.append("  Raw Vina STDERR")
        lines.append("=" * 68)
        lines.append(stderr)

    lines.append("=" * 68)
    return "\n".join(lines)


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

        # ALWAYS sanitize PDBQT files before passing to Vina (obabel can produce bad atom types)
        from api.docking_prepare import _sanitize_pdbqt, _validate_pdbqt
        _, detail_r, _ = _sanitize_pdbqt(receptor, is_ligand=False)
        _, detail_l, _ = _sanitize_pdbqt(ligand, is_ligand=True)
        ok, msg = _validate_pdbqt(receptor)
        if not ok:
            return {"error": f"Receptor PDBQT invalid after sanitization: {msg}", "detail": detail_r, "action": "reprepare"}
        ok, msg = _validate_pdbqt(ligand)
        if not ok:
            return {"error": f"Ligand PDBQT invalid after sanitization: {msg}", "detail": detail_l, "action": "reprepare"}

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

            # Parse detailed energy table from Vina stdout
            table_entries = _parse_energy_table(result.stdout)

            # Write structured log file
            log_content = _format_log(
                job_id=job_id,
                receptor=receptor,
                ligand=ligand,
                center=center,
                size=size,
                exhaustiveness=exhaustiveness,
                num_modes=num_modes,
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                table_entries=table_entries,
            )
            with open(log_path, "w") as f:
                f.write(log_content)

            # Check for Vina errors
            if result.returncode != 0:
                error_msg = result.stderr or "Vina exited with non-zero code"
                return {"status": "error", "error": f"Vina failed: {error_msg[:500]}", "stdout": result.stdout[:1000]}

            # Parse poses: prefer detailed table, fall back to REMARK lines, then output file
            poses = []
            if table_entries:
                for e in table_entries:
                    poses.append({
                        "energy": e["affinity"],
                        "rmsd_lb": e.get("rmsd_lb"),
                        "rmsd_ub": e.get("rmsd_ub"),
                    })
            else:
                # Fallback: parse REMARK VINA RESULT lines from stdout
                for line in result.stdout.split("\n"):
                    line_stripped = line.strip()
                    if line_stripped.startswith("REMARK VINA RESULT:"):
                        parts = line_stripped.split()
                        if len(parts) >= 4:
                            try:
                                energy = float(parts[3])
                                rmsd_lb = float(parts[4]) if len(parts) >= 5 else None
                                rmsd_ub = float(parts[5]) if len(parts) >= 6 else None
                                poses.append({
                                    "energy": energy,
                                    "rmsd_lb": rmsd_lb,
                                    "rmsd_ub": rmsd_ub,
                                })
                            except (ValueError, IndexError):
                                pass

            # If still no poses, parse from output PDBQT file
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

            # CRITICAL: sort poses by energy ascending (most-negative = strongest binding = 1st)
            poses.sort(key=lambda p: p.get("energy", 0) if p.get("energy") is not None else 0)

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

            # ── GNINA CNN Docking (auto-chain after Vina) ──
            gnina_result = None
            try:
                from api.docking_gnina import run_gnina
                gnina_result = run_gnina(
                    job_id=job_id,
                    receptor_pdbqt=receptor,
                    ligand_pdbqt=ligand,
                    center=center,
                    size=size,
                    exhaustiveness=exhaustiveness,
                    num_modes=num_modes,
                    cnn_scoring="rescore",
                )
                if gnina_result.get("success"):
                    log.info(f"GNINA completed for job {job_id}")
                else:
                    log.warning(f"GNINA skipped or failed: {gnina_result.get('error', 'unknown')}")
            except Exception as gnina_err:
                log.warning(f"GNINA chaining error: {gnina_err}")

            # ── Consensus Z-Score Scoring ──
            consensus = _compute_consensus_score(poses, gnina_result)

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
                "consensus": consensus,
                "download_links": {
                    "pdbqt": f"/api/docking_download?job_id={job_id}&filename=docked_output.pdbqt",
                    "sdf": f"/api/docking_download?job_id={job_id}&filename=docked_poses.sdf" if sdf_available else None,
                    "log": f"/api/docking_download?job_id={job_id}&filename=vina_log.txt",
                    "gnina_pdbqt": gnina_result.get("download_links", {}).get("gnina_pdbqt") if gnina_result else None,
                    "gnina_sdf": gnina_result.get("download_links", {}).get("gnina_sdf") if gnina_result else None,
                    "gnina_log": gnina_result.get("download_links", {}).get("gnina_log") if gnina_result else None,
                },
                "gnina": gnina_result,
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
