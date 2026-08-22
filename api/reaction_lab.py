"""Reaction Lab API — forward reactions, combinatorial enumeration, atom mapping,
impurity/degradation prediction, condition recommendation."""
from helpers.api import ApiHandler, Request, Response
import logging

log = logging.getLogger("api.reaction_lab")


class ReactionLabHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "")

        if action == "reactions":
            from modules.reaction_lab import list_reactions
            rxns = list_reactions()
            return {"reactions": rxns, "count": len(rxns)}
        elif action == "forward":
            return self._forward(input)
        elif action == "enumerate":
            return self._enumerate(input)
        elif action == "atom_map":
            return self._atom_map(input)
        elif action == "impurities":
            return self._impurities(input)
        elif action == "conditions":
            return self._conditions(input)
        else:
            return {
                "actions": ["reactions", "forward", "enumerate", "atom_map", "impurities", "conditions"],
                "hint": "Reaction Lab: forward reactions, library enumeration, atom mapping, impurity prediction, condition recommendation",
            }

    def _forward(self, input: dict) -> dict:
        reaction = input.get("reaction", "")
        smarts = input.get("reaction_smarts", "")
        reactants = input.get("reactants", [])
        if not reactants:
            return {"error": "reactants required (list of SMILES)"}
        from modules.reaction_lab import run_forward, run_smarts
        if smarts:
            return run_smarts(smarts, reactants)
        if not reaction:
            return {"error": "reaction name or reaction_smarts required"}
        return run_forward(reaction, reactants)

    def _enumerate(self, input: dict) -> dict:
        reaction = input.get("reaction", "")
        blocks = input.get("building_block_sets", [])
        if not reaction or not blocks:
            return {"error": "reaction and building_block_sets required"}
        from modules.reaction_lab import enumerate_library
        return enumerate_library(reaction, blocks, max_products=int(input.get("max_products", 200)))

    def _atom_map(self, input: dict) -> dict:
        reactants = input.get("reactants", [])
        product = input.get("product", "")
        from modules.reaction_lab import map_reaction
        return map_reaction(reactants, product)

    def _impurities(self, input: dict) -> dict:
        smiles = input.get("smiles", "")
        if not smiles:
            return {"error": "smiles required"}
        from modules.reaction_lab import predict_impurities
        return predict_impurities(smiles, conditions=input.get("conditions", None))

    def _conditions(self, input: dict) -> dict:
        reactants = input.get("reactants", input.get("reactant_smiles", []))
        from modules.reaction_lab import recommend_conditions
        return recommend_conditions(reactants)
