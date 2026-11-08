"""P3 Features API — pharmacophore export, fed-batch, phytochem user DB,
RIS/BibTeX export, Holm correction, pediatric dosing, BCPNN, FAERS parser.

Additive module — surfaces all P3 features from modules/writing/p3_features.py.
"""
from helpers.api import ApiHandler, Request, Response
import logging
import re

log = logging.getLogger("p3_features")


class P3FeaturesHandler(ApiHandler):

    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "")

        if action == "pharm_export":
            return self._pharm_export(input)
        elif action == "fedbatch":
            return self._fedbatch(input)
        elif action == "add_plant":
            return self._add_plant(input)
        elif action == "list_user_plants":
            from modules.writing.p3_features import list_user_plants
            return {"success": True, **list_user_plants()}
        elif action == "export_ris":
            return self._export_ris(input)
        elif action == "export_bibtex":
            return self._export_bibtex(input)
        elif action == "holm":
            return self._holm(input)
        elif action == "pediatric_dose":
            return self._pediatric(input)
        elif action == "bcpnn":
            return self._bcpnn(input)
        elif action == "parse_faers":
            return self._parse_faers(input)

        return {"actions": ["pharm_export", "fedbatch", "add_plant", "list_user_plants",
                            "export_ris", "export_bibtex", "holm", "pediatric_dose",
                            "bcpnn", "parse_faers"],
                "hint": "P3 Features — pharmacophore export, fed-batch simulation, plant DB, "
                        "RIS/BibTeX export, Holm correction, pediatric dosing, BCPNN, FAERS parser."}

    @staticmethod
    def _num(input, k, d=0.0):
        try:
            return float(input.get(k, d) or d)
        except (TypeError, ValueError):
            return d

    def _pharm_export(self, input: dict) -> dict:
        from modules.writing.p3_features import export_pharmacophore
        features = input.get("features") or []
        if not features:
            return {"error": "provide features: [{type, x, y, z, radius}]"}
        return {"success": True, **export_pharmacophore(features, str(input.get("format", "json")))}

    def _fedbatch(self, input: dict) -> dict:
        from modules.writing.p3_features import fedbatch_simulation
        r = fedbatch_simulation(self._num(input, "mu_max"), self._num(input, "ks"),
                                self._num(input, "s0"), self._num(input, "yxs"),
                                self._num(input, "feed_rate", 0.5), self._num(input, "feed_conc", 100.0),
                                int(self._num(input, "hours", 30) or 30), self._num(input, "x0", 0.5))
        return {"success": "error" not in r, **r}

    @staticmethod
    def _add_plant(input: dict) -> dict:
        from modules.writing.p3_features import add_plant
        if not str(input.get("name", "")).strip():
            return {"error": "plant name required"}
        return add_plant(input)

    def _export_ris(self, input: dict) -> dict:
        from modules.writing.p3_features import export_ris
        papers = input.get("papers") or []
        if not papers:
            return {"error": "provide papers array"}
        return {"success": True, **export_ris(papers)}

    def _export_bibtex(self, input: dict) -> dict:
        from modules.writing.p3_features import export_bibtex
        papers = input.get("papers") or []
        if not papers:
            return {"error": "provide papers array"}
        return {"success": True, **export_bibtex(papers)}

    def _holm(self, input: dict) -> dict:
        from modules.writing.p3_features import holm_bonferroni
        p_values = input.get("p_values") or []
        if isinstance(p_values, str):
            p_values = [float(p.strip()) for p in p_values.split(",") if p.strip()]
        if not p_values:
            return {"error": "provide p_values: [0.01, 0.04, ...]"}
        return {"success": True, **holm_bonferroni(p_values, self._num(input, "alpha", 0.05) or 0.05)}

    def _pediatric(self, input: dict) -> dict:
        from modules.writing.p3_features import pediatric_dose
        drug = str(input.get("drug", "")).strip()
        if not drug:
            return {"error": "drug name required"}
        return {"success": True, **pediatric_dose(drug, self._num(input, "weight_kg"),
                                                   int(self._num(input, "age_months", 0) or 0) or None)}

    def _bcpnn(self, input: dict) -> dict:
        from modules.writing.p3_features import bcpnn_signal
        try:
            a = int(input.get("a", 0))
            b = int(input.get("b", 0))
            c = int(input.get("c", 0))
            d = int(input.get("d", 0))
        except (TypeError, ValueError):
            return {"error": "a, b, c, d must be integers"}
        return {"success": True, **bcpnn_signal(a, b, c, d)}

    def _parse_faers(self, input: dict) -> dict:
        from modules.writing.p3_features import parse_faers_csv
        text = str(input.get("csv", ""))
        if not text.strip():
            return {"error": "provide FAERS CSV data"}
        r = parse_faers_csv(text)
        return {"success": "error" not in r, **r}
