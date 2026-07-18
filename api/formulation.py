"""Formulation API — Pharmaceutics department tools.

Release kinetics, dissolution profile comparison, nanoparticle characterization,
stability prediction, and formulation optimization. Built for pharma
formulation scientists and researchers.

Science-first: all calculations use validated models from peer-reviewed literature.
"""
from helpers.api import ApiHandler, Request
import logging, json, os, math
import numpy as np

log = logging.getLogger("formulation")


def _kb_store(title, content, tags=None):
    """Store result to Knowledge Base (formulation category)."""
    try:
        from modules.knowledge.auto_store import auto_store
        auto_store("formulation", title, content, source="Formulation Lab",
                   tags=tags or ["formulation"], category="formulation")
    except Exception:
        pass


class FormulationHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "")
        result = None
        if action == "release_kinetics": result = self._release_kinetics(input)
        elif action == "dissolution_f2": result = self._dissolution_f2(input)
        elif action == "nanoparticle": result = self._nanoparticle(input)
        elif action == "stability": result = self._stability(input)
        elif action == "excipient_db": result = self._excipient_db(input)
        elif action == "optimize": result = self._optimize(input)
        else:
            return {
                "actions": ["release_kinetics", "dissolution_f2", "nanoparticle", "stability", "excipient_db", "optimize"],
                "hint": "Pharmaceutics tools: release kinetics, dissolution comparison, nanoparticle characterization, stability prediction"
            }
        # Auto-store to Knowledge Base if successful
        if result and not result.get("error"):
            title = f"Formulation — {action.replace('_', ' ').title()}"
            _kb_store(title, result, tags=["formulation", action])
        return result

    def _release_kinetics(self, input):
        """Fit dissolution/release data to kinetic models.
        
        Models: Zero-order, First-order, Higuchi, Korsmeyer-Peppas, Weibull.
        Reference: Costa & Lobo, European J Pharmaceutical Sciences, 2001.
        """
        time_points = input.get("time", [])
        release_pct = input.get("release_pct", [])

        if not time_points or not release_pct:
            return {"error": "time and release_pct arrays required"}
        if len(time_points) != len(release_pct):
            return {"error": "time and release_pct must have equal length"}

        t = np.array(time_points, dtype=float)
        mt = np.array(release_pct, dtype=float)
        mt_frac = mt / 100.0  # Convert to fraction

        results = {}

        # Zero-order: Mt = k0*t + M0
        # Linear regression: release vs time
        try:
            coeffs = np.polyfit(t, mt, 1)
            k0, m0 = coeffs
            mt_pred = k0 * t + m0
            ss_res = np.sum((mt - mt_pred) ** 2)
            ss_tot = np.sum((mt - np.mean(mt)) ** 2)
            r2_zero = 1 - ss_res / ss_tot if ss_tot > 0 else 0
            results["zero_order"] = {"k0": round(float(k0), 4), "r2": round(float(r2_zero), 4), "equation": f"Mt = {k0:.4f}*t + {m0:.4f}"}
        except Exception as e:
            log.debug(f"Zero-order fit failed: {e}")
            results["zero_order"] = {"error": "fit failed"}

        # First-order: ln(Mt) = k1*t + ln(M0) → ln(1 - release_frac) vs time
        try:
            mask = mt_frac < 1.0
            if np.sum(mask) >= 2:
                ln_remain = np.log(1 - mt_frac[mask])
                coeffs = np.polyfit(t[mask], ln_remain, 1)
                k1, ln_m0 = coeffs
                ln_pred = k1 * t[mask] + ln_m0
                ss_res = np.sum((ln_remain - ln_pred) ** 2)
                ss_tot = np.sum((ln_remain - np.mean(ln_remain)) ** 2)
                r2_first = 1 - ss_res / ss_tot if ss_tot > 0 else 0
                results["first_order"] = {"k1": round(float(k1), 4), "r2": round(float(r2_first), 4), "equation": f"ln(1-Mt) = {k1:.4f}*t + {ln_m0:.4f}"}
            else:
                results["first_order"] = {"error": "need at least 2 points with release < 100%"}
        except Exception as e:
            log.debug(f"First-order fit failed: {e}")
            results["first_order"] = {"error": "fit failed"}

        # Higuchi: Mt = kH * sqrt(t)
        try:
            sqrt_t = np.sqrt(t)
            coeffs = np.polyfit(sqrt_t, mt, 1)
            kH, c = coeffs
            mt_pred = kH * sqrt_t + c
            ss_res = np.sum((mt - mt_pred) ** 2)
            ss_tot = np.sum((mt - np.mean(mt)) ** 2)
            r2_higuchi = 1 - ss_res / ss_tot if ss_tot > 0 else 0
            results["higuchi"] = {"kH": round(float(kH), 4), "r2": round(float(r2_higuchi), 4), "equation": f"Mt = {kH:.4f}*sqrt(t) + {c:.4f}"}
        except Exception as e:
            log.debug(f"Higuchi fit failed: {e}")
            results["higuchi"] = {"error": "fit failed"}

        # Korsmeyer-Peppas: Mt/Minf = k_KP * t^n  →  log(release_frac) = n*log(t) + log(k)
        try:
            mask = (mt_frac > 0) & (mt_frac < 1.0) & (t > 0)
            if np.sum(mask) >= 2:
                log_mt = np.log(mt_frac[mask])
                log_t = np.log(t[mask])
                coeffs = np.polyfit(log_t, log_mt, 1)
                n, log_k = coeffs
                k_KP = math.exp(log_k)
                results["korsmeyer_peppas"] = {
                    "n": round(float(n), 4),
                    "k": round(float(k_KP), 6),
                    "release_mechanism": self._interpret_n(float(n)),
                    "equation": f"Mt/Minf = {k_KP:.6f} * t^{n:.4f}"
                }
            else:
                results["korsmeyer_peppas"] = {"error": "need at least 2 points with 0 < release < 100%"}
        except Exception as e:
            log.debug(f"Korsmeyer-Peppas fit failed: {e}")
            results["korsmeyer_peppas"] = {"error": "fit failed"}

        # Weibull: Mt/Minf = 1 - exp(-(t^b)/a)  →  ln(-ln(1-Mt/Minf)) = b*ln(t) - b*ln(a)
        try:
            mask = (mt_frac > 0) & (mt_frac < 1.0) & (t > 0)
            if np.sum(mask) >= 2:
                y = np.log(-np.log(1 - mt_frac[mask]))
                x = np.log(t[mask])
                coeffs = np.polyfit(x, y, 1)
                b, intercept = coeffs
                a = math.exp(-intercept / b) if b != 0 else 1
                results["weibull"] = {"a": round(float(a), 4), "b": round(float(b), 4), "equation": f"Mt = 1 - exp(-(t^{b:.4f})/{a:.4f})"}
            else:
                results["weibull"] = {"error": "need at least 2 points with 0 < release < 100%"}
        except Exception as e:
            log.debug(f"Weibull fit failed: {e}")
            results["weibull"] = {"error": "fit failed"}

        # Best-fit recommendation
        best = None
        best_r2 = 0
        for model, data in results.items():
            if isinstance(data, dict) and "r2" in data:
                if data["r2"] > best_r2:
                    best_r2 = data["r2"]
                    best = model

        return {
            "success": True,
            "models": results,
            "best_fit": best,
            "best_r2": round(best_r2, 4),
            "data_points": len(t),
            "interpretation": f"Best fit: {best} (R²={best_r2:.4f}). {results.get(best, {}).get('equation', '')}"
        }

    def _interpret_n(self, n):
        """Interpret Korsmeyer-Peppas release exponent (Ritger-Peppas, 1987)."""
        if n <= 0.43:
            return "Fickian diffusion (Case I transport)"
        elif 0.43 < n < 0.85:
            return "Anomalous transport (combination of diffusion and erosion)"
        elif n >= 0.85:
            return "Case II transport (erosion/relaxation-controlled)"
        else:
            return "Super Case II transport"

    def _dissolution_f2(self, input):
        """Calculate f2 similarity factor (FDA) and f1 difference factor.
        
        Reference: FDA Guidance for Industry: Dissolution Testing, 1997.
        f2 = 50 * log(100 / sqrt(1 + (1/n) * sum((Rt - Tt)^2)))
        f1 = (sum|Rt - Tt|) / (sum Rt) * 100
        
        Acceptable: f2 >= 50 (similar), f1 <= 15 (not different)
        """
        ref = input.get("reference", [])
        test = input.get("test", [])

        if not ref or not test:
            return {"error": "reference and test arrays required"}
        if len(ref) != len(test):
            return {"error": "reference and test must have equal length"}

        r = np.array(ref, dtype=float)
        t = np.array(test, dtype=float)
        n = len(r)

        # f2 similarity factor
        diff_sq = (r - t) ** 2
        sum_diff_sq = np.sum(diff_sq)
        f2 = 50 * math.log10(100 / math.sqrt(1 + (1/n) * sum_diff_sq)) if sum_diff_sq >= 0 else 100

        # f1 difference factor
        sum_abs_diff = np.sum(np.abs(r - t))
        sum_ref = np.sum(r)
        f1 = (sum_abs_diff / sum_ref) * 100 if sum_ref > 0 else 0

        similar = f2 >= 50
        different = f1 > 15

        return {
            "success": True,
            "f2": round(float(f2), 2),
            "f1": round(float(f1), 2),
            "similar": similar,
            "different": different,
            "interpretation": f"f2={f2:.1f} ({'Similar' if similar else 'NOT similar'}, threshold ≥50), f1={f1:.1f} ({'Different' if different else 'Not different'}, threshold ≤15)",
            "data_points": n,
        }

    def _nanoparticle(self, input):
        """Nanoparticle characterization calculations.
        
        Calculates: zeta potential classification, PDI interpretation,
        encapsulation efficiency, loading capacity.
        """
        zeta = input.get("zeta_potential", None)  # mV
        pdi = input.get("pdi", None)  # polydispersity index (0-1)
        drug_loaded = input.get("drug_loaded_mg", None)
        total_weight = input.get("total_weight_mg", None)
        drug_in_supernatant = input.get("drug_in_supernatant_mg", None)

        result = {"success": True}

        # Zeta potential classification (Bhattacharjee, J Controlled Release, 2016)
        if zeta is not None:
            if abs(zeta) >= 60:
                stability = "Excellent stability"
            elif abs(zeta) >= 40:
                stability = "Good stability"
            elif abs(zeta) >= 30:
                stability = "Moderate stability"
            elif abs(zeta) >= 20:
                stability = "Incipient instability"
            else:
                stability = "Fast aggregation expected"
            result["zeta_potential"] = {"value_mV": zeta, "stability": stability}

        # PDI interpretation (Danaei et al., Pharmaceutics, 2018)
        if pdi is not None:
            if pdi < 0.05:
                pdi_class = "Highly monodisperse"
            elif pdi < 0.08:
                pdi_class = "Monodisperse"
            elif pdi < 0.2:
                pdi_class = "Narrow distribution"
            elif pdi < 0.4:
                pdi_class = "Moderate distribution"
            elif pdi < 0.7:
                pdi_class = "Broad distribution"
            else:
                pdi_class = "Very broad distribution"
            result["pdi"] = {"value": pdi, "classification": pdi_class}

        # Encapsulation efficiency
        if drug_loaded is not None and drug_in_supernatant is not None:
            total_drug = drug_loaded + drug_in_supernatant
            ee = ((drug_loaded / total_drug) * 100) if total_drug > 0 else 0
            result["encapsulation_efficiency"] = {"percent": round(ee, 2), "formula": "(drug_in_NPs / total_drug) * 100"}

        # Loading capacity
        if drug_loaded is not None and total_weight is not None:
            lc = ((drug_loaded / total_weight) * 100) if total_weight > 0 else 0
            result["loading_capacity"] = {"percent": round(lc, 2), "formula": "(drug_in_NPs / total_NP_weight) * 100"}

        return result

    def _stability(self, input):
        """ICH Q1E shelf-life prediction from accelerated stability data.
        
        Uses Arrhenius equation: k = A * exp(-Ea/RT)
        t90 = time for 10% degradation at target temperature.
        
        Reference: ICH Q1E: Evaluation of Stability Data.
        """
        temp_c = input.get("temperature_C", [])  # Accelerated temperatures
        t90_days = input.get("t90_days", [])  # t90 at each temperature
        target_temp = input.get("target_temp_C", 25)  # Storage temperature

        if not temp_c or not t90_days:
            return {"error": "temperature_C and t90_days arrays required"}
        if len(temp_c) != len(t90_days):
            return {"error": "arrays must have equal length"}

        temps_k = np.array(temp_c, dtype=float) + 273.15
        t90s = np.array(t90_days, dtype=float)
        target_k = target_temp + 273.15

        # Arrhenius: ln(t90) = Ea/R * (1/T) + C
        try:
            ln_t90 = np.log(t90s)
            inv_t = 1.0 / temps_k
            coeffs = np.polyfit(inv_t, ln_t90, 1)
            slope, intercept = coeffs

            # Predict t90 at target temperature
            ln_t90_target = slope * (1.0 / target_k) + intercept
            t90_target = math.exp(ln_t90_target)

            # Activation energy
            R = 8.314  # J/(mol·K)
            Ea = slope * R / 1000  # kJ/mol

            # R²
            ln_pred = slope * inv_t + intercept
            ss_res = np.sum((ln_t90 - ln_pred) ** 2)
            ss_tot = np.sum((ln_t90 - np.mean(ln_t90)) ** 2)
            r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

            return {
                "success": True,
                "t90_at_target_days": round(float(t90_target), 1),
                "t90_at_target_months": round(float(t90_target) / 30.44, 1),
                "target_temperature_C": target_temp,
                "activation_energy_kJ_mol": round(float(Ea), 2),
                "r2": round(float(r2), 4),
                "data_points": len(temp_c),
                "interpretation": f"Predicted shelf life (t90) at {target_temp}°C: {t90_target:.0f} days ({t90_target/30.44:.1f} months). Ea = {Ea:.1f} kJ/mol. R² = {r2:.4f}."
            }
        except Exception as e:
            return {"error": f"Arrhenius fit failed: {e}"}

    def _excipient_db(self, input):
        """Common pharmaceutical excipients database with properties."""
        category = input.get("category", "")

        excipients = {
            "fillers": [
                {"name": "Lactose monohydrate", "type": "Filler/Diluent", "solubility": "Freely soluble", "compressibility": "Good", "common_dose": "20-80%", "notes": "Most common filler for tablets"},
                {"name": "Microcrystalline cellulose (MCC)", "type": "Filler/Binder", "solubility": "Insoluble", "compressibility": "Excellent", "common_dose": "10-50%", "notes": "Avicel PH-101/102; excellent compressibility"},
                {"name": "Mannitol", "type": "Filler", "solubility": "Freely soluble", "compressibility": "Good", "common_dose": "20-80%", "notes": "Used in chewable tablets, good taste"},
                {"name": "Dicalcium phosphate", "type": "Filler", "solubility": "Insoluble", "compressibility": "Good", "common_dose": "20-60%", "notes": "Wet granulation filler"},
                {"name": "Starch", "type": "Filler/Disintegrant", "solubility": "Insoluble", "compressibility": "Poor", "common_dose": "5-30%", "notes": "Corn/potato starch"},
            ],
            "binders": [
                {"name": "Povidone (PVP K30)", "type": "Binder", "solubility": "Freely soluble", "viscosity": "Low-medium", "common_dose": "2-5%", "notes": "Most common binder for wet granulation"},
                {"name": "Hydroxypropyl methylcellulose (HPMC)", "type": "Binder/Coating", "solubility": "Soluble in cold water", "viscosity": "Variable (3-100 cP)", "common_dose": "2-10%", "notes": "Also used as film coating"},
                {"name": "Gelatin", "type": "Binder", "solubility": "Soluble in warm water", "viscosity": "Variable", "common_dose": "1-5%", "notes": "Used in hard gelatin capsules"},
                {"name": "Polyvinyl alcohol (PVA)", "type": "Binder", "solubility": "Soluble in hot water", "viscosity": "Variable", "common_dose": "2-8%", "notes": "Used in film coatings"},
            ],
            "disintegrants": [
                {"name": "Croscarmellose sodium", "type": "Superdisintegrant", "mechanism": "Swelling + wicking", "common_dose": "1-5%", "notes": "Ac-Di-Sol; most popular superdisintegrant"},
                {"name": "Sodium starch glycolate", "type": "Superdisintegrant", "mechanism": "Swelling", "common_dose": "1-8%", "notes": "Primojel; swelling up to 300%"},
                {"name": "Crospovidone", "type": "Superdisintegrant", "mechanism": "Swelling + wicking", "common_dose": "1-5%", "notes": "Polyplasdone XL; rapid disintegration"},
                {"name": "Starch 1500", "type": "Disintegrant", "mechanism": "Swelling", "common_dose": "5-15%", "notes": "Partially pregelatinized starch"},
            ],
            "lubricants": [
                {"name": "Magnesium stearate", "type": "Lubricant", "mechanism": "Hydrophobic film", "common_dose": "0.25-2%", "notes": "Most common; over-lubrication reduces dissolution"},
                {"name": "Sodium stearyl fumarate", "type": "Lubricant", "mechanism": "Hydrophobic film", "common_dose": "0.5-2%", "notes": "Alternative to Mg stearate; less negative effect on dissolution"},
                {"name": "Colloidal silicon dioxide", "type": "Glidant", "mechanism": "Surface adsorption", "common_dose": "0.1-0.5%", "notes": "Aerosil; improves powder flow"},
            ],
            "coatings": [
                {"name": "HPMC-based film coat", "type": "Film coating", "solubility": "Aqueous", "thickness": "20-100 µm", "notes": "OPADRY; enteric or sustained-release variants available"},
                {"name": "Shellac", "type": "Enteric coating", "solubility": "pH >7", "notes": "Natural enteric polymer; dissolves at intestinal pH"},
                {"name": "Eudragit L100-55", "type": "Enteric coating", "solubility": "pH >5.5", "notes": "Dissolves in upper intestine"},
                {"name": "Eudragit RS/RL", "type": "Sustained release", "solubility": "Slightly permeable", "notes": "Controls drug release rate"},
            ],
        }

        if category and category in excipients:
            return {"success": True, "category": category, "excipients": excipients[category], "count": len(excipients[category])}
        elif not category:
            return {"success": True, "categories": list(excipients.keys()), "total": sum(len(v) for v in excipients.values())}
        else:
            return {"error": f"Unknown category: {category}. Available: {list(excipients.keys())}"}

    def _optimize(self, input):
        """DOE/RSM formulation optimization.
        
        Uses Response Surface Methodology (Box-Behnken or Central Composite Design).
        Reference: Montgomery, Design and Analysis of Experiments, 8th ed.
        """
        factors = input.get("factors", [])  # List of factor names
        responses = input.get("responses", [])  # List of response names
        data = input.get("data", [])  # List of {factor1: val, factor2: val, response1: val}

        if not factors or not responses or not data:
            return {"error": "factors, responses, and data arrays required"}

        try:
            import pandas as pd
            df = pd.DataFrame(data)

            results = {"success": True, "factors": factors, "responses": responses, "models": {}}

            for resp in responses:
                if resp not in df.columns:
                    continue

                # Fit quadratic model: y = b0 + b1*x1 + b2*x2 + b11*x1² + b22*x2² + b12*x1*x2
                X_cols = [f for f in factors if f in df.columns]
                X = df[X_cols].values
                y = df[resp].values

                # Build quadratic features
                n_factors = len(X_cols)
                X_quad = np.column_stack([np.ones(len(X))] + [X[:, i] for i in range(n_factors)])
                # Add squared terms
                for i in range(n_factors):
                    X_quad = np.column_stack([X_quad, X[:, i] ** 2])
                # Add interaction terms
                for i in range(n_factors):
                    for j in range(i + 1, n_factors):
                        X_quad = np.column_stack([X_quad, X[:, i] * X[:, j]])

                # Fit via least squares
                try:
                    coeffs = np.linalg.lstsq(X_quad, y, rcond=None)[0]
                    y_pred = X_quad @ coeffs
                    ss_res = np.sum((y - y_pred) ** 2)
                    ss_tot = np.sum((y - np.mean(y)) ** 2)
                    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

                    results["models"][resp] = {
                        "r2": round(float(r2), 4),
                        "coefficients": [round(float(c), 4) for c in coeffs],
                        "predicted": [round(float(p), 2) for p in y_pred[:5]],
                    }
                except Exception as e:
                    log.debug(f"Polynomial fit failed for {resp}: {e}")
                    results["models"][resp] = {"error": "fit failed"}

            # Optimal point (simple: find data row with best response)
            for resp in responses:
                if resp in df.columns:
                    best_idx = df[resp].idxmax()
                    results[f"best_{resp}"] = {
                        "value": round(float(df.loc[best_idx, resp]), 4),
                        "conditions": {f: round(float(df.loc[best_idx, f]), 4) for f in factors if f in df.columns}
                    }

            return results

        except Exception as e:
            return {"error": f"Optimization failed: {e}"}
