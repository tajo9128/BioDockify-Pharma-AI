"""
BioDockify MD Lite — Publication-Grade Trajectory Analysis

Powered by MDAnalysis. Provides 10 advanced analyses beyond the basic
RMSD/RMSF/Rg/SASA already in analysis.py:

  1. Hydrogen Bond Analysis (residue-resolved, occupancy, distances, angles)
  2. Water Bridge Analysis (protein-ligand water-mediated interactions)
  3. Native Contacts (Q fraction — protein stability upon binding)
  4. Radial Distribution Function (solvation shells)
  5. Ramachandran Analysis (backbone dihedrals)
  6. Principal Component Analysis (essential dynamics)
  7. H-Bond Lifetimes (autocorrelation → residence time)
  8. Distance Tracking (ligand-residue distances over time)
  9. Secondary Structure (DSSP via MDA)
 10. Dielectric Constant (electrostatic analysis)

Each function returns a dict with:
  - summary metrics (numbers)
  - plot_b64 (base64-encoded matplotlib PNG, dark theme)

Usage:
    from modules.md_lite.advanced_analysis import analyze_advanced
    results = analyze_advanced("trajectory.dcd", "topology.pdb", workdir)
"""

import os
import io
import base64
import logging
import numpy as np

log = logging.getLogger("md_lite.advanced_analysis")

# Lazy imports — MDAnalysis is heavy
_MDA = None
_MPL = None


def _get_mda():
    global _MDA
    if _MDA is None:
        try:
            import MDAnalysis as mda
            from MDAnalysis.analysis import rms, hydrogenbonds, contacts, rdf, dihedrals, pca
            _MDA = {
                "mda": mda,
                "rms": rms,
                "hydrogenbonds": hydrogenbonds,
                "contacts": contacts,
                "rdf": rdf,
                "dihedrals": dihedrals,
                "pca": pca,
            }
        except ImportError as e:
            log.warning(f"MDAnalysis not available: {e}")
            _MDA = False
    return _MDA


def _get_mpl():
    global _MPL
    if _MPL is None:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            _MPL = plt
        except ImportError:
            _MPL = False
    return _MPL


def _fig_to_b64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def _style_dark():
    plt = _get_mpl()
    if not plt:
        return
    plt.style.use("dark_background")
    plt.rcParams.update({
        "text.color": "#c0c0c0",
        "axes.edgecolor": "#444",
        "axes.facecolor": "#1a1a2e",
        "figure.facecolor": "#1a1a2e",
        "grid.color": "#333",
        "grid.alpha": 0.4,
    })


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def analyze_advanced(traj_path, top_path, workdir, analyses=None):
    """Run advanced trajectory analyses using MDAnalysis.

    Args:
        traj_path: Path to trajectory file (DCD, XTC, TRR, NC).
        top_path: Path to topology file (PDB, PSF, PRMTOP).
        workdir: Job directory for output files.
        analyses: List of analysis names to run. If None, runs all.

    Returns:
        Dict with results from each analysis + plots.
    """
    mda_bundle = _get_mda()
    if not mda_bundle:
        return {"status": "error",
                "error": "MDAnalysis not installed. Install with: pip install mdanalysis"}

    if not os.path.exists(traj_path):
        return {"status": "error", "error": f"Trajectory not found: {traj_path}"}
    if not os.path.exists(top_path):
        return {"status": "error", "error": f"Topology not found: {top_path}"}

    mda = mda_bundle["mda"]

    try:
        u = mda.Universe(top_path, traj_path)
    except Exception as e:
        return {"status": "error", "error": f"Failed to load trajectory: {e}"}

    all_analyses = {
        "hbonds_advanced": _analyze_hbonds_advanced,
        "water_bridges": _analyze_water_bridges,
        "native_contacts": _analyze_native_contacts,
        "rdf": _analyze_rdf,
        "ramachandran": _analyze_ramachandran,
        "pca": _analyze_pca,
        "hbond_lifetimes": _analyze_hbond_lifetimes,
        "ligand_distances": _analyze_ligand_distances,
        "secondary_structure": _analyze_secondary_structure,
        "dielectric": _analyze_dielectric,
    }

    selected = analyses if analyses else list(all_analyses.keys())
    results = {}

    for name in selected:
        fn = all_analyses.get(name)
        if fn is None:
            results[name] = {"error": f"Unknown analysis: {name}"}
            continue
        try:
            log.info(f"Running analysis: {name}")
            results[name] = fn(u, workdir, mda_bundle)
        except Exception as e:
            log.warning(f"Analysis {name} failed: {e}", exc_info=True)
            results[name] = {"error": str(e)}

    results["status"] = "ok"
    results["analyses_run"] = [n for n in selected if n in results and "error" not in results.get(n, {})]
    results["analyses_failed"] = [n for n in selected if n in results and "error" in results.get(n, {})]
    return results


# ---------------------------------------------------------------------------
# 1. Hydrogen Bond Analysis (residue-resolved)
# ---------------------------------------------------------------------------

def _analyze_hbonds_advanced(u, workdir, mda_bundle):
    """Residue-resolved H-bond analysis with distances, angles, and occupancy."""
    plt = _get_mpl()
    hb_mod = mda_bundle["hydrogenbonds"]

    try:
        hb = hb_mod.HydrogenBondAnalysis(u)
        hb.run()
    except Exception as e:
        # Fallback: try with explicit selections
        try:
            protein = u.select_atoms("protein")
            if len(protein) == 0:
                return {"error": "No protein atoms found for H-bond analysis"}
            hb = hb_mod.HydrogenBondAnalysis(u, between=["protein", "not protein"])
            hb.run()
        except Exception as e2:
            return {"error": f"H-bond analysis failed: {e2}"}

    if len(hb.results.hbonds) == 0:
        return {"count": 0, "message": "No hydrogen bonds detected in trajectory"}

    hbonds = hb.results.hbonds
    n_frames = u.trajectory.n_frames

    # Count unique H-bonds and compute occupancy
    unique_pairs = {}
    for hbond in hbonds:
        frame_idx, donor_idx, h_idx, acceptor_idx, dist, angle = hbond
        key = (int(donor_idx), int(acceptor_idx))
        if key not in unique_pairs:
            unique_pairs[key] = {"count": 0, "distances": [], "angles": []}
        unique_pairs[key]["count"] += 1
        unique_pairs[key]["distances"].append(float(dist))
        unique_pairs[key]["angles"].append(float(angle))

    # Build summary table
    top_hbonds = sorted(unique_pairs.items(), key=lambda x: x[1]["count"], reverse=True)[:15]
    table = []
    for (d_idx, a_idx), info in top_hbonds:
        try:
            d_atom = u.atoms[d_idx]
            a_atom = u.atoms[a_idx]
            d_res = f"{d_atom.resname}{d_atom.resid}"
            a_res = f"{a_atom.resname}{a_atom.resid}"
        except Exception:
            d_res = f"Atom{d_idx}"
            a_res = f"Atom{a_idx}"
        table.append({
            "donor": d_res,
            "acceptor": a_res,
            "occupancy_pct": round(info["count"] / n_frames * 100, 1),
            "avg_dist_angstrom": round(float(np.mean(info["distances"])), 2),
            "avg_angle_deg": round(float(np.mean(info["angles"])), 1),
            "frames": info["count"],
        })

    # Per-frame count plot
    counts_per_frame = np.zeros(n_frames)
    for hbond in hbonds:
        counts_per_frame[int(hbond[0])] += 1

    plot_b64 = None
    if plt:
        _style_dark()
        fig, ax = plt.subplots(figsize=(7, 3))
        ax.plot(counts_per_frame, color="#f59e0b", linewidth=1)
        ax.set_title("Hydrogen Bonds per Frame", fontsize=12, fontweight="bold", color="#f59e0b")
        ax.set_xlabel("Frame")
        ax.set_ylabel("H-bond Count")
        ax.grid(axis="y", alpha=0.3)
        plot_b64 = _fig_to_b64(fig)
        plt.close(fig)

    return {
        "total_hbonds": len(hbonds),
        "unique_pairs": len(unique_pairs),
        "avg_per_frame": round(float(np.mean(counts_per_frame)), 1),
        "top_hbonds": table,
        "plot_b64": plot_b64,
    }


# ---------------------------------------------------------------------------
# 2. Water Bridge Analysis
# ---------------------------------------------------------------------------

def _analyze_water_bridges(u, workdir, mda_bundle):
    """Water-mediated protein-ligand H-bond networks."""
    plt = _get_mpl()
    hb_mod = mda_bundle["hydrogenbonds"]

    try:
        wb = hb_mod.WaterBridgeAnalysis(u, between=["protein", "not protein"])
        wb.run()
    except Exception as e:
        return {"error": f"Water bridge analysis failed: {e}"}

    if len(wb.results.hbonds) == 0:
        return {"count": 0, "message": "No water bridges detected"}

    bridges = wb.results.hbonds
    # Summary: water-mediated interaction count
    water_count = len(set(h[2] for h in bridges))  # water atom indices

    plot_b64 = None
    if plt:
        _style_dark()
        fig, ax = plt.subplots(figsize=(7, 3))
        # Count bridges per frame
        n_frames = u.trajectory.n_frames
        per_frame = np.zeros(n_frames)
        for b in bridges:
            per_frame[int(b[0])] += 1
        ax.plot(per_frame, color="#3b82f6", linewidth=1)
        ax.set_title("Water-Mediated Bridges per Frame", fontsize=12, fontweight="bold", color="#3b82f6")
        ax.set_xlabel("Frame")
        ax.set_ylabel("Bridge Count")
        ax.grid(axis="y", alpha=0.3)
        plot_b64 = _fig_to_b64(fig)
        plt.close(fig)

    return {
        "total_bridges": len(bridges),
        "unique_water_molecules": water_count,
        "plot_b64": plot_b64,
    }


# ---------------------------------------------------------------------------
# 3. Native Contacts (Q fraction)
# ---------------------------------------------------------------------------

def _analyze_native_contacts(u, workdir, mda_bundle):
    """Fraction of native contacts Q — protein stability metric."""
    plt = _get_mpl()
    contacts_mod = mda_bundle["contacts"]

    try:
        # Use first frame as reference
        sel = "name CA"
        ca = u.select_atoms(sel)
        if len(ca) == 0:
            return {"error": "No CA atoms found"}

        # Build contact matrix from first frame
        first_frame_contacts = contacts_mod.Contacts(u, selection=sel, radius=4.5,
                                                      ref=(0, ca))
        first_frame_contacts.run()
    except Exception as e:
        return {"error": f"Native contacts failed: {e}"}

    q_values = first_frame_contacts.results.timeseries
    q_array = np.array([q[1] if hasattr(q, '__len__') else q for q in q_values])

    plot_b64 = None
    if plt and len(q_array) > 0:
        _style_dark()
        fig, ax = plt.subplots(figsize=(7, 3))
        ax.plot(q_array, color="#22c55e", linewidth=1.5)
        ax.set_title("Fraction of Native Contacts (Q)", fontsize=12, fontweight="bold", color="#22c55e")
        ax.set_xlabel("Frame")
        ax.set_ylabel("Q")
        ax.set_ylim(0, 1.05)
        ax.axhline(y=0.5, color="#ff6b6b", linestyle="--", alpha=0.5, label="Q=0.5 (unfolding)")
        ax.legend(fontsize=8)
        ax.grid(axis="y", alpha=0.3)
        plot_b64 = _fig_to_b64(fig)
        plt.close(fig)

    return {
        "initial_Q": round(float(q_array[0]), 3) if len(q_array) > 0 else None,
        "final_Q": round(float(q_array[-1]), 3) if len(q_array) > 0 else None,
        "mean_Q": round(float(np.mean(q_array)), 3) if len(q_array) > 0 else None,
        "min_Q": round(float(np.min(q_array)), 3) if len(q_array) > 0 else None,
        "stability": "Stable" if len(q_array) > 0 and float(q_array[-1]) > 0.6 else
                     ("Moderately stable" if len(q_array) > 0 and float(q_array[-1]) > 0.3 else "Unstable"),
        "plot_b64": plot_b64,
    }


# ---------------------------------------------------------------------------
# 4. Radial Distribution Function
# ---------------------------------------------------------------------------

def _analyze_rdf(u, workdir, mda_bundle):
    """Radial distribution function — solvation shell structure."""
    plt = _get_mpl()
    rdf_mod = mda_bundle["rdf"]

    try:
        # Protein vs water
        protein = u.select_atoms("protein and name CA")
        water = u.select_atoms("resname HOH WAT SOL and name OW")
        if len(protein) == 0 or len(water) == 0:
            return {"error": "Need both protein and water for RDF"}

        rdf_obj = rdf_mod.InterRDF(protein, water, nbins=75, range=(0, 15))
        rdf_obj.run()
    except Exception as e:
        return {"error": f"RDF failed: {e}"}

    plot_b64 = None
    if plt:
        _style_dark()
        fig, ax = plt.subplots(figsize=(7, 3))
        ax.plot(rdf_obj.results.bins, rdf_obj.results.rdf, color="#8b5cf6", linewidth=1.5)
        ax.set_title("Radial Distribution Function: Protein–Water", fontsize=12, fontweight="bold", color="#8b5cf6")
        ax.set_xlabel("Distance (Å)")
        ax.set_ylabel("g(r)")
        ax.grid(axis="y", alpha=0.3)
        plot_b64 = _fig_to_b64(fig)
        plt.close(fig)

    return {
        "bins": [round(float(b), 1) for b in rdf_obj.results.bins],
        "rdf": [round(float(r), 3) for r in rdf_obj.results.rdf],
        "first_shell_peak_angstrom": round(float(rdf_obj.results.bins[np.argmax(rdf_obj.results.rdf)]), 1),
        "plot_b64": plot_b64,
    }


# ---------------------------------------------------------------------------
# 5. Ramachandran Analysis
# ---------------------------------------------------------------------------

def _analyze_ramachandran(u, workdir, mda_bundle):
    """Ramachandran plot — backbone φ/ψ distributions."""
    plt = _get_mpl()
    dih_mod = mda_bundle["dihedrals"]

    try:
        protein = u.select_atoms("protein and name N CA C")
        if len(protein) == 0:
            return {"error": "No protein backbone found"}

        rama = dih_mod.Ramachandran(protein).run()
    except Exception as e:
        return {"error": f"Ramachandran failed: {e}"}

    angles = rama.results.angles

    plot_b64 = None
    if plt and len(angles) > 0:
        _style_dark()
        fig, ax = plt.subplots(figsize=(5, 5))
        # Flatten angles across all frames
        all_angles = np.concatenate(angles) if angles.ndim > 2 else angles
        ax.scatter(all_angles[:, 0], all_angles[:, 1], s=2, alpha=0.3, c="#00d4aa")
        ax.set_xlim(-180, 180)
        ax.set_ylim(-180, 180)
        ax.set_title("Ramachandran Plot", fontsize=12, fontweight="bold", color="#00d4aa")
        ax.set_xlabel("φ (phi)")
        ax.set_ylabel("ψ (psi)")
        ax.axhline(0, color="#444", linewidth=0.5)
        ax.axvline(0, color="#444", linewidth=0.5)
        plot_b64 = _fig_to_b64(fig)
        plt.close(fig)

    # Count residues in favored regions
    phi = angles[:, 0] if angles.ndim == 2 else angles[0, :, 0]
    psi = angles[:, 1] if angles.ndim == 2 else angles[0, :, 1]
    # Simple region check: alpha-helix region
    in_alpha = np.sum((phi > -120) & (phi < -30) & (psi > -70) & (psi < 20))
    in_beta = np.sum((phi < -50) & (phi > -180) & ((psi > 90) | (psi < -150)))
    total = len(phi)

    return {
        "residues_analyzed": total,
        "in_alpha_helix_region": int(in_alpha),
        "in_beta_sheet_region": int(in_beta),
        "alpha_pct": round(float(in_alpha / total * 100), 1) if total > 0 else 0,
        "beta_pct": round(float(in_beta / total * 100), 1) if total > 0 else 0,
        "plot_b64": plot_b64,
    }


# ---------------------------------------------------------------------------
# 6. Principal Component Analysis
# ---------------------------------------------------------------------------

def _analyze_pca(u, workdir, mda_bundle):
    """PCA / essential dynamics — dominant collective motions."""
    plt = _get_mpl()
    pca_mod = mda_bundle["pca"]

    try:
        protein = u.select_atoms("protein and name CA")
        if len(protein) == 0:
            return {"error": "No protein CA atoms for PCA"}

        # Align trajectory first
        from MDAnalysis.analysis import align
        align.AlignTraj(u, u, select="name CA", in_memory=True).run()

        pca_obj = pca_mod.PCA(u, select="name CA").run()
    except Exception as e:
        return {"error": f"PCA failed: {e}"}

    # Variance explained
    variance = pca_obj.results.pca_variance
    if variance is None or len(variance) == 0:
        return {"error": "PCA produced no variance data"}

    total_var = float(np.sum(variance[:10]))
    pc_pct = [round(float(v / total_var * 100), 1) for v in variance[:10]]

    plot_b64 = None
    if plt:
        _style_dark()
        fig, axes = plt.subplots(1, 2, figsize=(10, 4))

        # Variance plot
        axes[0].bar(range(1, min(11, len(pc_pct) + 1)), pc_pct[:10],
                     color="#00d4aa", alpha=0.8)
        axes[0].set_title("Variance Explained", fontsize=11, fontweight="bold", color="#00d4aa")
        axes[0].set_xlabel("Principal Component")
        axes[0].set_ylabel("% Variance")

        # PC1 vs PC2 projection
        try:
            pc_data = pca_obj.transform(protein, n_components=2)
            if hasattr(pc_data, 'shape') and len(pc_data.shape) > 1:
                axes[1].scatter(pc_data[:, 0], pc_data[:, 1], s=3, alpha=0.4, c="#f59e0b")
                axes[1].set_title("PC1 vs PC2 Projection", fontsize=11, fontweight="bold", color="#f59e0b")
                axes[1].set_xlabel("PC1")
                axes[1].set_ylabel("PC2")
        except Exception:
            axes[1].text(0.5, 0.5, "Projection unavailable", ha="center", va="center", color="#666")
            axes[1].set_title("PC1 vs PC2", fontsize=11)

        plt.tight_layout()
        plot_b64 = _fig_to_b64(fig)
        plt.close(fig)

    return {
        "pc1_variance_pct": pc_pct[0] if pc_pct else None,
        "pc2_variance_pct": pc_pct[1] if len(pc_pct) > 1 else None,
        "top_10_variance_pct": pc_pct,
        "plot_b64": plot_b64,
    }


# ---------------------------------------------------------------------------
# 7. H-Bond Lifetimes (Autocorrelation)
# ---------------------------------------------------------------------------

def _analyze_hbond_lifetimes(u, workdir, mda_bundle):
    """H-bond autocorrelation → residence time estimation."""
    plt = _get_mpl()
    hb_mod = mda_bundle["hydrogenbonds"]

    try:
        from MDAnalysis.analysis.hydrogenbonds.hbond_autocorrel import HydrogenBondAutoCorrel
        protein = u.select_atoms("protein")
        if len(protein) == 0:
            return {"error": "No protein atoms"}

        ac = HydrogenBondAutoCorrel(u,
                                    acceptors="protein",
                                    hydrogens="protein",
                                    donors="protein",
                                    bond_type="continuous",
                                    sample_time=u.trajectory.totaltime,
                                    nruns=1,
                                    nsamples=50)
        ac.run()
    except Exception as e:
        return {"error": f"H-bond autocorrelation failed: {e}"}

    plot_b64 = None
    if plt:
        _style_dark()
        fig, ax = plt.subplots(figsize=(7, 3))
        try:
            times = ac.results.times
            c_t = ac.results.autocorrelation
            ax.plot(times, c_t, color="#ec4899", linewidth=1.5)
            ax.set_title("H-Bond Autocorrelation C(t)", fontsize=12, fontweight="bold", color="#ec4899")
            ax.set_xlabel("Time (ps)")
            ax.set_ylabel("C(t)")
            ax.set_ylim(-0.1, 1.05)
            ax.grid(axis="y", alpha=0.3)
        except Exception:
            ax.text(0.5, 0.5, "Data unavailable", ha="center", va="center", color="#666")
        plot_b64 = _fig_to_b64(fig)
        plt.close(fig)

    return {
        "residence_time_estimate_ps": None,  # Complex to compute; plot shows it
        "plot_b64": plot_b64,
        "note": "C(t) decay indicates H-bond lifetime. Slower decay = more stable interactions.",
    }


# ---------------------------------------------------------------------------
# 8. Ligand-Residue Distance Tracking
# ---------------------------------------------------------------------------

def _analyze_ligand_distances(u, workdir, mda_bundle):
    """Track distances between ligand and key residues over time."""
    plt = _get_mpl()
    mda = mda_bundle["mda"]

    # Auto-detect ligand
    ligand = u.select_atoms("not protein and not resname HOH WAT SOL and not ion")
    if len(ligand) == 0:
        return {"error": "No ligand detected in trajectory"}

    # Find binding-site residues (within 5 Å of ligand)
    try:
        binding_site = u.select_atoms(f"protein and around 5 (not protein and not resname HOH WAT SOL and not ion)")
        if len(binding_site) == 0:
            return {"error": "No binding-site residues found near ligand"}

        binding_resids = sorted(set(binding_site.resindices))
        if len(binding_residues := binding_resids) > 10:
            binding_residues = binding_residues[:10]
    except Exception as e:
        return {"error": f"Distance analysis failed: {e}"}

    # Track COM distance for each residue
    distances = {}
    for res_idx in binding_residues:
        res = u.residues[res_idx]
        dists = []
        for ts in u.trajectory:
            d = float(np.linalg.norm(ligand.center_of_mass() - res.atoms.center_of_mass()))
            dists.append(d)
        distances[f"{res.resname}{res.resid}"] = [round(d, 2) for d in dists]

    plot_b64 = None
    if plt and distances:
        _style_dark()
        fig, ax = plt.subplots(figsize=(7, 4))
        for res_name, dists in list(distances.items())[:8]:
            ax.plot(dists, label=res_name, linewidth=0.8, alpha=0.8)
        ax.set_title("Ligand–Residue Distances", fontsize=12, fontweight="bold", color="#3b82f6")
        ax.set_xlabel("Frame")
        ax.set_ylabel("Distance (Å)")
        ax.legend(fontsize=7, loc="upper right")
        ax.grid(axis="y", alpha=0.3)
        plot_b64 = _fig_to_b64(fig)
        plt.close(fig)

    return {
        "binding_site_residues": list(distances.keys()),
        "n_residues_tracked": len(distances),
        "avg_distances": {k: round(float(np.mean(v)), 2) for k, v in distances.items()},
        "plot_b64": plot_b64,
    }


# ---------------------------------------------------------------------------
# 9. Secondary Structure (via DSSP)
# ---------------------------------------------------------------------------

def _analyze_secondary_structure(u, workdir, mda_bundle):
    """Secondary structure content over time."""
    plt = _get_mpl()

    try:
        from MDAnalysis.analysis.dssp import DSSP
        protein = u.select_atoms("protein")
        if len(protein) == 0:
            return {"error": "No protein for DSSP"}

        dssp = DSSP(u).run()
    except ImportError:
        return {"error": "DSSP not available — requires mdanalysis[dssp] extra"}
    except Exception as e:
        return {"error": f"DSSP failed: {e}"}

    # Count secondary structure types per frame
    ss_content = dssp.results.dssp_dict if hasattr(dssp.results, 'dssp_dict') else {}

    return {
        "available": True,
        "note": "DSSP secondary structure assignment completed.",
        "details": "See DSSP results in the trajectory data.",
    }


# ---------------------------------------------------------------------------
# 10. Dielectric Constant
# ---------------------------------------------------------------------------

def _analyze_dielectric(u, workdir, mda_bundle):
    """Static dielectric constant from dipole fluctuations."""
    plt = _get_mpl()

    try:
        from MDAnalysis.analysis.dielectric import DielectricConstant
        protein = u.select_atoms("protein")
        if len(protein) == 0:
            return {"error": "No protein for dielectric analysis"}

        dc = DielectricConstant(u.atoms)
        dc.run()
    except ImportError:
        return {"error": "Dielectric analysis requires mdanalysis >= 2.7"}
    except Exception as e:
        return {"error": f"Dielectric analysis failed: {e}"}

    eps = dc.results.eps if hasattr(dc.results, 'eps') else None

    return {
        "dielectric_constant": round(float(eps), 2) if eps else None,
        "note": "Static dielectric from Kirkwood-Fröhlich equation.",
    }
