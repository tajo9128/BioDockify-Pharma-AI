from helpers.api import ApiHandler, Request, Response
import json
from helpers import files


class DrugBrowser(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        query = input.get("query", "").strip().lower()
        system = input.get("system", "").strip().lower()
        action = input.get("action", "search")

        # Load drug database
        drugs_path = files.get_abs_path("webui/components/drug-browser/drugs.json")
        try:
            with open(drugs_path) as f:
                all_drugs = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"drugs": [], "systems": [], "error": "Drug database not found"}

        # Get available systems
        systems = sorted(set(
            d.get("system", "") for d in all_drugs if d.get("system")
        ))

        if action == "systems":
            return {"systems": systems}

        if action == "detail":
            drug_id = input.get("id", "")
            drug = next((d for d in all_drugs if d.get("id") == drug_id), None)
            if drug:
                # Compute properties on the fly
                smiles = drug.get("smiles", "")
                properties = {}
                if smiles:
                    try:
                        from rdkit import Chem
                        from rdkit.Chem import Descriptors, Crippen
                        mol = Chem.MolFromSmiles(smiles)
                        if mol:
                            properties = {
                                "mw": round(Descriptors.MolWt(mol), 2),
                                "logp": round(Crippen.MolLogP(mol), 2),
                                "formula": Chem.rdMolDescriptors.CalcMolFormula(mol),
                            }
                    except ImportError:
                        pass
                return {"drug": drug, "properties": properties}

        # Search/filter
        results = all_drugs
        if system:
            results = [d for d in results if d.get("system", "").lower() == system]
        if query:
            results = [
                d for d in results
                if query in d.get("name", "").lower()
                or query in d.get("generic_name", "").lower()
                or query in d.get("mechanism", "").lower()
                or query in d.get("class_name", "").lower()
            ]

        return {"drugs": results[:50], "systems": systems, "total": len(results)}
