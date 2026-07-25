"""
Pharma Utilities API — Shared calculations across departments.

Provides: f2/f1 dissolution, Cheng-Prusoff, AUC-vancomycin, SST,
content uniformity, Beers Criteria, DOE, Chou-Talalay, SAR table.
"""

from helpers.api import ApiHandler, Request
import logging

log = logging.getLogger("pharma_utils")


class PharmaUtilsHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "")
        if action == "dissolution_f2":
            return self._dissolution_f2(input)
        if action == "cheng_prusoff":
            return self._cheng_prusoff(input)
        if action == "auc_vancomycin":
            return self._auc_vancomycin(input)
        if action == "system_suitability":
            return self._system_suitability(input)
        if action == "content_uniformity":
            return self._content_uniformity(input)
        if action == "beers_criteria":
            return self._beers_criteria(input)
        if action == "doe_design":
            return self._doe_design(input)
        if action == "combination_index":
            return self._combination_index(input)
        if action == "sar_table":
            return self._sar_table(input)
        return {
            "status": "error",
            "error": f"Unknown action: {action}",
            "actions": [
                "dissolution_f2", "cheng_prusoff", "auc_vancomycin",
                "system_suitability", "content_uniformity", "beers_criteria",
                "doe_design", "combination_index", "sar_table"
            ]
        }

    def _dissolution_f2(self, input: dict) -> dict:
        from modules.pharma_utils.dissolution import calculate_f2, calculate_f1
        test = input.get("test", [])
        ref = input.get("reference", [])
        if not test or not ref:
            return {"status": "error", "error": "Provide test and reference dissolution data"}
        result = calculate_f2(test, ref)
        return {"status": "ok", **result}

    def _cheng_prusoff(self, input: dict) -> dict:
        from modules.pharma_utils.pk_calculations import cheng_prusoff
        ic50 = input.get("ic50", 0)
        km = input.get("km", 0)
        s = input.get("substrate_conc", 0)
        if ic50 <= 0 or km <= 0:
            return {"status": "error", "error": "Provide ic50 (nM) and km (nM)"}
        result = cheng_prusoff(ic50, km, s)
        return {"status": "ok", **result}

    def _auc_vancomycin(self, input: dict) -> dict:
        from modules.pharma_utils.pk_calculations import auc_guided_vancomycin
        result = auc_guided_vancomycin(
            target_auc=input.get("target_auc", 400),
            mic=input.get("mic", 1.0),
            patient_weight_kg=input.get("weight", 70),
            current_dose_mg=input.get("current_dose", 1000),
            current_auc=input.get("current_auc", 300),
            current_interval_h=input.get("interval", 12),
        )
        return {"status": "ok", **result}

    def _system_suitability(self, input: dict) -> dict:
        from modules.pharma_utils.quality_control import system_suitability
        result = system_suitability(
            retention_times=input.get("retention_times", []),
            peak_areas=input.get("peak_areas", []),
            theoretical_plates=input.get("theoretical_plates"),
            tailing_factors=input.get("tailing_factors"),
            reference_rt=input.get("reference_rt"),
        )
        return {"status": "ok", **result}

    def _content_uniformity(self, input: dict) -> dict:
        from modules.pharma_utils.quality_control import content_uniformity
        result = content_uniformity(
            assay_values=input.get("assay_values", []),
            target_mg=input.get("target_mg", 0),
            method=input.get("method", "acceptance_value"),
        )
        return {"status": "ok", **result}

    def _beers_criteria(self, input: dict) -> dict:
        from modules.pharma_utils.clinical_tools import beers_criteria_screen
        medications = input.get("medications", [])
        if not medications:
            return {"status": "error", "error": "Provide list of medications"}
        result = beers_criteria_screen(medications)
        return {"status": "ok", **result}

    def _doe_design(self, input: dict) -> dict:
        from modules.pharma_utils.experimental_design import full_factorial, fractional_factorial, taguchi_design
        design_type = input.get("type", "full_factorial")
        factors = input.get("factors", [])
        
        if design_type == "full_factorial":
            if not factors:
                return {"status": "error", "error": "Provide factors list with name and levels"}
            result = full_factorial(factors)
        elif design_type == "fractional":
            n_factors = input.get("n_factors", 4)
            result = fractional_factorial(n_factors)
        elif design_type == "taguchi":
            n_factors = input.get("n_factors", 4)
            levels = input.get("levels", 2)
            result = taguchi_design(n_factors, levels)
        else:
            return {"status": "error", "error": f"Unknown design type: {design_type}. Use full_factorial, fractional, or taguchi"}
        return {"status": "ok", **result}

    def _combination_index(self, input: dict) -> dict:
        from modules.pharma_utils.synergy_analysis import chou_talalay_index
        result = chou_talalay_index(
            drug1_alone=input.get("drug1_alone", []),
            drug2_alone=input.get("drug2_alone", []),
            combination=input.get("combination", []),
            drug1_name=input.get("drug1_name", "Drug A"),
            drug2_name=input.get("drug2_name", "Drug B"),
        )
        return {"status": "ok", **result}

    def _sar_table(self, input: dict) -> dict:
        from modules.pharma_utils.sar_analysis import generate_sar_table
        compounds = input.get("compounds", [])
        if not compounds:
            return {"status": "error", "error": "Provide compounds list with activity data"}
        result = generate_sar_table(
            compounds=compounds,
            activity_col=input.get("activity_col", "IC50_nM"),
            structure_col=input.get("structure_col", "SMILES"),
            name_col=input.get("name_col", "Name"),
        )
        return {"status": "ok", **result}
