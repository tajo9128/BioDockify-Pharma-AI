"""Approximate Binding Score — CPU-only, no MD simulation.

⚠️  IMPORTANT SCIENTIFIC DISCLAIMER:
This is NOT a proper MM-GBSA calculation. True MM-GBSA requires:
- Nanosecond-scale molecular dynamics trajectories of complex, receptor, and ligand
- MM energy decomposition (bond, angle, dihedral, VdW, electrostatic)
- GB solvation via Still's model or GBOBC with AM1-BCC or RESP charges
- SA via ICOSA or Shrake-Rupley algorithm

This module uses a simplified approximation:
- MM term: Vina empirical scoring (not molecular mechanics)
- GB term: RDKit descriptor-based solvation proxy (not Generalized Born)
- SA term: Crude SASA approximation (not ICOSA/Shrake-Rupley)

For publication or regulatory submission, use proper MM-GBSA tools:
- gmx_MMPBSA (GROMACS + AMBER)
- AMBER MMPBSA.py
- Schrödinger Prime MM-GBSA

This approximation is useful for quick ranking of docking poses but should NOT
be cited as MM-GBSA in publications. Use "approximate binding score" instead.

Reference: The scoring approach is inspired by Genheden & Ryde, Expert Syst. Appl. 2015
but does NOT implement their methodology.
"""
import os, logging, math
import numpy as np

log = logging.getLogger("docking_mmgbsa")


def _parse_pdbqt_atoms(pdbqt_text: str) -> list:
    """Parse ATOM/HETATM lines from PDBQT text."""
    atoms = []
    for line in pdbqt_text.split("\n"):
        if line.startswith("ATOM") or line.startswith("HETATM"):
            try:
                atoms.append({
                    "serial": int(line[6:11]),
                    "name": line[12:16].strip(),
                    "resname": line[17:20].strip(),
                    "chain": line[21:22].strip() or "A",
                    "resseq": int(line[22:26]),
                    "x": float(line[30:38]),
                    "y": float(line[38:46]),
                    "z": float(line[46:54]),
                    "element": (line[76:78] or line[12:14]).strip().rstrip("0123456789"),
                    "charge": float(line[70:76]) if line[70:76].strip() else 0.0,
                })
            except (ValueError, IndexError):
                pass
    return atoms


def _parse_vina_energies(pdbqt_path: str) -> list:
    """Parse Vina energies from REMARK lines."""
    energies = []
    try:
        with open(pdbqt_path) as f:
            for line in f:
                if "REMARK VINA RESULT:" in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        try:
                            energies.append(float(parts[3]))
                        except ValueError:
                            pass
    except Exception:
        pass
    return energies


def _distance(a1, a2):
    return math.sqrt((a1["x"] - a2["x"])**2 + (a1["y"] - a2["y"])**2 + (a1["z"] - a2["z"])**2)


def _compute_sasa_approx(atoms: list, probe: float = 1.4) -> float:
    """Approximate solvent-accessible surface area using atom counting.
    Each atom contributes 4*pi*(r+probe)^2 minus overlap with neighbors.
    Uses distance cutoff for O(n) performance on large proteins."""
    VDW = {"C": 1.7, "N": 1.55, "O": 1.52, "S": 1.8, "H": 1.2, "P": 1.8, "F": 1.47, "Cl": 1.75, "Br": 1.85, "I": 1.98}
    max_probe = 1.8 + probe  # largest VDW radius + probe
    cutoff = max_probe * 2 + 1.0  # distance beyond which overlap is negligible

    # Build spatial grid for fast neighbor lookup
    from collections import defaultdict
    grid_size = cutoff
    grid = defaultdict(list)
    for idx, a in enumerate(atoms):
        gx = int(a["x"] / grid_size)
        gy = int(a["y"] / grid_size)
        gz = int(a["z"] / grid_size)
        grid[(gx, gy, gz)].append(idx)

    sasa = 0.0
    for i, a in enumerate(atoms):
        r = VDW.get(a.get("element", "C"), 1.7) + probe
        area = 4 * math.pi * r * r
        overlap = 0
        gx = int(a["x"] / grid_size)
        gy = int(a["y"] / grid_size)
        gz = int(a["z"] / grid_size)
        # Check neighboring cells
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for j in grid.get((gx+dx, gy+dy, gz+dz), []):
                        if i == j:
                            continue
                        b = atoms[j]
                        d = _distance(a, b)
                        if d < cutoff:
                            rj = VDW.get(b.get("element", "C"), 1.7) + probe
                            if d < r + rj:
                                overlap += area * min(1.0, (r + rj - d) / (2 * r))
        sasa += max(0, area - overlap)
    return sasa


def _compute_desolvation_energy(atoms: list) -> float:
    """Estimate desolvation penalty from atom types and charges.
    Uses simplified GB-like formula: sum of charge^2 / radius terms."""
    GB_RADII = {"C": 1.7, "N": 1.55, "O": 1.52, "S": 1.8, "H": 1.2, "P": 1.8}
    dielectric_inner = 1.0
    dielectric_outer = 80.0
    desolv = 0.0
    for a in atoms:
        q = a.get("charge", 0.0)
        r = GB_RADII.get(a.get("element", "C"), 1.7)
        if abs(q) > 0.01:
            # Born equation: GB = -q^2 / (2*r) * (1/di - 1/do)
            gb = -(q * q) / (2.0 * r) * (1.0 / dielectric_inner - 1.0 / dielectric_outer)
            desolv += gb
    return desolv


def mmgbsa_score(job_id: str, jobs_dir: str = None) -> dict:
    """Compute MM-GBSA binding free energy estimate for a docking job.

    Returns per-pose MM-GBSA scores combining:
    - Vina energy (MM term: VdW + electrostatics)
    - Desolvation penalty (GB term)
    - Surface area penalty (SA term)
    - Consensus with Vina Z-score
    """
    if jobs_dir is None:
        from helpers import files
        jobs_dir = files.get_abs_path("tmp/docking_jobs")

    results_dir = os.path.join(jobs_dir, job_id)
    receptor_path = os.path.join(results_dir, "protein.pdbqt")
    if not os.path.exists(receptor_path):
        receptor_path = os.path.join(results_dir, "protein.pdb")
    ligand_path = os.path.join(results_dir, "docked_output.pdbqt")

    if not os.path.exists(receptor_path):
        return {"success": False, "error": "Receptor file not found"}
    if not os.path.exists(ligand_path):
        return {"success": False, "error": "Docked poses not found"}

    try:
        with open(receptor_path) as f:
            receptor_text = f.read()
        with open(ligand_path) as f:
            ligand_text = f.read()

        receptor_atoms = _parse_pdbqt_atoms(receptor_text)
        energies = _parse_vina_energies(ligand_path)

        if not energies:
            return {"success": False, "error": "No Vina poses found"}

        # Parse ligand poses
        poses_atoms = []
        current = []
        for line in ligand_text.split("\n"):
            if line.startswith("MODEL"):
                current = []
            elif line.startswith("ENDMDL"):
                if current:
                    poses_atoms.append(current)
                current = []
            elif line.startswith("ATOM") or line.startswith("HETATM"):
                try:
                    current.append({
                        "serial": int(line[6:11]),
                        "name": line[12:16].strip(),
                        "element": (line[76:78] or line[12:14]).strip().rstrip("0123456789"),
                        "x": float(line[30:38]),
                        "y": float(line[38:46]),
                        "z": float(line[46:54]),
                        "charge": float(line[70:76]) if line[70:76].strip() else 0.0,
                    })
                except (ValueError, IndexError):
                    pass

        # Build spatial grid for receptor atoms (fast neighbor lookup)
        from collections import defaultdict
        grid_size = 5.0  # Angstroms
        receptor_grid = defaultdict(list)
        for idx, ra in enumerate(receptor_atoms):
            gx = int(ra["x"] / grid_size)
            gy = int(ra["y"] / grid_size)
            gz = int(ra["z"] / grid_size)
            receptor_grid[(gx, gy, gz)].append(idx)

        # Compute per-pose MM-GBSA
        mmgbsa_results = []
        for i, vina_e in enumerate(energies):
            latoms = poses_atoms[i] if i < len(poses_atoms) else []

            # MM term = Vina energy (includes VdW + electrostatics + torsional penalty)
            mm_term = vina_e

            # GB term = desolvation energy for ligand atoms
            gb_term = _compute_desolvation_energy(latoms) if latoms else 0.0

            # SA term = surface area penalty (hydrophobic solvation)
            sasa = _compute_sasa_approx(latoms) if latoms else 0.0
            sa_term = 0.0072 * sasa  # kcal/mol/A^2 (standard SA coefficient)

            # Interaction energy with protein (simplified: count close contacts)
            interaction_bonus = 0.0
            if latoms and receptor_atoms:
                for la in latoms:
                    gx = int(la["x"] / grid_size)
                    gy = int(la["y"] / grid_size)
                    gz = int(la["z"] / grid_size)
                    # Check neighboring cells
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            for dz in (-1, 0, 1):
                                for ri in receptor_grid.get((gx+dx, gy+dy, gz+dz), []):
                                    ra = receptor_atoms[ri]
                                    d = _distance(la, ra)
                                    if d < 3.5:
                                        interaction_bonus -= 0.3  # Favorable contact
                                    elif d < 5.0:
                                        interaction_bonus -= 0.05

            # MM-GBSA = MM + GB + SA + interaction
            # More negative = better binding
            mmgbsa = mm_term + gb_term + sa_term + interaction_bonus

            mmgbsa_results.append({
                "pose_index": i,
                "vina_energy": round(vina_e, 3),
                "mm_term": round(mm_term, 3),
                "gb_term": round(gb_term, 3),
                "sa_term": round(sa_term, 3),
                "interaction_bonus": round(interaction_bonus, 3),
                "mmgbsa_energy": round(mmgbsa, 3),
            })

        # Z-score normalization
        if len(mmgbsa_results) > 1:
            scores = np.array([r["mmgbsa_energy"] for r in mmgbsa_results])
            mean_s = scores.mean()
            std_s = scores.std()
            for r in mmgbsa_results:
                if std_s > 1e-10:
                    r["mmgbsa_z"] = round(float((r["mmgbsa_energy"] - mean_s) / std_s), 4)
                else:
                    r["mmgbsa_z"] = 0.0
        else:
            mmgbsa_results[0]["mmgbsa_z"] = 0.0

        # Sort by MM-GBSA energy (most negative first)
        mmgbsa_results.sort(key=lambda r: r["mmgbsa_energy"])

        # Consensus: combine Vina Z and MM-GBSA Z
        vina_z = []
        if len(energies) > 1:
            ve = np.array(energies)
            vina_z = list((ve - ve.mean()) / (ve.std() + 1e-10))

        for r in mmgbsa_results:
            pi = r["pose_index"]
            vz = vina_z[pi] if pi < len(vina_z) else 0.0
            mz = r.get("mmgbsa_z", 0.0)
            r["consensus_z"] = round(float(0.4 * vz + 0.6 * mz), 4)

        mmgbsa_results.sort(key=lambda r: r["consensus_z"])

        return {
            "success": True,
            "method": "MM-GBSA (simplified, CPU-only)",
            "num_poses": len(mmgbsa_results),
            "best_mmgbsa": mmgbsa_results[0]["mmgbsa_energy"],
            "best_consensus_z": mmgbsa_results[0]["consensus_z"],
            "per_pose": mmgbsa_results,
        }

    except Exception as e:
        log.error(f"MM-GBSA scoring failed: {e}")
        return {"success": False, "error": str(e)}
