"""Target Identification API — search disease-target links, gene lookup, druggability."""
from helpers.api import ApiHandler, Request, Response
import logging

log = logging.getLogger("api.target_identification")


class TargetIdentificationHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "")

        if action == "search_disease":
            return self._search_disease(input)
        elif action == "search_gene":
            return self._search_gene(input)
        elif action == "target_details":
            return self._target_details(input)
        elif action == "pathways":
            return self._pathways(input)
        elif action == "druggability":
            return self._druggability(input)
        elif action == "prioritize":
            return self._prioritize(input)
        elif action == "prioritize_disease":
            return self._prioritize_disease(input)
        else:
            return {
                "actions": ["search_disease", "search_gene", "target_details", "pathways",
                            "druggability", "prioritize", "prioritize_disease"],
                "hint": "Target identification: find targets for diseases, gene lookup, pathway enrichment, druggability assessment, multi-criteria prioritization",
            }

    def _search_disease(self, input: dict) -> dict:
        disease = input.get("disease", "")
        limit = input.get("limit", 10)

        if not disease:
            return {"error": "disease required (e.g. 'cancer', 'alzheimer', 'diabetes')"}

        from modules.target_identification import search_by_disease
        return search_by_disease(disease, limit)

    def _search_gene(self, input: dict) -> dict:
        gene = input.get("gene", "")

        if not gene:
            return {"error": "gene required (e.g. 'EGFR', 'BRAF', 'TP53')"}

        from modules.target_identification import search_by_gene
        return search_by_gene(gene)

    def _target_details(self, input: dict) -> dict:
        gene = input.get("gene", "")

        if not gene:
            return {"error": "gene required"}

        from modules.target_identification import get_target_details
        return get_target_details(gene)

    def _pathways(self, input: dict) -> dict:
        genes = input.get("genes", [])

        if not genes:
            return {"error": "genes required (array of gene symbols)"}

        from modules.target_identification.enrichment import pathway_enrichment
        return pathway_enrichment(genes)

    def _druggability(self, input: dict) -> dict:
        gene = input.get("gene", "")

        if not gene:
            return {"error": "gene required"}

        from modules.target_identification.enrichment import druggability_assessment
        return druggability_assessment(gene)

    def _prioritize(self, input: dict) -> dict:
        candidates = input.get("candidates", [])
        if not candidates:
            return {"error": "candidates required: [{gene, association (0-1), known_drugs}]"}
        from modules.target_identification import prioritize_targets
        return prioritize_targets(candidates, weights=input.get("weights", None))

    def _prioritize_disease(self, input: dict) -> dict:
        disease = input.get("disease", "")
        if not disease:
            return {"error": "disease required"}
        from modules.target_identification import prioritize_from_disease
        return prioritize_from_disease(disease, limit=int(input.get("limit", 10)),
                                       weights=input.get("weights", None))
