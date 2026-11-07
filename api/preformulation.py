"""Preformulation & Drug Delivery Designer API.

Additive module — Pharmaceutics department. Two halves:
  1. Preformulation workbench (SMILES → descriptor panel, solubility class,
     polymorph/hygroscopicity flags, excipient compatibility rules)
  2. Delivery-system calculators (liposome, nanoparticle, mucoadhesion, TDD)
  3. DoE designer — SURFACES the existing hidden QbD engines
     (modules/formulation/qbd.py 1537 L and mixture.py) unchanged.
"""
from helpers.api import ApiHandler, Request, Response
import logging

log = logging.getLogger("preformulation")


class PreformulationHandler(ApiHandler):

    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "")

        if action == "profile":
            return self._profile(input)
        elif action == "compatibility":
            return self._compatibility(input)
        elif action == "liposome":
            return self._liposome(input)
        elif action == "nanoparticle":
            return self._nanoparticle(input)
        elif action == "mucoadhesion":
            return self._mucoadhesion(input)
        elif action == "transdermal":
            return self._transdermal(input)
        elif action == "doe_design":
            return self._doe_design(input)
        elif action == "doe_mixture":
            return self._doe_mixture(input)
        elif action == "doe_analyze":
            return self._doe_analyze(input)

        return {"actions": ["profile", "compatibility", "liposome", "nanoparticle", "mucoadhesion",
                            "transdermal", "doe_design", "doe_mixture", "doe_analyze"],
                "hint": "Preformulation & Drug Delivery Designer — SMILES preformulation panel, "
                        "excipient compatibility, delivery calculators, and QbD DoE "
                        "(factorial/CCD/Box-Behnken/Plackett-Burman + mixture designs)."}

    # ── 1. Preformulation ────────────────────────────────────────────────────

    @staticmethod
    def _profile(input: dict) -> dict:
        from modules.formulation.preformulation import preformulation_profile
        smiles = str(input.get("smiles", "")).strip()
        if not smiles:
            return {"error": "provide smiles"}
        try:
            return {"success": True, **preformulation_profile(smiles, str(input.get("name", "")))}
        except Exception as e:
            return {"error": str(e)[:200]}

    @staticmethod
    def _compatibility(input: dict) -> dict:
        from modules.formulation.preformulation import compatibility_screen
        flags = input.get("flags") or []
        if isinstance(flags, str):
            flags = [f.strip() for f in flags.split(",") if f.strip()]
        if not flags:
            return {"error": "provide API feature flags (e.g. 'weak acid, high logP, hygroscopicity risk')"}
        return {"success": True, **compatibility_screen(flags)}

    # ── 2. Delivery calculators ──────────────────────────────────────────────

    @staticmethod
    def _num(input, k, default=None):
        try:
            v = input.get(k, default)
            return float(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    def _liposome(self, input: dict) -> dict:
        from modules.formulation.preformulation import liposome_calculator
        r = liposome_calculator(self._num(input, "drug_mg", 0) or 0,
                                self._num(input, "lipid_conc_mmol", 0) or 0,
                                self._num(input, "volume_ml", 0) or 0,
                                self._num(input, "entrapment_pct", 80.0) or 80.0,
                                self._num(input, "lipid_mw", 750.0) or 750.0)
        return {"success": "error" not in r, **r}

    def _nanoparticle(self, input: dict) -> dict:
        from modules.formulation.preformulation import nanoparticle_dose
        r = nanoparticle_dose(self._num(input, "mg_kg", 0) or 0,
                              self._num(input, "bodyweight_kg", 0) or 0,
                              self._num(input, "conc_mg_ml", 0) or 0,
                              self._num(input, "pdi", 0.2) or 0.2)
        return {"success": "error" not in r, **r}

    @staticmethod
    def _mucoadhesion(input: dict) -> dict:
        from modules.formulation.preformulation import mucoadhesion_score
        polymer = str(input.get("polymer", "")).strip()
        if not polymer:
            return {"error": "provide polymer name"}
        return {"success": True,
                **mucoadhesion_score(polymer, float(input.get("conc_pct", 1) or 1),
                                     str(input.get("mw_band", "high")))}

    def _transdermal(self, input: dict) -> dict:
        from modules.formulation.preformulation import transdermal_flux
        r = transdermal_flux(self._num(input, "area_cm2", 0) or 0,
                             self._num(input, "concentration_mg_ml", 0) or 0,
                             self._num(input, "thickness_cm", 0) or 0,
                             self._num(input, "partition_k", 1.0) or 1.0,
                             self._num(input, "diffusion_cm2_s", 1e-9) or 1e-9)
        return {"success": "error" not in r, **r}

    # ── 3. DoE — surface the hidden QbD engines (read-only reuse) ────────────

    VALID_DESIGNS = {"full_factorial", "fractional_screening", "central_composite",
                     "box_behnken", "plackett_burman"}

    def _doe_design(self, input: dict) -> dict:
        factors = input.get("factors") or []
        if not isinstance(factors, list) or len(factors) < 2:
            return {"error": "provide factors: [{name, low, high, unit?}] (min 2)"}
        design = str(input.get("design_type", "central_composite"))
        if design not in self.VALID_DESIGNS:
            return {"error": f"design_type must be one of {sorted(self.VALID_DESIGNS)}"}
        try:
            from modules.formulation.qbd import generate_design
            out = generate_design(
                factors, design_type=design,
                centre_points=int(input.get("centre_points", 3) or 3),
                randomize=bool(input.get("randomize", True)),
                seed=input.get("seed"),
                replicates=int(input.get("replicates", 1) or 1),
            )
            return {"success": True, **out}
        except Exception as e:
            return {"error": str(e)[:300]}

    def _doe_mixture(self, input: dict) -> dict:
        components = input.get("components") or []
        if not isinstance(components, list) or len(components) < 3:
            return {"error": "mixture designs need ≥ 3 components: [{name, low, high, unit?}]"}
        try:
            from modules.formulation.mixture import generate_mixture_design
            out = generate_mixture_design(
                components,
                design_type=str(input.get("design_type", "simplex_centroid")),
                degree=int(input.get("degree", 2) or 2),
                include_axial=bool(input.get("include_axial", True)),
                centre_replicates=int(input.get("centre_replicates", 3) or 3),
                total=float(input.get("total", 1.0) or 1.0),
                randomize=bool(input.get("randomize", True)),
                seed=input.get("seed"),
            )
            return {"success": True, **out}
        except Exception as e:
            return {"error": str(e)[:300]}

    def _doe_analyze(self, input: dict) -> dict:
        """Fit + ANOVA over a completed design's runs (qbd analyse path)."""
        runs = input.get("runs") or []
        if not isinstance(runs, list) or not runs:
            return {"error": "provide runs: [{factors…, y: value}] from a completed design"}
        try:
            from modules.formulation.qbd import analyse_rsm
            order = str(input.get("model_order", "quadratic"))
            if order not in ("linear", "2fi", "quadratic"):
                order = "quadratic"
            out = analyse_rsm(runs,
                              responses=input.get("responses") or [{"name": "y"}],
                              model_order=order,
                              factor_names=input.get("factor_names"))
            return {"success": True, **out}
        except Exception as e:
            return {"error": str(e)[:300]}
