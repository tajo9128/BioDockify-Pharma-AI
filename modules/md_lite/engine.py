"""OpenMM MD Engine — setup, force field, integrator, simulation runners."""
import os, json, time, logging
import openmm as mm
import openmm.app as app
import openmm.unit as unit

log = logging.getLogger("md_lite")

FORCEFIELD_CHAINS = [
    # AMBER14 protein forcefield — works with the bundled tip3p water file
    # (amber14/tip3p_standard.xml is often not shipped; tip3p.xml is the fallback)
    ("amber14-all.xml", "amber14/tip3p_standard.xml"),
    ("amber14-all.xml", "tip3p.xml"),
    ("amber14/protein.ff14SB.xml", "tip3p.xml"),
    # AMBER99 — reliable fallbacks shipped with every OpenMM install
    ("amber99sbildn.xml", "tip3p.xml"),
    ("amber99sb.xml", "tip3p.xml"),
]


def _sanitize_pdb(pdb_path):
    """Clean a PDB file so OpenMM's PdbStructure parser accepts it.

    Strategy: keep all records OpenMM understands (ATOM/HETATM/TER/END/MODEL/
    ENDMDL/CRYST1/SSBOND/LINK/HELIX/SHEET), and fix the common breakage that
    docking software / non-standard exporters introduce:
      - ATOM/HETATM lines shorter than the minimum 54 columns
      - non-numeric residue sequence / coordinate fields
      - missing final END
    Critically, CRYST1 is PRESERVED — without it OpenMM has no periodic box
    and addSolvent()+PME fails with 'no periodic box dimensions'.
    """
    # Records OpenMM's PDB reader uses. Anything else is dropped to avoid
    # confusing the parser, but the structure-critical ones are kept.
    KEEP_RECORDS = {
        "ATOM", "HETATM", "TER", "END", "MODEL", "ENDMDL",
        "CRYST1", "SSBOND", "LINK", "HELIX", "SHEET", "SEQRES", "DBREF",
    }
    clean_lines = []
    saw_atom = False
    with open(pdb_path, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.rstrip("\n").rstrip("\r")
            if not line:
                continue
            rec = line[:6].strip()

            if rec in ("ATOM", "HETATM"):
                # Pad short lines to the minimum column width we parse.
                if len(line) < 54:
                    line = line.ljust(54)
                # Validate the fixed-column numeric fields. If a single field
                # is bad, skip that atom rather than aborting the whole file.
                try:
                    int(line[22:26])           # residue sequence number
                    float(line[30:38])         # x
                    float(line[38:46])         # y
                    float(line[46:54])         # z
                except (ValueError, IndexError):
                    continue
                # Drop altLoc / segment noise that some exporters mangle by
                # blanking the occupancy/tempFactor columns is NOT needed —
                # OpenMM tolerates them. Keep the line as-is.
                clean_lines.append(line + "\n")
                saw_atom = True
            elif rec in KEEP_RECORDS:
                clean_lines.append(line + "\n")
            # else: silently drop unsupported record types (ANISOU, REMARK,
            # HEADER, TITLE, etc.) which OpenMM doesn't need and which can
            # confuse older PdbStructure parsing in edge cases.

    if not saw_atom:
        raise ValueError("PDB file contains no valid ATOM/HETATM records after sanitization")

    # Ensure a CRYST1 record exists so PME/periodic boundaries can be set up.
    # If the source PDB lacked one (common for docking output / bare protein),
    # synthesize a simple cubic box larger than any coordinate span.
    has_cryst = any(l.startswith("CRYST1") for l in clean_lines)
    if not has_cryst:
        xs = ys = zs = []
        for l in clean_lines:
            if l[:6].strip() in ("ATOM", "HETATM") and len(l) >= 54:
                try:
                    xs.append(float(l[30:38]))
                    ys.append(float(l[38:46]))
                    zs.append(float(l[46:54]))
                except (ValueError, IndexError):
                    pass
        if xs:
            # 1.0 nm padding on each side, in Angstroms (PDB units)
            pad = 10.0
            a = (max(xs) - min(xs)) + pad
            b = (max(ys) - min(ys)) + pad
            c = (max(zs) - min(zs)) + pad
            cryst = (f"CRYST1{a:9.3f}{b:9.3f}{c:9.3f}"
                     f"  90.00  90.00  90.00 P 1           1\n")
            clean_lines.insert(0, cryst)

    # Guarantee a terminating END record.
    if not any(l.startswith("END") for l in clean_lines):
        clean_lines.append("END\n")

    with open(pdb_path, "w", encoding="utf-8") as f:
        f.writelines(clean_lines)


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

        # STEP 1: Build a protein-only modeller (NO solvent yet).
        # Hydrogens must be added to the bare protein so the forcefield can
        # match residue templates. Adding solvent first (as before) disrupted
        # hydrogen placement and left residues missing H atoms, which crashed
        # createSystem with 'No template found for residue N (XXX)'.
        protein_modeller = app.Modeller(self.pdb.topology, self.pdb.positions)
        try:
            protein_modeller.deleteWater()
        except Exception:
            pass

        # STEP 2: Add hydrogens to the protein BEFORE solvent.
        # Try progressively: pH-aware, then standard, then forcefield-only.
        # This resolves 'missing 1 H atom' errors (e.g. NPRO/PRO terminal).
        hydrogens_ok = False
        last_h_error = None
        for hydro_args, label in [
            ({"pH": 7.0}, "pH=7.0"),
            ({}, "standard"),
        ]:
            try:
                protein_modeller.addHydrogens(ff, **hydro_args)
                hydrogens_ok = True
                log.info(f"addHydrogens({label}) succeeded.")
                break
            except Exception as e:
                last_h_error = e
                log.warning(f"addHydrogens({label}) failed: {e}")

        if not hydrogens_ok:
            # Last resort: let createSystem try with whatever hydrogens exist.
            # Many PDBs are usable even if addHydrogens can't resolve all variants.
            log.warning(
                "Could not fully add hydrogens via Modeller; continuing. "
                f"Last error: {last_h_error}"
            )

        # STEP 3: Build the OpenMM system on the hydrogen-complete protein.
        # The protein-only topology has NO periodic box yet (no solvent), so we
        # cannot use app.PME here — use NoCutoff just to validate that the
        # forcefield can parameterize every residue + that hydrogens are complete.
        built = False
        last_error = None
        for ff_protein, ff_water in FORCEFIELD_CHAINS:
            try:
                ff_try = app.ForceField(ff_protein, ff_water)
                # Validate parameterization without requiring a periodic box.
                self.system = ff_try.createSystem(
                    protein_modeller.topology,
                    nonbondedMethod=app.NoCutoff,
                    constraints=app.HBonds,
                )
                ff = ff_try  # lock in the working forcefield for solvent step
                built = True
                log.info(f"Protein parameterized with forcefield: {ff_protein} + {ff_water}")
                break
            except Exception as e:
                last_error = e
                log.warning(f"createSystem failed for {ff_protein}+{ff_water}: {e}")

        if not built:
            raise RuntimeError(
                f"Forcefield cannot parameterize this protein. "
                f"The PDB contains residues with no matching forcefield template. "
                f"Download a clean PDB from RCSB PDB and try again. "
                f"Details: {last_error}"
            )

        # STEP 4: NOW add solvent to the parameterized protein.
        self.modeller = protein_modeller
        solvated = True
        try:
            self.modeller.addSolvent(ff, model='tip3p', padding=1.0*unit.nanometers)
        except Exception as e:
            log.warning(f"addSolvent failed (continuing without solvent box): {e}")
            solvated = False

        # STEP 5: Build the FINAL system on the SAME topology we will simulate.
        # This guarantees topology/positions/system all have matching atom counts.
        # Use PME (periodic) when solvated, NoCutoff when running bare-protein.
        if solvated:
            try:
                self.system = ff.createSystem(
                    self.modeller.topology,
                    nonbondedMethod=app.PME, nonbondedCutoff=1.0*unit.nanometers,
                    constraints=app.HBonds,
                )
            except Exception as e:
                log.warning(f"PME system build failed ({e}); retrying NoCutoff.")
                solvated = False
        if not solvated:
            # Bare protein (no solvent / no periodic box) — must be consistent.
            self.system = ff.createSystem(
                self.modeller.topology,
                nonbondedMethod=app.NoCutoff,
                constraints=app.HBonds,
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
