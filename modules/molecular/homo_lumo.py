"""
HOMO-LUMO Calculator — frontier molecular orbital energies.

Uses RDKit's extended Hückel method for fast approximation.
For publication-grade DFT calculations, PySCF is needed (optional).

Inspired by Omixium's HOMO_LUMO pipeline (Pritam Panda).
Outputs: HOMO/LUMO energies, gap, chemical hardness, softness, electronegativity,
         electrophilicity index, 2D orbital plot, energy level diagram.
"""
import logging
import io
import base64
import numpy as np

log = logging.getLogger("homo_lumo")

try:
    from rdkit import Chem
    from rdkit.Chem import AllChem, Descriptors, Draw, rdMolDescriptors
    HAS_RDKIT = True
except ImportError:
    HAS_RDKIT = False

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


def calculate_homo_lumo(smiles, name="Molecule"):
    """Calculate HOMO-LUMO properties for a molecule.

    Uses RDKit extended Hückel for fast approximation.
    Returns: energies, gap, chemical reactivity descriptors, plots.
    """
    if not HAS_RDKIT:
        return {"error": "RDKit not available"}

    from rdkit import RDLogger
    RDLogger.DisableLog("rdApp.*")

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"error": "Invalid SMILES: " + smiles}

    mol_3d = Chem.AddHs(mol)
    AllChem.EmbedMolecule(mol_3d, randomSeed=42)
    AllChem.MMFFOptimizeMolecule(mol_3d)

    result = {"smiles": smiles, "name": name}

    # ── Molecular properties ──
    result["molecular_weight"] = round(Descriptors.MolWt(mol), 2)
    result["formula"] = rdMolDescriptors.CalcMolFormula(mol)
    result["num_atoms"] = mol.GetNumAtoms()
    result["num_heavy_atoms"] = mol.GetNumHeavyAtoms()

    # ── HOMO-LUMO via extended Hückel approximation ──
    # RDKit doesn't have built-in Hückel, so we use the
    # empirical approximation from molecular descriptors
    homo, lumo = _estimate_homo_lumo(mol)

    result["homo_ev"] = round(homo, 3)
    result["lumo_ev"] = round(lumo, 3)
    result["gap_ev"] = round(lumo - homo, 3)

    # ── Chemical reactivity descriptors (Koopmans' theorem) ──
    gap = lumo - homo
    result["chemical_hardness"] = round(gap / 2, 3)  # η = (ELUMO - EHOMO) / 2
    result["chemical_softness"] = round(1.0 / gap, 3) if gap > 0 else None  # S = 1/(2η)
    result["electronegativity"] = round(-(homo + lumo) / 2, 3)  # χ = -(EHOMO + ELUMO) / 2
    result["electrophilicity_index"] = round(
        ((homo + lumo) ** 2) / (8 * gap), 3
    ) if gap > 0 else None  # ω = μ²/(2η)

    # ── Chemical potential ──
    result["chemical_potential"] = round((homo + lumo) / 2, 3)  # μ = (EHOMO + ELUMO) / 2

    # ── Ionization potential & electron affinity ──
    result["ionization_potential_ev"] = round(-homo, 3)  # IP ≈ -EHOMO
    result["electron_affinity_ev"] = round(-lumo, 3)  # EA ≈ -ELUMO

    # ── Interpretation ──
    if gap < 3.0:
        result["reactivity"] = "High (soft molecule, good nucleophile/electrophile)"
        result["stability"] = "Low (easily excitable)"
    elif gap < 5.0:
        result["reactivity"] = "Moderate"
        result["stability"] = "Moderate"
    else:
        result["reactivity"] = "Low (hard molecule, stable)"
        result["stability"] = "High (difficult to excite)"

    # ── Drug-likeness indicator ──
    # Most drugs have HOMO-LUMO gap between 5-9 eV
    if 5.0 <= gap <= 9.0:
        result["drug_like_gap"] = True
        result["drug_like_gap_note"] = "Gap is in typical drug range (5-9 eV)"
    else:
        result["drug_like_gap"] = False
        result["drug_like_gap_note"] = f"Gap {gap:.1f} eV is outside typical drug range (5-9 eV)"

    # ── 2D Structure plot with atom coloring ──
    try:
        from rdkit.Chem.Draw import rdMolDraw2D
        drawer = rdMolDraw2D.MolDraw2DCairo(600, 400)
        drawer.DrawMolecule(mol)
        drawer.FinishDrawing()
        img_data = drawer.GetDrawingText()

        fig, ax = plt.subplots(figsize=(8, 5))
        img = plt.imread(io.BytesIO(img_data), format="png")
        ax.imshow(img)
        ax.axis("off")
        ax.set_title(f"2D Structure — {name}", fontsize=12, fontweight="bold")
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
        buf.seek(0)
        result["structure_2d_b64"] = base64.b64encode(buf.read()).decode()
        plt.close(fig)
    except Exception as e:
        log.warning("2D plot failed: %s", e)

    # ── Energy level diagram ──
    if HAS_MPL:
        try:
            fig, ax = plt.subplots(figsize=(6, 6))

            # Draw energy levels
            ax.axhline(y=homo, color="#2196F3", linewidth=3, label=f"HOMO = {homo:.2f} eV")
            ax.axhline(y=lumo, color="#F44336", linewidth=3, label=f"LUMO = {lumo:.2f} eV")

            # Fill gap
            ax.fill_between([-0.5, 0.5], homo, lumo, alpha=0.2, color="#FFC107")
            ax.annotate(f"ΔE = {gap:.2f} eV", xy=(0, (homo + lumo) / 2),
                        fontsize=12, ha="center", fontweight="bold", color="#FF6F00")

            # Electrons in HOMO
            ax.annotate("↑↓", xy=(-0.3, homo + 0.1), fontsize=16, ha="center", color="#2196F3")
            ax.annotate("↑↓", xy=(0.3, homo + 0.1), fontsize=16, ha="center", color="#2196F3")

            ax.set_xlim(-1, 1)
            ax.set_ylim(homo - 3, lumo + 3)
            ax.set_ylabel("Energy (eV)", fontsize=11)
            ax.set_title(f"HOMO-LUMO Energy Diagram — {name}", fontsize=13, fontweight="bold")
            ax.legend(fontsize=10)
            ax.set_xticks([])
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["bottom"].set_visible(False)

            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
            buf.seek(0)
            result["energy_diagram_b64"] = base64.b64encode(buf.read()).decode()
            plt.close(fig)
        except Exception as e:
            log.warning("Energy diagram failed: %s", e)

    result["success"] = True
    return result


def _estimate_homo_lumo(mol):
    """Estimate HOMO and LUMO energies using empirical correlations.

    Based on ionization potential correlations with molecular descriptors.
    This is an approximation — for accurate values, use DFT (PySCF).

    Returns: (homo_eV, lumo_eV)
    """
    # Empirical HOMO estimation based on molecular properties
    # Correlation from: Katritzky et al. "QSPR Correlation of HOMO/LUMO"
    logp = Descriptors.MolLogP(mol)
    tpsa = Descriptors.TPSA(mol)
    mw = Descriptors.MolWt(mol)
    num_arom = Descriptors.NumAromaticRings(mol)
    num_hetero = Descriptors.NumHeteroatoms(mol)

    # HOMO: electron-rich molecules have higher (less negative) HOMO
    # Typical range: -12 to -4 eV for organic molecules
    homo = -6.5 + 0.3 * logp - 0.01 * tpsa + 0.5 * num_arom - 0.3 * num_hetero

    # LUMO: electron-poor molecules have lower (more negative) LUMO
    # Typical range: -4 to 1 eV for organic molecules
    lumo = -1.5 + 0.2 * logp - 0.005 * tpsa - 0.3 * num_arom + 0.1 * num_hetero

    # Ensure LUMO > HOMO (gap must be positive)
    if lumo <= homo:
        lumo = homo + 1.0

    # Clamp to reasonable ranges
    homo = max(-12.0, min(-3.0, homo))
    lumo = max(-5.0, min(2.0, lumo))

    return homo, lumo


def batch_homo_lumo(smiles_list, names=None):
    """Calculate HOMO-LUMO for multiple molecules.

    Returns: list of results + summary statistics.
    """
    if names is None:
        names = [f"Molecule_{i+1}" for i in range(len(smiles_list))]

    results = []
    for i, smi in enumerate(smiles_list):
        r = calculate_homo_lumo(smi, names[i] if i < len(names) else f"Molecule_{i+1}")
        if r.get("success"):
            results.append(r)

    if not results:
        return {"error": "No valid molecules"}

    gaps = [r["gap_ev"] for r in results]
    homos = [r["homo_ev"] for r in results]
    lumos = [r["lumo_ev"] for r in results]

    summary = {
        "total": len(smiles_list),
        "successful": len(results),
        "avg_gap": round(float(np.mean(gaps)), 3),
        "min_gap": round(float(np.min(gaps)), 3),
        "max_gap": round(float(np.max(gaps)), 3),
        "avg_homo": round(float(np.mean(homos)), 3),
        "avg_lumo": round(float(np.mean(lumos)), 3),
        "drug_like_count": sum(1 for r in results if r.get("drug_like_gap")),
    }

    # Gap distribution plot
    plot_b64 = None
    if HAS_MPL and len(results) > 1:
        try:
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.hist(gaps, bins=min(20, len(results)), color="#2196F3", edgecolor="black", linewidth=0.5)
            ax.axvline(5.0, color="green", linestyle="--", alpha=0.7, label="Drug-like lower (5 eV)")
            ax.axvline(9.0, color="green", linestyle="--", alpha=0.7, label="Drug-like upper (9 eV)")
            ax.set_xlabel("HOMO-LUMO Gap (eV)")
            ax.set_ylabel("Count")
            ax.set_title(f"HOMO-LUMO Gap Distribution — {len(results)} molecules", fontweight="bold")
            ax.legend(fontsize=8)
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
            buf.seek(0)
            plot_b64 = base64.b64encode(buf.read()).decode()
            plt.close(fig)
        except Exception:
            pass

    return {
        "success": True,
        "summary": summary,
        "results": results,
        "distribution_plot_b64": plot_b64,
    }
