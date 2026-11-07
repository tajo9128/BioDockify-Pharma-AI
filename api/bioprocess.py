"""Bioprocess & Protein Studio API — additive module (Biotechnology department)."""
from helpers.api import ApiHandler, Request, Response
import logging

log = logging.getLogger("bioprocess")

BIOSIMILAR_CHECKLIST = {
    "sections": [
        {"section": "1. Quality target product profile (QTPP)", "items": [
            "Reference product identified (INN, strength, route)",
            "Critical quality attributes (CQAs) listed with rationale",
            "Potency units aligned with reference"]},
        {"section": "2. Analytical similarity — structural (ICH Q5E)", "items": [
            "Primary structure (intact mass, peptide mapping, MS/MS)",
            "Higher-order structure (HDX-MS, NMR, CD, DSC)",
            "Glycosylation profile (glycan map, sialylation, fucosylation)",
            "Disulfide mapping and free thiols",
            "Charge variants (CEX/iCIEF, C-terminal lysine)"]},
        {"section": "3. Analytical similarity — functional", "items": [
            "Bioassay potency vs reference (parallel-line or 4PL)",
            "Binding assays (SPR/BLI affinity, kinetics)",
            "Fc function if mAb (ADCC, CDC, FcγR binding)",
            "Forced degradation comparability"]},
        {"section": "4. Manufacturing & control", "items": [
            "Cell bank characterization & genetic stability",
            "Process comparability (scale-down models)",
            "Impurity profile (HCP, DNA, process-related)",
            "Specification justification (reference lots ≥ 10)"]},
        {"section": "5. Non-clinical & clinical (CDSCO/EMA/FDA pathways)", "items": [
            "Comparative PK (half-life, clearance)",
            "Comparative PD marker",
            "Confirmatory efficacy/safety study (or waiver rationale)"]},
    ],
    "reference": "WHO TRS 1004; EMA biosimilar guideline; FDA Scientific Considerations (2015); CDSCO Biosimilar Guidelines 2016",
}


class BioprocessHandler(ApiHandler):

    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "")
        if action == "protein":
            return self._protein(input)
        elif action == "antigenicity":
            return self._antigenicity(input)
        elif action == "bioreactor":
            return self._bioreactor(input)
        elif action == "media_cn":
            return self._media(input)
        elif action == "cloning":
            return self._cloning(input)
        elif action == "biosimilar_checklist":
            return {"success": True, **BIOSIMILAR_CHECKLIST}

        return {"actions": ["protein", "antigenicity", "bioreactor", "media_cn", "cloning", "biosimilar_checklist"],
                "hint": "Bioprocess Studio — protein properties, epitope screen, chemostat kinetics, media C:N, cloning math, biosimilar comparability."}

    @staticmethod
    def _num(input, k, d=0.0):
        try:
            return float(input.get(k, d) or d)
        except (TypeError, ValueError):
            return d

    def _protein(self, input: dict) -> dict:
        from modules.bioprocess import protein_properties
        return {"success": True, **protein_properties(str(input.get("sequence", "")), str(input.get("name", "")))}

    def _antigenicity(self, input: dict) -> dict:
        from modules.bioprocess import antigenicity_score
        return {"success": True, **antigenicity_score(str(input.get("sequence", "")))}

    def _bioreactor(self, input: dict) -> dict:
        from modules.bioprocess import bioreactor_kinetics
        r = bioreactor_kinetics(self._num(input, "mu_max"), self._num(input, "ks"),
                                self._num(input, "s0"), self._num(input, "yxs"),
                                self._num(input, "f_rate"), self._num(input, "volume", 1.0))
        return {"success": "error" not in r, **r}

    def _media(self, input: dict) -> dict:
        from modules.bioprocess import media_cn
        return {"success": True, **media_cn(str(input.get("carbon_source", "glucose")),
                                            self._num(input, "carbon_g_l"),
                                            str(input.get("nitrogen_source", "ammonium sulfate")),
                                            self._num(input, "nitrogen_g_l"))}

    def _cloning(self, input: dict) -> dict:
        from modules.bioprocess import cloning_calculator
        r = cloning_calculator(int(self._num(input, "insert_bp")),
                               int(self._num(input, "vector_bp")),
                               self._num(input, "insert_mass_ng"),
                               self._num(input, "vector_mass_ng"),
                               int(self._num(input, "ratio", 3)))
        return {"success": "error" not in r, **r}
