"""
Interactive Molecular Property Plots — Plotly dashboards.

Inspired by Omixium's interactive_mol_plots.py (Pritam Panda).
Generates: chemical space (PCA/t-SNE), property distributions, correlation heatmap,
drug-likeness radar chart, Lipinski analysis.

All returned as plotly HTML strings for embedding in the frontend.
"""
import logging
import numpy as np

log = logging.getLogger("molecular_plots")

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, Crippen, rdMolDescriptors
    HAS_RDKIT = True
except ImportError:
    HAS_RDKIT = False


def generate_interactive_plots(smiles_list, names=None):
    """Generate interactive plotly plots for a set of molecules.

    Returns dict of plotly HTML strings for each plot type.
    """
    if not HAS_RDKIT:
        return {"error": "RDKit not available"}

    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        import plotly.express as px
    except ImportError:
        return {"error": "plotly not available"}

    from rdkit import RDLogger
    RDLogger.DisableLog("rdApp.*")

    if names is None:
        names = [f"Mol_{i+1}" for i in range(len(smiles_list))]

    # Calculate properties for all molecules
    props = []
    valid_names = []
    valid_smiles = []
    for i, smi in enumerate(smiles_list):
        mol = Chem.MolFromSmiles(str(smi).strip())
        if mol is None:
            continue
        try:
            mw = Descriptors.MolWt(mol)
            logp = Crippen.MolLogP(mol)
            tpsa = Descriptors.TPSA(mol)
            hbd = Descriptors.NumHDonors(mol)
            hba = Descriptors.NumHAcceptors(mol)
            rot = Descriptors.NumRotatableBonds(mol)

            # Drug-likeness categories (Omixium style)
            fragment_like = mw <= 300 and logp <= 3 and hbd <= 3 and hba <= 3
            lead_like = mw <= 350 and logp <= 3 and hbd <= 3 and hba <= 6
            lipinski_pass = mw <= 500 and logp <= 5 and hbd <= 5 and hba <= 10

            if fragment_like:
                drug_cat = "Fragment-like"
            elif lead_like:
                drug_cat = "Lead-like"
            elif lipinski_pass:
                drug_cat = "Drug-like"
            else:
                drug_cat = "Non-drug-like"

            p = {
                "name": names[i] if i < len(names) else f"Mol_{i+1}",
                "smiles": smi,
                "MW": round(mw, 2),
                "LogP": round(logp, 2),
                "TPSA": round(tpsa, 2),
                "HBD": hbd,
                "HBA": hba,
                "RotBonds": rot,
                "AromaticRings": Descriptors.NumAromaticRings(mol),
                "HeavyAtoms": mol.GetNumHeavyAtoms(),
                "QED": round(Descriptors.qed(mol), 3),
                "MR": round(Crippen.MolMR(mol), 2),
                "FractionCSP3": round(Descriptors.FractionCSP3(mol), 3),
                "DrugCategory": drug_cat,
                "LipinskiPass": lipinski_pass,
                "LeadLike": lead_like,
                "FragmentLike": fragment_like,
            }
            props.append(p)
            valid_names.append(p["name"])
            valid_smiles.append(smi)
        except Exception:
            continue

    if not props:
        return {"error": "No valid molecules"}

    import pandas as pd
    df = pd.DataFrame(props)
    plots = {}

    # 1. Property Distributions (subplots)
    try:
        fig = make_subplots(
            rows=2, cols=3,
            subplot_titles=["Molecular Weight", "LogP", "TPSA", "HBD", "HBA", "QED"]
        )
        for i, col in enumerate(["MW", "LogP", "TPSA", "HBD", "HBA", "QED"]):
            row = i // 3 + 1
            c = i % 3 + 1
            fig.add_trace(
                go.Histogram(x=df[col], name=col, marker_color=px.colors.qualitative.Set2[i % 8],
                             nbinsx=20, showlegend=False),
                row=row, col=c
            )
        fig.update_layout(title="Molecular Property Distributions", height=500)
        plots["distributions_html"] = fig.to_html(include_plotlyjs="cdn", full_html=False)
    except Exception as e:
        log.warning("Distribution plot failed: %s", e)

    # 2. Correlation Heatmap
    try:
        numeric_cols = ["MW", "LogP", "TPSA", "HBD", "HBA", "RotBonds", "QED", "MR"]
        corr = df[numeric_cols].corr()
        fig = go.Figure(data=go.Heatmap(
            z=corr.values, x=corr.columns, y=corr.columns,
            colorscale="RdBu", zmid=0,
            text=corr.round(2).values, texttemplate="%{text}", textfont={"size": 10}
        ))
        fig.update_layout(title="Property Correlation Matrix", width=600, height=500)
        plots["correlation_html"] = fig.to_html(include_plotlyjs="cdn", full_html=False)
    except Exception as e:
        log.warning("Correlation plot failed: %s", e)

    # 3. Chemical Space (PCA on molecular descriptors)
    try:
        from sklearn.decomposition import PCA
        from sklearn.preprocessing import StandardScaler

        feature_cols = ["MW", "LogP", "TPSA", "HBD", "HBA", "RotBonds", "MR", "FractionCSP3"]
        X = df[feature_cols].values
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        pca = PCA(n_components=2)
        coords = pca.fit_transform(X_scaled)

        fig = go.Figure(data=go.Scatter(
            x=coords[:, 0], y=coords[:, 1],
            mode="markers+text",
            marker=dict(size=10, color=df["QED"], colorscale="Viridis",
                        colorbar=dict(title="QED"), showscale=True),
            text=valid_names, textposition="top center", textfont=dict(size=8),
            hovertemplate="<b>%{text}</b><br>PC1: %{x:.2f}<br>PC2: %{y:.2f}<extra></extra>"
        ))
        fig.update_layout(
            title=f"Chemical Space (PCA) — {len(valid_names)} molecules",
            xaxis_title=f"PC1 ({100*pca.explained_variance_ratio_[0]:.1f}% var)",
            yaxis_title=f"PC2 ({100*pca.explained_variance_ratio_[1]:.1f}% var)",
            width=800, height=600
        )
        plots["chemical_space_html"] = fig.to_html(include_plotlyjs="cdn", full_html=False)
    except Exception as e:
        log.warning("Chemical space plot failed: %s", e)

    # 4. Lipinski Ro5 Analysis
    try:
        fig = make_subplots(rows=1, cols=2,
                           subplot_titles=["MW vs LogP (Lipinski)", "TPSA vs LogP (Veber)"])

        # MW vs LogP with Lipinski boundaries
        colors = ["#4CAF50" if (r["MW"] <= 500 and r["LogP"] <= 5) else "#F44336" for _, r in df.iterrows()]
        fig.add_trace(go.Scatter(
            x=df["LogP"], y=df["MW"], mode="markers",
            marker=dict(size=8, color=colors),
            text=valid_names, hovertemplate="<b>%{text}</b><br>LogP: %{x:.2f}<br>MW: %{y:.1f}<extra></extra>"
        ), row=1, col=1)
        fig.add_hline(y=500, line_dash="dash", line_color="red", row=1, col=1)
        fig.add_vline(x=5, line_dash="dash", line_color="red", row=1, col=1)

        # TPSA vs LogP with Veber boundaries
        colors2 = ["#4CAF50" if (r["TPSA"] <= 140 and r["RotBonds"] <= 10) else "#F44336" for _, r in df.iterrows()]
        fig.add_trace(go.Scatter(
            x=df["LogP"], y=df["TPSA"], mode="markers",
            marker=dict(size=8, color=colors2),
            text=valid_names, hovertemplate="<b>%{text}</b><br>LogP: %{x:.2f}<br>TPSA: %{y:.1f}<extra></extra>"
        ), row=1, col=2)
        fig.add_hline(y=140, line_dash="dash", line_color="red", row=1, col=2)

        fig.update_layout(title="Drug-likeness Analysis", width=1000, height=450)
        plots["druglikeness_html"] = fig.to_html(include_plotlyjs="cdn", full_html=False)
    except Exception as e:
        log.warning("Drug-likeness plot failed: %s", e)

    # 5. 3D Chemical Space (LogP vs MW vs TPSA, colored by DrugCategory)
    try:
        if "DrugCategory" in df.columns:
            cat_colors = {
                "Fragment-like": "#1f77b4", "Lead-like": "#ff7f0e",
                "Drug-like": "#2ca02c", "Non-drug-like": "#d62728"
            }
            fig = go.Figure()
            for cat in df["DrugCategory"].unique():
                mask = df["DrugCategory"] == cat
                fig.add_trace(go.Scatter3d(
                    x=df.loc[mask, "LogP"], y=df.loc[mask, "MW"], z=df.loc[mask, "TPSA"],
                    mode="markers", name=cat,
                    marker=dict(size=6, color=cat_colors.get(cat, "#888"), opacity=0.7),
                    text=[valid_names[i] for i in df.index[mask]],
                    hovertemplate="<b>%{text}</b><br>LogP: %{x:.2f}<br>MW: %{y:.1f}<br>TPSA: %{z:.1f}<extra></extra>"
                ))
            fig.update_layout(
                title="3D Chemical Space (Omixium style)",
                scene=dict(xaxis_title="LogP", yaxis_title="MW (Da)", zaxis_title="TPSA (A²)"),
                width=900, height=700
            )
            plots["chemical_space_3d_html"] = fig.to_html(include_plotlyjs="cdn", full_html=False)
    except Exception as e:
        log.warning("3D chemical space failed: %s", e)

    # 6. Parallel Coordinates Plot (multi-property comparison)
    try:
        sample = df.sample(n=min(200, len(df)), random_state=42) if len(df) > 200 else df
        color_map = {"Fragment-like": 0, "Lead-like": 1, "Drug-like": 2, "Non-drug-like": 3}
        if "DrugCategory" in sample.columns:
            color_vals = [color_map.get(c, 3) for c in sample["DrugCategory"]]
        else:
            color_vals = [0] * len(sample)

        fig = go.Figure(data=go.Parcoords(
            line=dict(color=color_vals, colorscale=[[0, "#1f77b4"], [0.33, "#ff7f0e"],
                                                     [0.67, "#2ca02c"], [1, "#d62728"]],
                      showscale=False),
            dimensions=[
                dict(label="MW", values=sample["MW"]),
                dict(label="LogP", values=sample["LogP"]),
                dict(label="TPSA", values=sample["TPSA"]),
                dict(label="HBD", values=sample["HBD"]),
                dict(label="HBA", values=sample["HBA"]),
                dict(label="QED", values=sample["QED"]),
                dict(label="RotBonds", values=sample["RotBonds"]),
            ]
        ))
        fig.update_layout(title="Parallel Coordinates (multi-property)", width=900, height=500)
        plots["parallel_coordinates_html"] = fig.to_html(include_plotlyjs="cdn", full_html=False)
    except Exception as e:
        log.warning("Parallel coordinates failed: %s", e)

    # 7. Scatter Matrix (pairwise property relationships)
    try:
        sample = df.sample(n=min(200, len(df)), random_state=42) if len(df) > 200 else df
        dims = ["MW", "LogP", "TPSA", "HBD", "HBA", "QED"]
        fig = go.Figure(data=go.Splom(
            dimensions=[dict(label=c, values=sample[c]) for c in dims],
            marker=dict(size=4, color="#2196F3", opacity=0.5),
            text=sample["name"] if "name" in sample.columns else None,
        ))
        fig.update_layout(title="Scatter Matrix (pairwise properties)", width=900, height=700)
        plots["scatter_matrix_html"] = fig.to_html(include_plotlyjs="cdn", full_html=False)
    except Exception as e:
        log.warning("Scatter matrix failed: %s", e)

    # 8. Summary table
    plots["summary_table"] = df.to_dict(orient="records")
    plots["success"] = True
    return plots
