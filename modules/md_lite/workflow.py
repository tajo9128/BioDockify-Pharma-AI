"""MD Workflow — Minimize → Fast Equilibrate → Production MD."""
from .engine import MDEngine
import os, json, time, logging
import openmm
import openmm.unit as unit

log = logging.getLogger("md_lite_workflow")

class MDWorkflow:
    def __init__(self, workdir, engine=None):
        self.workdir = workdir
        self.engine = engine
        self._stopped = False

    def _safe_update_status(self, status, extra=None):
        """Write status.json even if self.engine is None (early-failure safety)."""
        if self.engine:
            self.engine._update_status(status, extra)
        else:
            # Engine not yet created — write a minimal status file so the
            # frontend sees the error instead of hanging on 'running' forever.
            try:
                sf = os.path.join(self.workdir, "status.json")
                data = {"status": status, "timestamp": time.time(),
                        "phase": status, "progress_pct": 0}
                if extra:
                    data.update(extra)
                os.makedirs(self.workdir, exist_ok=True)
                with open(sf, "w") as f:
                    json.dump(data, f)
            except Exception:
                pass

    def run(self, pdb_path, total_ns=5, forcefield="amber14", temperature=300,
            pressure=1.0, platform="CUDA", fast_mode=True):
        eng = self.engine or MDEngine(self.workdir, forcefield, temperature,
                                       pressure, platform)
        self.engine = eng  # ensure self.engine is set for the error handler

        try:
            # skip_fixer=True because PDBFixer already ran during prepare/prepare_complex.
            # Running it again doubles the preparation time for zero benefit.
            eng.load_system(pdb_path, skip_fixer=True).build_simulation()
            eng.add_reporters(
                os.path.join(self.workdir, "trajectory.dcd"),
                os.path.join(self.workdir, "md.log"))
            had_checkpoint = eng.load_checkpoint()
            if had_checkpoint:
                log.info(f"Resumed from checkpoint at {eng.progress_ns} ns")

            if not had_checkpoint:
                energy = eng.minimize()
                log.info(f"Minimization: {energy:.1f} kJ/mol")
                eng._update_status("minimized", {"min_energy_kjmol": round(energy, 1)})

                # FAST equilibration: 10 ps (5,000 steps) NVT, then 10 ps NPT.
                # The old 200 ps (100,000 steps) is what made "1 ns take hours"
                # on CPU. For a Lite prototyping tool, 10 ps is enough to settle
                # the worst steric clashes before production.
                eng.phase = "equilibrating"
                eng._update_status("equilibrating")
                eq_steps = 2500 if fast_mode else 50000  # 5 ps fast, 100 ps full
                eng.simulation.step(eq_steps)  # NVT
                barostat = openmm.MonteCarloBarostat(
                    pressure * unit.bar, temperature * unit.kelvin, 25)
                eng.system.addForce(barostat)
                eng.simulation.context.reinitialize(preserveState=True)
                eng.simulation.step(eq_steps)  # NPT

            prod_ns = total_ns - eng.progress_ns
            if prod_ns <= 0:
                eng.phase = "completed"
                eng._update_status("completed")
                return eng

            if self._stopped:
                eng.phase = "stopped"
                eng._update_status("stopped")
                return eng

            eng.run_for_ns(prod_ns, stop_check=lambda: self._stopped)
            eng.phase = "completed"
            eng._update_status("completed")
            return eng
        except Exception as e:
            log.error(f"MD run failed: {e}", exc_info=True)
            eng.phase = "error"
            self._safe_update_status("error", {"error": str(e), "phase": "error"})
            raise

    def stop(self):
        self._stopped = True
        if self.engine:
            self.engine.phase = "stopped"
            self.engine._update_status("stopped")

    @staticmethod
    def get_status(workdir):
        sf = os.path.join(workdir, "status.json")
        if os.path.exists(sf):
            try:
                with open(sf) as f:
                    return json.load(f)
            except Exception:
                pass
        return {"status": "unknown", "progress_pct": 0, "phase": "unknown"}
