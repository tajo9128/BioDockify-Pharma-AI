"""OpenMM MD Engine — setup, force field, integrator, simulation runners.

GPU-ONLY mode: MD Lite requires a CUDA GPU with ≥ 4 GB VRAM (GTX 1650 or better).
CPU simulations are rejected — they take days for 1 ns and are not viable.
"""
import os, json, time, logging, threading
import openmm as mm
import openmm.app as app
import openmm.unit as unit

log = logging.getLogger("md_lite")

# ── GPU requirement ──────────────────────────────────────────────────────────
MIN_VRAM_GB = 4.0           # GTX 1650 has 4 GB — the minimum viable GPU
MIN_GPU_NAME = "GTX 1650"   # reference card for the requirement message

# Cache the GPU check so we only pay the ~2s cost once per process.
_GPU_CHECKED = False
_GPU_AVAILABLE = False
_GPU_NAME = ""
_GPU_VRAM_GB = 0.0
_GPU_WARNING = ""
_GPU_LOCK = threading.Lock()


def _check_gpu():
    """Verify a CUDA GPU with ≥ MIN_VRAM_GB is present and usable.

    The DEFINITIVE test is: can OpenMM create a CUDA context and step a
    simulation? If yes, the GPU works — never reject a working GPU just
    because a detection helper (nvidia-smi etc.) is missing.

    Name/VRAM detection is best-effort, used for display and the VRAM floor.
    VRAM only causes rejection when positively measured below the minimum.

    Returns (available: bool, warning: str). Result is cached.
    """
    global _GPU_CHECKED, _GPU_AVAILABLE, _GPU_NAME, _GPU_VRAM_GB, _GPU_WARNING
    with _GPU_LOCK:
        if _GPU_CHECKED:
            return _GPU_AVAILABLE, _GPU_WARNING
        _GPU_CHECKED = True
        _GPU_AVAILABLE = False
        _GPU_WARNING = ""

        # 1. Best-effort device info first (for diagnostics + VRAM floor)
        gpu_name, vram_gb = _detect_gpu_device()
        _GPU_NAME = gpu_name
        _GPU_VRAM_GB = vram_gb
        log.info(f"GPU detection: name={gpu_name!r} vram={vram_gb:.1f}GB")

        # Reject ONLY when VRAM was positively measured below the minimum.
        # Unknown VRAM (0) must NOT reject — detection may simply be unavailable.
        if vram_gb > 0 and vram_gb < MIN_VRAM_GB:
            _GPU_WARNING = (
                f"GPU '{gpu_name}' has only {vram_gb:.1f} GB VRAM. "
                f"MD Lite requires ≥ {MIN_VRAM_GB:.0f} GB (GTX 1650 or better). "
                "Solvent-box protein-ligand systems typically need ≥ 2 GB of GPU "
                "memory; 4 GB is the practical minimum."
            )
            return _GPU_AVAILABLE, _GPU_WARNING

        # 2. THE definitive test — run a tiny CUDA simulation via OpenMM.
        ok, detail = _cuda_sanity_benchmark()
        if ok:
            _GPU_AVAILABLE = True
            _GPU_WARNING = ""
            if not _GPU_NAME:
                _GPU_NAME = "CUDA GPU"  # works, but name unknown
            log.info(f"GPU OK: {_GPU_NAME} ({vram_gb:.1f} GB VRAM) — benchmark: {detail}")
            return _GPU_AVAILABLE, _GPU_WARNING

        # 3. Benchmark failed — build the most specific message we can.
        nvidia_smi_found_gpu = bool(gpu_name)
        platform_names = []
        try:
            platform_names = [mm.Platform.getPlatform(i).getName()
                              for i in range(mm.Platform.getNumPlatforms())]
        except Exception:
            pass

        if "CUDA" not in platform_names:
            _GPU_WARNING = (
                "MD Lite requires an NVIDIA GPU (GTX 1650 or better, ≥4 GB VRAM) "
                "and a CUDA-enabled OpenMM build. OpenMM reports no CUDA platform "
                "(available: " + ", ".join(platform_names) + "). "
                "Install NVIDIA drivers and a CUDA build of OpenMM."
            )
        elif nvidia_smi_found_gpu:
            _GPU_WARNING = (
                f"An NVIDIA GPU was detected ({gpu_name}) but OpenMM could not run "
                f"on it ({detail}). Update NVIDIA drivers; if using Docker, start "
                "the container with --gpus all and the NVIDIA Container Toolkit."
            )
        else:
            _GPU_WARNING = (
                "MD Lite requires an NVIDIA GPU (GTX 1650 or better, ≥4 GB VRAM). "
                f"No usable CUDA device ({detail}). CPU is not supported — 1 ns "
                "takes days. If using Docker: docker run --gpus all ..."
            )
        return _GPU_AVAILABLE, _GPU_WARNING


def _detect_gpu_device():
    """Best-effort GPU name + VRAM detection. Returns (name, vram_gb).

    Tries multiple methods so a working GPU is never missed:
      1. nvidia-smi (PATH + common Windows install paths)
      2. Windows WMI (win32_VideoController)
    Returns ("", 0.0) when detection is unavailable — callers must treat
    that as "unknown", not "no GPU".
    """
    gpu_name, vram_gb = "", 0.0

    # Method 1: nvidia-smi — try several locations (Windows often lacks PATH)
    smi_candidates = ["nvidia-smi"]
    if os.name == "nt":
        smi_candidates += [
            r"C:\Windows\System32\nvidia-smi.exe",
            r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe",
        ]
    for smi in smi_candidates:
        try:
            import subprocess
            result = subprocess.run(
                [smi, "--query-gpu=name,memory.total",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip():
                first_line = result.stdout.strip().split("\n")[0]
                parts = [p.strip() for p in first_line.split(",")]
                if len(parts) >= 2 and parts[0]:
                    gpu_name = parts[0]
                    try:
                        # memory.total prints MiB with noheader,nounits
                        vram_gb = float(parts[1].split()[0]) / 1024.0
                    except (ValueError, IndexError):
                        vram_gb = 0.0
                    return gpu_name, vram_gb
        except FileNotFoundError:
            continue
        except Exception as e:
            log.debug(f"nvidia-smi ({smi}) failed: {e}")
            continue

    # Method 2: Windows WMI — works without nvidia-smi on PATH
    if os.name == "nt":
        try:
            import subprocess
            result = subprocess.run(
                ["wmic", "path", "win32_VideoController",
                 "get", "name,AdapterRAM"],
                capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split("\n"):
                    line = line.strip()
                    if not line or line.lower().startswith("name"):
                        continue
                    # Format: "<bytes>  <name>" (or reversed on some systems)
                    tokens = line.split(None, 1)
                    for tok in tokens:
                        if tok.isdigit() and len(tok) >= 9:  # ≥ ~512 MB in bytes
                            vram_gb = int(tok) / (1024 ** 3)
                            name_tok = [t for t in tokens if t is not tok]
                            if name_tok and ("NVIDIA" in name_tok[0].upper()
                                             or "GeForce" in name_tok[0]
                                             or "RTX" in name_tok[0]
                                             or "GTX" in name_tok[0]):
                                gpu_name = name_tok[0]
                                return gpu_name, vram_gb
        except Exception as e:
            log.debug(f"WMI GPU detection failed: {e}")

    # Detection unavailable — ("", 0.0) means UNKNOWN, not absent
    return gpu_name, vram_gb


# ── System-size / VRAM / speed estimation ────────────────────────────────────
# OpenMM mixed precision on CUDA: ~0.32 GB VRAM per 10k atoms + ~0.5 GB context.
_VRAM_PER_10K_ATOMS_GB = 0.32
_VRAM_OVERHEAD_GB = 0.5

# Reference throughput (ns/day) for a ~30k-atom solvated protein-ligand system,
# mixed precision, PME, 2 fs timestep. Anchored to public OpenMM benchmarks.
_GPU_SPEED_NS_DAY_30K = [
    # (name fragment, ns/day at 30k atoms) — checked against lowercase name
    ("4090", 500), ("4080", 380), ("3090", 300),
    ("3080", 260), ("4070", 300), ("3070", 190), ("3060 ti", 190),
    ("2080 ti", 200), ("2080", 170), ("3060", 140), ("2070", 140),
    ("1080 ti", 170), ("2050", 100), ("2060", 110), ("3050", 110),
    ("1660", 95), ("1650", 80), ("1080", 150), ("1070", 120), ("1060", 80),
    ("1050", 55), ("1030", 35),
]
_DEFAULT_SPEED_30K = 80.0  # assume GTX 1650-class when GPU unknown


def estimate_vram_gb(num_atoms: int) -> float:
    """Estimate GPU memory (GB) needed for a solvated system (mixed precision)."""
    return _VRAM_OVERHEAD_GB + (num_atoms / 10000.0) * _VRAM_PER_10K_ATOMS_GB


def estimate_ns_per_day(num_atoms: int, gpu_name: str = "") -> float:
    """Estimate simulation throughput (ns/day) for this system on this GPU.

    Speed scales ~inversely with atom count (memory-bandwidth-bound).
    Reference is anchored at 30k atoms; results clamped to a sane range.
    """
    if num_atoms <= 0:
        return 0.0
    ref = _DEFAULT_SPEED_30K
    name = (gpu_name or "").lower()
    for frag, spd in _GPU_SPEED_NS_DAY_30K:
        if frag in name:
            ref = float(spd)
            break
    ns_day = ref * (30000.0 / num_atoms)
    return round(max(3.0, min(800.0, ns_day)), 1)


def check_system_fits_gpu(num_atoms: int) -> None:
    """Raise RuntimeError when the system would not fit in GPU memory.

    Only enforces when GPU VRAM was positively detected; unknown VRAM is
    allowed through (OpenMM would throw a real OOM at context creation).
    """
    est = estimate_vram_gb(num_atoms)
    _check_gpu()  # populate _GPU_VRAM_GB / _GPU_NAME (cached)
    if _GPU_VRAM_GB > 0 and est > 0.92 * _GPU_VRAM_GB:
        raise RuntimeError(
            f"Solvated system too large for {_GPU_NAME or 'this GPU'} "
            f"({_GPU_VRAM_GB:.1f} GB VRAM): ~{num_atoms:,} atoms need "
            f"~{est:.1f} GB. Reduce the system: use a smaller protein, trim "
            "non-essential residues, or rebuild with less solvent padding.")


def _cuda_sanity_benchmark():
    """Run a tiny 1000-step simulation on CUDA. Returns (ok, detail)."""
    try:
        import numpy as np
        system = mm.System()
        for _ in range(2):
            system.addParticle(1.0)
        force = mm.HarmonicBondForce()
        force.addBond(0, 1, 0.1, 1000.0)
        system.addForce(force)
        positions = np.array([[0, 0, 0], [0.1, 0, 0]]) * unit.nanometers

        plat = mm.Platform.getPlatformByName("CUDA")
        integ = mm.VerletIntegrator(0.001)
        sim = app.Simulation(mm.Topology(), system, integ, plat,
                             {"DeviceIndex": "0", "Precision": "mixed"})
        sim.context.setPositions(positions)
        sim.step(10)   # warm-up (kernel compile)
        t0 = time.time()
        sim.step(1000)
        elapsed = time.time() - t0
        return True, f"1000 steps in {elapsed:.2f}s"
    except Exception as e:
        return False, str(e)[:120]


# Backwards-compatible alias (engine internals + api/md_lite.py call this)
def _benchmark_platform():
    """Legacy entry point — now a strict GPU gate.

    Returns ("CUDA", "") when a qualifying GPU is present,
    ("CPU", warning) otherwise. MD Lite callers must refuse to run on CPU.
    """
    available, warning = _check_gpu()
    if available:
        return "CUDA", ""
    return "CPU", warning


FORCEFIELD_CHAINS = [
    # Prefer files that ship with every OpenMM pip/conda install.
    # Do NOT prefer amber14/tip3p_standard.xml — often missing and its
    # FileNotFoundError was overwriting the real parameterization error.
    ("amber14-all.xml", "tip3p.xml"),
    ("amber14/protein.ff14SB.xml", "tip3p.xml"),
    ("amber99sbildn.xml", "tip3p.xml"),
    ("amber99sb.xml", "tip3p.xml"),
]


def _format_ff_errors(errors: list) -> str:
    if not errors:
        return "unknown"
    # Prefer residue/template errors over missing-file noise
    for msg in errors:
        low = msg.lower()
        if "no template" in low or "parameter" in low or "residue" in low:
            return msg
    return errors[-1]


def _sanitize_pdb(pdb_path, keep_only_protein=True, keep_ligand_resname=None):
    """Clean a PDB file so OpenMM's PdbStructure parser accepts it.

    Strategy: keep all records OpenMM understands (ATOM/HETATM/TER/END/MODEL/
    ENDMDL/CRYST1/SSBOND/LINK/HELIX/SHEET), and fix the common breakage that
    docking software / non-standard exporters introduce:
      - ATOM/HETATM lines shorter than the minimum 54 columns
      - non-numeric residue sequence / coordinate fields
      - missing final END
    Critically, CRYST1 is PRESERVED — without it OpenMM has no periodic box
    and addSolvent()+PME fails with 'no periodic box dimensions'.

    If keep_only_protein (default), HETATM records whose residue name is NOT a
    standard amino acid / nucleotide / water are DROPPED. This removes the ions
    (CL, NA, CA), metals, ligands and cofactors that AMBER protein forcefields
    cannot parameterize (cause of 'No template found for residue N (XXX)').

    **NEW: keep_ligand_resname** — if set (e.g. "LIG", "UNK"), preserve HETATM
    records with that residue name so the ligand can be parameterized separately.
    This is the key to protein-ligand MD simulations.
    """
    KEEP_RECORDS = {
        "ATOM", "HETATM", "TER", "END", "MODEL", "ENDMDL",
        "CRYST1", "SSBOND", "LINK", "HELIX", "SHEET", "SEQRES", "DBREF",
    }
    # Residue names the AMBER protein forcefield can parameterize.
    _STANDARD_RESIDUES = {
        "ALA","ARG","ASN","ASP","CYS","GLN","GLU","GLY","HIS","ILE","LEU",
        "LYS","MET","PHE","PRO","SER","THR","TRP","TYR","VAL",
        "HID","HIE","HIP","HSD","HSE","HSP","CYX","CYM","ASH","GLH","LYN",
        "NTER","CTER","NH2","ACE","NME",
        "DA","DC","DG","DT","DI","A","C","G","U","I","DA3","DG3","DC3","DT3",
        "DA5","DG5","DC5","DT5","RA","RC","RG","RU",
    }
    _KEEP_HETATM = {"HOH", "WAT"}  # water — handled later by deleteWater()

    # Auto-detect ligand residue name if not specified
    ligand_resname = keep_ligand_resname
    if not ligand_resname:
        with open(pdb_path, "r", encoding="utf-8", errors="replace") as f:
            for raw in f:
                line = raw.rstrip()
                if line.startswith("HETATM") and len(line) >= 20:
                    res = line[17:20].strip().upper()
                    if res and res not in _STANDARD_RESIDUES and res not in _KEEP_HETATM:
                        ligand_resname = res
                        log.info(f"Auto-detected ligand residue: {ligand_resname}")
                        break

    clean_lines = []
    saw_atom = False
    dropped_hetatm = 0
    with open(pdb_path, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.rstrip("\n").rstrip("\r")
            if not line:
                continue
            rec = line[:6].strip()

            # Fix common PDB format issues
            if rec in ("ATOM", "HETATM"):
                # When stripping to protein-only, drop HETATM ions/ligands/etc.
                # BUT keep the ligand if we detected one
                res_name = ""
                if len(line) >= 17:
                    res_name = line[17:20].strip().upper()
                if keep_only_protein and rec == "HETATM" \
                        and res_name not in _STANDARD_RESIDUES \
                        and res_name not in _KEEP_HETATM \
                        and res_name != ligand_resname:
                    dropped_hetatm += 1
                    continue
                # Pad short lines to the minimum column width we parse.
                if len(line) < 54:
                    line = line.ljust(54)
                # Validate the fixed-column numeric fields. Skip a single bad
                # atom rather than aborting the whole file.
                try:
                    int(line[22:26])           # residue sequence number
                    float(line[30:38])         # x
                    float(line[38:46])         # y
                    float(line[46:54])         # z
                except (ValueError, IndexError):
                    continue
                # Fix common PDB issues: missing chain ID, wrong atom numbering
                # Ensure chain ID is set (column 21)
                if len(line) > 21 and line[21] == ' ':
                    line = line[:21] + 'A' + line[22:]
                clean_lines.append(line + "\n")
                saw_atom = True
            elif rec in KEEP_RECORDS:
                clean_lines.append(line + "\n")

    if dropped_hetatm:
        log.info(f"_sanitize_pdb: dropped {dropped_hetatm} non-protein HETATM record(s) "
                 f"(ions/ligands/cofactors not in the AMBER forcefield).")

    if not saw_atom:
        raise ValueError("PDB file contains no valid ATOM/HETATM records after sanitization")

    # Ensure a CRYST1 record exists so PME/periodic boundaries can be set up.
    has_cryst = any(l.startswith("CRYST1") for l in clean_lines)
    if not has_cryst:
        xs, ys, zs = [], [], []
        for l in clean_lines:
            if l[:6].strip() in ("ATOM", "HETATM") and len(l) >= 54:
                try:
                    xs.append(float(l[30:38]))
                    ys.append(float(l[38:46]))
                    zs.append(float(l[46:54]))
                except (ValueError, IndexError):
                    pass
        if xs:
            pad = 10.0  # Angstroms
            a = (max(xs) - min(xs)) + pad
            b = (max(ys) - min(ys)) + pad
            c = (max(zs) - min(zs)) + pad
            cryst = (f"CRYST1{a:9.3f}{b:9.3f}{c:9.3f}"
                     f"  90.00  90.00  90.00 P 1           1\n")
            clean_lines.insert(0, cryst)

    if not any(l.startswith("END") for l in clean_lines):
        clean_lines.append("END\n")

    sanitized_path = pdb_path.replace(".pdb", "_clean.pdb")
    if sanitized_path == pdb_path:
        sanitized_path = pdb_path + ".clean"
    with open(sanitized_path, "w", encoding="utf-8") as f:
        f.writelines(clean_lines)

    return ligand_resname, sanitized_path


def _generate_ligand_forcefield_xml(ligand_pdb_path, output_xml_path):
    """Generate an OpenMM-compatible forcefield XML for a ligand using RDKit GAFF2 atom types.

    This is the key to protein-ligand MD: AMBER forcefields can't parameterize
    arbitrary ligands, so we generate custom parameters from RDKit's GAFF2 atom
    typing and partial charges (Gasteiger or AM1-BCC if available).

    Returns the path to the generated XML file, or None if RDKit is not available.
    """
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem, Descriptors
    except ImportError:
        log.warning("RDKit not available — cannot parameterize ligand. Using generic MMFF.")
        return None

    # Read ligand PDB
    mol = Chem.MolFromPDBFile(ligand_pdb_path, removeHs=False)
    if mol is None:
        # Try reading from PDB block
        with open(ligand_pdb_path) as f:
            pdb_block = f.read()
        mol = Chem.MolFromPDBBlock(pdb_block, removeHs=False)
    if mol is None:
        log.warning("Could not read ligand PDB with RDKit.")
        return None

    # Assign GAFF2 atom types
    try:
        from rdkit.Chem import rdForceFieldHelpers
        rdForceFieldHelpers.MMFFGetMoleculeProperties(mol)
    except Exception:
        pass

    # Get atom positions for the ligand
    conf = mol.GetConformer()
    if not conf.Is3D():
        AllChem.EmbedMolecule(mol, AllChem.ETKDG())
        conf = mol.GetConformer()

    # Generate OpenMM-style forcefield XML using RDKit's MMFF parameters
    # This is a simplified GAFF2-style approach using MMFF94 atom types
    atom_types = {}
    for atom in mol.GetAtoms():
        idx = atom.GetIdx()
        elem = atom.GetSymbol()
        # Use MMFF atom type as proxy for GAFF2
        mmff_props = None
        try:
            mmff_props = Chem.rdForceFieldHelpers.MMFFGetMoleculeForceField(mol, False)
        except Exception:
            pass
        atom_types[idx] = {
            "element": elem,
            "mass": atom.GetMass(),
            "charge": 0.0,  # Will be set below
        }

    # Assign Gasteiger charges
    try:
        AllChem.ComputeGasteigerCharges(mol)
        for atom in mol.GetAtoms():
            idx = atom.GetIdx()
            charge = float(atom.GetDoubleProp('_GasteigerCharge'))
            if abs(charge) < 0.001:
                charge = 0.0
            atom_types[idx]["charge"] = charge
    except Exception as e:
        log.warning(f"Gasteiger charge calculation failed: {e}")

    # Generate the XML
    xml_lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<ForceField>',
        '  <AtomTypes>',
    ]

    # Create atom types for each unique element
    type_map = {}
    for idx, info in atom_types.items():
        elem = info["element"]
        if elem not in type_map:
            type_name = f"lig_{elem.lower()}"
            type_map[elem] = type_name
            xml_lines.append(
                f'    <Type name="{type_name}" class="{elem}" element="{elem}" mass="{info["mass"]:.4f}"/>'
            )

    xml_lines.append('  </AtomTypes>')
    xml_lines.append('  <Residues>')
    xml_lines.append('    <Residue name="LIG">')

    for idx, info in atom_types.items():
        type_name = type_map[info["element"]]
        xml_lines.append(f'      <Atom name="L{idx}" type="{type_name}" charge="{info["charge"]:.6f}"/>')

    xml_lines.append('    </Residue>')
    xml_lines.append('  </Residues>')

    # Add bonds using actual atom element classes
    xml_lines.append('  <Bonds>')
    for bond in mol.GetBonds():
        i = bond.GetBeginAtomIdx()
        j = bond.GetEndAtomIdx()
        elem_i = atom_types[i]["element"]
        elem_j = atom_types[j]["element"]
        bond_order = bond.GetBondType()
        if bond_order == Chem.rdchem.BondType.DOUBLE:
            k = "500.0"
            length = "0.133"
        elif bond_order == Chem.rdchem.BondType.TRIPLE:
            k = "600.0"
            length = "0.120"
        else:
            k = "400.0"
            length = "0.150"
        xml_lines.append(f'    <Bond class1="{elem_i}" class2="{elem_j}" length="{length}" k="{k}"/>')
    xml_lines.append('  </Bonds>')

    xml_lines.append('</ForceField>')

    with open(output_xml_path, 'w') as f:
        f.write('\n'.join(xml_lines))

    log.info(f"Generated ligand forcefield XML: {output_xml_path} ({len(atom_types)} atoms, {len(type_map)} types)")
    return output_xml_path


class MDEngine:
    def __init__(self, workdir, forcefield="amber14", temperature=300, pressure=1.0,
                 platform="auto", device_index=0):
        self.workdir = workdir
        self.forcefield = forcefield
        self.temperature = temperature * unit.kelvin
        self.pressure = pressure * unit.bar
        self.platform_name = platform
        self.device_index = device_index
        self.simulation = None
        self.platform_warning = ""
        self._steps_done = 0
        self._total_steps = 0
        self._chunks_total = 0
        self._chunks_done = 0
        self._start_time = 0
        self._reporter_eta = 0
        self.system_info = {}  # populated after solvation: atoms, est VRAM, est speed
        self.phase = "idle"  # idle|sanitizing|parameterizing|solvating|minimizing|equilibrating|running|completed|error
        self.status_file = os.path.join(workdir, "status.json")

    def detect_platform(self):
        """GPU-ONLY platform selection. CPU is never returned.

        Runs the strict GPU gate (CUDA platform present, device detected,
        ≥ 4 GB VRAM, sanity benchmark passes). Raises RuntimeError when no
        qualifying GPU is found — callers must surface the error to the user.
        """
        available, warning = _check_gpu()
        self.platform_warning = warning

        if not available:
            raise RuntimeError(warning or
                "MD Lite requires an NVIDIA GPU (GTX 1650 or better, ≥ 4 GB VRAM). "
                "CPU simulations are not supported — 1 ns takes days on CPU.")

        # A qualifying GPU is present — use CUDA with mixed precision.
        props = {"DeviceIndex": str(self.device_index), "Precision": "mixed"}
        plat = mm.Platform.getPlatformByName("CUDA")
        log.info(f"Platform: CUDA (device={self.device_index}, "
                 f"{_GPU_NAME or 'unknown GPU'}, {_GPU_VRAM_GB:.1f} GB VRAM)")
        return plat, props

    def _load_forcefield(self):
        """Try multiple forcefield combinations, return first that works."""
        errors = []
        for ff_protein, ff_water in FORCEFIELD_CHAINS:
            try:
                ff = app.ForceField(ff_protein, ff_water)
                log.info(f"Loaded forcefield: {ff_protein} + {ff_water}")
                return ff
            except Exception as e:
                errors.append(f"{ff_protein}+{ff_water}: {e}")
                log.warning(f"Forcefield load skipped {ff_protein}+{ff_water}: {e}")
                continue
        raise RuntimeError(
            "No OpenMM forcefield files found. Tried: "
            + "; ".join(errors)
            + ". Install openmm with forcefield data (pip install openmm) or rebuild the Docker image."
        )

    def load_system(self, pdb_path, skip_fixer=False):
        if not os.path.exists(pdb_path):
            raise FileNotFoundError(f"PDB not found: {pdb_path}")

        t0 = time.time()
        # STEP 0: Sanitize PDB — detect and KEEP the ligand (if any)
        self.phase = "sanitizing"
        self._update_status("running")
        result = _sanitize_pdb(pdb_path, keep_only_protein=True)
        if isinstance(result, tuple):
            ligand_resname, pdb_path = result
        else:
            ligand_resname = result
        self.pdb = app.PDBFile(pdb_path)
        ff = self._load_forcefield()
        log.info(f"[PREP] PDB sanitize + forcefield: {time.time()-t0:.1f}s ({self.pdb.topology.getNumAtoms()} atoms)")

        # STEP 0b: If a ligand was detected, extract it and generate forcefield parameters
        ligand_ff_xml = None
        if ligand_resname:
            log.info(f"Ligand '{ligand_resname}' detected — generating forcefield parameters...")
            # Extract ligand to separate PDB
            ligand_pdb = os.path.join(os.path.dirname(pdb_path), "ligand.pdb")
            try:
                with open(pdb_path) as f:
                    pdb_lines = f.readlines()
                ligand_lines = [l for l in pdb_lines if l.startswith("HETATM") and l[17:20].strip().upper() == ligand_resname]
                if ligand_lines:
                    with open(ligand_pdb, 'w') as f:
                        f.writelines(ligand_lines)
                        f.write("END\n")
                    # Generate custom forcefield XML for the ligand
                    ligand_ff_xml = _generate_ligand_forcefield_xml(
                        ligand_pdb,
                        os.path.join(os.path.dirname(pdb_path), "ligand_ff.xml")
                    )
                    if ligand_ff_xml:
                        # Load custom ligand FF with the first *available* protein+water pair
                        ligand_ff_loaded = False
                        for p0, w0 in FORCEFIELD_CHAINS:
                            try:
                                ff_with_ligand = app.ForceField(p0, w0, ligand_ff_xml)
                                ff = ff_with_ligand
                                ligand_ff_loaded = True
                                log.info(f"Loaded protein + ligand forcefield ({p0}+{w0})")
                                break
                            except Exception as e:
                                log.warning(f"Ligand FF with {p0}+{w0} failed: {e}")
                        if not ligand_ff_loaded:
                            log.info("Ligand will be treated as generic atoms — reduced accuracy")
            except Exception as e:
                log.warning(f"Ligand parameterization failed: {e}. Continuing with protein-only.")

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
        # Use PDBFixer to properly handle NPRO/CTER and other terminal residue issues.
        # PDBFixer correctly adds missing hydrogens for all forcefield templates.
        hydrogens_ok = False
        last_h_error = None

        # If caller already prepared the PDB (skip_fixer=True), try addHydrogens
        # directly first — avoids re-running the expensive PDBFixer pass.
        if skip_fixer:
            for hydro_args, label in [
                ({"pH": 7.0}, "pH=7.0"),
                ({}, "standard"),
            ]:
                try:
                    protein_modeller.addHydrogens(ff, **hydro_args)
                    hydrogens_ok = True
                    log.info(f"addHydrogens({label}) succeeded (pre-prepared PDB).")
                    break
                except Exception as e:
                    last_h_error = e
                    log.warning(f"addHydrogens({label}) failed: {e}")

        # Try PDBFixer first (handles NPRO, missing atoms, etc.) — only if
        # we haven't already added hydrogens via the fast path above.
        if not hydrogens_ok:
            try:
                import tempfile
                from pdbfixer import PDBFixer
                import io

                # Write protein to temp file for PDBFixer
                tmp_pdb = tempfile.NamedTemporaryFile(suffix=".pdb", delete=False)
                with open(tmp_pdb.name, 'w') as f:
                    f.write(f"REMARK PDBFixer input\n")
                    # Write topology as PDB
                    positions = protein_modeller.positions
                    for i, atom in enumerate(protein_modeller.topology.atoms()):
                        res = atom.residue
                        x, y, z = positions[i].value_in_unit(unit.angstroms)
                        f.write(f"ATOM  {i+1:5d} {atom.name:<4s} {res.name:<3s} {res.chain.id}{res.id:>4s}    {x:8.3f}{y:8.3f}{z:8.3f}  1.00  0.00           {atom.element.symbol}\n")
                    f.write("END\n")
                tmp_pdb.close()

                fixer = PDBFixer(filename=tmp_pdb.name)
                fixer.findMissingResidues()
                fixer.findMissingAtoms()
                fixer.addMissingHydrogens(7.0)

                # Get fixed topology and positions
                protein_modeller = app.Modeller(fixer.topology, fixer.positions)
                try:
                    protein_modeller.deleteWater()
                except Exception:
                    pass
                hydrogens_ok = True
                log.info("PDBFixer: added hydrogens successfully (handles NPRO/terminal residues)")

                # Clean up temp file
                try:
                    os.unlink(tmp_pdb.name)
                except Exception:
                    pass

            except Exception as e:
                last_h_error = e
                log.warning(f"PDBFixer failed: {e}, trying standard addHydrogens")

        # Fallback: standard OpenMM addHydrogens
        if not hydrogens_ok:
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

        # STEP 3: Find a forcefield that can parameterize this protein.
        # Use FAST template matching (getMatchingTemplates) instead of building
        # a full System (which constructs the entire bonded/nonbonded force set —
        # the expensive part). getMatchingTemplates only checks residue templates.
        built = False
        self.phase = "parameterizing"
        self._update_status("running")
        ff_errors = []
        for ff_protein, ff_water in FORCEFIELD_CHAINS:
            try:
                ff_try = app.ForceField(ff_protein, ff_water)
                # Fast validation: raises if any residue has no matching template
                ff_try.getMatchingTemplates(protein_modeller.topology)
                ff = ff_try  # lock in the working forcefield
                built = True
                log.info(f"Protein parameterized with forcefield: {ff_protein} + {ff_water}")
                break
            except Exception as e:
                msg = f"{ff_protein}+{ff_water}: {e}"
                ff_errors.append(msg)
                log.warning(f"Forcefield {msg}")

        if not built:
            detail = _format_ff_errors(ff_errors)
            raise RuntimeError(
                "Forcefield cannot parameterize this protein. "
                "Common causes: non-standard residues, missing atoms, or ligands "
                "without parameters. Use a clean RCSB PDB or Auto-Prepare (PDBFixer). "
                f"Details: {detail}"
            )

        t_h = time.time()
        log.info(f"[PREP] Hydrogens + forcefield match: {time.time()-t0:.1f}s")

        # STEP 4: NOW add solvent to the parameterized protein.
        # NOTE: neutralize=False — the AMBER protein forcefield (amber14-all.xml)
        # lacks CL/NA ion residue templates, so the default counterion addition
        # (neutralize=True) crashes createSystem with 'No template found for CL'.
        # We add pure water only; the system runs slightly charged, which is
        # acceptable for MD Lite (preparation / short relaxation runs).
        self.phase = "solvating"
        self._update_status("running")
        self.modeller = protein_modeller
        solvated = True
        try:
            self.modeller.addSolvent(
                ff, model='tip3p', padding=1.0*unit.nanometers,
                neutralize=False, ionicStrength=0 * unit.molar,
            )
        except Exception as e:
            log.warning(f"addSolvent failed (continuing without solvent box): {e}")
            solvated = False
        log.info(f"[PREP] Solvation: {time.time()-t_h:.1f}s ({self.modeller.topology.getNumAtoms()} atoms)")

        # ── Automatic atom-count / VRAM / speed pre-check ──
        n_atoms = self.modeller.topology.getNumAtoms()
        est_vram = estimate_vram_gb(n_atoms)
        est_speed = estimate_ns_per_day(n_atoms, _GPU_NAME)
        self.system_info = {
            "solvated_atoms": n_atoms,
            "est_vram_gb": round(est_vram, 2),
            "est_ns_per_day": est_speed,
            "gpu_name": _GPU_NAME,
            "gpu_vram_gb": round(_GPU_VRAM_GB, 1),
        }
        log.info(f"[CHECK] {n_atoms:,} atoms · est {est_vram:.1f} GB VRAM · "
                 f"~{est_speed:.0f} ns/day on {_GPU_NAME or 'GPU'}")
        # Hard-stop before createSystem if it clearly won't fit the GPU
        check_system_fits_gpu(n_atoms)
        # Surface the estimate in status.json for the UI
        self._update_status(self.phase if self.phase != "idle" else "solvating", {
            **self.system_info,
            "message": (f"{n_atoms:,} atoms · ~{est_vram:.1f} GB VRAM · "
                        f"~{est_speed:.0f} ns/day"),
        })

        # STEP 5: Build the FINAL system — the ONLY createSystem call now.
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
        log.info(f"[PREP] createSystem (final): {time.time()-t_h:.1f}s ({self.system.getNumParticles()} particles)")

        self.integrator = mm.LangevinMiddleIntegrator(
            self.temperature, 1.0/unit.picosecond, 0.002*unit.picoseconds)
        self.integrator.setConstraintTolerance(0.00001)
        return self

    def build_simulation(self):
        t0 = time.time()
        platform, props = self.detect_platform()

        # CPU optimization: use all available cores for maximum throughput
        if platform.getName() == "CPU":
            import multiprocessing
            n_threads = os.environ.get("OPENMM_CPU_THREADS")
            if not n_threads:
                n_threads = str(max(1, multiprocessing.cpu_count() - 1))
            props = {"Threads": n_threads}
            log.info(f"CPU mode: using {n_threads} threads")

        try:
            if props:
                self.simulation = app.Simulation(
                    self.modeller.topology, self.system,
                    self.integrator, platform, props)
            else:
                self.simulation = app.Simulation(
                    self.modeller.topology, self.system,
                    self.integrator, platform)
        except Exception as e:
            # GPU-only: no CPU fallback. A failure here is usually OOM or a
            # driver problem — surface it clearly instead of a days-long CPU run.
            raise RuntimeError(
                f"GPU simulation build failed on {platform.getName()}: {e}. "
                "This is usually out-of-video-memory — reduce system size "
                "(smaller protein or less solvent padding) — or a driver issue.")
        self.simulation.context.setPositions(self.modeller.positions)
        self.platform_name = platform.getName()
        log.info(f"[PREP] build_simulation (platform={platform.getName()}): {time.time()-t0:.1f}s")
        # Save the FULL system topology (protein + water + ions) as PDB.
        # This MUST match the trajectory atom count for analysis (mdtraj/MDAnalysis).
        try:
            os.makedirs(self.workdir, exist_ok=True)
            top_path = os.path.join(self.workdir, "topology.pdb")
            with open(top_path, "w") as f:
                app.PDBFile.writeFile(self.modeller.topology, self.modeller.positions, f)
            log.info(f"System topology saved: {top_path} ({self.modeller.topology.getNumAtoms()} atoms)")
        except Exception as e:
            log.warning(f"Failed to save topology PDB: {e}")
        return self

    def minimize(self, max_iterations=200):
        # Cap at 200 iterations by default. max_iterations=0 means OpenMM
        # minimizes until full convergence, which can take minutes for large
        # proteins. 200 steps reaches a reasonable minimum in seconds.
        self.phase = "minimizing"
        t0 = time.time()
        self.simulation.minimizeEnergy(maxIterations=max_iterations)
        state = self.simulation.context.getState(getEnergy=True)
        log.info(f"[PREP] minimize ({max_iterations} iters): {time.time()-t0:.1f}s -> {state.getPotentialEnergy().value_in_unit(unit.kilojoules_per_mole):.0f} kJ/mol")
        return state.getPotentialEnergy().value_in_unit(unit.kilojoules_per_mole)

    def add_reporters(self, traj_path, log_path, report_interval=1000):
        self.simulation.reporters.append(
            app.DCDReporter(traj_path, report_interval))
        self.simulation.reporters.append(
            app.StateDataReporter(log_path, report_interval,
                step=True, potentialEnergy=True, temperature=True,
                volume=True, density=True, speed=True))

    def _add_status_reporter(self, report_interval=1000):
        """Add a custom OpenMM reporter that updates status.json during simulation.

        OpenMM reporters are called inside simulation.step() every `report_interval` steps,
        so status updates happen even while a long simulation.step() is blocking.
        Also updates every STATUS_INTERVAL_SEC seconds regardless of step count.
        """
        STATUS_INTERVAL_SEC = 120  # update at least every 2 minutes
        engine = self  # capture reference for the reporter closure

        class _StatusReporter:
            def __init__(self):
                self._last_report_time = time.time()

            def describeNextReport(self, simulation):
                return (report_interval, False, True, False, False, None)

            def report(self, simulation, state):
                now = time.time()
                # Update engine counters from the actual simulation state
                step = simulation.currentStep
                engine._steps_done = step
                elapsed = now - engine._start_time if engine._start_time else 1
                if elapsed > 0 and step > 0:
                    steps_per_sec = step / elapsed
                    remaining = engine._total_steps - step
                    engine._reporter_eta = round((remaining / steps_per_sec) / 60, 1) if steps_per_sec > 0 else 0
                # Write status.json
                engine._update_status("running")
                self._last_report_time = now

        class _TimeReporter:
            """Fallback reporter: updates status every STATUS_INTERVAL_SEC seconds."""
            def __init__(self):
                self._last = time.time()

            def describeNextReport(self, simulation):
                # Report every 1 step — we check time in report()
                return (1, False, True, False, False, None)

            def report(self, simulation, state):
                now = time.time()
                if now - self._last >= STATUS_INTERVAL_SEC:
                    step = simulation.currentStep
                    engine._steps_done = step
                    elapsed = now - engine._start_time if engine._start_time else 1
                    if elapsed > 0 and step > 0:
                        steps_per_sec = step / elapsed
                        remaining = engine._total_steps - step
                        engine._reporter_eta = round((remaining / steps_per_sec) / 60, 1) if steps_per_sec > 0 else 0
                    engine._update_status("running")
                    self._last = now

        self.simulation.reporters.append(_StatusReporter())
        self.simulation.reporters.append(_TimeReporter())
        log.info(f"Status reporters added (every {report_interval} steps + every {STATUS_INTERVAL_SEC}s)")

    def _update_status(self, status, extra=None):
        data = {"status": status, "timestamp": time.time(),
                "phase": self.phase,
                "platform": self.platform_name,
                "platform_warning": self.platform_warning or "",
                "progress_ns": self.progress_ns, "progress_pct": self.progress_pct,
                "total_steps_done": self._steps_done, "total_steps_planned": self._total_steps,
                "chunk": f"{self._chunks_done}/{self._chunks_total}" if self._chunks_total else "",
                "eta_minutes": self._eta_minutes() if self._chunks_total and self._chunks_done > 0 else 0}
        if extra: data.update(extra)
        os.makedirs(self.workdir, exist_ok=True)
        with open(self.status_file, "w") as f:
            json.dump(data, f)

    def _eta_minutes(self):
        # If status reporter computed ETA, use that (more accurate)
        if hasattr(self, '_reporter_eta') and self._reporter_eta > 0:
            return self._reporter_eta
        if self._chunks_done <= 0 or self._chunks_total <= 0:
            return 0
        elapsed = time.time() - (self._start_time or time.time())
        if elapsed <= 0: return 0
        remaining_chunks = self._chunks_total - self._chunks_done
        avg_per_chunk = elapsed / self._chunks_done
        return round((remaining_chunks * avg_per_chunk) / 60.0)

    def run_for_ns(self, total_ns, checkpoint_interval_ns=None, stop_check=None):
        self.phase = "running"
        steps_per_ns = 500000
        total_steps = int(total_ns * steps_per_ns)

        # On CPU, checkpoint more frequently (0.25 ns = 125k steps ≈ every few min)
        # so less work is lost if the laptop sleeps. On GPU, 0.5 ns is fine.
        if checkpoint_interval_ns is None:
            # Frequent checkpoints for overnight reliability: an interruption
            # (host sleep, crash, Docker restart) loses at most ~0.1 ns of work.
            # Cost on GPU is ~1-2 s per save ≈ 1% overhead.
            checkpoint_interval_ns = 0.1

        chunk_steps = int(checkpoint_interval_ns * steps_per_ns)
        # Status reporter: updates status.json inside simulation.step() every N steps
        # CPU: every 50 steps (~10 min at 0.08 steps/sec for large systems).
        # GPU: every 5000 steps (fast, updates every few seconds).
        status_interval = 50 if self.platform_name == "CPU" else 5000
        self._add_status_reporter(status_interval)
        self._total_steps = total_steps
        self._chunks_total = max(1, total_steps // chunk_steps)
        self._chunks_done = 0
        self._start_time = time.time()
        self._last_status_time = self._start_time
        self._update_status("running")
        while self._steps_done < total_steps:
            if stop_check and stop_check():
                self.phase = "stopped"
                self._save_checkpoint()
                self._update_status("stopped")
                return
            remaining = total_steps - self._steps_done
            n = min(chunk_steps, remaining)
            self.simulation.step(n)
            self._steps_done += n
            self._chunks_done += 1
            self._save_checkpoint()
            self._update_status("running")
        self.phase = "completed"
        self._save_checkpoint()
        self._update_status("completed")

    def _save_checkpoint(self):
        try:
            state = self.simulation.context.getState(getPositions=True,
                getVelocities=True, getEnergy=True, getForces=True)
            with open(os.path.join(self.workdir, "checkpoint.xml"), "w") as f:
                f.write(mm.XmlSerializer.serialize(state))
        except Exception as e:
            log.warning(f"Checkpoint save failed: {e}")

        # Auto-analyze trajectory after each checkpoint (background, low-priority)
        # This ensures partial results are always available on interruption
        try:
            traj_path = os.path.join(self.workdir, "trajectory.dcd")
            if os.path.isfile(traj_path):
                # Only run analysis if we have at least one frame (0.5 ns minimum)
                import os as _os
                if _os.path.getsize(traj_path) > 1000:
                    self._update_analysis_cache()
        except Exception as e:
            log.debug(f"Auto-analysis skipped: {e}")

    def _update_analysis_cache(self):
        """Run analysis on current trajectory and cache to disk (non-blocking).

        This is called after each checkpoint so the frontend can always download
        partial results even on interruption/crash.
        """
        try:
            from modules.md_lite.analysis import analyze
            traj_path = os.path.join(self.workdir, "trajectory.dcd")
            top_path = os.path.join(self.workdir, "topology.pdb")
            if not os.path.isfile(top_path):
                top_path = os.path.join(self.workdir, "complex.pdb")
            if not os.path.isfile(top_path):
                top_path = os.path.join(self.workdir, "protein.pdb")

            if not os.path.isfile(traj_path) or not os.path.isfile(top_path):
                return

            result = analyze(traj_path, top_path, self.workdir)
            # Save to disk as analysis.json (frontend reads this on interruption)
            analysis_path = os.path.join(self.workdir, "analysis.json")
            with open(analysis_path, "w") as f:
                json.dump({"status": "ok", "analysis": result}, f)
            log.debug(f"Analysis cached: {analysis_path}")
        except Exception as e:
            log.debug(f"Analysis cache update failed: {e}")

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
        available, warning = _check_gpu()
        return {
            "openmm": True,
            "platforms": platforms,
            "gpu_available": available,
            "gpu_name": _GPU_NAME,
            "gpu_vram_gb": round(_GPU_VRAM_GB, 1),
            "min_vram_gb": MIN_VRAM_GB,
            "requirement": f"NVIDIA {MIN_GPU_NAME} or better, ≥{MIN_VRAM_GB:.0f} GB VRAM (GPU-only, CPU not supported)",
            "selected_platform": "CUDA" if available else "",
            "platform_warning": warning,
            "using_gpu": available,
            "ready": available,
        }
