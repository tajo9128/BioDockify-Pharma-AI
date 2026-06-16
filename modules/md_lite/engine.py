"""OpenMM MD Engine — setup, force field, integrator, simulation runners."""
import os, json, time, logging
import openmm as mm
import openmm.app as app
import openmm.unit as unit

log = logging.getLogger("md_lite")

FORCEFIELD_CHAINS = [
    ("amber14-all.xml", "amber14/tip3p_standard.xml"),
    ("amber14-all.xml", "amber14/tip3p.xml"),
    ("amber14-all.xml", "tip3p.xml"),
    ("amber99sb.xml", "tip3p.xml"),
    ("amber99sbildn.xml", "tip3p.xml"),
]


def _sanitize_pdb(pdb_path):
    """Strip malformed PDB lines that crash OpenMM's PdbStructure parser."""
    clean_lines = []
    with open(pdb_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            rec = line[:6].strip()
            if rec in ("ATOM", "HETATM"):
                if len(line) < 54:
                    continue
                try:
                    int(line[22:26])
                    float(line[30:38])
                    float(line[38:46])
                    float(line[46:54])
                except (ValueError, IndexError):
                    continue
                clean_lines.append(line)
            elif rec in ("TER", "END", "MODEL", "ENDMDL", "CONECT"):
                clean_lines.append(line)
    if not clean_lines:
        raise ValueError("PDB file contains no valid ATOM/HETATM records after sanitization")
    with open(pdb_path, "w", encoding="utf-8") as f:
        f.writelines(clean_lines)
        if not any(l.startswith("END") for l in clean_lines):
            f.write("END\n")


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
        self._start_time = 0
        self.status_file = os.path.join(workdir, "status.json")

    def detect_platform(self):
        """Auto-detect best platform: GPU first (CUDA > OpenCL), fallback CPU."""
        all_platforms = []
        for i in range(mm.Platform.getNumPlatforms()):
            p = mm.Platform.getPlatform(i)
            all_platforms.append((p.getName(), p.getSpeed()))

        if self.platform_name in ("CUDA", "OpenCL"):
            matched = [p for p, s in all_platforms if self.platform_name in p]
            if matched:
                best = max(matched, key=lambda n: next(s for pn, s in all_platforms if pn == n))
                log.info(f"Using {self.platform_name}: {best}")
                return mm.Platform.getPlatformByName(best)

        for pref in ["CUDA", "OpenCL"]:
            matched = [(p, s) for p, s in all_platforms if pref in p]
            if matched:
                best = max(matched, key=lambda x: x[1])[0]
                log.info(f"Auto-detected GPU: {best}")
                return mm.Platform.getPlatformByName(best)

        log.warning("No GPU detected — falling back to CPU")
        return mm.Platform.getPlatformByName("CPU")

    def _load_forcefield(self):
        """Try multiple forcefield combinations, return first that works."""
        for ff_protein, ff_water in FORCEFIELD_CHAINS:
            try:
                ff = app.ForceField(ff_protein, ff_water)
                log.info(f"Loaded forcefield: {ff_protein} + {ff_water}")
                return ff
            except Exception:
                continue
        raise RuntimeError(
            "No OpenMM forcefield files found. Tried: "
            + ", ".join(f"{p}+{w}" for p, w in FORCEFIELD_CHAINS)
            + ". Rebuild Docker image to install OpenMM forcefields."
        )

    def load_system(self, pdb_path):
        if not os.path.exists(pdb_path):
            raise FileNotFoundError(f"PDB not found: {pdb_path}")
        _sanitize_pdb(pdb_path)
        self.pdb = app.PDBFile(pdb_path)
        ff = self._load_forcefield()

        def _setup_modeller():
            m = app.Modeller(self.pdb.topology, self.pdb.positions)
            try:
                m.deleteWater()
            except Exception:
                pass
            m.addSolvent(ff, model='tip3p', padding=1.0*unit.nanometers)
            return m

        # Build system — try pH-aware hydrogens, catch template mismatches
        built = False
        last_error = None
        for attempt, (hydro_args, label) in enumerate([
            ({"pH": 7.0}, "pH=7.0"),
            ({}, "standard"),
            ({"variants": None}, "all variants"),
        ]):
            try:
                self.modeller = _setup_modeller()
                try:
                    self.modeller.addHydrogens(ff, **hydro_args)
                except Exception as e:
                    log.warning(f"addHydrogens({label}) failed for some residues: {e}")
                self.system = ff.createSystem(self.modeller.topology,
                    nonbondedMethod=app.PME, nonbondedCutoff=1.0*unit.nanometers,
                    constraints=app.HBonds)
                built = True
                break
            except Exception as e:
                last_error = e
                if "No template found" not in str(e) and "missing" not in str(e).lower():
                    raise
                log.warning(f"Forcefield template mismatch (attempt {attempt+1}/3): {e}")

        if not built:
            raise RuntimeError(
                f"Forcefield cannot parameterize this protein. "
                f"The PDB contains residues with no matching forcefield template. "
                f"Download a clean PDB from RCSB PDB and try again. "
                f"Details: {last_error}"
            )

        self.integrator = mm.LangevinMiddleIntegrator(
            self.temperature, 1.0/unit.picosecond, 0.002*unit.picoseconds)
        self.integrator.setConstraintTolerance(0.00001)
        return self

    def build_simulation(self):
        platform = self.detect_platform()
        self.simulation = app.Simulation(self.modeller.topology, self.system,
            self.integrator, platform)
        self.simulation.context.setPositions(self.modeller.positions)
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
                "total_steps_done": self._steps_done, "total_steps_planned": self._total_steps,
                "chunk": f"{self._chunks_done}/{self._chunks_total}" if self._chunks_total else "",
                "eta_minutes": self._eta_minutes() if self._chunks_total and self._chunks_done > 0 else 0}
        if extra: data.update(extra)
        os.makedirs(self.workdir, exist_ok=True)
        with open(self.status_file, "w") as f:
            json.dump(data, f)

    def _eta_minutes(self):
        if self._chunks_done <= 0 or self._chunks_total <= 0:
            return 0
        elapsed = time.time() - (self._start_time or time.time())
        if elapsed <= 0: return 0
        remaining_chunks = self._chunks_total - self._chunks_done
        avg_per_chunk = elapsed / self._chunks_done
        return round((remaining_chunks * avg_per_chunk) / 60.0)

    def run_for_ns(self, total_ns, checkpoint_interval_ns=0.5):
        steps_per_ns = 500000
        total_steps = int(total_ns * steps_per_ns)
        chunk_steps = int(checkpoint_interval_ns * steps_per_ns)
        self._total_steps = total_steps
        self._chunks_total = max(1, total_steps // chunk_steps)
        self._chunks_done = 0
        self._start_time = time.time()
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
                sf = os.path.join(self.workdir, "status.json")
                if os.path.exists(sf):
                    with open(sf) as f:
                        data = json.load(f)
                        self._steps_done = int(data.get("total_steps_done", 0))
                        self._total_steps = int(data.get("total_steps_planned", self._steps_done))
                else:
                    log.warning("Checkpoint found but status.json missing — starting progress from 0")
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
