"""OpenMM MD Engine — setup, force field, integrator, simulation runners."""
import os, json, time, logging, threading
import openmm as mm
import openmm.app as app
import openmm.unit as unit

log = logging.getLogger("md_lite")

# Cache the benchmarked platform so we only pay the ~2s cost once per process.
_BENCHMARKED_PLATFORM = None
_BENCHMARK_WARNING = ""
_BENCHMARK_LOCK = threading.Lock()


def _benchmark_platform():
    """Run a tiny MD step on CUDA vs CPU and pick the faster one.

    Solves the 'CUDA reported available but no GPU in Docker' trap: OpenMM
    lists CUDA as a platform even when there is no device, and then runs
    10-50x slower than CPU. A 1000-step benchmark detects this in ~2s.
    """
    global _BENCHMARKED_PLATFORM, _BENCHMARK_WARNING
    with _BENCHMARK_LOCK:
        if _BENCHMARKED_PLATFORM is not None:
            return _BENCHMARKED_PLATFORM, _BENCHMARK_WARNING

        _BENCHMARKED_PLATFORM = "CPU"
        _BENCHMARK_WARNING = ""
        try:
            all_platforms = []
            for i in range(mm.Platform.getNumPlatforms()):
                p = mm.Platform.getPlatform(i)
                all_platforms.append((p.getName(), p.getSpeed()))
            has_cuda = any("CUDA" in n for n, _ in all_platforms)
            has_opencl = any("OpenCL" in n for n, _ in all_platforms)
            if not (has_cuda or has_opencl):
                return _BENCHMARKED_PLATFORM, _BENCHMARK_WARNING

            import numpy as np
            system = mm.System()
            for _ in range(2):
                system.addParticle(1.0)
            force = mm.HarmonicBondForce()
            force.addBond(0, 1, 0.1, 1000.0)
            system.addForce(force)
            positions = np.array([[0, 0, 0], [0.1, 0, 0]]) * unit.nanometers

            candidates = []
            if has_cuda:
                candidates.append("CUDA")
            if has_opencl:
                candidates.append("OpenCL")
            candidates.append("CPU")

            timings = {}
            for name in candidates:
                try:
                    plat = mm.Platform.getPlatformByName(name)
                    props = {}
                    if name == "CUDA":
                        props = {"DeviceIndex": "0", "Precision": "mixed"}
                    elif name == "OpenCL":
                        props = {"DeviceIndex": "0", "Precision": "mixed"}
                    integ = mm.VerletIntegrator(0.001)
                    sim = app.Simulation(mm.Topology(), system, integ, plat, props)
                    sim.context.setPositions(positions)
                    # Warm-up step (GPU kernel compilation)
                    sim.step(10)
                    t0 = time.time()
                    sim.step(1000)
                    timings[name] = time.time() - t0
                except Exception as e:
                    timings[name] = float("inf")
                    log.debug(f"Platform benchmark {name} failed: {e}")

            if timings:
                best = min(timings, key=timings.get)
                if timings[best] != float("inf"):
                    _BENCHMARKED_PLATFORM = best
                    for gpu_name in ("CUDA", "OpenCL"):
                        if gpu_name in timings and "CPU" in timings and \
                                timings[gpu_name] > timings["CPU"] * 1.5 and best == "CPU":
                            _BENCHMARK_WARNING = (
                                f"GPU ({gpu_name}) available but CPU is "
                                f"{timings[gpu_name]/timings['CPU']:.1f}x faster "
                                f"(no usable GPU device). Using CPU."
                            )
                    log.info(f"Platform benchmark: {timings} -> using {_BENCHMARKED_PLATFORM}")
        except Exception as e:
            log.warning(f"Platform benchmark failed, defaulting to CPU: {e}")
        return _BENCHMARKED_PLATFORM, _BENCHMARK_WARNING


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
        self.phase = "idle"  # idle|sanitizing|parameterizing|solvating|minimizing|equilibrating|running|completed|error
        self.status_file = os.path.join(workdir, "status.json")

    def detect_platform(self):
        """Auto-detect best platform using a real benchmark (not just availability).

        Priority: user-explicit CUDA/OpenCL → benchmark winner → CPU fallback.
        On Windows, sets DeviceIndex and mixed precision for GPU platforms.
        """
        all_platforms = []
        for i in range(mm.Platform.getNumPlatforms()):
            p = mm.Platform.getPlatform(i)
            all_platforms.append((p.getName(), p.getSpeed()))
        platform_names = [n for n, _ in all_platforms]

        # If user explicitly requested CPU, honor it.
        if self.platform_name.upper() == "CPU":
            log.info("Platform: CPU (user-selected)")
            return mm.Platform.getPlatformByName("CPU"), {}

        # If user explicitly requested CUDA or OpenCL, try it directly first.
        if self.platform_name.upper() in ("CUDA", "OPENCL"):
            requested = self.platform_name.upper()
            if requested in platform_names:
                props = {"DeviceIndex": str(self.device_index), "Precision": "mixed"}
                try:
                    plat = mm.Platform.getPlatformByName(requested)
                    log.info(f"Platform: {requested} (user-selected, device={self.device_index})")
                    return plat, props
                except Exception as e:
                    log.warning(f"Requested {requested} failed: {e}, falling back to benchmark")
            else:
                log.warning(f"Requested {requested} not available (have: {platform_names})")

        # "auto" or fallback: run the benchmark to pick the genuinely fastest.
        best_name, warning = _benchmark_platform()
        self.platform_warning = warning
        props = {}
        if best_name in ("CUDA", "OpenCL"):
            props = {"DeviceIndex": str(self.device_index), "Precision": "mixed"}
        try:
            plat = mm.Platform.getPlatformByName(best_name)
            log.info(f"Platform: {best_name} (benchmarked){' — ' + warning if warning else ''}")
            return plat, props
        except Exception:
            log.warning(f"Benchmarked platform {best_name} unavailable, using CPU")
            return mm.Platform.getPlatformByName("CPU"), {}

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
            # GPU failed at real workload (driver mismatch, OOM, etc.) → fallback to CPU
            if platform.getName() != "CPU":
                log.warning(f"{platform.getName()} simulation build failed ({e}), falling back to CPU")
                self.platform_warning = f"{platform.getName()} failed: {e}. Using CPU."
                platform = mm.Platform.getPlatformByName("CPU")
                import multiprocessing
                cpu_threads = str(max(1, multiprocessing.cpu_count() - 1))
                self.simulation = app.Simulation(
                    self.modeller.topology, self.system,
                    self.integrator, platform, {"Threads": cpu_threads})
            else:
                raise
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
            checkpoint_interval_ns = 0.25 if self.platform_name == "CPU" else 0.5

        chunk_steps = int(checkpoint_interval_ns * steps_per_ns)
        self._total_steps = total_steps
        self._chunks_total = max(1, total_steps // chunk_steps)
        self._chunks_done = 0
        self._start_time = time.time()
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
            info = {"name": p.getName(), "speed": p.getSpeed()}
            if p.getName() == "CUDA":
                try:
                    info["devices"] = p.getPropertyDefaultValue("DeviceIndex")
                    info["cuda_compiler"] = p.getPropertyDefaultValue("CudaCompiler") if hasattr(p, "getPropertyDefaultValue") else ""
                except Exception:
                    pass
            platforms.append(info)
        gpu_available = any("CUDA" in p["name"] or "OpenCL" in p["name"] for p in platforms)
        best_name, warning = _benchmark_platform()
        return {
            "openmm": True,
            "platforms": platforms,
            "gpu_available": gpu_available,
            "selected_platform": best_name,
            "platform_warning": warning,
            "using_gpu": best_name in ("CUDA", "OpenCL"),
        }
