from helpers.api import ApiHandler, Request, Response
from helpers import files
import os
import subprocess
import json
import logging
import re

log = logging.getLogger("docking_run")

JOBS_DIR = files.get_abs_path("tmp/docking_jobs")


def _compute_consensus_score(poses):
    """Simple Vina-only scoring (MM-GBSA handles multi-score consensus)."""
    import numpy as np
    vina_scores = np.array([p.get("energy", 0) for p in poses], dtype=np.float64)
    n_poses = len(vina_scores)
    consensus = []
    for i in range(n_poses):
        ze = (vina_scores[i] - vina_scores.mean()) / (vina_scores.std() + 1e-10) if n_poses > 1 else 0
        consensus.append({
            "pose_index": i,
            "vina_energy": float(vina_scores[i]),
            "vina_z": round(float(ze), 4),
        })
    consensus.sort(key=lambda c: c["vina_z"])
    return {"num_poses": n_poses, "per_pose": consensus}


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
        # ── BATCH / VIRTUAL SCREENING MODE ──
        # If input contains "smiles_list" or "ligand_list", dock multiple compounds
        # in parallel against the same receptor. Returns ranked list by binding energy.
        smiles_list = input.get("smiles_list", [])
        ligand_list = input.get("ligand_list", [])
        if smiles_list or ligand_list:
            return await self._batch_screen(input, smiles_list, ligand_list)

        job_id = input.get("job_id", "")
        receptor = input.get("receptor_pdbqt", "") or input.get("receptor", "")
        ligand = input.get("ligand_pdbqt", "") or input.get("ligand", "")
        center = input.get("center", {"x": 0, "y": 0, "z": 0})
        size = input.get("size", {"x": 20, "y": 20, "z": 20})
        exhaustiveness = input.get("exhaustiveness", 64)
        if exhaustiveness < 32:
            log.warning(f"Exhaustiveness={exhaustiveness} is below 32 — results may not be reproducible. "
                        f"Journals recommend >= 32 for publication-quality docking.")
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
            "--seed", "42",
        ]

        log.info(f"Running Vina: {' '.join(vina_args)}")

        try:
            import asyncio
            result = await asyncio.to_thread(
                subprocess.run,
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
                import asyncio
                conv = await asyncio.to_thread(
                    subprocess.run,
                    ["obabel", output_path, "-O", sdf_output_path],
                    capture_output=True, text=True, timeout=30
                )
                sdf_available = conv.returncode == 0 and os.path.exists(sdf_output_path)
            except Exception:
                pass

            # ── MM-GBSA Free Energy Scoring (CPU-only, no MD) ──
            mmgbsa_result = None
            try:
                from api.docking_mmgbsa import mmgbsa_score
                mmgbsa_result = mmgbsa_score(job_id=job_id)
                if mmgbsa_result.get("success"):
                    log.info(f"MM-GBSA scoring completed for job {job_id}")
                else:
                    log.warning(f"MM-GBSA scoring failed: {mmgbsa_result.get('error', 'unknown')}")
            except Exception as mmgbsa_err:
                log.warning(f"MM-GBSA scoring error: {mmgbsa_err}")

            # ── AUTO-STORE to Knowledge Base ──
            try:
                from modules.knowledge.auto_store import auto_store, auto_store_file
                result_summary = {
                    "job_id": job_id,
                    "num_poses": len(poses),
                    "poses": poses,
                    "mmgbsa": mmgbsa_result,
                }
                lig_name = input.get("ligand_smiles", input.get("ligand_name", "compound"))[:30]
                auto_store("docking_run", f"Docking: {lig_name}", result_summary,
                           source="AutoDock Vina", tags=["docking", "vina", lig_name])
                if os.path.exists(output_path):
                    auto_store_file("docking_run", f"Docked poses: {lig_name}", output_path,
                                   source="AutoDock Vina", tags=["docking", "pdbqt"])
            except Exception as kb_err:
                log.debug(f"KB auto-store (non-fatal): {kb_err}")

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
                "mmgbsa": mmgbsa_result,
                "download_links": {
                    "pdbqt": f"/api/docking_download?job_id={job_id}&filename=docked_output.pdbqt",
                    "sdf": f"/api/docking_download?job_id={job_id}&filename=docked_poses.sdf" if sdf_available else None,
                    "log": f"/api/docking_download?job_id={job_id}&filename=vina_log.txt",
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

    async def _batch_screen(self, input: dict, smiles_list: list, ligand_list: list) -> dict:
        """Virtual screening: dock multiple ligands against one receptor in parallel.

        Args:
            smiles_list: List of SMILES strings to dock (will be converted to PDBQT)
            ligand_list: List of pre-prepared PDBQT file paths
            receptor: Receptor PDBQT path (required)
            center/size/exhaustiveness: Same as single docking

        Returns:
            Ranked list of compounds by binding energy (best first)
        """
        import asyncio
        from api.docking_prepare import _sanitize_pdbqt

        receptor = input.get("receptor_pdbqt", "") or input.get("receptor", "")
        center = input.get("center", {"x": 0, "y": 0, "z": 0})
        size = input.get("size", {"x": 20, "y": 20, "z": 20})
        exhaustiveness = input.get("exhaustiveness", 32)
        num_modes = input.get("num_modes", 9)
        screen_id = input.get("job_id") or f"screen_{int(time.time())}"

        if not receptor or not os.path.exists(receptor):
            return {"error": "receptor_pdbqt path required for batch screening"}

        screen_dir = os.path.join(JOBS_DIR, screen_id)
        os.makedirs(screen_dir, exist_ok=True)

        # Sanitize receptor once
        _sanitize_pdbqt(receptor, is_ligand=False)

        # Build list of (compound_id, ligand_path) to dock
        compounds = []
        for i, smi in enumerate(smiles_list):
            compound_id = f"compound_{i+1}"
            # Convert SMILES to PDBQT using Meeko
            try:
                lig_pdbqt = os.path.join(screen_dir, f"{compound_id}.pdbqt")
                proc = await asyncio.to_thread(
                    subprocess.run,
                    ["mk_prepare_ligand.py", "-i", "/dev/stdin", "-o", lig_pdbqt],
                    input=smi, capture_output=True, text=True, timeout=30
                )
                if os.path.exists(lig_pdbqt):
                    compounds.append((compound_id, lig_pdbqt, smi))
            except Exception as e:
                log.warning(f"Failed to prepare {compound_id} from SMILES: {e}")

        for lig_path in ligand_list:
            if os.path.exists(lig_path):
                compound_id = os.path.splitext(os.path.basename(lig_path))[0]
                compounds.append((compound_id, lig_path, ""))

        if not compounds:
            return {"error": "No valid ligands to screen. Provide smiles_list or ligand_list."}

        log.info(f"[Virtual Screening] Screening {len(compounds)} compounds against {receptor}")

        async def _dock_one(compound_id, lig_path, smiles):
            """Dock a single ligand. Returns result dict."""
            try:
                _sanitize_pdbqt(lig_path, is_ligand=True)
                out_path = os.path.join(screen_dir, f"{compound_id}_docked.pdbqt")
                log_path = os.path.join(screen_dir, f"{compound_id}_log.txt")

                cmd = [
                    "vina",
                    "--receptor", receptor,
                    "--ligand", lig_path,
                    "--center_x", str(center["x"]),
                    "--center_y", str(center["y"]),
                    "--center_z", str(center["z"]),
                    "--size_x", str(size["x"]),
                    "--size_y", str(size["y"]),
                    "--size_z", str(size["z"]),
                    "--exhaustiveness", str(exhaustiveness),
                    "--num_modes", str(num_modes),
                    "--out", out_path,
                    "--log", log_path,
                    "--cpu", "2",  # limit CPU per compound for parallelism
                ]
                proc = await asyncio.to_thread(
                    subprocess.run, cmd,
                    capture_output=True, text=True, timeout=300
                )
                # Parse best energy from log
                best_energy = None
                if os.path.exists(log_path):
                    with open(log_path) as f:
                        for line in f:
                            if line.strip().startswith("1"):
                                parts = line.split()
                                if len(parts) >= 2:
                                    best_energy = float(parts[1])
                                break
                return {
                    "compound_id": compound_id,
                    "smiles": smiles,
                    "binding_energy": best_energy,
                    "status": "docked" if best_energy is not None else "failed",
                    "output": out_path,
                }
            except Exception as e:
                return {"compound_id": compound_id, "smiles": smiles,
                        "binding_energy": None, "status": f"error: {e}"}

        # Run all dockings in parallel (max 4 concurrent to avoid CPU overload)
        semaphore = asyncio.Semaphore(4)

        async def _docked(c):
            async with semaphore:
                return await _dock_one(*c)

        results = await asyncio.gather(*[_docked(c) for c in compounds])

        # Rank by binding energy (most negative = best)
        docked = [r for r in results if r["binding_energy"] is not None]
        failed = [r for r in results if r["binding_energy"] is None]
        docked.sort(key=lambda r: r["binding_energy"])

        # Store results to KB
        try:
            from modules.knowledge.auto_store import auto_store
            auto_store(
                "docking_run",
                f"Virtual Screening: {len(docked)}/{len(compounds)} compounds docked",
                {"screen_id": screen_id, "compounds_screened": len(compounds),
                 "compounds_docked": len(docked), "compounds_failed": len(failed),
                 "top_10": docked[:10]},
                source="AutoDock Vina Virtual Screening",
                tags=["docking", "virtual_screening", "batch"],
                category="docking",
            )
        except Exception:
            pass

        return {
            "status": "ok",
            "screen_id": screen_id,
            "total_compounds": len(compounds),
            "successfully_docked": len(docked),
            "failed": len(failed),
            "ranked_results": docked,
            "failed_compounds": failed,
            "message": f"Virtual screening complete: {len(docked)}/{len(compounds)} compounds docked. "
                       f"Best binding energy: {docked[0]['binding_energy'] if docked else 'N/A'} kcal/mol",
        }
