"""Retrosynthesis Planning API — plan routes, analyze disconnections, estimate complexity."""
from helpers.api import ApiHandler, Request, Response
import logging

log = logging.getLogger("api.retrosynthesis")


class RetrosynthesisHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "")

        if action == "plan":
            return self._plan(input)
        elif action == "disconnect":
            return self._disconnect(input)
        elif action == "complexity":
            return self._complexity(input)
        elif action == "building_blocks":
            return self._building_blocks(input)
        elif action == "templates":
            return self._templates()
        else:
            return {
                "actions": ["plan", "disconnect", "complexity", "building_blocks", "templates"],
                "hint": "Retrosynthesis: plan routes, analyze disconnections, estimate complexity, find building blocks",
            }

    def _plan(self, input: dict) -> dict:
        smiles = input.get("smiles", "")
        max_depth = input.get("max_depth", 4)
        max_routes = input.get("max_routes", 5)

        if not smiles:
            return {"error": "smiles required"}

        from modules.retrosynthesis import plan_synthesis
        result = plan_synthesis(smiles, max_depth=max_depth, max_routes=max_routes)
        return result

    def _disconnect(self, input: dict) -> dict:
        smiles = input.get("smiles", "")
        if not smiles:
            return {"error": "smiles required"}

        from modules.retrosynthesis import disconnection_analysis
        result = disconnection_analysis(smiles)
        return result

    def _complexity(self, input: dict) -> dict:
        smiles = input.get("smiles", "")
        if not smiles:
            return {"error": "smiles required"}

        from modules.retrosynthesis.routes import estimate_complexity
        result = estimate_complexity(smiles)
        return result

    def _building_blocks(self, input: dict) -> dict:
        smiles = input.get("smiles", "")
        if not smiles:
            return {"error": "smiles required"}

        from modules.retrosynthesis import find_building_blocks
        return find_building_blocks(smiles)

    def _templates(self) -> dict:
        from modules.retrosynthesis import get_reaction_templates
        templates = get_reaction_templates()
        return {"templates": templates, "count": len(templates)}
