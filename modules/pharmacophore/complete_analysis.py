"""
Complete Pharmacophore Analysis - generates all 8 publication-grade outputs.

Inspired by Omixium's pharmacophore modeling pipeline (Pritam Panda).
Produces: 2D plot, 3D HTML, distance CSV, distance heatmap, distribution plot,
feature CSV, fingerprint summary CSV, properties CSV.

All outputs returned as base64 PNG/HTML or CSV strings for API consumption.
"""
import os
import io
import base64
import logging
import numpy as np

log = logging.getLogger("pharmacophore.complete")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    from rdkit import Chem
    from rdkit.Chem import AllChem, Descriptors, rdMolDescriptors, rdDepictor
    from rdkit.Chem import ChemicalFeatures
    from rdkit.Chem.Draw import rdMolDraw2D
    from rdkit import RDConfig
    from rdkit.Chem.Pharm2D import Gobbi_Pharm2D, Generate
    HAS_RDKIT = True
except ImportError:
    HAS_RDKIT = False

FEATURE_COLORS = {
    "Donor": "#2ECC40", "Acceptor": "#FF4136", "Aromatic": "#FFDC00",
    "Hydrophobe": "#01C9E1", "Hydrophobic": "#01C9E1",
    "PosIonizable": "#0074D9", "NegIonizable": "#B10DC9",
    "LumpedHydrophobe": "#FF851B", "Cation": "#0074D9", "Anion": "#B10DC9",
    "HBond_donor": "#2ECC40", "HBond_acceptor": "#FF4136", "Halogen": "#00CED1",
}
FEATURE_SYMBOLS = {
    "Donor": "D", "Acceptor": "A", "Aromatic": "R", "Hydrophobe": "H",
    "Hydrophobic": "H", "PosIonizable": "+", "NegIonizable": "-",
    "LumpedHydrophobe": "L", "Cation": "+", "Anion": "-",
    "HBond_donor": "D", "HBond_acceptor": "A", "Halogen": "X",
}


def _fig_to_b64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def complete_pharmacophore_analysis(smiles, name="Molecule"):
    """Run complete pharmacophore analysis - returns all 8 outputs as dict."""
    if not HAS_RDKIT:
        return {"error": "RDKit not available"}
    if not HAS_MPL:
        return {"error": "matplotlib not available"}

    from rdkit import RDLogger
    RDLogger.DisableLog("rdApp.*")

    result = {"smiles": smiles, "name": name}

    # Load molecule
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"error": "Invalid SMILES: " + smiles}
    mol = Chem.AddHs(mol)
    AllChem.EmbedMolecule(mol, randomSeed=42)
    AllChem.MMFFOptimizeMolecule(mol)
    mol.SetProp("_Name", name)

    # Extract features
    fdef = os.path.join(RDConfig.RDDataDir, "BaseFeatures.fdef")
    factory = ChemicalFeatures.BuildFeatureFactory(fdef)
    raw_features = factory.GetFeaturesForMol(mol)

    features = []
    feature_summary = {}
    for feat in raw_features:
        ftype = feat.GetFamily()
        atom_ids = list(feat.GetAtomIds())
        pos = feat.GetPos()
        features.append({
            "type": ftype, "family": ftype, "atom_ids": atom_ids,
            "position": {"x": round(pos.x, 3), "y": round(pos.y, 3), "z": round(pos.z, 3)},
            "color": FEATURE_COLORS.get(ftype, "#888888"),
            "symbol": FEATURE_SYMBOLS.get(ftype, "X"),
        })
        feature_summary[ftype] = feature_summary.get(ftype, 0) + 1

    result["feature_summary"] = feature_summary
    result["num_features"] = len(features)

    # Calculate distances
    conf = mol.GetConformer()
    feature_coords = []
    feature_labels = []
    for i, f in enumerate(features):
        coords = []
        for aid in f["atom_ids"]:
            p = conf.GetAtomPosition(aid)
            coords.append([p.x, p.y, p.z])
        centroid = np.mean(coords, axis=0)
        feature_coords.append(centroid)
        label = f["symbol"] + str(i + 1)
        feature_labels.append(label)
        f["label"] = label

    nfeat = len(feature_coords)
    dist_matrix = np.zeros((nfeat, nfeat))
    for i in range(nfeat):
        for j in range(i + 1, nfeat):
            d = float(np.linalg.norm(feature_coords[i] - feature_coords[j]))
            dist_matrix[i, j] = d
            dist_matrix[j, i] = d

    # Generate fingerprint
    fp_info = {}
    try:
        sig_factory = Gobbi_Pharm2D.factory
        fp = Generate.Gen2DFingerprint(mol, sig_factory)
        on_bits = list(fp.GetOnBits())
        fp_info = {
            "size": fp.GetNumBits(), "active_bits": len(on_bits),
            "density": round(len(on_bits) / fp.GetNumBits(), 4),
            "first_100_bits": on_bits[:100],
        }
    except Exception as e:
        log.warning("Fingerprint failed: %s", e)

    # OUTPUT 1: Features CSV
    csv_lines = ["Feature_ID,Feature_Type,Symbol,X,Y,Z,Atom_Indices,Num_Atoms"]
    for f in features:
        p = f["position"]
        csv_lines.append('{},{},{},"{}",{},{},"{}",{}'.format(
            f["label"], f["type"], f["symbol"],
            p["x"], p["y"], p["z"],
            str(f["atom_ids"]), len(f["atom_ids"])
        ))
    result["features_csv"] = "\n".join(csv_lines)

    # OUTPUT 2: Distances CSV
    if HAS_PANDAS:
        df_dist = pd.DataFrame(dist_matrix, index=feature_labels, columns=feature_labels)
        result["distances_csv"] = df_dist.to_csv()
    else:
        clines = ["," + ",".join(feature_labels)]
        for i, lbl in enumerate(feature_labels):
            row = [lbl] + ["{:.2f}".format(dist_matrix[i, j]) for j in range(nfeat)]
            clines.append(",".join(row))
        result["distances_csv"] = "\n".join(clines)

    # OUTPUT 3: Fingerprint Summary CSV
    fp_csv = "Metric,Value\n"
    fp_csv += "Fingerprint_Size,{}\n".format(fp_info.get("size", "N/A"))
    fp_csv += "Active_Bits,{}\n".format(fp_info.get("active_bits", "N/A"))
    fp_csv += "Bit_Density,{}\n".format(fp_info.get("density", "N/A"))
    fp_csv += 'First_100_Bit_Positions,"{}"\n'.format(str(fp_info.get("first_100_bits", [])))
    result["fingerprint_summary_csv"] = fp_csv

    # OUTPUT 4: Properties CSV
    props = [
        ("Molecular_Formula", rdMolDescriptors.CalcMolFormula(mol)),
        ("Molecular_Weight", round(Descriptors.MolWt(mol), 2)),
        ("Num_Atoms", mol.GetNumAtoms()),
        ("Num_Bonds", mol.GetNumBonds()),
        ("Num_Heavy_Atoms", Descriptors.HeavyAtomCount(mol)),
        ("Num_Rotatable_Bonds", Descriptors.NumRotatableBonds(mol)),
        ("Num_HBD", Descriptors.NumHDonors(mol)),
        ("Num_HBA", Descriptors.NumHAcceptors(mol)),
        ("TPSA", round(Descriptors.TPSA(mol), 2)),
        ("LogP", round(Descriptors.MolLogP(mol), 2)),
        ("Num_Aromatic_Rings", Descriptors.NumAromaticRings(mol)),
        ("Num_Pharmacophore_Features", len(features)),
    ]
    result["properties_csv"] = "Property,Value\n" + "\n".join("{},{}".format(k, v) for k, v in props)
    result["molecular_properties"] = dict(props)

    # OUTPUT 5: 2D Pharmacophore Plot
    try:
        rdDepictor.Compute2DCoords(mol)
        highlight_atoms = []
        highlight_colors = {}
        for f in features:
            rgb = tuple(int(f["color"][i:i+2], 16) / 255.0 for i in (1, 3, 5))
            for aid in f["atom_ids"]:
                highlight_atoms.append(aid)
                highlight_colors[aid] = rgb
        drawer = rdMolDraw2D.MolDraw2DCairo(800, 600)
        drawer.drawOptions().addAtomIndices = True
        drawer.DrawMolecule(mol, highlightAtoms=highlight_atoms, highlightAtomColors=highlight_colors)
        drawer.FinishDrawing()
        img_data = drawer.GetDrawingText()
        fig, ax = plt.subplots(figsize=(10, 8))
        img = plt.imread(io.BytesIO(img_data), format="png")
        ax.imshow(img)
        ax.axis("off")
        ax.set_title("2D Pharmacophore \u2014 " + name, fontsize=14, fontweight="bold")
        legend_patches = []
        for ftype, cnt in feature_summary.items():
            color = FEATURE_COLORS.get(ftype, "#888888")
            legend_patches.append(mpatches.Patch(color=color, label="{} ({})".format(ftype, cnt)))
        ax.legend(handles=legend_patches, loc="lower right", fontsize=8, framealpha=0.9)
        result["plot_2d_b64"] = _fig_to_b64(fig)
        plt.close(fig)
    except Exception as e:
        log.warning("2D plot failed: %s", e)
        result["plot_2d_b64"] = None

    # OUTPUT 6: 3D Pharmacophore HTML
    try:
        import plotly.graph_objects as go
        fig3d = go.Figure()
        for bond in mol.GetBonds():
            bi, ei = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
            bp = conf.GetAtomPosition(bi)
            ep = conf.GetAtomPosition(ei)
            fig3d.add_trace(go.Scatter3d(
                x=[bp.x, ep.x], y=[bp.y, ep.y], z=[bp.z, ep.z],
                mode="lines", line=dict(color="gray", width=2), showlegend=False, hoverinfo="skip"))
        ax_, ay_, az_, ac_, al_ = [], [], [], [], []
        for i in range(mol.GetNumAtoms()):
            p = conf.GetAtomPosition(i)
            ax_.append(p.x); ay_.append(p.y); az_.append(p.z)
            el = mol.GetAtomWithIdx(i).GetSymbol()
            al_.append(el + str(i))
            ac_.append({"C": "black", "N": "blue", "O": "red", "S": "yellow"}.get(el, "gray"))
        fig3d.add_trace(go.Scatter3d(
            x=ax_, y=ay_, z=az_, mode="markers+text",
            marker=dict(size=8, color=ac_, opacity=0.9),
            text=al_, textposition="top center", textfont=dict(size=8),
            showlegend=False, name="Atoms"))
        for ftype in feature_summary:
            fx, fy, fz = [], [], []
            for f in features:
                if f["type"] == ftype:
                    fx.append(f["position"]["x"]); fy.append(f["position"]["y"]); fz.append(f["position"]["z"])
            fig3d.add_trace(go.Scatter3d(
                x=fx, y=fy, z=fz, mode="markers+text",
                marker=dict(size=20, color=FEATURE_COLORS.get(ftype, "#888"), opacity=0.4,
                            line=dict(color=FEATURE_COLORS.get(ftype, "#888"), width=2)),
                text=[FEATURE_SYMBOLS.get(ftype, "X") + str(i+1) for i in range(len(fx))],
                textposition="top center", name=ftype))
        fig3d.update_layout(
            title="3D Pharmacophore \u2014 " + name,
            scene=dict(xaxis_title="X (\u00c5)", yaxis_title="Y (\u00c5)", zaxis_title="Z (\u00c5)", aspectmode="data"),
            width=1000, height=700, showlegend=True,
            legend=dict(bgcolor="rgba(255,255,255,0.8)"))
        result["plot_3d_html"] = fig3d.to_html(include_plotlyjs="cdn", full_html=False)
    except Exception as e:
        log.warning("3D plot failed: %s", e)
        result["plot_3d_html"] = None

    # OUTPUT 7: Distance Heatmap
    try:
        fig_hm, ax_hm = plt.subplots(figsize=(8, 6))
        im = ax_hm.imshow(dist_matrix, cmap="YlOrRd", aspect="auto")
        ax_hm.set_xticks(range(nfeat)); ax_hm.set_yticks(range(nfeat))
        ax_hm.set_xticklabels(feature_labels, fontsize=8, rotation=45)
        ax_hm.set_yticklabels(feature_labels, fontsize=8)
        for i in range(nfeat):
            for j in range(nfeat):
                ax_hm.text(j, i, "{:.1f}".format(dist_matrix[i, j]), ha="center", va="center", fontsize=7)
        fig_hm.colorbar(im, label="Distance (\u00c5)")
        ax_hm.set_title("Pharmacophore Distance Matrix \u2014 " + name, fontsize=12, fontweight="bold")
        result["distance_heatmap_b64"] = _fig_to_b64(fig_hm)
        plt.close(fig_hm)
    except Exception as e:
        log.warning("Heatmap failed: %s", e)
        result["distance_heatmap_b64"] = None

    # OUTPUT 8: Feature Distribution
    try:
        fig_d, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        types = list(feature_summary.keys())
        counts = list(feature_summary.values())
        colors = [FEATURE_COLORS.get(t, "#888") for t in types]
        bars = ax1.bar(types, counts, color=colors, edgecolor="black", linewidth=1.5)
        for bar in bars:
            ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                     str(int(bar.get_height())), ha="center", va="bottom", fontweight="bold", fontsize=9)
        ax1.set_xlabel("Feature Type"); ax1.set_ylabel("Count")
        ax1.set_title("Feature Distribution", fontweight="bold"); ax1.grid(axis="y", alpha=0.3)
        ax2.pie(counts, labels=types, colors=colors, autopct="%1.1f%%", startangle=90,
                wedgeprops=dict(edgecolor="black", linewidth=1.5))
        ax2.set_title("Feature Proportions", fontweight="bold")
        fig_d.suptitle("Pharmacophore Analysis \u2014 " + name, fontsize=14, fontweight="bold")
        plt.tight_layout()
        result["distribution_b64"] = _fig_to_b64(fig_d)
        plt.close(fig_d)
    except Exception as e:
        log.warning("Distribution failed: %s", e)
        result["distribution_b64"] = None

    result["success"] = True
    return result
