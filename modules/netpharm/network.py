"""Network Pharmacology — disease targets x compound targets network analysis.

Builds a compound-target bipartite network against a disease target set,
computes target degree centrality/hubs, ranks compounds by overlap with the
disease target set, and runs pathway enrichment on the overlapping targets.
Pathway data reused from modules/target_identification (curated, offline).
"""
import logging
from typing import Dict, List

log = logging.getLogger("netpharm.network")


def analyze_network(disease_targets: List[str],
                    compounds: Dict[str, List[str]] = None,
                    custom_compounds: Dict[str, List[str]] = None,
                    top_compounds: int = 15) -> Dict:
    """compounds: curated DB subset (or full); custom_compounds: user mapping."""
    if not disease_targets:
        return {"error": "disease_targets required (gene symbols)"}
    disease_set = {g.upper().strip() for g in disease_targets if g and g.strip()}

    pool: Dict[str, List[str]] = {}
    if compounds:
        pool.update({k: [t.upper() for t in v] for k, v in compounds.items()})
    if custom_compounds:
        pool.update({k: [str(t).upper().strip() for t in v] for k, v in custom_compounds.items()})
    if not pool:
        return {"error": "no compounds available (provide custom_compounds {name: [targets]})"}

    # ── compound ranking by overlap with disease targets ────────────
    ranked = []
    target_compound_count: Dict[str, int] = {}
    for cname, ctargets in pool.items():
        tset = set(ctargets)
        hits = sorted(tset & disease_set)
        jaccard = len(hits) / len(tset | disease_set) if (tset | disease_set) else 0.0
        coverage = len(hits) / len(disease_set) if disease_set else 0.0
        if hits:  # only compounds touching the disease target set
            ranked.append({
                "compound": cname,
                "direct_hits": hits,
                "num_hits": len(hits),
                "percent_of_disease_targets": round(100 * coverage, 1),
                "jaccard": round(jaccard, 4),
                "multi_target": len(hits) >= 2,
            })
        for t in tset & disease_set:
            target_compound_count[t] = target_compound_count.get(t, 0) + 1

    ranked.sort(key=lambda r: (-r["num_hits"], -r["jaccard"]))

    # ── target hubs (most-connected within the disease-relevant network) ──
    hubs = sorted(target_compound_count.items(), key=lambda kv: -kv[1])
    hub_list = [{"target": t, "degree": d} for t, d in hubs[:20]]

    # ── pathway enrichment on covered targets ───────────────────────
    covered = sorted(target_compound_count.keys())
    enrichment = None
    if covered:
        try:
            from modules.target_identification.enrichment import pathway_enrichment
            enrichment = pathway_enrichment(covered)
        except Exception as e:
            log.warning("enrichment failed: %s", e)

    multi = [r for r in ranked if r["multi_target"]]
    return {
        "disease_targets": sorted(disease_set),
        "num_disease_targets": len(disease_set),
        "num_compounds_screened": len(pool),
        "compounds_hitting_network": len(ranked),
        "multi_target_compounds": len(multi),
        "ranked_compounds": ranked[:top_compounds],
        "target_hubs": hub_list,
        "pathway_enrichment": enrichment,
        "network_note": "Compounds ranked by direct-target overlap with the disease set; "
                        "hubs = disease targets hit by the most compounds (attractive "
                        "multi-target intervention points).",
        "disclaimer": "Curated starter database — extend with custom_compounds or literature "
                      "target lists for publication-grade networks.",
    }


def network_from_disease(disease: str, limit: int = 25, custom_compounds=None) -> Dict:
    """Disease → targets (via target_identification search) → network analysis."""
    from .compound_targets import COMPOUND_TARGETS
    from modules.target_identification import search_by_disease

    res = search_by_disease(disease, limit=limit)
    if "error" in res:
        return res
    targets = [t.get("gene") for t in res.get("targets", []) if t.get("gene")]
    if not targets:
        return {"error": f"No targets found for disease '{disease}'"}

    analysis = analyze_network(targets, compounds=COMPOUND_TARGETS,
                               custom_compounds=custom_compounds)
    if "error" in analysis:
        return analysis
    analysis["disease"] = disease
    analysis["target_source"] = res.get("source", "")
    return analysis
