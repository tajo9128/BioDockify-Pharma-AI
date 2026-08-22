"""Pathway enrichment and druggability analysis for identified targets."""
import logging
from typing import Dict, List

log = logging.getLogger("target_identification.enrichment")

PATHWAY_DATABASE = {
    "EGFR": ["MAPK/ERK signaling", "PI3K-AKT signaling", "JAK-STAT signaling"],
    "BRAF": ["MAPK/ERK signaling", "RAF-MEK-ERK cascade"],
    "KRAS": ["MAPK/ERK signaling", "PI3K-AKT signaling", "RAS-RAF-MEK-ERK"],
    "TP53": ["p53 signaling pathway", "Apoptosis", "Cell cycle arrest"],
    "HER2": ["ErbB signaling", "PI3K-AKT signaling", "MAPK/ERK signaling"],
    "JAK1": ["JAK-STAT signaling", "Cytokine signaling", "Inflammatory response"],
    "TNF": ["NF-kB signaling", "TNF signaling", "Apoptosis", "Inflammatory response"],
    "GLP1R": ["cAMP signaling", "Insulin secretion", "Glucose homeostasis"],
    "DPP4": ["Incretin signaling", "Glucose homeostasis"],
    "PCSK9": ["Cholesterol metabolism", "LDL receptor recycling"],
    "ACE": ["Renin-angiotensin system", "Blood pressure regulation"],
    "HMGCR": ["Mevalonate pathway", "Cholesterol biosynthesis"],
    "APP": ["Amyloid processing", "Notch signaling"],
    "BACE1": ["Amyloid processing", "APP cleavage"],
}

DRUGGABILITY_CRITERIA = {
    "binding_pocket": {"kinase": True, "gpcr": True, "protease": True, "ion_channel": True,
                       "nuclear_receptor": True, "transporter": True, "enzyme": True},
    "modality": {
        "high": ["Small molecule", "Antibody", "Peptide"],
        "medium": ["Small molecule", "Antibody"],
        "low": ["Antibody", "Gene therapy", "Antisense oligonucleotide"],
    },
}

TARGET_FAMILIES = {
    "EGFR": "kinase", "BRAF": "kinase", "JAK1": "kinase", "HER2": "kinase",
    "GLP1R": "gpcr", "TNF": "cytokine", "IL6": "cytokine",
    "BACE1": "protease", "DPP4": "protease", "ACE": "protease",
    "PCSK9": "protease", "HMGCR": "enzyme", "COX2": "enzyme",
    "PPARG": "nuclear_receptor", "SGLT2": "transporter",
    "TP53": "transcription_factor", "KRAS": "gtpase",
    "APP": "membrane_protein", "MAPT": "structural_protein",
    "APOE": "lipid_transport",
}


def pathway_enrichment(gene_list: List[str]) -> Dict:
    """Find enriched pathways given a list of target genes.

    Counts how many input genes map to each pathway.
    """
    if not gene_list:
        return {"error": "Empty gene list"}

    pathway_counts = {}
    gene_pathway_map = {}

    for gene in gene_list:
        gene_upper = gene.upper().strip()
        pathways = PATHWAY_DATABASE.get(gene_upper, [])
        gene_pathway_map[gene_upper] = pathways
        for p in pathways:
            if p not in pathway_counts:
                pathway_counts[p] = {"count": 0, "genes": []}
            pathway_counts[p]["count"] += 1
            pathway_counts[p]["genes"].append(gene_upper)

    enriched = []
    for pathway, data in pathway_counts.items():
        enrichment_ratio = data["count"] / len(gene_list)
        enriched.append({
            "pathway": pathway,
            "gene_count": data["count"],
            "genes": data["genes"],
            "enrichment_ratio": round(enrichment_ratio, 3),
        })

    enriched.sort(key=lambda x: x["gene_count"], reverse=True)

    return {
        "input_genes": len(gene_list),
        "pathways_found": len(enriched),
        "enriched_pathways": enriched,
        "gene_coverage": {g: len(ps) > 0 for g, ps in gene_pathway_map.items()},
        "uncovered_genes": [g for g, ps in gene_pathway_map.items() if not ps],
    }


def druggability_assessment(gene_symbol: str) -> Dict:
    """Assess how druggable a target is based on protein family and known precedent."""
    gene_upper = gene_symbol.upper().strip()

    family = TARGET_FAMILIES.get(gene_upper, "unknown")

    has_pocket = DRUGGABILITY_CRITERIA["binding_pocket"].get(family, False)

    from .searcher import GENE_DATABASE
    local_info = GENE_DATABASE.get(gene_upper, {})
    known_drugs = local_info.get("known_drugs", [])
    druggability_label = local_info.get("druggability", "unknown")

    if druggability_label == "unknown":
        if known_drugs:
            druggability_label = "high"
        elif has_pocket:
            druggability_label = "medium"
        else:
            druggability_label = "low"

    modalities = DRUGGABILITY_CRITERIA["modality"].get(druggability_label, ["Unknown"])

    score = 0.0
    reasons = []

    if known_drugs:
        score += 0.4
        reasons.append(f"Validated: {len(known_drugs)} approved drug(s)")
    if has_pocket:
        score += 0.3
        reasons.append(f"Predicted binding pocket ({family} family)")
    if family in ("kinase", "gpcr", "protease", "nuclear_receptor"):
        score += 0.2
        reasons.append(f"Highly druggable protein family: {family}")
    elif family in ("enzyme", "ion_channel", "transporter"):
        score += 0.15
        reasons.append(f"Druggable family: {family}")
    else:
        reasons.append(f"Challenging target class: {family}")

    score = min(1.0, score)

    return {
        "gene": gene_upper,
        "family": family,
        "druggability": druggability_label,
        "druggability_score": round(score, 2),
        "has_binding_pocket": has_pocket,
        "suggested_modalities": modalities,
        "known_drugs": known_drugs,
        "assessment_reasons": reasons,
    }
