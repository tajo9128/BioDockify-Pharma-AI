"""Phytochemistry Deep-Dive API — additive module (Pharmacognosy department)."""
from helpers.api import ApiHandler, Request, Response
import logging

log = logging.getLogger("phytochem")


class PhytochemHandler(ApiHandler):

    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "")
        if action == "fingerprint":
            return self._fingerprint(input)
        elif action == "assay":
            return self._assay(input)
        elif action == "check_limit":
            return self._check_limit(input)
        elif action == "limits_reference":
            from modules.phytochem import limits_reference
            return {"success": True, **limits_reference()}
        elif action == "plants":
            from modules.phytochem import search_plants
            return {"success": True, **search_plants(str(input.get("query", "")))}

        return {"actions": ["fingerprint", "assay", "check_limit", "limits_reference", "plants"],
                "hint": "Phytochemistry — fingerprint similarity, marker assay w/ LOD-LOQ, "
                        "heavy-metal & aflatoxin limits, ethnobotany database."}

    @staticmethod
    def _fingerprint(input: dict) -> dict:
        from modules.phytochem import fingerprint_similarity
        r = fingerprint_similarity(input.get("profile_a") or [], input.get("profile_b") or [])
        return {"success": "error" not in r, **r}

    @staticmethod
    def _assay(input: dict) -> dict:
        from modules.phytochem import marker_assay
        r = marker_assay(input.get("calibration_conc") or [], input.get("calibration_area") or [],
                         float(input.get("sample_area", 0) or 0),
                         float(input.get("sample_weight_mg", 0) or 0),
                         float(input.get("dilution", 1) or 1),
                         float(input.get("volume_ml", 10) or 10))
        return {"success": "error" not in r, **r}

    @staticmethod
    def _check_limit(input: dict) -> dict:
        from modules.phytochem import check_limits
        try:
            value = float(input.get("value", 0))
        except (TypeError, ValueError):
            return {"error": "value must be numeric"}
        return {"success": True, **check_limits(str(input.get("analyte", "")), value,
                                                str(input.get("standard", "WHO/API herbal")))}
