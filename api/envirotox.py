"""EnviroTox API — environmental fate & ecotoxicity screening (BCF, Koc, LC50,
biodegradability, PBT/vPvB, batch)."""
from helpers.api import ApiHandler, Request, Response
import logging

log = logging.getLogger("api.envirotox")


class EnviroToxHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "")

        if action == "assess":
            smiles = input.get("smiles", "")
            if not smiles:
                return {"error": "smiles required"}
            from modules.envirotox import assess
            return assess(smiles)
        elif action == "batch":
            smiles_list = input.get("smiles_list", [])
            if not smiles_list:
                return {"error": "smiles_list required"}
            from modules.envirotox import batch
            return batch(smiles_list)
        else:
            return {
                "actions": ["assess", "batch"],
                "hint": "EnviroTox: BCF, Koc, fish LC50, biodegradability, PBT/vPvB screening (QSAR estimates)",
            }
