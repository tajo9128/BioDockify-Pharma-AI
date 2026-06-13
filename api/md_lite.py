"""MD Lite API — OpenMM molecular dynamics simulation handler."""
from helpers.api import ApiHandler, Request, Response
from helpers import files
import os, json, uuid, threading, logging, shutil, base64

log = logging.getLogger("md_lite")

log = logging.getLogger("md_lite")
WORKDIR = files.get_abs_path("usr/md-lite")
os.makedirs(WORKDIR, exist_ok=True)

_jobs = {}  # in-memory job tracking: job_id -> threading.Thread


class MDLite(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "")
        if action == "health":        return self._health()
        if action == "prepare":       return self._prepare(input)
        if action == "run":           return self._run(input)
        if action == "status":        return self._status(input)
        if action == "stop":          return self._stop(input)
        if action == "results":       return self._results(input)
        if action == "download":      return self._download(input)
        if action == "import_docking": return self._import_docking(input)
        if action == "mmpbsa":        return self._mmpbsa(input)
        return {"actions": ["health","prepare","run","status","stop","results","download","import_docking","mmpbsa"],
                "hint": "1. prepare (upload PDB) → 2. run (start MD) → 3. status (poll) → 4. results (analysis)"}

    def _health(self):
        try:
            from modules.md_lite.engine import MDEngine
            return {"status": "ok", **MDEngine.health()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _prepare(self, input):
        job_id = input.get("job_id") or str(uuid.uuid4())[:8]
        job_dir = os.path.join(WORKDIR, job_id)
        os.makedirs(job_dir, exist_ok=True)

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

        if not pdb_path:
            return {"status": "error", "error": "No valid PDB file detected. Upload a .pdb file containing ATOM/HETATM lines."}

        try:
            from modules.md_lite.engine import MDEngine
            ff = input.get("forcefield", "amber14")
            temp = float(input.get("temperature", 300))
            plat = str(input.get("platform", "CUDA"))
            eng = MDEngine(job_dir, ff, temp, platform=plat)
            eng.load_system(pdb_path).build_simulation()
            energy = eng.minimize()
            eng._save_checkpoint()
            eng._update_status("prepared", {"min_energy_kjmol": round(energy, 1)})
            return {"status": "ok", "job_id": job_id, "prepared": True,
                    "min_energy_kjmol": round(energy, 1)}
        except FileNotFoundError as e:
            return {"status": "error", "error": f"PDB file not found: {e}"}
        except ImportError as e:
            return {"status": "error", "error": f"Missing dependency: {e}. Install OpenMM: pip install openmm mdtraj"}
        except Exception as e:
            log.exception("Prepare failed")
            # Return a clean error message — strip technical traceback info
            msg = str(e)
            if "invalid literal for int()" in msg:
                msg = "PDB file format error. Ensure the file is a valid PDB with proper ATOM/HETATM records."
            elif "Could not locate" in msg:
                msg = f"OpenMM forcefield not found: {msg}. The amber14-all.xml file should be installed with OpenMM."
            return {"status": "error", "error": msg}

    def _run(self, input):
        job_id = input["job_id"]
        total_ns = float(input.get("total_ns", 5))
        forcefield = input.get("forcefield", "amber14")
        temperature = float(input.get("temperature", 300))
        pressure = float(input.get("pressure", 1.0))
        platform = input.get("platform", "CUDA")
        job_dir = os.path.join(WORKDIR, job_id)

        if not os.path.exists(job_dir):
            return {"status": "error", "error": f"Job {job_id} not found. Run prepare first."}

        try:
            from modules.md_lite.workflow import MDWorkflow
            wf = MDWorkflow(job_dir)
            pdb = os.path.join(job_dir, "complex.pdb") if os.path.exists(os.path.join(job_dir, "complex.pdb")) else os.path.join(job_dir, "protein.pdb")
            if not os.path.exists(pdb):
                return {"status": "error", "error": "No PDB found. Run prepare first."}

            def _run_md():
                try:
                    wf.run(pdb, total_ns, forcefield, temperature, pressure, platform)
                except Exception as e:
                    log.error(f"MD run failed: {e}")
                    wf.engine._update_status("error", {"error": str(e)})

            t = threading.Thread(target=_run_md, daemon=True)
            t.start()
            _jobs[job_id] = t
            return {"status": "ok", "job_id": job_id, "running": True,
                    "total_ns": total_ns, "platform": platform}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _status(self, input):
        job_id = input["job_id"]
        from modules.md_lite.workflow import MDWorkflow
        return MDWorkflow.get_status(os.path.join(WORKDIR, job_id))

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
        top = os.path.join(job_dir, "complex.pdb") or os.path.join(job_dir, "protein.pdb")
        from modules.md_lite.analysis import analyze
        r = analyze(traj, top, job_dir)
        return {"status": "ok", "job_id": job_id, "analysis": r}

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
        top = os.path.join(job_dir, "complex.pdb") or os.path.join(job_dir, "protein.pdb")
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

        if os.path.exists(protein_src):
            shutil.copy(protein_src, os.path.join(new_dir, "protein.pdb"))
        if os.path.exists(ligand_src):
            shutil.copy(ligand_src, os.path.join(new_dir, "docked_ligand.pdbqt"))
        return {"status": "ok", "job_id": new_job, "imported_from": job_id,
                "hint": "Files imported. Run prepare to minimize the system."}
