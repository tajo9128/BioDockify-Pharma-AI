"""Bioactivity Predictor API — predict IC50/pIC50, find similar actives, activity cliffs."""
from helpers.api import ApiHandler, Request, Response
import logging

log = logging.getLogger("api.bioactivity_predictor")


class BioactivityPredictorHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "")

        if action == "predict":
            return self._predict(input)
        elif action == "batch_predict":
            return self._batch_predict(input)
        elif action == "target_classes":
            return self._target_classes()
        elif action == "similar":
            return self._similar(input)
        elif action == "activity_cliffs":
            return self._activity_cliffs(input)
        else:
            return {
                "actions": ["predict", "batch_predict", "target_classes", "similar", "activity_cliffs"],
                "hint": "Bioactivity prediction: IC50/pIC50 from structure, similarity search, SAR analysis",
            }

    def _predict(self, input: dict) -> dict:
        smiles = input.get("smiles", "")
        target_class = input.get("target_class", "general")

        if not smiles:
            return {"error": "smiles required"}

        from modules.bioactivity_predictor import predict_ic50
        return predict_ic50(smiles, target_class)

    def _batch_predict(self, input: dict) -> dict:
        smiles_list = input.get("smiles_list", [])
        target_class = input.get("target_class", "general")

        if not smiles_list:
            return {"error": "smiles_list required (array of SMILES strings)"}

        from modules.bioactivity_predictor import predict_bioactivity
        return predict_bioactivity(smiles_list, target_class)

    def _target_classes(self) -> dict:
        from modules.bioactivity_predictor import get_target_classes
        return {"target_classes": get_target_classes()}

    def _similar(self, input: dict) -> dict:
        smiles = input.get("smiles", "")
        target_class = input.get("target_class", "general")
        threshold = input.get("threshold", 0.3)

        if not smiles:
            return {"error": "smiles required"}

        from modules.bioactivity_predictor import find_similar_actives
        return find_similar_actives(smiles, target_class, threshold)

    def _activity_cliffs(self, input: dict) -> dict:
        smiles_list = input.get("smiles_list", [])
        activities = input.get("activities", [])

        if not smiles_list or not activities:
            return {"error": "smiles_list and activities (pIC50 values) required"}

        from modules.bioactivity_predictor.similarity import activity_cliff_analysis
        return activity_cliff_analysis(smiles_list, activities)
