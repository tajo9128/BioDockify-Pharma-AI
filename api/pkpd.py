"""PK/PD Dashboard API — wraps existing pkpd_analysis module."""
from helpers.api import ApiHandler, Request, Response
import logging, os, json, uuid

log = logging.getLogger("pkpd")
_temp_data = {}

class PKPD(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "")
        if action == "nca":         return self._run_pkpd("non_compartmental_analysis", input)
        if action == "auc":         return self._run_pkpd("calculate_auc", input)
        if action == "cmax_tmax":   return self._run_pkpd("calculate_cmax_tmax", input)
        if action == "half_life":   return self._run_pkpd("estimate_half_life", input)
        if action == "clearance":   return self._run_pkpd("calculate_clearance", input)
        if action == "bioavail":    return self._run_pkpd("calculate_bioavailability", input)
        if action == "pd_response": return self._run_pkpd("model_pd_response", input)
        if action == "compartmental": return self._run_pkpd("fit_compartmental_model", input)
        if action == "summary":     return self._run_pkpd("calculate_pk_summary", input)
        if action == "health":      return self._health()
        return {"actions": ["nca","auc","cmax_tmax","half_life","clearance","bioavail","pd_response","compartmental","summary","health"]}

    def _health(self):
        try:
            from modules.statistics.pkpd_analysis import PKPDAnalysis
            return {"status": "ok", "pkpd": True}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _run_pkpd(self, method: str, input: dict):
        try:
            from modules.statistics.pkpd_analysis import PKPDAnalysis
            pk = PKPDAnalysis(alpha=float(input.get("alpha", 0.05)))
            time_col = input.get("time_col", "Time_h")
            conc_col = input.get("conc_col", "Concentration_ng_ml")
            dose_col = input.get("dose_col", "Dose_mg")

            if method == "non_compartmental_analysis":
                r = pk.non_compartmental_analysis(time_col, conc_col)
            elif method == "calculate_auc":
                r = pk.calculate_auc(time_col, conc_col)
            elif method == "calculate_cmax_tmax":
                r = pk.calculate_cmax_tmax(time_col, conc_col)
            elif method == "estimate_half_life":
                r = pk.estimate_half_life(time_col, conc_col)
            elif method == "calculate_clearance":
                r = pk.calculate_clearance(time_col, conc_col, dose_col)
            elif method == "calculate_bioavailability":
                r = pk.calculate_bioavailability(time_col, conc_col, dose_col,
                    input.get("ref_time_col", time_col), input.get("ref_conc_col", conc_col))
            elif method == "model_pd_response":
                r = pk.model_pd_response(input.get("dose_col", "Dose_mg"), input.get("response_col", "Effect_Pct"))
            elif method == "fit_compartmental_model":
                r = pk.fit_compartmental_model(time_col, conc_col,
                    dose=float(input.get("dose", 1)), compartments=int(input.get("compartments", 2)))
            elif method == "calculate_pk_summary":
                r = pk.calculate_pk_summary(input.get("data", {}))
            else:
                return {"status": "error", "error": f"Unknown method: {method}"}

            return {"status": "ok", "method": method, "results": self._safe(r)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _safe(self, obj):
        if isinstance(obj, dict): return {k: self._safe(v) for k, v in obj.items()}
        if isinstance(obj, list): return [self._safe(v) for v in obj]
        if hasattr(obj, "item"): return obj.item()
        if isinstance(obj, float): return round(obj, 4)
        return obj
