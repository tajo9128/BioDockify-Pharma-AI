"""Network Pharmacology API — disease/compound-target network analysis + enrichment."""
from helpers.api import ApiHandler, Request, Response
import logging

log = logging.getLogger("api.netpharm")


class NetPharmHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "")

        if action == "compounds":
            from modules.netpharm import COMPOUND_TARGETS
            return {"compounds": {k: v for k, v in COMPOUND_TARGETS.items()},
                    "count": len(COMPOUND_TARGETS)}
        elif action == "compound_targets":
            return self._compound_targets(input)
        elif action == "analyze":
            return self._analyze(input)
        elif action == "analyze_disease":
            return self._analyze_disease(input)
        else:
            return {
                "actions": ["compounds", "compound_targets", "analyze", "analyze_disease"],
                "hint": "Network pharmacology: compound-target networks, disease overlap, hubs, pathway enrichment",
            }

    def _compound_targets(self, input: dict) -> dict:
        compound = input.get("compound", "")
        if not compound:
            return {"error": "compound required"}
        from modules.netpharm import get_compound_targets
        name, targets = get_compound_targets(compound)
        if name is None:
            return {"error": f"Compound '{compound}' not in curated DB. Use analyze with custom_compounds.",
                    "db_size": len(__import__('modules.netpharm', fromlist=['COMPOUND_TARGETS']).COMPOUND_TARGETS)}
        return {"compound": name, "targets": targets, "count": len(targets)}

    def _analyze(self, input: dict) -> dict:
        genes = input.get("gene_list", input.get("disease_targets", []))
        if isinstance(genes, str):
            genes = [g.strip() for g in genes.replace(",", "\n").split("\n") if g.strip()]
        if not genes:
            return {"error": "gene_list required (array or newline/comma-separated gene symbols)"}
        custom = input.get("custom_compounds", None)
        use_db = input.get("use_curated_db", True)
        from modules.netpharm import analyze_network, COMPOUND_TARGETS
        return analyze_network(genes,
                               compounds=COMPOUND_TARGETS if use_db else None,
                               custom_compounds=custom,
                               top_compounds=int(input.get("top", 15)))

    def _analyze_disease(self, input: dict) -> dict:
        disease = input.get("disease", "")
        if not disease:
            return {"error": "disease required (e.g. 'diabetes', 'alzheimer')"}
        from modules.netpharm import network_from_disease
        return network_from_disease(disease,
                                    limit=int(input.get("limit", 25)),
                                    custom_compounds=input.get("custom_compounds", None))
