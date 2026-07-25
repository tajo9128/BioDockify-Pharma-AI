"""PK/PD Dashboard API — wraps existing pkpd_analysis module."""
from helpers.api import ApiHandler, Request, Response
import logging, os, json, uuid

log = logging.getLogger("pkpd")

class PKPD(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "")
        if action == "nca":         return self._run_pkpd("nca", input)
        if action == "auc":         return self._run_pkpd("auc", input)
        if action == "cmax_tmax":   return self._run_pkpd("cmax_tmax", input)
        if action == "half_life":   return self._run_pkpd("half_life", input)
        if action == "clearance":   return self._run_pkpd("clearance", input)
        if action == "bioavail":    return self._run_pkpd("bioavail", input)
        if action == "pd_response": return self._run_pkpd("pd_response", input)
        if action == "compartmental": return self._run_pkpd("compartmental", input)
        if action == "summary":     return self._run_pkpd("summary", input)
        if action == "health":      return self._health()
        return {"actions": ["nca","auc","cmax_tmax","half_life","clearance","bioavail","pd_response","compartmental","summary","health"]}

    def _health(self):
        try:
            from modules.statistics.pkpd_analysis import PKPDAnalysis
            return {"status": "ok", "pkpd": True}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _build_pkpd(self, input: dict):
        import pandas as pd
        import numpy as np
        raw = input.get("data", {})
        time_col = input.get("time_col", "Time_h")
        conc_col = input.get("conc_col", "Concentration_ng_ml")
        dose = float(input.get("dose", 100))
        route = input.get("route", "EV")
        alpha = float(input.get("alpha", 0.05))

        if isinstance(raw, dict):
            df = pd.DataFrame.from_dict(raw, orient="index")
        elif isinstance(raw, list):
            df = pd.DataFrame(raw)
        else:
            return None, None, {"status": "error", "error": "Invalid data format"}

        rename = {}
        for c in df.columns:
            cl = str(c).lower().strip()
            if cl == time_col.lower() or "time" in cl:
                rename[c] = "time"
            elif cl == conc_col.lower() or "conc" in cl:
                rename[c] = "concentration"
        df = df.rename(columns=rename)

        if "time" not in df.columns or "concentration" not in df.columns:
            return None, None, {"status": "error", "error": f"Could not find time/concentration columns. Available: {list(df.columns)}"}

        df["time"] = pd.to_numeric(df["time"], errors="coerce")
        df["concentration"] = pd.to_numeric(df["concentration"], errors="coerce")
        df = df.dropna(subset=["time", "concentration"])

        from modules.statistics.pkpd_analysis import PKPDAnalysis
        pk = PKPDAnalysis(df, dose=dose, route=route)
        return pk, alpha, None

    def _run_pkpd(self, method: str, input: dict):
        try:
            import numpy as np
            pk, alpha, err = self._build_pkpd(input)
            if err: return err

            if method == "nca":
                r = pk.non_compartmental_analysis(alpha=alpha)
            elif method == "auc":
                r = pk.calculate_auc()
            elif method == "cmax_tmax":
                r = pk.calculate_cmax_tmax()
            elif method == "half_life":
                r = pk.estimate_half_life()
            elif method == "clearance":
                r = pk.calculate_clearance(alpha=alpha)
            elif method == "bioavail":
                # Calculate absolute bioavailability from IV and oral PK data
                iv_data = input.get("iv_data", {})
                oral_data = input.get("oral_data", {})
                iv_dose = input.get("iv_dose", 0)
                oral_dose = input.get("oral_dose", 0)
                
                if not iv_data or not oral_data or iv_dose == 0 or oral_dose == 0:
                    return {
                        "status": "error", 
                        "error": "Bioavailability requires: iv_data, oral_data, iv_dose, oral_dose. Example: {\"action\":\"pkpd\",\"method\":\"bioavail\",\"iv_data\":{...},\"oral_data\":{...},\"iv_dose\":100,\"oral_dose\":200}"
                    }
                
                try:
                    import pandas as pd
                    # Calculate AUC for IV data
                    if isinstance(iv_data, dict):
                        iv_df = pd.DataFrame.from_dict(iv_data, orient="index")
                    else:
                        iv_df = pd.DataFrame(iv_data)
                    
                    # Calculate AUC for oral data
                    if isinstance(oral_data, dict):
                        oral_df = pd.DataFrame.from_dict(oral_data, orient="index")
                    else:
                        oral_df = pd.DataFrame(oral_data)
                    
                    # Get time and concentration columns
                    time_col = input.get("time_col", "Time_h")
                    conc_col = input.get("conc_col", "Conc_ng_mL")
                    
                    if time_col not in iv_df.columns or conc_col not in iv_df.columns:
                        return {"status": "error", "error": f"IV data missing columns: {time_col}, {conc_col}"}
                    if time_col not in oral_df.columns or conc_col not in oral_df.columns:
                        return {"status": "error", "error": f"Oral data missing columns: {time_col}, {conc_col}"}
                    
                    # Sort by time
                    iv_df = iv_df.sort_values(time_col).reset_index(drop=True)
                    oral_df = oral_df.sort_values(time_col).reset_index(drop=True)
                    
                    # Calculate AUC using trapezoidal rule
                    iv_times = iv_df[time_col].values.astype(float)
                    iv_concs = iv_df[conc_col].values.astype(float)
                    oral_times = oral_df[time_col].values.astype(float)
                    oral_concs = oral_df[conc_col].values.astype(float)
                    
                    iv_auc = np.trapz(iv_concs, iv_times)
                    oral_auc = np.trapz(oral_concs, oral_times)
                    
                    # Calculate bioavailability: F = (AUC_oral / AUC_iv) * (Dose_iv / Dose_oral)
                    f_abs = (oral_auc / iv_auc) * (iv_dose / oral_dose) if iv_auc > 0 else 0
                    f_abs_pct = f_abs * 100
                    
                    # Cmax and Tmax for oral
                    oral_cmax = float(np.max(oral_concs))
                    oral_tmax = float(oral_times[np.argmax(oral_concs)])
                    
                    return {
                        "status": "ok",
                        "method": "bioavail",
                        "F_absolute": round(f_abs, 4),
                        "F_absolute_pct": round(f_abs_pct, 1),
                        "iv_dose": iv_dose,
                        "oral_dose": oral_dose,
                        "iv_auc": round(iv_auc, 2),
                        "oral_auc": round(oral_auc, 2),
                        "oral_cmax": round(oral_cmax, 2),
                        "oral_tmax": round(oral_tmax, 2),
                        "interpretation": (
                            f"Absolute bioavailability: {f_abs_pct:.1f}% "
                            f"({'high' if f_abs_pct >= 80 else 'moderate' if f_abs_pct >= 50 else 'low'}). "
                            f"Oral Cmax: {oral_cmax:.2f} at Tmax: {oral_tmax:.1f} h."
                        ),
                        "guidelines": "Calculated per FDA Guidance for Industry: Bioavailability and Bioequivalence Studies (2003)"
                    }
                except Exception as e:
                    return {"status": "error", "error": f"Bioavailability calculation failed: {str(e)}"}
            elif method == "pd_response":
                resp_col = input.get("response_col", "Effect_Pct")
                raw = input.get("data", {})
                import pandas as pd
                if isinstance(raw, dict):
                    df = pd.DataFrame.from_dict(raw, orient="index")
                else:
                    df = pd.DataFrame(raw)
                if resp_col in df.columns:
                    effect = pd.to_numeric(df[resp_col], errors="coerce").dropna().values
                else:
                    effect = np.array([])
                if len(effect) == 0:
                    return {"status": "error", "error": f"Response column '{resp_col}' not found or empty"}
                r = pk.pd_response_modeling(effect_data=effect)
            elif method == "compartmental":
                r = pk.pk_parameter_estimation(alpha=alpha)
            elif method == "summary":
                r = pk.pk_summary_statistics(alpha=alpha)
            else:
                return {"status": "error", "error": f"Unknown method: {method}"}

            return {"status": "ok", "method": method, "results": self._safe_result(r)}
        except Exception as e:
            log.exception("PK/PD error")
            return {"status": "error", "error": str(e)}

    def _safe_result(self, obj):
        if hasattr(obj, "parameters"):
            d = {}
            if hasattr(obj, "parameters") and obj.parameters:
                d.update({k: self._safe(v) for k, v in obj.parameters.items()})
            if hasattr(obj, "interpretation") and obj.interpretation:
                d["interpretation"] = obj.interpretation
            if hasattr(obj, "warnings") and obj.warnings:
                d["warnings"] = obj.warnings
            return d
        return self._safe(obj)

    def _safe(self, obj):
        if isinstance(obj, dict): return {k: self._safe(v) for k, v in obj.items()}
        if isinstance(obj, list): return [self._safe(v) for v in obj]
        if isinstance(obj, tuple): return [self._safe(v) for v in obj]
        if hasattr(obj, "item"): return obj.item()
        if isinstance(obj, float): return round(obj, 4)
        return obj
