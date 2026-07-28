"""Interactive Molecular Plots API — Plotly dashboards for molecular properties."""
from helpers.api import ApiHandler, Request
import logging

log = logging.getLogger("mol_plots_api")


class MolPlotsHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "generate")
        if action == "generate":
            return self._generate(input)
        return {
            "actions": ["generate"],
            "hint": "POST with action=generate, smiles_list (list), names (optional list)"
        }

    def _generate(self, input):
        smiles_list = input.get("smiles_list", [])
        names = input.get("names", [])
        if not smiles_list:
            return {"error": "smiles_list is required"}

        try:
            from modules.molecular.interactive_plots import generate_interactive_plots
            result = generate_interactive_plots(smiles_list, names)

            if result.get("success"):
                try:
                    from modules.knowledge.auto_store import auto_store
                    auto_store("mol_plots", f"Interactive Plots: {len(smiles_list)} molecules",
                               {"n_molecules": len(smiles_list)},
                               source="Interactive Molecular Plots",
                               tags=["molecular", "plots", "interactive"])
                except Exception:
                    pass

            return result
        except Exception as e:
            return {"error": str(e)}
