"""Pharmaceutical Analysis API — ICH Q2 method validation, dissolution testing,
forced degradation planning, chromatographic calculations.

All calculations follow ICH, USP, and FDA guidelines. For pharma analysts and QC labs.
"""
from helpers.api import ApiHandler, Request, Response
import logging, math
import numpy as np

log = logging.getLogger("pharma_analysis")


class PharmaAnalysisHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "")
        if action == "method_validation": return self._method_validation(input)
        elif action == "dissolution_f2": return self._dissolution_f2(input)
        elif action == "forced_degradation": return self._forced_degradation(input)
        elif action == "chromatography": return self._chromatography(input)
        elif action == "lod_loq": return self._lod_loq(input)
        return {
            "actions": ["method_validation", "dissolution_f2", "forced_degradation", "chromatography", "lod_loq"],
            "hint": "Pharma analysis: ICH Q2 validation, dissolution testing, forced degradation, HPLC calculations"
        }

    def _method_validation(self, input):
        """ICH Q2(R2) method validation parameters calculator.
        
        Calculates: accuracy, precision, LOD, LOQ, linearity, range.
        Reference: ICH Q2(R2) Validation of Analytical Procedures, 2023.
        """
        data = input.get("data", {})  # {spiked_conc: [measured_values]}

        if not data:
            return {"error": "data required: {concentration: [measured_values]}"}

        result = {"success": True, "reference": "ICH Q2(R2) 2023"}

        # Linearity
        concs = sorted([float(c) for c in data.keys()])
        means = []
        for c in concs:
            vals = data[str(c)] if str(c) in data else data[c]
            means.append(np.mean(vals))

        if len(concs) >= 3:
            coeffs = np.polyfit(concs, means, 1)
            slope, intercept = coeffs
            predicted = [slope * c + intercept for c in concs]
            ss_res = sum((m - p) ** 2 for m, p in zip(means, predicted))
            ss_tot = sum((m - np.mean(means)) ** 2 for m in means)
            r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
            result["linearity"] = {
                "r_squared": round(r2, 6),
                "slope": round(slope, 4),
                "intercept": round(intercept, 4),
                "equation": f"y = {slope:.4f}x + {intercept:.4f}",
                "concentration_range": f"{min(concs)} - {max(concs)}",
                "acceptable": r2 >= 0.999,
                "guideline": "R² >= 0.999 (ICH Q2)"
            }

        # Accuracy (% Recovery)
        recoveries = []
        for c in concs:
            vals = data[str(c)] if str(c) in data else data[c]
            recovery = (np.mean(vals) / c) * 100 if c > 0 else 0
            recoveries.append(round(recovery, 2))
        result["accuracy"] = {
            "percent_recovery": recoveries,
            "mean_recovery": round(np.mean(recoveries), 2),
            "acceptable": 80 <= np.mean(recoveries) <= 120,
            "guideline": "80-120% recovery (ICH Q2)"
        }

        # Precision (RSD)
        rsds = []
        for c in concs:
            vals = data[str(c)] if str(c) in data else data[c]
            if len(vals) >= 2:
                rsd = (np.std(vals, ddof=1) / np.mean(vals)) * 100
                rsds.append(round(rsd, 2))
        result["precision"] = {
            "rsd_percent": rsds,
            "mean_rsd": round(np.mean(rsds), 2) if rsds else None,
            "acceptable": all(r <= 2.0 for r in rsds) if rsds else False,
            "guideline": "RSD <= 2.0% for assay (ICH Q2)"
        }

        return result

    def _dissolution_f2(self, input):
        """f2 similarity factor and f1 difference factor (FDA 1997)."""
        ref = input.get("reference", [])
        test = input.get("test", [])
        if not ref or not test or len(ref) != len(test):
            return {"error": "reference and test arrays of equal length required"}

        r = np.array(ref, dtype=float)
        t = np.array(test, dtype=float)
        n = len(r)

        diff_sq = (r - t) ** 2
        f2 = 50 * math.log10(100 / math.sqrt(1 + (1/n) * np.sum(diff_sq))) if np.sum(diff_sq) >= 0 else 100
        f1 = (np.sum(np.abs(r - t)) / np.sum(r)) * 100 if np.sum(r) > 0 else 0

        return {
            "success": True,
            "f2": round(float(f2), 2),
            "f1": round(float(f1), 2),
            "similar": f2 >= 50,
            "interpretation": f"f2={f2:.1f} ({'Similar' if f2 >= 50 else 'NOT similar'}, threshold ≥50), f1={f1:.1f} ({'Different' if f1 > 15 else 'Not different'}, threshold ≤15)",
            "reference": "FDA Guidance: Dissolution Testing 1997"
        }

    def _forced_degradation(self, input):
        """Forced degradation study planner.
        
        Returns recommended conditions for acid/base/oxidative/photolytic/thermal
        degradation per ICH Q1B and industry practice.
        """
        drug_name = input.get("drug_name", "Drug")

        conditions = [
            {"stress": "Acid hydrolysis", "reagent": "0.1-1 N HCl", "temp": "60-80°C", "time": "2-24 hours", "target_degradation": "10-30%", "neutralization": "Neutralize with NaOH"},
            {"stress": "Base hydrolysis", "reagent": "0.1-1 N NaOH", "temp": "60-80°C", "time": "2-24 hours", "target_degradation": "10-30%", "neutralization": "Neutralize with HCl"},
            {"stress": "Oxidative", "reagent": "3% H₂O₂", "temp": "Room temp or 40°C", "time": "2-24 hours", "target_degradation": "10-30%", "neutralization": "Catalase or Na₂SO₃"},
            {"stress": "Photolytic (ICH Q1B)", "reagent": "D65 fluorescent lamp (1.2M lux·hr) + UV (200 W·hr/m²)", "temp": "Room temp", "time": "Per ICH Q1B", "target_degradation": "10-30%", "neutralization": "Light-protected container"},
            {"stress": "Thermal", "reagent": "Dry heat", "temp": "60-80°C", "time": "24-72 hours", "target_degradation": "10-30%", "neutralization": "Cool to RT"},
            {"stress": "Humidity", "reagent": "75% RH", "temp": "40°C", "time": "4 weeks", "target_degradation": "10-30%", "neutralization": "Desiccant storage"},
        ]

        return {
            "success": True,
            "drug": drug_name,
            "conditions": conditions,
            "guidelines": [
                "ICH Q1A(R2): Stability Testing of New Drug Substances",
                "ICH Q1B: Photostability Testing",
                "Target: 10-30% degradation (enough to see degradants without complete destruction)",
                "Always run unstressed control alongside stressed samples",
                "Use stability-indicating method (HPLC/UV or LC-MS) to track degradation products"
            ]
        }

    def _chromatography(self, input):
        """Chromatographic method development calculations.
        
        Calculates: resolution, plate number, tailing factor, capacity factor,
        selectivity, theoretical plates per meter.
        """
        t_r = input.get("retention_time_min", 0)
        t_0 = input.get("void_time_min", 0)
        w = input.get("peak_width_min", 0)
        w_half = input.get("peak_width_half_height_min", 0)
        t_r2 = input.get("retention_time_2_min", 0)
        w2 = input.get("peak_width_2_min", 0)

        result = {"success": True}

        if t_r and t_0 and w_half:
            # Capacity factor (k')
            k_prime = (t_r - t_0) / t_0 if t_0 > 0 else 0
            result["capacity_factor"] = round(k_prime, 3)

            # Theoretical plates (N) - USP method
            n = 16 * (t_r / w) ** 2 if w else 5.54 * (t_r / w_half) ** 2 if w_half else 0
            result["theoretical_plates"] = round(n, 0)

            # Tailing factor (T) - USP method
            if w and w_half:
                t_factor = w / (2 * (t_r - (t_r - w_half/2)))
                result["tailing_factor"] = round(t_factor, 3)
                result["tailing_acceptable"] = 0.8 <= t_factor <= 1.5

            result["guideline"] = "USP <621> Chromatography"

        if t_r and t_r2 and w and w2:
            # Resolution (Rs)
            rs = 2 * (t_r2 - t_r) / (w + w2)
            result["resolution"] = round(rs, 3)
            result["baseline_resolved"] = rs >= 1.5

        return result

    def _lod_loq(self, input):
        """LOD and LOQ calculation (ICH Q2).
        
        Methods: signal-to-noise (S/N=3 for LOD, S/N=10 for LOQ),
        or standard deviation of response + slope.
        """
        method = input.get("method", "snr")
        slope = input.get("slope", 0)
        std_blank = input.get("std_blank_response", 0)
        snr_lod = input.get("snr_lod", 3)
        snr_loq = input.get("snr_loq", 10)
        signal = input.get("signal", 0)
        noise = input.get("noise", 0)

        result = {"success": True, "method": method, "reference": "ICH Q2(R2) 2023"}

        if method == "snr" and noise > 0:
            lod_conc = (snr_lod * noise) / slope if slope > 0 else 0
            loq_conc = (snr_loq * noise) / slope if slope > 0 else 0
            result["lod"] = round(lod_conc, 4)
            result["loq"] = round(loq_conc, 4)
            result["lod_snr"] = snr_lod
            result["loq_snr"] = snr_loq

        elif method == "std" and slope > 0:
            lod = 3.3 * std_blank / slope
            loq = 10 * std_blank / slope
            result["lod"] = round(lod, 4)
            result["loq"] = round(loq, 4)
            result["formula_lod"] = "3.3 × σ / S"
            result["formula_loq"] = "10 × σ / S"

        return result
