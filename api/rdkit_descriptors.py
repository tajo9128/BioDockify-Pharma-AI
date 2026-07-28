"""Comprehensive RDKit Descriptor Calculator — 200+ molecular descriptors."""
from helpers.api import ApiHandler, Request
import logging

log = logging.getLogger("rdkit_descriptors_api")


class RdkitDescriptorsHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "calculate")
        if action == "calculate":
            return self._calculate(input)
        if action == "batch":
            return self._batch(input)
        if action == "summary":
            return self._summary(input)
        if action == "categories":
            return self._categories()
        return {
            "actions": ["calculate", "batch", "summary", "categories"],
            "hint": "POST with action=calculate and smiles, or batch with smiles_list"
        }

    def _calculate(self, input):
        smiles = input.get("smiles", "").strip()
        categories = input.get("categories", None)
        if not smiles:
            return {"error": "smiles is required"}
        try:
            from rdkit import Chem
            from modules.molecular.rdkit_descriptors import calculate_all_descriptors
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return {"error": "Invalid SMILES"}
            result = calculate_all_descriptors(mol, categories)
            result["smiles"] = smiles
            result["success"] = True
            return result
        except Exception as e:
            return {"error": str(e)}

    def _batch(self, input):
        smiles_list = input.get("smiles_list", [])
        categories = input.get("categories", None)
        names = input.get("names", [])
        if not smiles_list:
            return {"error": "smiles_list is required"}
        try:
            from modules.molecular.rdkit_descriptors import calculate_batch
            result = calculate_batch(smiles_list, categories, names)
            if "error" in result:
                return result
            # Convert numpy array to list for JSON
            result["descriptor_matrix"] = result["descriptor_matrix"].tolist()
            result["success"] = True
            return result
        except Exception as e:
            return {"error": str(e)}

    def _summary(self, input):
        smiles_list = input.get("smiles_list", [])
        categories = input.get("categories", None)
        if not smiles_list:
            return {"error": "smiles_list is required"}
        try:
            from modules.molecular.rdkit_descriptors import get_descriptor_summary
            result = get_descriptor_summary(smiles_list, categories)
            result["success"] = True
            return result
        except Exception as e:
            return {"error": str(e)}

    def _categories(self):
        from modules.molecular.rdkit_descriptors import (
            BASIC_DESCRIPTORS, TOPOLOGICAL_DESCRIPTORS, ELECTRONIC_DESCRIPTORS,
            SURFACE_DESCRIPTORS, BCUT_DESCRIPTORS, AUTOCORR_DESCRIPTORS, FRAGMENT_DESCRIPTORS
        )
        return {
            "success": True,
            "categories": {
                "basic": {"count": len(BASIC_DESCRIPTORS), "descriptors": BASIC_DESCRIPTORS},
                "topological": {"count": len(TOPOLOGICAL_DESCRIPTORS), "descriptors": TOPOLOGICAL_DESCRIPTORS},
                "electronic": {"count": len(ELECTRONIC_DESCRIPTORS), "descriptors": ELECTRONIC_DESCRIPTORS},
                "surface": {"count": len(SURFACE_DESCRIPTORS), "descriptors": SURFACE_DESCRIPTORS},
                "bcut": {"count": len(BCUT_DESCRIPTORS), "descriptors": BCUT_DESCRIPTORS},
                "autocorr": {"count": len(AUTOCORR_DESCRIPTORS), "descriptors": AUTOCORR_DESCRIPTORS},
                "fragment": {"count": len(FRAGMENT_DESCRIPTORS), "descriptors": FRAGMENT_DESCRIPTORS},
            },
            "total_descriptors": sum(len(d) for d in [
                BASIC_DESCRIPTORS, TOPOLOGICAL_DESCRIPTORS, ELECTRONIC_DESCRIPTORS,
                SURFACE_DESCRIPTORS, BCUT_DESCRIPTORS, AUTOCORR_DESCRIPTORS, FRAGMENT_DESCRIPTORS
            ]) + 7,  # +7 for drug-likeness
        }
