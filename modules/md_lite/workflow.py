"""MD Workflow — Minimize → NVT Equilibrate → NPT Equilibrate → Production MD."""
from .engine import MDEngine
import os, logging
import openmm
import openmm.unit as unit

log = logging.getLogger("md_lite_workflow")

class MDWorkflow:
    def __init__(self, workdir, engine=None):
        self.workdir = workdir
        self.engine = engine
        self._stopped = False

    def run(self, pdb_path, total_ns=5, forcefield="amber14", temperature=300,
            pressure=1.0, platform="CUDA"):
        eng = self.engine or MDEngine(self.workdir, forcefield, temperature,
                                       pressure, platform)
        eng.load_system(pdb_path).build_simulation()
        eng.add_reporters(
            os.path.join(self.workdir, "trajectory.dcd"),
            os.path.join(self.workdir, "md.log"))
        had_checkpoint = eng.load_checkpoint()
        if had_checkpoint:
            log.info(f"Resumed from checkpoint at {eng.progress_ns} ns")

        if not had_checkpoint:
            eng._update_status("minimizing")
            energy = eng.minimize()
            log.info(f"Minimization: {energy:.1f} kJ/mol")

            eng._update_status("equilibrating")
            eng.simulation.step(50000)  # 100 ps NVT at 2 fs
            barostat = openmm.MonteCarloBarostat(
                pressure * unit.bar, temperature * unit.kelvin, 25)
            eng.system.addForce(barostat)
            eng.simulation.context.reinitialize(preserveState=True)
            eng.simulation.step(50000)  # 100 ps NPT at 2 fs

        prod_ns = max(0.5, total_ns - eng.progress_ns)
        if prod_ns <= 0:
            eng._update_status("completed")
            return eng

        eng._update_status("running")
        eng.run_for_ns(prod_ns)
        eng._update_status("completed")
        return eng

    def stop(self):
        self._stopped = True
        if self.engine:
            self.engine._update_status("stopped")

    @staticmethod
    def get_status(workdir):
        import json
        sf = os.path.join(workdir, "status.json")
        if os.path.exists(sf):
            with open(sf) as f:
                return json.load(f)
        return {"status": "unknown", "progress_pct": 0}
