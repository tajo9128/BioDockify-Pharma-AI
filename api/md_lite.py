"""MD Lite API — OpenMM molecular dynamics simulation handler."""
from helpers.api import ApiHandler, Request
from helpers import files
import os, json, time, uuid, asyncio, threading, logging, shutil

log = logging.getLogger("md_lite")
WORKDIR = files.get_abs_path("usr/md-lite")
os.makedirs(WORKDIR, exist_ok=True)

_jobs = {}  # in-memory job tracking: job_id -> threading.Thread


def _write_status(job_dir, status, extra=None):
    """Write status.json directly (used before an MDEngine exists)."""
    try:
        data = {"status": status, "timestamp": time.time(),
                "phase": status, "progress_pct": 0}
        if extra:
            data.update(extra)
        os.makedirs(job_dir, exist_ok=True)
        with open(os.path.join(job_dir, "status.json"), "w") as f:
            json.dump(data, f)
    except Exception:
        pass


def _friendly_error(msg):
    if "No valid ATOM" in msg or "no valid ATOM" in msg:
        return "PDB file is empty or contains no valid atomic coordinates. Upload a valid protein structure."
    if "invalid literal for int()" in msg or "PdbStructure" in msg:
        return ("PDB file format error. The file contains malformed ATOM/HETATM records. "
                "Upload a clean .pdb file from RCSB PDB or your docking software. "
                "Tip: If using a docked complex, ensure the protein has all hydrogens and "
                "no non-standard residues. Use PDBFixer or Modeller to clean the PDB first.")
    if "Could not locate file" in msg or "No OpenMM forcefield" in msg or (
        "forcefield" in msg.lower() and "locate" in msg.lower()
    ):
        return (
            "OpenMM forcefield data missing (need amber14-all.xml + tip3p.xml). "
            "Rebuild/restart the container with OpenMM installed. "
            f"Details: {msg}"
        )
    if "No template found" in msg or "cannot parameterize" in msg.lower() or (
        "missing" in msg.lower() and "H atom" in msg
    ):
        return ("Could not parameterize all residues for MD. "
                "Use a clean RCSB PDB or Auto-Prepare (PDBFixer). "
                f"Details: {msg}")
    return msg


class MDLite(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "")
        if action == "health":           return self._health()
        if action == "prepare":          return await self._prepare(input)
        if action == "prepare_complex":  return await self._prepare_complex(input)
        if action == "run":              return self._run(input)
        if action == "status":           return self._status(input)
        if action == "stop":             return self._stop(input)
        if action == "results":          return self._results(input)
        if action == "download":         return self._download(input)
        if action == "import_docking":   return self._import_docking(input)
        if action == "mmpbsa":           return self._mmpbsa(input)
        if action == "log":              return self._log(input)
        if action == "analyze_advanced": return await self._analyze_advanced(input)
        return {"actions": ["health","prepare","prepare_complex","run","status","stop","results","download","import_docking","mmpbsa","log","analyze_advanced"],
                "hint": "1. prepare_complex (auto-prepare protein+ligand) → 2. run (start MD) → 3. status (poll) → 4. results (basic analysis) → 5. analyze_advanced (publication-grade analysis)"}

    def _health(self):
        try:
            from modules.md_lite.engine import MDEngine
            return {"status": "ok", **MDEngine.health()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _prepare(self, input):
        """Prepare PDB for MD — runs in a worker thread so the event loop
        (and the frontend status poller) stay responsive. Writes phase updates
        to status.json so the user sees progress instead of a black box."""
        job_id = input.get("job_id") or str(uuid.uuid4())[:8]
        job_dir = os.path.join(WORKDIR, job_id)
        os.makedirs(job_dir, exist_ok=True)

        # Write initial status so the frontend shows 'preparing' immediately
        _write_status(job_dir, "preparing", {"phase": "preparing", "progress_pct": 0})

        # Safely extract string content — strip BOM and whitespace
        complex_content = str(input.get("complex_pdb", "") or "").strip()
        protein_content = str(input.get("protein_pdb", "") or "").strip()
        ligand_content = str(input.get("ligand_sdf", "") or "").strip()

        pdb_path = None
        if complex_content and len(complex_content) > 50 and ("ATOM" in complex_content or "HETATM" in complex_content):
            pdb_path = os.path.join(job_dir, "complex.pdb")
            with open(pdb_path, "w", encoding="utf-8") as f:
                f.write(complex_content)
        elif protein_content and len(protein_content) > 50 and ("ATOM" in protein_content or "HETATM" in protein_content):
            pdb_path = os.path.join(job_dir, "protein.pdb")
            with open(pdb_path, "w", encoding="utf-8") as f:
                f.write(protein_content)
            if ligand_content and len(ligand_content) > 10:
                with open(os.path.join(job_dir, "ligand.sdf"), "w", encoding="utf-8") as f:
                    f.write(ligand_content)

        # After import_docking (or resume): reuse PDB already on disk for this job_id
        if not pdb_path:
            for name in ("prepared_complex.pdb", "prepared.pdb", "complex.pdb", "protein.pdb"):
                candidate = os.path.join(job_dir, name)
                if os.path.isfile(candidate) and os.path.getsize(candidate) > 50:
                    pdb_path = candidate
                    log.info(f"Prepare using existing job file: {name}")
                    break

        if not pdb_path:
            _write_status(job_dir, "error", {"phase": "error", "error": "No valid PDB file detected"})
            return {"status": "error", "error": "No valid PDB file detected. Upload a .pdb file containing ATOM/HETATM lines."}

        final_pdb_path = pdb_path

        def _do_prepare():
            nonlocal final_pdb_path
            # STEP 0: Prepare PDB with PDBFixer BEFORE passing to OpenMM
            _write_status(job_dir, "preparing", {"phase": "preparing", "progress_pct": 0})
            try:
                from modules.md_lite.preparation import prepare_protein
                prepared_path = os.path.join(job_dir, "prepared.pdb")
                prep_result = prepare_protein(pdb_path, prepared_path)
                if prep_result.get("status") == "ok":
                    log.info(f"PDB prepared: {prep_result.get('atoms')} atoms, {prep_result.get('residues')} residues")
                    final_pdb_path = prepared_path
                else:
                    log.warning(f"PDBFixer failed: {prep_result.get('error')}, continuing with original")
            except Exception as e:
                log.warning(f"PDBFixer not available: {e}, continuing with original PDB")

            from modules.md_lite.engine import MDEngine
            ff = input.get("forcefield", "amber14")
            temp = float(input.get("temperature", 300))
            plat = str(input.get("platform", "auto"))
            eng = MDEngine(job_dir, ff, temp, platform=plat)
            # PDBFixer already ran above — skip the second expensive pass.
            eng.load_system(final_pdb_path, skip_fixer=True).build_simulation()
            energy = eng.minimize()
            eng._save_checkpoint()
            eng._update_status("prepared", {"min_energy_kjmol": round(energy, 1)})
            return round(energy, 1)

        try:
            energy = await asyncio.to_thread(_do_prepare)
            return {"status": "ok", "job_id": job_id, "prepared": True,
                    "min_energy_kjmol": energy}
        except FileNotFoundError as e:
            _write_status(job_dir, "error", {"phase": "error", "error": str(e)})
            return {"status": "error", "error": f"PDB file not found: {e}"}
        except ImportError as e:
            _write_status(job_dir, "error", {"phase": "error", "error": str(e)})
            return {"status": "error", "error": f"Missing dependency: {e}. Install OpenMM: pip install openmm mdtraj"}
        except Exception as e:
            log.exception("Prepare failed")
            _write_status(job_dir, "error", {"phase": "error", "error": str(e)})
            msg = _friendly_error(str(e))
            return {"status": "error", "error": msg}

    async def _prepare_complex(self, input):
        """Prepare a protein-ligand complex for MD — bridges docking → MD gap.

        Takes protein PDB + docked ligand PDBQT → prepared complex PDB ready for MD.
        Accepts either file paths OR inline content (base64 or raw text).
        Uses PDBFixer for protein prep, RDKit for ligand prep.
        """
        protein_path = input.get("protein_pdb", "") or ""
        ligand_path = input.get("ligand_pdbqt", "") or ""
        protein_content = input.get("protein_pdb_content", "") or ""
        ligand_content = input.get("ligand_pdbqt_content", "") or ""
        job_id = input.get("job_id") or str(uuid.uuid4())[:8]
        job_dir = os.path.join(WORKDIR, job_id)
        os.makedirs(job_dir, exist_ok=True)
        _write_status(job_dir, "preparing_complex", {"phase": "preparing_complex"})

        # Resolve protein: existing path → job_dir files → inline content
        if not protein_path or not os.path.exists(protein_path):
            for name in ("protein.pdb", "protein.pdbqt", "complex.pdb"):
                candidate = os.path.join(job_dir, name)
                if os.path.isfile(candidate) and os.path.getsize(candidate) > 50:
                    protein_path = candidate
                    break
        if not protein_path or not os.path.exists(protein_path):
            if protein_content and len(protein_content) > 50:
                import base64 as _b64
                if not protein_content.startswith(("ATOM", "HETATM", "MODEL", "REMARK")):
                    try: protein_content = _b64.b64decode(protein_content).decode("utf-8", errors="replace")
                    except Exception: pass
                protein_path = os.path.join(job_dir, "protein.pdb")
                with open(protein_path, "w", encoding="utf-8") as f:
                    f.write(protein_content)
            else:
                return {"status": "error", "error": "protein_pdb path required and must exist, or provide protein_pdb_content (or import_docking first)"}

        # Resolve ligand: existing path → job_dir docked files → inline content
        if not ligand_path or not os.path.exists(ligand_path):
            for name in ("docked_ligand.pdbqt", "ligand.pdbqt", "ligand.sdf", "ligand.pdb", "ligand.mol2"):
                candidate = os.path.join(job_dir, name)
                if os.path.isfile(candidate) and os.path.getsize(candidate) > 50:
                    ligand_path = candidate
                    break
        if not ligand_path or not os.path.exists(ligand_path):
            if ligand_content and len(ligand_content) > 50:
                import base64 as _b64
                if not ligand_content.startswith(("HETATM", "ATOM", "@<TRIPOS")):
                    try: ligand_content = _b64.b64decode(ligand_content).decode("utf-8", errors="replace")
                    except Exception: pass
                ext = ".pdbqt" if "ATOM" in ligand_content or "HETATM" in ligand_content else ".sdf"
                ligand_path = os.path.join(job_dir, f"ligand{ext}")
                with open(ligand_path, "w", encoding="utf-8") as f:
                    f.write(ligand_content)
            else:
                return {"status": "error", "error": "ligand_pdbqt path required and must exist, or provide ligand_pdbqt_content (or import_docking first)"}

        def _do_complex():
            from modules.md_lite.preparation import prepare_complex
            output_path = os.path.join(job_dir, "prepared_complex.pdb")
            return prepare_complex(protein_path, ligand_path, output_path)

        try:
            result = await asyncio.to_thread(_do_complex)

            if result.get("status") == "ok":
                # Ensure UI-facing totals
                pa = result.get("protein_atoms") or 0
                la = result.get("ligand_atoms") or 0
                result["total_atoms"] = result.get("total_atoms") or (pa + la if (pa or la) else 0)
                _write_status(job_dir, "prepared", {"phase": "prepared", "total_atoms": result["total_atoms"]})
                try:
                    from modules.knowledge.auto_store import auto_store
                    auto_store("md_lite",
                        f"MD Complex Prepared: {result.get('total_atoms', 0)} atoms",
                        result,
                        source="MD Lite Preparation",
                        tags=["md", "preparation", "complex"],
                        category="md_simulation")
                except Exception:
                    pass

                result["job_id"] = job_id
                result["job_dir"] = job_dir
                result["next_step"] = f"Call action='run' with job_id='{job_id}' to start MD simulation"

            elif result.get("status") == "error" and "error" in result:
                _write_status(job_dir, "error", {"phase": "error", "error": result.get("error")})

            return result

        except Exception as e:
            log.error(f"Complex preparation failed: {e}")
            _write_status(job_dir, "error", {"phase": "error", "error": str(e)})
            return {"status": "error", "error": str(e)}

    def _run(self, input):
        job_id = input["job_id"]
        total_ns = float(input.get("total_ns", 1))
        forcefield = input.get("forcefield", "amber14")
        temperature = float(input.get("temperature", 300))
        pressure = float(input.get("pressure", 1.0))
        platform = input.get("platform", "auto")
        fast_mode = input.get("fast_mode", True)
        job_dir = os.path.join(WORKDIR, job_id)

        if not os.path.exists(job_dir):
            return {"status": "error", "error": f"Job {job_id} not found. Run prepare first."}

        try:
            from modules.md_lite.workflow import MDWorkflow
            wf = MDWorkflow(job_dir)
            # Prefer prepared files over raw (prepared has hydrogens, fixed residues)
            pdb = None
            for candidate in ["prepared_complex.pdb", "prepared.pdb", "complex.pdb", "protein.pdb"]:
                path = os.path.join(job_dir, candidate)
                if os.path.exists(path):
                    pdb = path
                    break
            if not pdb:
                return {"status": "error", "error": "No PDB found. Run prepare first."}

            _write_status(job_dir, "starting", {"phase": "starting"})

            def _run_md():
                try:
                    wf.run(pdb, total_ns, forcefield, temperature, pressure, platform, fast_mode=fast_mode)
                except Exception as e:
                    log.error(f"MD run failed: {e}")
                    # wf._safe_update_status handles the case where wf.engine is None
                    wf._safe_update_status("error", {"error": str(e), "phase": "error"})

            t = threading.Thread(target=_run_md, daemon=True)
            t.start()
            _jobs[job_id] = t
            return {"status": "ok", "job_id": job_id, "running": True,
                    "total_ns": total_ns, "platform": platform, "fast_mode": fast_mode}
        except Exception as e:
            _write_status(job_dir, "error", {"error": str(e)})
            return {"status": "error", "error": str(e)}

    def _status(self, input):
        job_id = input["job_id"]
        from modules.md_lite.workflow import MDWorkflow
        s = MDWorkflow.get_status(os.path.join(WORKDIR, job_id))
        # Include the platform warning if available
        job_dir = os.path.join(WORKDIR, job_id)
        if not s.get("platform_warning"):
            try:
                with open(os.path.join(job_dir, "status.json")) as f:
                    d = json.load(f)
                    s["platform_warning"] = d.get("platform_warning", "")
            except Exception:
                pass
        return s

    def _log(self, input):
        """Return last N lines of the md.log file (OpenMM StateDataReporter)."""
        job_id = input.get("job_id", "")
        lines = int(input.get("lines", 30))
        job_dir = os.path.join(WORKDIR, job_id)
        log_path = os.path.join(job_dir, "md.log")
        if not os.path.exists(log_path):
            return {"status": "ok", "lines": [], "hint": "MD log will appear once simulation starts running."}
        try:
            with open(log_path) as f:
                all_lines = f.readlines()
            tail = all_lines[-lines:] if len(all_lines) > lines else all_lines
            return {"status": "ok", "lines": [l.rstrip() for l in tail],
                    "total_lines": len(all_lines)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _stop(self, input):
        job_id = input["job_id"]
        if job_id in _jobs:
            from modules.md_lite.workflow import MDWorkflow
            wf = MDWorkflow(os.path.join(WORKDIR, job_id))
            wf.stop()
            del _jobs[job_id]
            return {"status": "ok", "job_id": job_id, "stopped": True}
        return {"status": "error", "error": "Job not running"}

    def _results(self, input):
        job_id = input["job_id"]
        job_dir = os.path.join(WORKDIR, job_id)
        traj = os.path.join(job_dir, "trajectory.dcd")
        # Use topology.pdb (full system) if available, else fall back
        top = os.path.join(job_dir, "topology.pdb")
        if not os.path.exists(top):
            top = os.path.join(job_dir, "complex.pdb")
        if not os.path.exists(top):
            top = os.path.join(job_dir, "protein.pdb")
        from modules.md_lite.analysis import analyze
        r = analyze(traj, top, job_dir)
        result = {"status": "ok", "job_id": job_id, "analysis": r}
        # ── AUTO-STORE ──
        try:
            from modules.knowledge.auto_store import auto_store
            auto_store("md_lite", f"MD Results: job {job_id}", result,
                       source="MD Lite (OpenMM)", tags=["md", "docking", job_id])
        except Exception as e:
            log.debug(f"Auto-store for MD job {job_id} failed: {e}")
        return result

    def _download(self, input):
        job_id = input["job_id"]
        job_dir = os.path.join(WORKDIR, job_id)
        import zipfile, io
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(job_dir):
                for fn in files:
                    fp = os.path.join(root, fn)
                    zf.write(fp, os.path.relpath(fp, job_dir))
        buf.seek(0)
        return Response(
            response=buf.getvalue(),
            status=200,
            mimetype="application/zip",
            headers={"Content-Disposition": f"attachment; filename=md_lite_{job_id}.zip"}
        )

    def _mmpbsa(self, input):
        """Run MM-PBSA binding free energy calculation on completed MD trajectory."""
        job_id = input["job_id"]
        job_dir = os.path.join(WORKDIR, job_id)
        traj = os.path.join(job_dir, "trajectory.dcd")
        top = os.path.join(job_dir, "topology.pdb")
        if not os.path.exists(top):
            top = os.path.join(job_dir, "complex.pdb")
        if not os.path.exists(top):
            top = os.path.join(job_dir, "protein.pdb")
        from modules.md_lite.mmpbsa import calculate_mmpbsa
        return {"status": "ok", "job_id": job_id, "mmpbsa": calculate_mmpbsa(traj, top, job_dir)}

    def _import_docking(self, input):
        job_id = input.get("docking_job_id", "")
        if not job_id:
            return {"status": "error", "error": "docking_job_id required"}
        docking_dir = files.get_abs_path(f"tmp/docking_jobs/{job_id}")
        protein_src = os.path.join(docking_dir, "protein.pdb")
        if not os.path.exists(protein_src):
            protein_src = os.path.join(docking_dir, "protein.pdbqt")
        ligand_src = os.path.join(docking_dir, "docked_output.pdbqt")

        new_job = str(uuid.uuid4())[:8]
        new_dir = os.path.join(WORKDIR, new_job)
        os.makedirs(new_dir, exist_ok=True)

        copied = []
        if os.path.exists(protein_src):
            dest = os.path.join(new_dir, "protein.pdb")
            shutil.copy(protein_src, dest)
            copied.append("protein.pdb")
        if os.path.exists(ligand_src):
            dest = os.path.join(new_dir, "docked_ligand.pdbqt")
            shutil.copy(ligand_src, dest)
            copied.append("docked_ligand.pdbqt")

        if not copied:
            return {
                "status": "error",
                "error": f"No docking files found for job '{job_id}'. Expected protein.pdb and docked_output.pdbqt under tmp/docking_jobs/{job_id}.",
            }

        _write_status(new_dir, "imported", {"phase": "imported", "docking_job_id": job_id, "files": copied})
        return {"status": "ok", "job_id": new_job, "imported_from": job_id, "files": copied,
                "next_step": f"Call action='prepare_complex' with job_id='{new_job}' to prepare the system for MD"}

    async def _analyze_advanced(self, input):
        """Run publication-grade trajectory analysis via MDAnalysis.

        Runs 10 advanced analyses on a completed MD trajectory:
          hbonds_advanced, water_bridges, native_contacts, rdf,
          ramachandran, pca, hbond_lifetimes, ligand_distances,
          secondary_structure, dielectric
        """
        import asyncio
        job_id = input.get("job_id", "")
        if not job_id:
            return {"status": "error", "error": "job_id required"}

        job_dir = os.path.join(WORKDIR, job_id)
        if not os.path.isdir(job_dir):
            return {"status": "error", "error": f"Job directory not found: {job_id}"}

        # Find trajectory and topology
        traj_path = os.path.join(job_dir, "trajectory.dcd")
        if not os.path.exists(traj_path):
            for ext in [".xtc", ".trr", ".nc", ".dtr"]:
                alt = os.path.join(job_dir, f"trajectory{ext}")
                if os.path.exists(alt):
                    traj_path = alt
                    break

        top_path = os.path.join(job_dir, "prepared.pdb")
        if not os.path.exists(top_path):
            top_path = os.path.join(job_dir, "topology.pdb")
        if not os.path.exists(top_path):
            for name in ["input.pdb", "protein.pdb", "system.pdb"]:
                alt = os.path.join(job_dir, name)
                if os.path.exists(alt):
                    top_path = alt
                    break

        if not os.path.exists(traj_path):
            return {"status": "error", "error": "No trajectory file found. Run MD simulation first."}
        if not os.path.exists(top_path):
            return {"status": "error", "error": "No topology file found."}

        analyses = input.get("analyses")  # None = all

        def _do():
            from modules.md_lite.advanced_analysis import analyze_advanced
            return analyze_advanced(traj_path, top_path, job_dir, analyses)

        return await asyncio.to_thread(_do)
