"""MD Analysis — RMSD, RMSF, Energy plots via MDTraj + matplotlib."""
import os, io, base64, logging
import numpy as np

log = logging.getLogger("md_lite_analysis")

try:
    import mdtraj as md
    HAS_MDTRAJ = True
except ImportError:
    HAS_MDTRAJ = False

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


def _fig_to_b64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def _style_dark():
    plt.style.use("dark_background")
    plt.rcParams["text.color"] = "#c0c0c0"
    plt.rcParams["axes.edgecolor"] = "#444"
    plt.rcParams["axes.facecolor"] = "#1a1a2e"
    plt.rcParams["figure.facecolor"] = "#1a1a2e"
    plt.rcParams["grid.color"] = "#333"
    plt.rcParams["grid.alpha"] = 0.4


def analyze(traj_path, top_path, workdir):
    if not os.path.exists(traj_path):
        return {"error": "Trajectory not found"}
    if not HAS_MDTRAJ or not HAS_MPL:
        return {"status": "ok", "error": "mdtraj or matplotlib not installed", "rmsd": {}, "rmsf": {}, "energy": {}}

    traj = md.load(traj_path, top=top_path) if os.path.exists(top_path) else md.load(traj_path)
    results = {}

    # RMSD
    try:
        rmsd = md.rmsd(traj, traj, 0)
        results["rmsd"] = {"mean_nm": round(float(np.mean(rmsd)), 4), "final_nm": round(float(rmsd[-1]), 4)}
        _style_dark()
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.plot(rmsd, color="#00d4aa", linewidth=1)
        ax.set_title("RMSD", fontsize=12, fontweight="bold", color="#00d4aa")
        ax.set_xlabel("Frame"); ax.set_ylabel("RMSD (nm)")
        ax.grid(axis="y", alpha=0.3)
        results["rmsd_plot"] = _fig_to_b64(fig); plt.close(fig)
    except Exception as e:
        results["rmsd"] = {"error": str(e)}

    # RMSF
    try:
        rmsf = md.rmsf(traj, traj, 0)
        results["rmsf"] = {"mean_nm": round(float(np.mean(rmsf)), 4), "max_nm": round(float(np.max(rmsf)), 4)}
        _style_dark()
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.plot(rmsf, color="#6366f1", linewidth=1)
        ax.set_title("RMSF", fontsize=12, fontweight="bold", color="#6366f1")
        ax.set_xlabel("Residue"); ax.set_ylabel("RMSF (nm)")
        ax.grid(axis="y", alpha=0.3)
        results["rmsf_plot"] = _fig_to_b64(fig); plt.close(fig)
    except Exception as e:
        results["rmsf"] = {"error": str(e)}

    # Energy from log
    log_path = os.path.join(workdir, "md.log")
    if os.path.exists(log_path):
        try:
            energies = []
            with open(log_path) as f:
                next(f)  # skip header
                for line in f:
                    if not line.strip() or line.startswith("#"): continue
                    parts = line.split(",")
                    if len(parts) > 1:
                        try: energies.append(float(parts[1]))
                        except: pass
            if energies:
                results["energy"] = {"min": round(min(energies), 1), "max": round(max(energies), 1),
                                      "mean": round(float(np.mean(energies)), 1)}
                _style_dark()
                fig, ax = plt.subplots(figsize=(6, 3))
                ax.plot(energies, color="#f59e0b", linewidth=1)
                ax.set_title("Potential Energy", fontsize=12, fontweight="bold", color="#f59e0b")
                ax.set_xlabel("Frame"); ax.set_ylabel("kJ/mol")
                ax.grid(axis="y", alpha=0.3)
                results["energy_plot"] = _fig_to_b64(fig); plt.close(fig)
        except Exception as e:
            results["energy"] = {"error": str(e)}

    # Gyration Radius
    try:
        rg = md.compute_rg(traj)
        results["gyration"] = {"mean_nm": round(float(np.mean(rg)), 4), "final_nm": round(float(rg[-1]), 4)}
        _style_dark()
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.plot(rg, color="#8b5cf6", linewidth=1)
        ax.set_title("Radius of Gyration", fontsize=12, fontweight="bold", color="#8b5cf6")
        ax.set_xlabel("Frame"); ax.set_ylabel("Rg (nm)")
        ax.grid(axis="y", alpha=0.3)
        results["gyration_plot"] = _fig_to_b64(fig); plt.close(fig)
    except Exception as e:
        results["gyration"] = {"error": str(e)}

    # SASA
    try:
        sasa = md.shrake_rupley(traj)
        results["sasa"] = {"mean_nm2": round(float(np.mean(sasa)), 2), "final_nm2": round(float(sasa[-1]), 2)}
        _style_dark()
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.plot(sasa, color="#22c55e", linewidth=1)
        ax.set_title("Solvent Accessible Surface Area", fontsize=12, fontweight="bold", color="#22c55e")
        ax.set_xlabel("Frame"); ax.set_ylabel("SASA (nm²)")
        ax.grid(axis="y", alpha=0.3)
        results["sasa_plot"] = _fig_to_b64(fig); plt.close(fig)
    except Exception as e:
        results["sasa"] = {"error": str(e)}

    # H-Bonds
    try:
        hb = md.baker_hubbard(traj, periodic=False)
        hb_count = len(hb)
        hb_labels = [f"D{hb[i][0]}-A{hb[i][2]}" for i in range(min(hb_count, 10))]
        results["hbonds"] = {"count": hb_count, "top_donor_acceptor": hb_labels}
        _style_dark()
        fig, ax = plt.subplots(figsize=(6, 3))
        # Compute per-frame H-bond count
        hb_per_frame = []
        for i in range(traj.n_frames):
            f = traj[i]
            hbf = md.baker_hubbard(f, periodic=False)
            hb_per_frame.append(len(hbf))
        ax.plot(hb_per_frame, color="#f59e0b", linewidth=1)
        ax.set_title("Hydrogen Bonds per Frame", fontsize=12, fontweight="bold", color="#f59e0b")
        ax.set_xlabel("Frame"); ax.set_ylabel("Count")
        ax.grid(axis="y", alpha=0.3)
        results["hbonds_plot"] = _fig_to_b64(fig); plt.close(fig)
        results["hbonds"]["avg_per_frame"] = round(float(np.mean(hb_per_frame)), 1)
    except Exception as e:
        results["hbonds"] = {"error": str(e)}

    results["status"] = "ok"
    return results
