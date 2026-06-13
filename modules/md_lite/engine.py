"""OpenMM MD Engine — setup, force field, integrator, simulation runners."""
import os, json, time, logging
import openmm as mm
import openmm.app as app
import openmm.unit as unit

log = logging.getLogger("md_lite")

class MDEngine:
    def __init__(self, workdir, forcefield="amber14", temperature=300, pressure=1.0,
                 platform="CUDA", device_index=0):
        self.workdir = workdir
        self.forcefield = forcefield
        self.temperature = temperature * unit.kelvin
        self.pressure = pressure * unit.bar
        self.platform_name = platform
        self.device_index = device_index
        self.simulation = None
        self._steps_done = 0
        self._total_steps = 0
        self._chunks_total = 0
        self._chunks_done = 0
        self.status_file = os.path.join(workdir, "status.json")

    def detect_platform(self):
        """Auto-detect best platform: GPU first (CUDA > OpenCL), fallback CPU."""
        platforms = []
        for i in range(mm.Platform.getNumPlatforms()):
            p = mm.Platform.getPlatform(i)
            platforms.append(p.getName())
        # GPU preference order
        for pref in ["CUDA", "OpenCL"]:
            for pn in platforms:
                if pref in pn:
                    log.info(f"Using GPU platform: {pn}")
                    return mm.Platform.getPlatformByName(pn)
        log.warning("No GPU detected — falling back to CPU")
        return mm.Platform.getPlatformByName("CPU")

    def load_system(self, pdb_path):
        if not os.path.exists(pdb_path):
            raise FileNotFoundError(f"PDB not found: {pdb_path}")
        self.pdb = app.PDBFile(pdb_path)
        ff = app.ForceField(f"{self.forcefield}.xml", "tip3p.xml")
        self.modeller = app.Modeller(self.pdb.topology, self.pdb.positions)
        self.modeller.addSolvent(ff, model='tip3p', padding=1.0*unit.nanometers)
        self.system = ff.createSystem(self.modeller.topology,
            nonbondedMethod=app.PME, nonbondedCutoff=1.0*unit.nanometers,
            constraints=app.HBonds)
        self.integrator = mm.LangevinMiddleIntegrator(
            self.temperature, 1.0/unit.picosecond, 0.002*unit.picoseconds)
        self.integrator.setConstraintTolerance(0.00001)
        return self

    def build_simulation(self):
        platform = self.detect_platform()
        self.simulation = app.Simulation(self.modeller.topology, self.system,
            self.integrator, platform)
        self.simulation.context.setPositions(self.modeller.positions)
        # Auto-resume from checkpoint if available
        had_checkpoint = self.load_checkpoint()
        if had_checkpoint:
            log.info(f"Resumed from checkpoint at {self.progress_ns} ns")
        return self

    def minimize(self, max_iterations=0):
        self.simulation.minimizeEnergy(maxIterations=max_iterations)
        state = self.simulation.context.getState(getEnergy=True)
        return state.getPotentialEnergy().value_in_unit(unit.kilojoules_per_mole)

    def add_reporters(self, traj_path, log_path, report_interval=1000):
        self.simulation.reporters.append(
            app.DCDReporter(traj_path, report_interval))
        self.simulation.reporters.append(
            app.StateDataReporter(log_path, report_interval,
                step=True, potentialEnergy=True, temperature=True,
                volume=True, density=True, speed=True))

    def _update_status(self, status, extra=None):
        data = {"status": status, "timestamp": time.time(),
                "progress_ns": self.progress_ns, "progress_pct": self.progress_pct,
                "total_steps_done": self._steps_done, "total_steps_planned": self._total_steps}
        if extra: data.update(extra)
        os.makedirs(self.workdir, exist_ok=True)
        with open(self.status_file, "w") as f:
            json.dump(data, f)

    def run_for_ns(self, total_ns, checkpoint_interval_ns=0.5):
        steps_per_ns = 500000
        total_steps = int(total_ns * steps_per_ns)
        chunk_steps = int(checkpoint_interval_ns * steps_per_ns)
        self._total_steps = total_steps
        self._chunks_total = max(1, total_steps // chunk_steps)
        self._chunks_done = 0
        self._update_status("running")
        while self._steps_done < total_steps:
            remaining = total_steps - self._steps_done
            n = min(chunk_steps, remaining)
            self.simulation.step(n)
            self._steps_done += n
            self._chunks_done += 1
            self._save_checkpoint()
            self._update_status("running")
        self._update_status("completed")

    def _save_checkpoint(self):
        try:
            state = self.simulation.context.getState(getPositions=True,
                getVelocities=True, getEnergy=True, getForces=True)
            with open(os.path.join(self.workdir, "checkpoint.xml"), "w") as f:
                f.write(mm.XmlSerializer.serialize(state))
        except Exception as e:
            log.warning(f"Checkpoint save failed: {e}")

    def load_checkpoint(self):
        """Restore simulation state from checkpoint file."""
        path = os.path.join(self.workdir, "checkpoint.xml")
        if os.path.exists(path):
            try:
                with open(path) as f:
                    self.simulation.context.setState(mm.XmlSerializer.deserialize(f.read()))
                # Restore step count from status file
                import json
                sf = os.path.join(self.workdir, "status.json")
                if os.path.exists(sf):
                    with open(sf) as f:
                        data = json.load(f)
                        self._steps_done = int(data.get("total_steps_done", 0))
                        self._total_steps = int(data.get("total_steps_planned", self._steps_done))
                return True
            except Exception as e:
                log.warning(f"Checkpoint load failed: {e}")
        return False

    @property
    def progress_pct(self):
        if self._total_steps == 0: return 0
        return round(100.0 * self._steps_done / self._total_steps, 1)

    @property
    def progress_ns(self):
        return round(self._steps_done / 500000.0, 2)

    @staticmethod
    def health():
        platforms = []
        for i in range(mm.Platform.getNumPlatforms()):
            p = mm.Platform.getPlatform(i)
            platforms.append({"name": p.getName(), "speed": p.getSpeed()})
        gpu = any("CUDA" in p["name"] or "OpenCL" in p["name"] for p in platforms)
        return {"openmm": True, "platforms": platforms, "gpu": gpu, "default": platforms[0]["name"] if platforms else "CPU"}
