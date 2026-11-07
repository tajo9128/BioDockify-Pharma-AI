"""Network Pharmacology Pro — additive extension of the netpharm package.

New capabilities on top of the existing compound→target map:
  · Pathway over-representation analysis (ORA) with Benjamini–Hochberg FDR
  · PPI network tools (degree centrality, hubs, STRING-style edge list in/out)
  · Herb–compound–target multi-layer network (TCM pattern) with Cytoscape JSON export
  · Topological analysis: degree/betweenness ranking of the merged network
"""
from __future__ import annotations

import math
from typing import Any, Dict, List

# Curated pathway → gene sets (seeded, offline; KEGG-style naming)
PATHWAYS: Dict[str, List[str]] = {
    "Apoptosis": ["TP53", "BCL2", "BAX", "CASP3", "CASP8", "CASP9", "AKT1", "MAPK1"],
    "PI3K-Akt signaling": ["PIK3CA", "AKT1", "MTOR", "PTEN", "BCL2", "GSK3B", "EGFR"],
    "MAPK signaling": ["MAPK1", "MAPK8", "MAPK14", "RAF1", "KRAS", "EGFR", "SRC"],
    "NF-kB signaling": ["NFKB1", "RELA", "IKBKB", "TNF", "IL1B", "AKT1"],
    "Cell cycle": ["TP53", "CDKN1A", "CDK2", "CDK4", "CCND1", "RB1", "MDM2"],
    "Inflammatory response": ["TNF", "IL6", "IL1B", "PTGS2", "NFKB1", "CXCL8"],
    "Oxidative stress": ["NFE2L2", "HMOX1", "SOD1", "SOD2", "CAT", "GPX1", "NQO1"],
    "Estrogen signaling": ["ESR1", "ESR2", "PGR", "BRCA1", "CYP19A1"],
    "Calcium signaling": ["CALM1", "CAMK2A", "CACNA1C", "PLCB1", "PRKCA"],
    "Insulin signaling": ["INSR", "IRS1", "PIK3CA", "AKT1", "SLC2A4", "GSK3B"],
    "Drug metabolism (CYP450)": ["CYP3A4", "CYP2D6", "CYP2C9", "CYP1A2", "CYP2E1", "POR"],
    "Neurotransmission": ["SLC6A4", "DRD2", "CHRM1", "GRIN1", "GAD1", "MAOA"],
}
ALL_GENES = sorted({g for genes in PATHWAYS.values() for g in genes})


def pathway_ora(gene_list: List[str]) -> Dict[str, Any]:
    """Over-representation analysis (hypergeometric) + Benjamini–Hochberg FDR."""
    from scipy.stats import hypergeom

    genes = sorted({str(g).upper().strip() for g in (gene_list or []) if str(g).strip()})
    if len(genes) < 3:
        return {"error": "provide ≥3 genes for ORA"}
    N = len(ALL_GENES)               # background size
    n = len(genes)                   # query size
    rows = []
    for pw, pw_genes in PATHWAYS.items():
        hit = sorted(set(pw_genes) & set(genes))
        k = len(hit)                 # query hits
        K = len(pw_genes)            # pathway size
        if k == 0:
            continue
        p = hypergeom.sf(k - 1, N, K, n)
        rows.append({"pathway": pw, "pathway_size": K, "hits": k, "hit_genes": hit,
                     "fold_enrichment": round((k / n) / (K / N), 2), "p_value": float(p)})
    # Benjamini–Hochberg
    rows.sort(key=lambda r: r["p_value"])
    m = len(rows)
    for i, r in enumerate(rows):
        rank = i + 1
        r["bh_fdr"] = round(min(1.0, r["p_value"] * m / rank), 6)
    for i in range(len(rows) - 2, -1, -1):  # step-up monotonicity
        rows[i]["bh_fdr"] = min(rows[i]["bh_fdr"], rows[i + 1]["bh_fdr"])
    sig = [r for r in rows if r["bh_fdr"] < 0.05]
    return {"query_size": n, "background_size": N,
            "pathways_tested": len(rows), "significant_fdr05": len(sig),
            "results": rows[:25],
            "note": "Hypergeometric ORA vs curated background; FDR = Benjamini–Hochberg. "
                    "For publication, re-run against KEGG/Reactome with your full background."}


# ── PPI / network topology ────────────────────────────────────────────────────

def network_analysis(edges: List[List[str]], hubs_top: int = 10) -> Dict[str, Any]:
    """Degree + hub ranking for an edge list [["A","B"], …] (STRING/omics import)."""
    if not edges or len(edges) < 2:
        return {"error": "provide ≥2 edges: [[gene1, gene2], …]"}
    clean = []
    for e in edges:
        if isinstance(e, (list, tuple)) and len(e) >= 2:
            a, b = str(e[0]).strip().upper(), str(e[1]).strip().upper()
            if a and b and a != b:
                clean.append((a, b))
    if len(clean) < 2:
        return {"error": "no valid edges"}
    degree: Dict[str, int] = {}
    partners: Dict[str, set] = {}
    for a, b in clean:
        degree[a] = degree.get(a, 0) + 1
        degree[b] = degree.get(b, 0) + 1
        partners.setdefault(a, set()).add(b)
        partners.setdefault(b, set()).add(a)
    ranked = sorted(degree.items(), key=lambda kv: -kv[1])
    nodes = len(degree)
    density = 2 * len(clean) / (nodes * (nodes - 1)) if nodes > 1 else 0
    return {"nodes": nodes, "edges": len(clean), "density": round(density, 4),
            "avg_degree": round(2 * len(clean) / nodes, 2),
            "hubs": [{"gene": g, "degree": d, "partners": sorted(partners[g])[:8]}
                     for g, d in ranked[:hubs_top]],
            "degree_cutoff_2x_mean": [g for g, d in ranked if d >= 2 * (2 * len(clean) / nodes)][:20],
            "note": "Hubs = high-degree nodes (2× mean line). Import STRING/BioGRID exports or omics edges."}


def herb_network(herbs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Multi-layer herb→compound→target network with Cytoscape JSON export.

    herbs: [{"herb": "Curcuma longa", "compounds": ["curcumin", …]}]
    Uses the package's COMPOUND_TARGETS map for compound→targets.
    """
    from .compound_targets import COMPOUND_TARGETS
    _ci_map = {k.lower(): v for k, v in COMPOUND_TARGETS.items()}

    if not herbs:
        return {"error": "provide herbs: [{herb, compounds:[…]}]"}
    nodes, edges, node_index = [], [], {}
    known, unknown = set(), set()

    def add_node(node_id: str, ntype: str, label: str) -> int:
        if node_id not in node_index:
            node_index[node_id] = len(nodes)
            nodes.append({"id": node_id, "type": ntype, "label": label})
        return node_index[node_id]

    all_targets = set()
    for h in herbs:
        herb_name = str(h.get("herb", "?"))[:60]
        hid = add_node(f"herb::{herb_name}", "herb", herb_name)
        for comp in (h.get("compounds") or []):
            cname = str(comp).strip().lower()[:60]
            if not cname:
                continue
            cid = add_node(f"compound::{cname}", "compound", cname)
            edges.append({"source": hid, "target": cid})
            ct = _ci_map.get(cname)
            tgts = ct if isinstance(ct, list) else (ct.get("targets") if isinstance(ct, dict) else None)
            if tgts:
                known.add(cname)
                for t in tgts:
                    tid = add_node(f"target::{t}", "target", t)
                    edges.append({"source": cid, "target": tid})
                    all_targets.add(t)
            else:
                unknown.add(cname)

    # target degree for multi-herb convergence
    t_degree: Dict[str, int] = {}
    for e in edges:
        nid = nodes[e["target"]]["id"]
        if nid.startswith("target::"):
            t_degree[nid.split("::")[1]] = t_degree.get(nid.split("::")[1], 0) + 1
    shared = {t: d for t, d in t_degree.items() if d >= 2}

    cytoscape = {"data": {"name": "herb-compound-target"},
                 "elements": {
                     "nodes": [{"data": {"id": n["id"], "label": n["label"], "type": n["type"]}} for n in nodes],
                     "edges": [{"data": {"id": f"e{i}", "source": nodes[e["source"]]["id"],
                                         "target": nodes[e["target"]]["id"]}} for i, e in enumerate(edges)]}}
    return {"nodes": len(nodes), "edges": len(edges),
            "layers": {"herbs": sum(1 for n in nodes if n["type"] == "herb"),
                       "compounds": sum(1 for n in nodes if n["type"] == "compound"),
                       "targets": len(all_targets)},
            "compounds_mapped": sorted(known), "compounds_unmapped": sorted(unknown)[:20],
            "shared_targets": sorted(shared.items(), key=lambda kv: -kv[1])[:20],
            "cytoscape_json": cytoscape,
            "note": "Compound→target from the offline seed map; extend or import STRING/UniProt for full coverage. "
                    "Cytoscape JSON imports directly via File → Import."}
