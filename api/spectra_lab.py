"""Spectra & Elucidation Lab API — additive module (Analysis + Pharmacognosy)."""
from helpers.api import ApiHandler, Request, Response
import logging

log = logging.getLogger("spectra_lab")


class SpectraLabHandler(ApiHandler):

    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "")
        if action == "ir_match":
            return self._ir_match(input)
        elif action == "nmr_estimate":
            return self._nmr_estimate(input)
        elif action == "multiplets":
            return self._multiplets(input)
        elif action == "ms_fragments":
            return self._ms_fragments(input)
        elif action == "uv_rules":
            return self._uv(input)

        return {"actions": ["ir_match", "nmr_estimate", "multiplets", "ms_fragments", "uv_rules"],
                "hint": "Spectra Lab — IR matcher, NMR estimate + multiplet analyzer, MS fragment predictor, UV rules."}

    @staticmethod
    def _ir_match(input: dict) -> dict:
        from modules.spectra_lab import match_ir
        peaks = input.get("peaks") or []
        if not peaks:
            return {"error": "provide peaks: [{wavenumber, note?}]"}
        return {"success": True, **match_ir(peaks)}

    @staticmethod
    def _nmr_estimate(input: dict) -> dict:
        from modules.spectra_lab import estimate_nmr
        return {"success": True, **estimate_nmr(str(input.get("smiles", "")))}

    @staticmethod
    def _multiplets(input: dict) -> dict:
        from modules.spectra_lab import analyze_multiplets
        peaks = input.get("peaks") or []
        if not peaks:
            return {"error": "provide peaks: [{shift, multiplicity, integration?, j_hz?}]"}
        return {"success": True, **analyze_multiplets(peaks)}

    @staticmethod
    def _ms_fragments(input: dict) -> dict:
        from modules.spectra_lab import predict_fragments
        return {"success": True, **predict_fragments(str(input.get("smiles", "")),
                                                     str(input.get("ionization", "ESI+")))}

    @staticmethod
    def _uv(input: dict) -> dict:
        from modules.spectra_lab import uv_rules
        return {"success": True, **uv_rules(str(input.get("smiles", "")))}
