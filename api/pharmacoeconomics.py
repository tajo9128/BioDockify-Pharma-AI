"""Pharmacoeconomics Mini-Lab API — additive module (Pharmacy Practice)."""
from helpers.api import ApiHandler, Request, Response
import logging

log = logging.getLogger("pharmacoeconomics")


class PharmacoeconomicsHandler(ApiHandler):

    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "")
        if action == "cea":
            return self._cea(input)
        elif action == "qaly":
            return self._qaly(input)
        elif action == "nnt":
            return self._nnt(input)
        elif action == "budget":
            return self._budget(input)
        elif action == "sensitivity":
            return self._sensitivity(input)

        return {"actions": ["cea", "qaly", "nnt", "budget", "sensitivity"],
                "hint": "Pharmacoeconomics — ICER/CEA, QALYs, NNT+cost/responder, budget impact, sensitivity grids."}

    @staticmethod
    def _n(input, k, d=0.0):
        try:
            return float(input.get(k, d) or d)
        except (TypeError, ValueError):
            return d

    def _cea(self, input: dict) -> dict:
        from modules.pharmacoeconomics import cost_effectiveness
        r = cost_effectiveness(self._n(input, "cost_new"), self._n(input, "cost_comparator"),
                               self._n(input, "effect_new"), self._n(input, "effect_comparator"),
                               self._n(input, "wtp_threshold", 100000.0) or 100000.0)
        return {"success": "error" not in r, **r}

    def _qaly(self, input: dict) -> dict:
        from modules.pharmacoeconomics import qaly_calc
        r = qaly_calc(self._n(input, "utility_before"), self._n(input, "utility_after"),
                      self._n(input, "years", 1), self._n(input, "discount", 0.03) or 0.03)
        return {"success": "error" not in r, **r}

    def _nnt(self, input: dict) -> dict:
        from modules.pharmacoeconomics import nnt_cost
        r = nnt_cost(self._n(input, "arr_control"), self._n(input, "arr_treatment"),
                     self._n(input, "cost_per_patient_treatment"), self._n(input, "cost_per_patient_control"))
        return {"success": "error" not in r, **r}

    def _budget(self, input: dict) -> dict:
        from modules.pharmacoeconomics import budget_impact
        r = budget_impact(int(self._n(input, "population")),
                          self._n(input, "patients_diagnosed_pct", 100) or 100,
                          self._n(input, "treated_pct_current"), self._n(input, "treated_pct_new"),
                          self._n(input, "cost_per_patient_current"), self._n(input, "cost_per_patient_new"),
                          int(self._n(input, "years", 1) or 1))
        return {"success": "error" not in r, **r}

    def _sensitivity(self, input: dict) -> dict:
        from modules.pharmacoeconomics import sensitivity
        r = sensitivity(self._n(input, "cost_new"), self._n(input, "cost_comparator"),
                        self._n(input, "effect_new"), self._n(input, "effect_comparator"),
                        self._n(input, "wtp_low"), self._n(input, "wtp_high", 200000) or 200000)
        return {"success": "error" not in r, **r}
