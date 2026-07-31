"""Clinical Pharmacy API — thin wrapper around modules/clinical/.

All calculation logic lives in modules/clinical/. This handler only
handles HTTP/JSON concerns, KB storage, and action dispatch.
"""
from helpers.api import ApiHandler, Request
import logging

log = logging.getLogger("clinical")


def _kb_store(title, content, tags=None):
    """Store result to Knowledge Base (clinical category)."""
    try:
        from modules.knowledge.auto_store import auto_store
        auto_store("clinical", title, content, source="Clinical Pharmacy",
                   tags=tags or ["clinical"], category="clinical")
    except Exception:
        pass


class ClinicalHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "")
        result = None
        if action == "drug_interaction":
            result = self._drug_interaction(input)
        elif action == "tdm":
            result = self._tdm(input)
        elif action == "renal_adjust":
            result = self._renal_adjust(input)
        elif action == "hepatic_adjust":
            result = self._hepatic_adjust(input)
        elif action == "naranjo":
            result = self._naranjo(input)
        elif action == "ckd_epi":
            result = self._ckd_epi(input)
        elif action == "vancomycin_auc":
            result = self._vancomycin_auc(input)
        elif action == "beers_criteria":
            result = self._beers_criteria(input)
        elif action == "stopp_start":
            result = self._stopp_start(input)
        else:
            return {
                "actions": [
                    "drug_interaction", "tdm", "renal_adjust", "hepatic_adjust",
                    "naranjo", "ckd_epi", "vancomycin_auc", "beers_criteria", "stopp_start"
                ],
                "hint": "Clinical pharmacy tools: drug interactions, TDM, dose adjustment, ADR assessment, geriatric screening"
            }
        if result and not result.get("error"):
            _kb_store(f"Clinical — {action.replace('_', ' ').title()}", result, ["clinical", action])
        return result

    def _drug_interaction(self, input):
        from modules.clinical.drug_interactions import check_drug_interaction
        drug1 = input.get("drug1", "")
        drug2 = input.get("drug2", "")
        return check_drug_interaction(drug1, drug2)

    def _tdm(self, input):
        from modules.clinical.tdm import calculate_tdm
        # Accept both UI keys (interval_hr, half_life_hr, target_trough, measured_trough)
        # and API keys (interval_h, steady_state_peak, steady_state_trough)
        interval = input.get("interval_h") or input.get("interval_hr") or 12
        peak = input.get("steady_state_peak") or input.get("half_life_hr")
        trough = input.get("steady_state_trough") or input.get("measured_trough")
        return calculate_tdm(
            drug=input.get("drug", ""),
            dose_mg=input.get("dose_mg", 0),
            interval_h=float(interval),
            route=input.get("route", "iv"),
            infusion_time_h=input.get("infusion_time_h", 0),
            steady_state_peak=float(peak) if peak else None,
            steady_state_trough=float(trough) if trough else None,
            patient_weight_kg=input.get("patient_weight_kg", 70),
            renal_function=input.get("renal_function"),
        )

    def _renal_adjust(self, input):
        from modules.clinical.renal import calculate_renal_adjust
        # Accept both UI key (current_dose_mg) and API key (dose_mg)
        dose = input.get("dose_mg") or input.get("current_dose_mg")
        return calculate_renal_adjust(
            serum_creatinine_mg_dl=input.get("serum_creatinine_mg_dl", 1.0),
            age=input.get("age", 65),
            sex=input.get("sex", "male"),
            drug=input.get("drug"),
            dose_mg=float(dose) if dose else None,
        )

    def _hepatic_adjust(self, input):
        from modules.clinical.hepatic import calculate_hepatic_adjust
        return calculate_hepatic_adjust(
            bilirubin_mg_dl=input.get("bilirubin_mg_dl", 1.0),
            albumin_g_dl=input.get("albumin_g_dl", 4.0),
            inr=input.get("inr", 1.0),
            ascites=input.get("ascites", "none"),
            encephalopathy=input.get("encephalopathy", "none"),
            drug=input.get("drug"),
        )

    def _naranjo(self, input):
        from modules.clinical.adr import calculate_naranjo
        answers = input.get("answers", [])
        return calculate_naranjo(answers)

    def _ckd_epi(self, input):
        from modules.clinical.renal import calculate_ckd_epi
        return calculate_ckd_epi(
            serum_creatinine_mg_dl=input.get("serum_creatinine_mg_dl", 1.0),
            age=input.get("age", 65),
            sex=input.get("sex", "male"),
        )

    def _vancomycin_auc(self, input):
        from modules.clinical.vancomycin import calculate_vancomycin_auc
        return calculate_vancomycin_auc(
            trough_mg_l=input.get("trough_mg_l", 0),
            dose_mg=input.get("dose_mg", 0),
            interval_h=input.get("interval_h", 12),
            infusion_time_h=input.get("infusion_time_h", 1.0),
            patient_weight_kg=input.get("patient_weight_kg", 70),
            renal_function_ml_min=input.get("renal_function_ml_min"),
        )

    def _beers_criteria(self, input):
        from modules.clinical.geriatrics import screen_beers
        medications = input.get("medications", [])
        return screen_beers(medications)

    def _stopp_start(self, input):
        from modules.clinical.geriatrics import screen_stopp_start
        return screen_stopp_start(
            medications=input.get("medications", []),
            conditions=input.get("conditions", []),
        )
