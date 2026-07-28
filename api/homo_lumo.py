"""HOMO-LUMO API — frontier molecular orbital energies and chemical reactivity."""
from helpers.api import ApiHandler, Request
import logging

log = logging.getLogger("homo_lumo_api")


class HomoLumoHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "calculate")
        if action == "calculate":
            return self._calculate(input)
        if action == "batch":
            return self._batch(input)
        return {
            "actions": ["calculate", "batch"],
            "hint": "POST with action=calculate and smiles for single molecule, or action=batch with smiles_list"
        }

    def _calculate(self, input):
        smiles = input.get("smiles", "").strip()
        name = input.get("name", "Molecule")
        if not smiles:
            return {"error": "smiles is required"}

        try:
            from modules.molecular.homo_lumo import calculate_homo_lumo
            result = calculate_homo_lumo(smiles, name)

            if result.get("success"):
                try:
                    from modules.knowledge.auto_store import auto_store
                    auto_store("homo_lumo", f"HOMO-LUMO: {name}", result,
                               source="HOMO-LUMO Calculator",
                               tags=["molecular", "homo_lumo", "quantum", smiles[:20]])
                except Exception:
                    pass

            return result
        except Exception as e:
            return {"error": str(e)}

    def _batch(self, input):
        smiles_list = input.get("smiles_list", [])
        names = input.get("names", [])
        if not smiles_list:
            return {"error": "smiles_list is required"}

        try:
            from modules.molecular.homo_lumo import batch_homo_lumo
            result = batch_homo_lumo(smiles_list, names)

            if result.get("success"):
                try:
                    from modules.knowledge.auto_store import auto_store
                    auto_store("homo_lumo", f"Batch HOMO-LUMO: {len(smiles_list)} molecules",
                               result.get("summary", {}),
                               source="HOMO-LUMO Batch",
                               tags=["molecular", "homo_lumo", "batch"])
                except Exception:
                    pass

            return result
        except Exception as e:
            return {"error": str(e)}
