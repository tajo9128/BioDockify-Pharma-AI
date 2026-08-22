"""Target Prioritization — multi-criteria weighted scoring for target selection.

Combines: genetic association (user-supplied or from disease search),
druggability (family-based), safety (essential-gene penalty), pathway
centrality, and novelty (existing-drug count) into a weighted composite
with transparent per-criterion breakdown and rationale.
"""
import logging
from typing import Dict, List

log = logging.getLogger("target_identification.prioritization")

# essential/safety-critical gene set (curated, core housekeeping + known toxicity liabilities)
ESSENTIAL_GENES = {
    "TP53", "KRAS", "PTEN", "BRCA1", "BRCA2", "MYC", "EGFR", "BRAF", "PIK3CA", "AKT1",
    "MAPK1", "MAPK3", "MTOR", "CDK1", "PLK1", "AURKA", "AURKB", "TOP2A", "PARP1",
    "HSP90AA1", "TUBB", "ACTB", "GAPDH", "RPL5", "RPL11", "PCNA", "MCM2", "CDC20",
}
# note: essentiality is double-edged (essential = on-target toxicity risk but often cancer-validated)

DEFAULT_WEIGHTS = {
    "association": 0.35,
    "druggability": 0.30,
    "safety": 0.15,
    "pathway_centrality": 0.10,
    "novelty": 0.10,
}


def _pathway_centrality(gene: str, pathway_db: Dict) -> float:
    """How many pathways the gene participates in (0-1 normalized, cap 4)."""
    n = len(pathway_db.get(gene.upper().strip(), []))
    return min(n / 4.0, 1.0)


def prioritize_targets(candidates: List[Dict], weights: Dict = None,
                       pathway_db: Dict = None) -> Dict:
    """candidates: [{gene, association (0-1), known_drugs (int), ...optional family}]"""
    if not candidates:
        return {"error": "candidates required: [{gene, association (0-1), known_drugs}]"}
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    pathway_db = pathway_db or {}

    from .enrichment import druggability_assessment

    ranked = []
    for cand in candidates:
        gene = str(cand.get("gene", "")).upper().strip()
        if not gene:
            continue
        association = float(cand.get("association", cand.get("score", 0.5)) or 0)
        association = max(0.0, min(1.0, association))
        known_drugs = int(cand.get("known_drugs", 0) or 0)

        # druggability from the existing assessment (family-based)
        try:
            dg = druggability_assessment(gene)
            drug_score = float(dg.get("druggability_score", 0.5) or 0.5)
            family = dg.get("family", "unknown")
        except Exception:
            drug_score, family = 0.5, "unknown"

        # safety: essential genes carry on-target toxicity risk (score lowered)
        essential = gene in ESSENTIAL_GENES
        safety = 0.4 if essential else 1.0

        centrality = _pathway_centrality(gene, pathway_db)

        # novelty: fewer existing drugs = higher novelty (first-in-class chance)
        novelty = 1.0 if known_drugs == 0 else max(0.0, 1.0 - known_drugs / 10.0)

        composite = (w["association"] * association
                     + w["druggability"] * drug_score
                     + w["safety"] * safety
                     + w["pathway_centrality"] * centrality
                     + w["novelty"] * novelty)

        rationale = []
        if association >= 0.7:
            rationale.append(f"strong genetic association ({association:.2f})")
        if drug_score >= 0.7:
            rationale.append(f"highly druggable {family}")
        if essential:
            rationale.append("essential gene — on-target toxicity risk (safety-weighted down)")
        if centrality >= 0.5:
            rationale.append(f"pathway hub ({int(centrality*4)}+ pathways)")
        if known_drugs == 0:
            rationale.append("no approved drugs — first-in-class opportunity")
        else:
            rationale.append(f"{known_drugs} known drug(s) — validated but crowded")

        ranked.append({
            "gene": gene,
            "family": family,
            "criteria": {
                "association": round(association, 3),
                "druggability": round(drug_score, 2),
                "safety": safety,
                "pathway_centrality": round(centrality, 2),
                "novelty": round(novelty, 2),
            },
            "essential_gene": essential,
            "known_drugs": known_drugs,
            "weighted_score": round(composite, 3),
            "rationale": rationale,
            "user_fields": {k: v for k, v in cand.items() if k not in ("gene", "association", "known_drugs")},
        })

    ranked.sort(key=lambda r: -r["weighted_score"])
    return {
        "num_targets": len(ranked),
        "weights_used": w,
        "ranked_targets": ranked,
        "recommendation": f"Top target: {ranked[0]['gene']} ({ranked[0]['weighted_score']})" if ranked else "none",
        "note": "Transparent multi-criteria screening — adjust weights to your strategy "
                "(e.g. {association: 0.6} for genetics-first, {novelty: 0.4} for first-in-class).",
    }


def prioritize_from_disease(disease: str, limit: int = 10, weights: Dict = None) -> Dict:
    """Convenience: pull disease-associated targets then prioritize."""
    from .searcher import search_by_disease
    from .enrichment import PATHWAY_DATABASE
    res = search_by_disease(disease, limit=limit)
    if "error" in res:
        return res
    targets = res.get("targets", [])
    candidates = []
    for t in targets:
        candidates.append({
            "gene": t.get("gene"),
            "association": t.get("score", t.get("association", 0.5)),
            "known_drugs": len(t.get("known_drugs", []) or []) if isinstance(t.get("known_drugs"), list) else int(t.get("known_drugs", 0) or 0),
        })
    result = prioritize_targets(candidates, weights=weights, pathway_db=PATHWAY_DATABASE)
    result["disease"] = disease
    result["source"] = res.get("source", "")
    return result
