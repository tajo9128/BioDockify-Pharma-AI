"""Pharmacology API — Pharmacology department tools.

Receptor binding analysis, dose-response curves (EC50/IC50), Schild analysis,
Black-Leff operational model, selectivity ratios, receptor database, and
in-vivo study design helpers. Built for pharmacology researchers.

Science-first: all calculations use validated models from peer-reviewed literature.
Does NOT duplicate pkpd.py (PK/NCA), admet_predict.py, drug_properties.py (hERG/Ames),
or clinical.py (DDI/TDM).
"""
from helpers.api import ApiHandler, Request
import logging, math
import numpy as np

log = logging.getLogger("pharmacology")


class PharmacologyHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "")
        if action == "receptor_binding": return self._receptor_binding(input)
        elif action == "dose_response": return self._dose_response(input)
        elif action == "schild_analysis": return self._schild_analysis(input)
        elif action == "operational_model": return self._operational_model(input)
        elif action == "selectivity_ratio": return self._selectivity_ratio(input)
        elif action == "receptor_database": return self._receptor_database(input)
        elif action == "in_vivo_design": return self._in_vivo_design(input)
        elif action == "enzyme_kinetics": return self._enzyme_kinetics(input)
        elif action == "inhibition": return self._inhibition(input)
        return {
            "actions": ["receptor_binding", "dose_response", "schild_analysis",
                        "operational_model", "selectivity_ratio", "receptor_database",
                        "in_vivo_design"],
            "hint": "Pharmacology tools: receptor binding (Kd/Bmax), dose-response (EC50/IC50), Schild pA2, operational model, selectivity, receptor DB, in-vivo design"
        }

    # ─────────────────────────────────────────────────────────────
    # Receptor Binding — radioligand saturation analysis
    # Reference: Bylund & Toews, Methods in Enzymology, 1993.
    # ─────────────────────────────────────────────────────────────
    def _receptor_binding(self, input):
        """Saturation binding → Kd, Bmax, receptor occupancy, Scatchard & Hill plots."""
        ligand_conc = input.get("concentration", [])  # nM radioligand
        total_binding = input.get("total_binding", [])  # total cpm/fmol
        nonspecific = input.get("nonspecific", [])  # nonspecific cpm/fmol (parallel +cold)

        if not ligand_conc or not total_binding:
            return {"error": "concentration and total_binding arrays required"}
        n = min(len(ligand_conc), len(total_binding))
        if len(nonspecific) < n:
            nonspecific = [0.0] * n
        if n < 3:
            return {"error": "need at least 3 concentration points"}

        L = np.array(ligand_conc[:n], dtype=float)
        B_total = np.array(total_binding[:n], dtype=float)
        B_ns = np.array(nonspecific[:n], dtype=float)
        B_spec = B_total - B_ns  # specific binding

        # ── Saturation fit: B = (Bmax * L) / (Kd + L) ──
        Kd, Bmax = None, None
        try:
            from scipy.optimize import curve_fit

            def one_site(L_arr, Bmax_v, Kd_v):
                return (Bmax_v * L_arr) / (Kd_v + L_arr)

            # Initial guess via Lineweaver-Burk
            mask = B_spec > 0
            if np.sum(mask) >= 2:
                p, _ = np.polyfit(L[mask], L[mask] / B_spec[mask], 1)
                Bmax0 = 1.0 / p if p != 0 else np.max(B_spec)
                Kd0 = Bmax0 * np.mean(L[mask] / B_spec[mask]) - np.mean(L[mask])
                Kd0 = max(Kd0, 1e-3)
            else:
                Kd0, Bmax0 = float(np.median(L)), float(np.max(B_spec))

            popt, _ = curve_fit(one_site, L, B_spec, p0=[Bmax0, Kd0],
                                bounds=([0, 1e-6], [np.inf, np.inf]), maxfev=10000)
            Bmax_fit, Kd_fit = float(popt[0]), float(popt[1])
            B_pred = one_site(L, Bmax_fit, Kd_fit)
            ss_res = float(np.sum((B_spec - B_pred) ** 2))
            ss_tot = float(np.sum((B_spec - np.mean(B_spec)) ** 2))
            r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
            Kd, Bmax = Kd_fit, Bmax_fit
        except Exception as e:
            log.debug(f"Saturation fit failed: {e}")

        # ── Scatchard transform: B/L vs B → -1/Kd slope, Bmax x-intercept ──
        scatchard = []
        try:
            mask = (L > 0) & (B_spec > 0)
            if np.sum(mask) >= 2:
                BoverL = B_spec[mask] / L[mask]
                slope, intercept = np.polyfit(B_spec[mask], BoverL, 1)
                scatchard_kd = -1.0 / slope if slope < 0 else None
                scatchard_bmax = -intercept / slope if slope < 0 else None
                scatchard = {
                    "slope": round(float(slope), 4),
                    "intercept": round(float(intercept), 4),
                    "Kd_scatchard": round(float(scatchard_kd), 3) if scatchard_kd else None,
                    "Bmax_scatchard": round(float(scatchard_bmax), 2) if scatchard_bmax else None,
                    "note": "Linear Scatchard = single-site; concave-up = cooperative; concave-down = two-site"
                }
        except Exception:
            pass

        # ── Hill plot: log[B/(Bmax-B)] vs log[L] → slope = nH ──
        hill = None
        if Kd and Bmax:
            try:
                mask = (B_spec > 0) & (B_spec < Bmax * 0.98) & (L > 0)
                if np.sum(mask) >= 3:
                    log_L = np.log10(L[mask])
                    occupancy = B_spec[mask] / (Bmax - B_spec[mask])
                    occupancy = np.clip(occupancy, 1e-9, 1e9)
                    log_occ = np.log10(occupancy)
                    slope, intercept = np.polyfit(log_L, log_occ, 1)
                    hill = {
                        "nH": round(float(slope), 3),
                        "log_Kd": round(float(-intercept / slope), 3) if slope else None,
                        "interpretation": "cooperative" if abs(float(slope)) > 1.15 else ("non-cooperative" if 0.85 <= abs(float(slope)) <= 1.15 else "negative cooperativity")
                    }
            except Exception:
                pass

        # ── Receptor occupancy at each concentration ──
        occupancy_table = []
        for i in range(n):
            if Kd:
                occ = (L[i]) / (Kd + L[i]) * 100
                occupancy_table.append({
                    "concentration_nM": round(float(L[i]), 3),
                    "specific_binding": round(float(B_spec[i]), 2),
                    "occupancy_pct": round(float(occ), 2),
                })

        result = {
            "Kd_nM": round(Kd, 3) if Kd else None,
            "Bmax": round(Bmax, 2) if Bmax else None,
            "R2_fit": round(r2, 4) if Kd else None,
            "scatchard": scatchard if isinstance(scatchard, dict) else None,
            "hill_plot": hill,
            "occupancy_table": occupancy_table,
            "interpretation": (
                f"Kd = {Kd:.3f} nM (affinity), Bmax = {Bmax:.1f} fmol/mg (density). "
                f"Occupancy 50% at [L]=Kd. "
                + (f"Hill nH = {hill['nH']:.2f} → {hill['interpretation']}." if hill else "")
            ).strip(),
        }

        # Auto-store to KB
        try:
            from modules.knowledge.auto_store import auto_store
            auto_store("pharmacology", f"Receptor Binding — Kd={Kd:.2f}nM Bmax={Bmax:.1f}",
                       result, source="Saturation Binding Analysis", tags=["receptor_binding", "kd", "bmax"])
        except Exception:
            pass

        return result

    # ─────────────────────────────────────────────────────────────
    # Dose-Response — 4-parameter logistic (4PL)
    # Reference: Sebaugh, Pharmaceutical Statistics, 2011.
    # ─────────────────────────────────────────────────────────────
    def _dose_response(self, input):
        """4PL dose-response fit → EC50 (agonist) or IC50 (inhibitor)."""
        doses = input.get("dose", [])
        responses = input.get("response", [])
        direction = input.get("direction", "agonist")  # agonist=increasing | inhibitor=decreasing
        unit = input.get("unit", "µM")

        if not doses or not responses:
            return {"error": "dose and response arrays required"}
        if len(doses) != len(responses):
            return {"error": "dose and response must have equal length"}
        if len(doses) < 4:
            return {"error": "need at least 4 dose points for 4PL fit"}

        d = np.array(doses, dtype=float)
        r = np.array(responses, dtype=float)
        # Filter zero/negative doses (log undefined)
        mask = d > 0
        d, r = d[mask], r[mask]
        if len(d) < 4:
            return {"error": "need at least 4 positive dose points"}

        # ── 4PL: R = Bottom + (Top - Bottom) / (1 + (EC50/dose)^Hill) ──
        try:
            from scipy.optimize import curve_fit
            from scipy.stats import t as t_dist

            def four_pl(x, top, bottom, ec50, hill):
                return bottom + (top - bottom) / (1 + (ec50 / x) ** hill)

            top0 = float(np.max(r)) if direction == "agonist" else float(np.min(r))
            bot0 = float(np.min(r)) if direction == "agonist" else float(np.max(r))
            ec50_0 = float(np.median(d))
            hill0 = 1.0 if direction == "agonist" else -1.0

            popt, pcov = curve_fit(four_pl, d, r, p0=[top0, bot0, ec50_0, hill0],
                                   bounds=([-np.inf, -np.inf, 1e-9, -10],
                                           [np.inf, np.inf, np.inf, 10]),
                                   maxfev=20000)
            top, bottom, ec50, hill = (float(v) for v in popt)
            r_pred = four_pl(d, *popt)
            ss_res = float(np.sum((r - r_pred) ** 2))
            ss_tot = float(np.sum((r - np.mean(r)) ** 2))
            r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
            # 95% CI on EC50 from diagonal of covariance
            perr = np.sqrt(np.diag(pcov))
            ec50_ci = None
            try:
                dof = max(1, len(d) - 4)
                tval = float(t_dist.ppf(0.975, dof))
                ec50_ci = [ec50 - tval * perr[2], ec50 + tval * perr[2]]
            except Exception:
                pass

            # EC90 / EC95 (or IC90 / IC95) from Hill equation
            label = "EC" if direction == "agonist" else "IC"
            ec90 = ec50 * (9.0 ** (1.0 / abs(hill))) if hill else None
            ec95 = ec50 * (19.0 ** (1.0 / abs(hill))) if hill else None

            result = {
                "direction": direction,
                f"{label}50": round(ec50, 4),
                f"{label}50_unit": unit,
                f"{label}50_CI95": [round(float(ec50_ci[0]), 4), round(float(ec50_ci[1]), 4)] if ec50_ci else None,
                "hill_slope": round(hill, 3),
                "top": round(top, 3),
                "bottom": round(bottom, 3),
                "R2": round(r2, 4),
                f"{label}90": round(ec90, 4) if ec90 else None,
                f"{label}95": round(ec95, 4) if ec95 else None,
                "interpretation": (
                    f"{label}50 = {ec50:.4f} {unit} (potency), Hill = {hill:.2f} "
                    f"({'steep' if abs(hill) > 1.5 else 'standard'} slope), R² = {r2:.3f}. "
                    f"Efficacy range: {bottom:.1f} → {top:.1f}."
                )
            }
        except Exception as e:
            return {"error": f"4PL fit failed: {e}", "hint": "Ensure dose spans from no-effect to max-effect, all doses > 0"}

        try:
            from modules.knowledge.auto_store import auto_store
            auto_store("pharmacology", f"Dose-Response — {label}50={ec50:.3f}{unit}",
                       result, source="4PL Dose-Response", tags=["dose_response", label.lower() + "50"])
        except Exception:
            pass
        return result

    # ─────────────────────────────────────────────────────────────
    # Schild Analysis — competitive antagonist potency
    # Reference: Arunlakshana & Schild, Br J Pharmacol, 1959.
    # ─────────────────────────────────────────────────────────────
    def _schild_analysis(self, input):
        """Schild regression → pA2, KB, Schild slope (should ≈1 for competitive)."""
        conc_antag = input.get("antagonist_conc", [])  # [B] M
        ec50_control = input.get("ec50_control")  # EC50 without antagonist (same unit)
        ec50_shifted = input.get("ec50_shifted", [])  # EC50 at each antagonist conc

        if not conc_antag or not ec50_shifted:
            return {"error": "antagonist_conc and ec50_shifted arrays required"}
        if ec50_control is None:
            return {"error": "ec50_control (EC50 without antagonist) required"}
        if len(conc_antag) != len(ec50_shifted):
            return {"error": "antagonist_conc and ec50_shifted must have equal length"}
        if len(conc_antag) < 2:
            return {"error": "need at least 2 antagonist concentrations for Schild regression"}

        B = np.array(conc_antag, dtype=float)
        ec50_w = np.array(ec50_shifted, dtype=float)
        ec50_c = float(ec50_control)

        # Dose ratio: DR = EC50_shifted / EC50_control
        DR = ec50_w / ec50_c
        # log(DR - 1) vs log[B]
        log_B = np.log10(B)
        log_dr1 = np.log10(DR - 1)
        mask = np.isfinite(log_dr1) & np.isfinite(log_B) & (DR > 1)
        if np.sum(mask) < 2:
            return {"error": "Need DR > 1 (EC50 must increase with antagonist). Check data."}

        slope, intercept = np.polyfit(log_B[mask], log_dr1[mask], 1)
        slope, intercept = float(slope), float(intercept)
        r_pred = slope * log_B[mask] + intercept
        ss_res = float(np.sum((log_dr1[mask] - r_pred) ** 2))
        ss_tot = float(np.sum((log_dr1[mask] - np.mean(log_dr1[mask])) ** 2))
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        # pA2 = x-intercept when slope constrained to 1 → -intercept_unconstrained
        # Standard: pA2 from constrained slope=1 = log10(1/KB)
        # If slope ≈ 1, pA2_schild = -intercept/slope
        pA2_schild = -intercept / slope if slope else None
        # KB (dissociation constant of antagonist) from pA2_schild
        KB = 10 ** (-pA2_schild) if pA2_schild is not None else None
        pA2 = pA2_schild  # pA2 ≈ pKB when slope = 1

        competitive = 0.85 <= abs(slope) <= 1.15
        result = {
            "pA2": round(float(pA2), 3) if pA2 else None,
            "pKB": round(float(pA2), 3) if pA2 else None,
            "KB_M": float(f"{KB:.2e}") if KB else None,
            "schild_slope": round(slope, 3),
            "R2": round(r2, 4),
            "dose_ratios": [round(float(x), 2) for x in DR],
            "mechanism": (
                "competitive antagonism (slope ≈ 1) — pA2 reliable"
                if competitive else
                f"non-competitive / allosteric (slope={slope:.2f} ≠ 1) — pA2 may be unreliable, use pKB cautiously"
            ),
            "interpretation": (
                f"pA2 = {pA2:.2f} (antagonist affinity), KB = {KB:.2e} M. "
                f"Schild slope = {slope:.2f} → {'competitive' if competitive else 'non-competitive'}."
            )
        }

        try:
            from modules.knowledge.auto_store import auto_store
            auto_store("pharmacology", f"Schild — pA2={pA2:.2f}",
                       result, source="Schild Regression", tags=["schild", "pa2", "antagonist"])
        except Exception:
            pass
        return result

    # ─────────────────────────────────────────────────────────────
    # Operational (Black-Leff) Model — efficacy vs affinity
    # Reference: Black & Leff, Proc R Soc Lond B, 1983.
    # ─────────────────────────────────────────────────────────────
    def _operational_model(self, input):
        """Black-Leff operational model → τ (transducer ratio), KA, receptor reserve."""
        emax_system = input.get("emax_system")  # maximal system response
        ec50_obs = input.get("ec50_observed")  # observed EC50 of agonist
        emax_obs = input.get("emax_observed")  # observed maximal response of agonist

        if None in (emax_system, ec50_obs, emax_obs):
            return {"error": "emax_system, ec50_observed, emax_observed required"}

        try:
            emax_sys = float(emax_system)
            ec50 = float(ec50_obs)
            emax_ag = float(emax_obs)
        except (TypeError, ValueError):
            return {"error": "emax_system, ec50_observed, emax_observed must be numbers"}
        if emax_sys <= 0 or ec50 <= 0 or emax_ag <= 0:
            return {"error": "all values must be positive"}

        # Operational model: E = Emax_sys * (τ * [A]) / ((KA + [A]) * (1 + τ) + τ * [A])
        # At EC50: E = Emax_obs/2, and Emax_obs = Emax_sys * τ / (1 + τ)
        # → solve for τ from Emax_obs / Emax_sys
        ratio = emax_ag / emax_sys
        if ratio >= 1.0:
            tau = float("inf")
            receptor_reserve = "full agonist, maximal stimulation (τ → ∞)"
        else:
            # τ / (1+τ) = ratio → τ = ratio / (1 - ratio)
            tau = ratio / (1.0 - ratio)
            # KA: from operational model, EC50 = KA * (1 + τ) / (1 + 2τ) approximately
            # Rearranging: KA = EC50 * (1 + 2τ) / (1 + τ)
            KA = ec50 * (1.0 + 2.0 * tau) / (1.0 + tau)
            receptor_reserve = (
                "high receptor reserve (spare receptors)"
                if tau > 10 else
                ("moderate receptor reserve" if tau > 3 else "low/no receptor reserve (full occupancy required)")
            )

        # Affinity vs efficacy interpretation
        if tau == float("inf"):
            KA = ec50  # Cannot resolve; KA ≈ EC50 for full agonists
            tau_str = "∞ (full agonist)"
        else:
            tau_str = f"{tau:.2f}"

        result = {
            "tau": tau_str,
            "KA": round(float(KA), 4),
            "KA_interpretation": "functional affinity (KA ≈ Kd only for full agonists)",
            "receptor_reserve": receptor_reserve,
            "efficacy_classification": (
                "full agonist" if ratio >= 0.85 else
                ("partial agonist" if ratio >= 0.25 else "weak partial agonist")
            ),
            "emax_ratio": round(ratio, 3),
            "interpretation": (
                f"τ = {tau_str}, KA = {KA:.3f}. Efficacy = {ratio*100:.1f}% of system max → "
                f"{('full' if ratio >= 0.85 else 'partial')} agonist with {receptor_reserve}."
            )
        }

        try:
            from modules.knowledge.auto_store import auto_store
            auto_store("pharmacology", f"Operational Model — τ={tau_str}",
                       result, source="Black-Leff Model", tags=["operational_model", "tau", "efficacy"])
        except Exception:
            pass
        return result

    # ─────────────────────────────────────────────────────────────
    # Selectivity Ratio — therapeutic window / target preference
    # Reference: Bowes et al., Nat Rev Drug Discov, 2012.
    # ─────────────────────────────────────────────────────────────
    def _selectivity_ratio(self, input):
        """Selectivity index across multiple targets."""
        targets = input.get("targets", [])  # [{"name":"A", "kd_or_ic50": 10, "unit":"nM"}, ...]
        therapeutic_target = input.get("therapeutic_target", "")
        unit = input.get("unit", "nM")

        if not targets:
            return {"error": "targets array required (each: {name, kd_or_ic50, unit})"}
        if len(targets) < 2:
            return {"error": "need at least 2 targets for selectivity comparison"}

        # Sort by potency (lower = more potent)
        sorted_t = sorted(targets, key=lambda x: float(x.get("kd_or_ic50", 1e9)))
        primary = sorted_t[0]
        ratios = []
        for t in sorted_t[1:]:
            primary_val = float(primary["kd_or_ic50"])
            off_val = float(t["kd_or_ic50"])
            ratio = off_val / primary_val if primary_val > 0 else None
            ratios.append({
                "off_target": t["name"],
                f"primary_{unit}": round(primary_val, 2),
                f"off_{unit}": round(off_val, 2),
                "selectivity_ratio": round(ratio, 1) if ratio else None,
                "fold_selective": f"{ratio:.0f}×" if ratio else "N/A",
                "therapeutic_relevance": (
                    "acceptable (>30×)" if ratio and ratio >= 30 else
                    ("marginal (10-30×)" if ratio and ratio >= 10 else "low selectivity (<10×)")
                )
            })

        # Therapeutic window if specified
        tw = None
        if therapeutic_target:
            tt = next((t for t in targets if t["name"].lower() == therapeutic_target.lower()), None)
            if tt:
                tt_val = float(tt["kd_or_ic50"])
                least_potent = max(float(t["kd_or_ic50"]) for t in targets if t["name"] != tt["name"])
                tw = round(least_potent / tt_val, 1) if tt_val > 0 else None

        result = {
            "primary_target": primary["name"],
            "primary_potency": f"{primary['kd_or_ic50']} {unit}",
            "selectivity_table": ratios,
            "therapeutic_window_fold": tw,
            "interpretation": (
                f"Primary target: {primary['name']} ({primary['kd_or_ic50']} {unit}). "
                f"Most selective off-target ratio: {ratios[-1]['fold_selective']}. "
                f"Aim for >30× selectivity over off-targets to minimize side effects."
            )
        }

        try:
            from modules.knowledge.auto_store import auto_store
            auto_store("pharmacology", f"Selectivity — primary={primary['name']}",
                       result, source="Selectivity Analysis", tags=["selectivity", "therapeutic_window"])
        except Exception:
            pass
        return result

    # ─────────────────────────────────────────────────────────────
    # Receptor Database — curated reference
    # ─────────────────────────────────────────────────────────────
    def _receptor_database(self, input):
        """Curated receptor/transporter/enzyme database."""
        query = input.get("query", "").lower().strip()

        RECEPTORS = [
            {"name": "β2-Adrenergic", "family": "GPCR (Class A)", "endogenous": "Epinephrine, Norepinephrine",
             "therapeutics": "Salbutamol, Salmeterol (agonists); Propranolol (antagonist)",
             "indication": "Asthma, COPD", "signal": "Gs → cAMP ↑"},
            {"name": "μ-Opioid (MOR)", "family": "GPCR (Class A)", "endogenous": "Endorphins, Enkephalins",
             "therapeutics": "Morphine, Fentanyl, Naloxone (antagonist)",
             "indication": "Pain", "signal": "Gi/o → cAMP ↓"},
            {"name": "D2 Dopamine", "family": "GPCR (Class A)", "endogenous": "Dopamine",
             "therapeutics": "Haloperidol, Risperidone (antagonists); Bromocriptine (agonist)",
             "indication": "Schizophrenia, Parkinson's", "signal": "Gi/o → cAMP ↓"},
            {"name": "5-HT2A", "family": "GPCR (Class A)", "endogenous": "Serotonin",
             "therapeutics": "Clozapine, LSD (agonist), Ketanserin (antagonist)",
             "indication": "Depression, Schizophrenia", "signal": "Gq → IP3/DAG"},
            {"name": "CB1 Cannabinoid", "family": "GPCR (Class A)", "endogenous": "Anandamide, 2-AG",
             "therapeutics": "Rimonabant (antagonist), Dronabinol (agonist)",
             "indication": "Appetite, Pain", "signal": "Gi/o → cAMP ↓"},
            {"name": "Histamine H1", "family": "GPCR (Class A)", "endogenous": "Histamine",
             "therapeutics": "Cetirizine, Loratadine (antagonists)",
             "indication": "Allergy", "signal": "Gq → IP3/DAG"},
            {"name": "Angiotensin II AT1", "family": "GPCR (Class A)", "endogenous": "Angiotensin II",
             "therapeutics": "Losartan, Valsartan (antagonists)",
             "indication": "Hypertension", "signal": "Gq → IP3/DAG"},
            {"name": "EGFR (ErbB1)", "family": "Receptor Tyrosine Kinase", "endogenous": "EGF, TGF-α",
             "therapeutics": "Gefitinib, Erlotinib, Cetuximab",
             "indication": "Non-small cell lung cancer", "signal": "MAPK/PI3K"},
            {"name": "VEGFR2", "family": "Receptor Tyrosine Kinase", "endogenous": "VEGF-A",
             "therapeutics": "Sunitinib, Sorafenib, Bevacizumab",
             "indication": "Renal, Hepatocellular carcinoma", "signal": "MAPK/PI3K"},
            {"name": "BCR-ABL", "family": "Tyrosine Kinase", "endogenous": "— (fusion oncogene)",
             "therapeutics": "Imatinib, Dasatinib, Nilotinib",
             "indication": "Chronic myeloid leukemia", "signal": "Constitutive kinase"},
            {"name": "JAK2", "family": "Non-receptor Tyr Kinase", "endogenous": "Cytokines (IL, IFN)",
             "therapeutics": "Ruxolitinib, Tofacitinib",
             "indication": "Myelofibrosis, Rheumatoid arthritis", "signal": "JAK-STAT"},
            {"name": "mTOR", "family": "Ser/Thr Kinase", "endogenous": "Insulin, growth factors",
             "therapeutics": "Rapamycin, Everolimus",
             "indication": "Transplant rejection, Cancer", "signal": "mTORC1/2"},
            {"name": "HER2 (ErbB2)", "family": "Receptor Tyrosine Kinase", "endogenous": "Heregulin",
             "therapeutics": "Trastuzumab, Lapatinib, Pertuzumab",
             "indication": "Breast cancer", "signal": "MAPK/PI3K"},
            {"name": "HERG (hERG/KCNH2)", "family": "Ion Channel (K+)", "endogenous": "—",
             "therapeutics": "Avoid blockade (cardiotoxicity screen)",
             "indication": "Cardiac safety target", "signal": "IKr current"},
            {"name": "Voltage-gated Na+ (Nav1.5)", "family": "Ion Channel (Na+)", "endogenous": "—",
             "therapeutics": "Lidocaine, Mexiletine, Flecainide",
             "indication": "Arrhythmia, Epilepsy", "signal": "Na+ influx"},
            {"name": "L-type Ca2+ (Cav1.2)", "family": "Ion Channel (Ca2+)", "endogenous": "—",
             "therapeutics": "Amlodipine, Verapamil, Diltiazem",
             "indication": "Hypertension, Angina", "signal": "Ca2+ influx"},
            {"name": "GABAA", "family": "Ligand-gated Cl- channel", "endogenous": "GABA",
             "therapeutics": "Diazepam, Zolpidem, Propofol (PAMs)",
             "indication": "Anxiety, Epilepsy, Anesthesia", "signal": "Cl- influx"},
            {"name": "NMDA", "family": "Ligand-gated cation channel", "endogenous": "Glutamate, Glycine",
             "therapeutics": "Ketamine, Memantine (antagonists)",
             "indication": "Anesthesia, Alzheimer's", "signal": "Na+/Ca2+ influx"},
            {"name": "P-glycoprotein (MDR1)", "family": "ABC Transporter", "endogenous": "—",
             "therapeutics": "Verapamil, Cyclosporin (inhibitors)",
             "indication": "Drug resistance, BBB transport", "signal": "ATP-driven efflux"},
            {"name": "SERCA", "family": "P-type ATPase", "endogenous": "—",
             "therapeutics": "Thapsigargin (inhibitor)",
             "indication": "Research tool, Cardiac contractility", "signal": "Ca2+ into SR"},
            {"name": "ACE", "family": "Carboxypeptidase", "endogenous": "Angiotensin I",
             "therapeutics": "Enalapril, Lisinopril",
             "indication": "Hypertension, Heart failure", "signal": "Angiotensin II production"},
            {"name": "HMG-CoA Reductase", "family": "Oxidoreductase", "endogenous": "HMG-CoA",
             "therapeutics": "Atorvastatin, Simvastatin",
             "indication": "Hypercholesterolemia", "signal": "Cholesterol synthesis ↓"},
            {"name": "PDE5", "family": "Phosphodiesterase", "endogenous": "cGMP",
             "therapeutics": "Sildenafil, Tadalafil",
             "indication": "Erectile dysfunction, PAH", "signal": "cGMP ↑"},
            {"name": "COX-2", "family": "Cyclooxygenase", "endogenous": "Arachidonic acid",
             "therapeutics": "Celecoxib, Rofecoxib",
             "indication": "Inflammation, Pain", "signal": "Prostaglandin H2"},
            {"name": "Aromatase (CYP19A1)", "family": "Cytochrome P450", "endogenous": "Androstenedione",
             "therapeutics": "Letrozole, Anastrozole",
             "indication": "Breast cancer (ER+)", "signal": "Estrogen synthesis ↓"},
            {"name": "DPP-4", "family": "Dipeptidyl peptidase", "endogenous": "GLP-1, GIP",
             "therapeutics": "Sitagliptin, Linagliptin",
             "indication": "Type 2 diabetes", "signal": "Incretin levels ↑"},
        ]

        families = sorted(set(r["family"] for r in RECEPTORS))
        if query:
            matches = [r for r in RECEPTORS if query in r["name"].lower() or query in r["family"].lower()
                       or query in r["indication"].lower() or query in r["therapeutics"].lower()]
            return {
                "query": query,
                "matches": matches,
                "count": len(matches),
                "families": families,
                "total_in_db": len(RECEPTORS),
            }
        return {
            "receptors": RECEPTORS,
            "count": len(RECEPTORS),
            "families": families,
            "hint": "Pass query=name/family/indication to filter"
        }

    # ─────────────────────────────────────────────────────────────
    # In-Vivo Study Design — animal models + power analysis
    # Reference: Festing, ILAR J, 2002 (sample size); animal model refs in dict.
    # ─────────────────────────────────────────────────────────────
    def _in_vivo_design(self, input):
        """Animal model selection + group sizing power analysis + dosing."""
        endpoint = input.get("endpoint", "").lower()  # anti-inflammatory | analgesic | antidiabetic | stroke | anticancer
        effect_size = float(input.get("effect_size", 1.5))  # Cohen's d (1.0=medium, 1.5=large)
        alpha = float(input.get("alpha", 0.05))
        power = float(input.get("power", 0.80))
        species = input.get("species", "rat").lower()

        MODELS = {
            "anti-inflammatory": {
                "models": [
                    {"name": "Carrageenan paw edema", "species": "Rat (Wistar/SD)",
                     "induction": "1% λ-carrageenan 0.1 mL intraplantar",
                     "readout": "Paw volume (plethysmometer) at 1, 2, 3, 4, 5 h",
                     "positive_control": "Indomethacin 10 mg/kg p.o.", "ref": "Winter et al., 1962"},
                    {"name": "Formalin test", "species": "Mouse/Rat",
                     "induction": "2.5% formalin 20 µL intraplantar",
                     "readout": "Licking/biting time (phase 1: 0-5min, phase 2: 15-30min)",
                     "positive_control": "Diclofenac 10 mg/kg", "ref": "Hunskaar & Hole, 1987"},
                    {"name": "Cotton pellet granuloma", "species": "Rat",
                     "induction": "10 mg sterile cotton pellet subcutaneous, 7 days",
                     "readout": "Granuloma dry weight", "positive_control": "Dexamethasone 1 mg/kg",
                     "ref": "D'Arcy & Howard, 1962"},
                ],
                "typical_dose_range": "50-400 mg/kg (plant extracts); 5-50 mg/kg (pure compounds)",
            },
            "analgesic": {
                "models": [
                    {"name": "Hot plate test", "species": "Mouse/Rat",
                     "induction": "Hot plate 52-55°C",
                     "readout": "Reaction latency (licking/jumping) at 0,30,60,90 min, cut-off 30s",
                     "positive_control": "Morphine 5 mg/kg i.p.", "ref": "Woolfe & Macdonald, 1944"},
                    {"name": "Tail flick test", "species": "Mouse/Rat",
                     "induction": "Radiant heat on tail",
                     "readout": "Tail withdrawal latency, cut-off 10s",
                     "positive_control": "Pentazocine 10 mg/kg", "ref": "D'Amour & Smith, 1941"},
                    {"name": "Acetic acid writhing", "species": "Mouse",
                     "induction": "0.6% acetic acid 10 mL/kg i.p.",
                     "readout": "Writhes in 20 min", "positive_control": "Aspirin 100 mg/kg",
                     "ref": "Koster et al., 1959"},
                ],
                "typical_dose_range": "50-300 mg/kg (extracts); 1-20 mg/kg (compounds)",
            },
            "antidiabetic": {
                "models": [
                    {"name": "STZ-induced diabetes", "species": "Rat/Mouse",
                     "induction": "Streptozotocin 55-65 mg/kg i.v. (single dose)",
                     "readout": "Blood glucose, insulin, HbA1c; 72h & 4-8 weeks",
                     "positive_control": "Glibenclamide 5 mg/kg or Metformin 250 mg/kg", "ref": "Furman, 2021"},
                    {"name": "Alloxan-induced", "species": "Rat/Rabbit",
                     "induction": "Alloxan 120-150 mg/kg i.v.",
                     "readout": "Blood glucose over 7-28 days",
                     "positive_control": "Insulin 2-4 IU", "ref": "Dunn & McLetchie, 1943"},
                    {"name": "db/db genetic", "species": "Mouse (db/db)",
                     "induction": "Genetic (leptin receptor deficient)",
                     "readout": "Glucose, insulin, lipids over 4-12 weeks",
                     "positive_control": "Pioglitazone 10 mg/kg", "ref": "Hummel et al., 1966"},
                ],
                "typical_dose_range": "100-500 mg/kg (extracts); 5-50 mg/kg (compounds)",
            },
            "stroke": {
                "models": [
                    {"name": "MCAO (middle cerebral artery occlusion)", "species": "Rat (SD/Wistar)",
                     "induction": "Intraluminal suture, 60-90 min occlusion, reperfusion",
                     "readout": "Infarct volume (TTC), neurological score at 24-72h",
                     "positive_control": "— (few effective in man)", "ref": "Longa et al., 1989"},
                    {"name": "Photothrombotic stroke", "species": "Mouse/Rat",
                     "induction": "Rose Bengal + cold light irradiation through skull",
                     "readout": "Infarct size, sensorimotor tests at 1-7 days",
                     "positive_control": "—", "ref": "Watson et al., 1985"},
                ],
                "typical_dose_range": "1-50 mg/kg; pre-treatment common",
            },
            "anticancer": {
                "models": [
                    {"name": "Xenograft (subcutaneous)", "species": "Mouse (nu/nu, SCID)",
                     "induction": "1×10⁶ tumor cells s.c. flank",
                     "readout": "Tumor volume (caliper) q3d, body weight, survival",
                     "positive_control": "Cisplatin 3 mg/kg i.p. or 5-FU 25 mg/kg", "ref": "Garralda et al., 2019"},
                    {"name": "Ehrlich ascites", "species": "Mouse",
                     "induction": "1×10⁶ EAC cells i.p.",
                     "readout": "Survival, ascites volume, body weight",
                     "positive_control": "5-FU 20 mg/kg", "ref": "Sledge & Dexeus, 1985"},
                    {"name": "DMBA-induced breast cancer", "species": "Rat",
                     "induction": "DMBA 80 mg/kg single oral dose, 8-12 weeks",
                     "readout": "Tumor incidence, multiplicity, volume",
                     "positive_control": "Tamoxifen 2 mg/kg", "ref": "Huggins et al., 1961"},
                ],
                "typical_dose_range": "10-200 mg/kg; chronic dosing 2-4 weeks",
            },
        }

        # ── Power analysis (group size) ──
        # Simplified Lehr's formula: n = 16 / d² (per group, two-sample t-test, α=0.05, power=0.80)
        # Generalized: n ≈ 2 * (z_α/2 + z_β)² / d²
        from scipy.stats import norm
        z_alpha = norm.ppf(1 - alpha / 2)
        z_beta = norm.ppf(power)
        n_per_group = math.ceil(2 * ((z_alpha + z_beta) ** 2) / (effect_size ** 2))
        n_per_group = max(n_per_group, 6)  # ethical minimum

        # Total animals
        n_groups = 4  # vehicle + low + mid + high + (positive control = 5)
        total_animals = n_per_group * (n_groups + 1)  # +1 for positive control group

        # Refine by species
        species_note = {
            "mouse": "Mice: typically 20-30g, group size 6-10",
            "rat": "Rats: 200-300g Wistar/SD, group size 6-8",
            "rabbit": "Rabbits: 2-3 kg NZW, group size 4-6",
        }.get(species, "Standard group sizes apply")

        if endpoint not in MODELS:
            return {
                "error": f"endpoint must be one of: {list(MODELS.keys())}",
                "hint": "endpoint options: anti-inflammatory, analgesic, antidiabetic, stroke, anticancer"
            }

        result = {
            "endpoint": endpoint,
            "species_default": species,
            "models": MODELS[endpoint]["models"],
            "typical_dose_range": MODELS[endpoint]["typical_dose_range"],
            "study_groups": [
                {"group": "Vehicle control", "n": n_per_group, "purpose": "Negative control (CMC/saline)"},
                {"group": "Low dose", "n": n_per_group, "purpose": "1/10 of high dose or 1×ED₅₀"},
                {"group": "Mid dose", "n": n_per_group, "purpose": "1/3 of high dose"},
                {"group": "High dose", "n": n_per_group, "purpose": "MTD or 10× low dose"},
                {"group": "Positive control", "n": n_per_group, "purpose": "Validate assay sensitivity"},
            ],
            "power_analysis": {
                "effect_size_cohen_d": effect_size,
                "alpha": alpha,
                "power_target": power,
                "n_per_group": n_per_group,
                "total_animals": total_animals,
                "method": "Two-sample t-test, Lehr approximation"
            },
            "species_guidance": species_note,
            "ethics_note": (
                "Apply 3Rs (Replace, Reduce, Refine). "
                "Minimize to n_per_group above — do not exceed without justification. "
                "Approval from Institutional Animal Ethics Committee (IAEC/IACUC) mandatory."
            ),
        }

        try:
            from modules.knowledge.auto_store import auto_store
            auto_store("pharmacology", f"In-Vivo Design — {endpoint}",
                       result, source="In-Vivo Study Designer", tags=["in_vivo", endpoint, "animal_models"])
        except Exception:
            pass
        return result


    # -- Enzyme kinetics (ported from biodockify-web biochemistry/pharmacology) --

    def _enzyme_kinetics(self, input):
        """Michaelis-Menten fit: Vmax and Km from substrate-velocity data, with
        Lineweaver-Burk cross-check."""
        substrate = input.get("substrate", [])
        velocity = input.get("velocity", [])
        if not substrate or not velocity:
            return {"error": "substrate and velocity arrays required"}
        if len(substrate) != len(velocity):
            return {"error": "substrate and velocity must have equal length"}
        if len(substrate) < 4:
            return {"error": "need at least 4 [S]-v points"}

        s = np.array(substrate, dtype=float)
        v = np.array(velocity, dtype=float)
        mask = (s > 0) & (v > 0)
        s, v = s[mask], v[mask]
        if len(s) < 4:
            return {"error": "need at least 4 positive [S]-v points"}

        def mm(x, vmax, km):
            return vmax * x / (km + x)

        from scipy.optimize import curve_fit
        vmax0 = float(np.max(v))
        km0 = float(np.median(s))
        try:
            popt, pcov = curve_fit(mm, s, v, p0=[vmax0, km0], maxfev=20000,
                                   bounds=([0.0, 1e-12], [np.inf, np.inf]))
        except Exception as e:
            return {"error": f"Michaelis-Menten fit failed: {e}"}
        vmax, km = float(popt[0]), float(popt[1])

        v_pred = mm(s, *popt)
        ss_res = float(np.sum((v - v_pred) ** 2))
        ss_tot = float(np.sum((v - np.mean(v)) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else None

        try:
            lb_slope, lb_int = np.polyfit(1.0 / s, 1.0 / v, 1)
            vmax_lb = float(1.0 / lb_int) if lb_int != 0 else None
            km_lb = float(lb_slope * vmax_lb) if vmax_lb else None
        except Exception:
            vmax_lb, km_lb = None, None

        kcat = input.get("kcat")
        efficiency = float(kcat / km) if kcat and km else None

        xs = np.linspace(float(np.min(s)), float(np.max(s)), 50)
        curve = [{"x": float(x), "y": float(mm(x, *popt))} for x in xs]

        return {
            "vmax": round(vmax, 6), "km": round(km, 6),
            "r_squared": round(r2, 6) if r2 is not None else None,
            "lineweaver_burk": {"vmax": round(vmax_lb, 6) if vmax_lb else None,
                                "km": round(km_lb, 6) if km_lb else None,
                                "note": "LB is unweighted and biased toward low [S]; the nonlinear fit is the primary estimate."},
            "kcat": kcat,
            "catalytic_efficiency_kcat_over_km": round(efficiency, 4) if efficiency else None,
            "n_points": int(len(s)),
            "predicted_curve": curve,
            "model": "v = Vmax*[S] / (Km + [S])",
            "note": "Report Vmax/Km with the nonlinear-fit R2; use LB only as a visual cross-check.",
        }

    def _inhibition(self, input):
        """Enzyme inhibition analysis.

        competitive: velocity MATRIX v[I][S] -> LB slopes vs [I] -> Ki (x-intercept = -Ki)
        ic50: velocities vs [I] at fixed [S] -> 4PL IC50, Ki via Cheng-Prusoff (needs km + [S])
        """
        inhibitor = input.get("inhibitor", [])
        substrate = input.get("substrate", [])
        velocities = input.get("velocities", [])
        km = input.get("km")
        mode = input.get("mode", "")

        if not inhibitor:
            return {"error": "inhibitor concentrations required"}
        if len(inhibitor) < 2:
            return {"error": "need at least 2 inhibitor concentrations"}

        i_arr = np.array(inhibitor, dtype=float)
        is_matrix = (isinstance(velocities, list) and len(velocities) > 1
                     and all(isinstance(r, list) for r in velocities))
        if not mode:
            mode = "competitive" if (is_matrix and len(substrate) >= 3
                                     and all(len(r) == len(substrate) for r in velocities)
                                     and len(velocities) == len(inhibitor)) else "ic50"

        if mode == "competitive":
            if not is_matrix:
                return {"error": "competitive mode needs velocities as a matrix: velocities[i][j] at [I]_i, [S]_j"}
            s = np.array(substrate, dtype=float)
            slopes, intercepts = [], []
            per_curve = []
            for ii, vrow in zip(i_arr, velocities):
                v = np.array(vrow, dtype=float)
                xs, ys = [], []
                for si, vi in zip(s, v):
                    if si > 0 and vi > 0:
                        xs.append(1.0 / si); ys.append(1.0 / vi)
                if len(xs) >= 2:
                    slope, intercept = np.polyfit(np.array(xs), np.array(ys), 1)
                    slopes.append(float(slope)); intercepts.append(float(intercept))
                    per_curve.append({"inhibitor_conc": float(ii),
                                      "lb_slope": round(float(slope), 6),
                                      "lb_intercept": round(float(intercept), 6)})
                else:
                    slopes.append(None)
                    per_curve.append({"inhibitor_conc": float(ii), "lb_slope": None})
            valid = [(ii, sl) for ii, sl in zip(i_arr, slopes) if sl is not None]
            if len(valid) < 2:
                return {"error": "Not enough valid Lineweaver-Burk points per [I]"}
            xs_i = np.array([x for x, _ in valid]); ys_s = np.array([y for _, y in valid])
            m, b = np.polyfit(xs_i, ys_s, 1)
            # LB slope line: slope(I) = (Km/Vmax)(1 + I/Ki) -> x-intercept at I = -Ki,
            # so Ki = b/m (the webapp's -b/m is always negative and self-nulifies)
            ki = float(b / m) if m > 0 else None
            vmax_shared = float(1.0 / np.mean(intercepts)) if intercepts else None
            km0 = float(b * vmax_shared) if vmax_shared else None
            ss_res = float(np.sum((ys_s - (m * xs_i + b)) ** 2))
            ss_tot = float(np.sum((ys_s - np.mean(ys_s)) ** 2))
            r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else None
            return {
                "mode": "competitive_lineweaver_burk",
                "ki": round(ki, 6) if ki and ki > 0 else None,
                "vmax": round(vmax_shared, 6) if vmax_shared else None,
                "km_app_at_zero_inhibitor": round(km0, 6) if km0 else None,
                "slope_vs_I": round(float(m), 6), "intercept_vs_I": round(float(b), 6),
                "r_squared": round(r2, 6) if r2 is not None else None,
                "per_inhibitor_curves": per_curve,
                "method": "slope(I) = (Km/Vmax)(1 + I/Ki); x-intercept = -Ki (Dixon-style LB analysis)",
            }

        if is_matrix:
            v_series = [r[0] for r in velocities if len(r) >= 1]
        else:
            v_series = list(velocities)
        if len(v_series) != len(inhibitor) or len(v_series) < 3:
            return {"error": "IC50 mode needs velocities aligned 1:1 with inhibitor concentrations (>=3 points)"}
        v = np.array(v_series, dtype=float)
        top0, bottom0 = float(np.max(v)), float(np.min(v))
        ic50_0 = float(np.median(i_arr[i_arr > 0])) if np.any(i_arr > 0) else 1.0

        def four_pl(x, bottom, top, ic50, hill):
            return bottom + (top - bottom) / (1.0 + (x / ic50) ** hill)

        from scipy.optimize import curve_fit
        try:
            popt, _ = curve_fit(four_pl, i_arr, v, p0=[bottom0, top0, ic50_0, 1.0],
                                bounds=([0, 0, 1e-12, -20], [1e12, 1e12, 1e12, 20]),
                                maxfev=20000)
        except Exception as e:
            return {"error": f"IC50 fit failed: {e}"}
        bottom_f, top_f, ic50_f, hill_f = (float(x) for x in popt)
        v_pred = four_pl(i_arr, *popt)
        ss_res = float(np.sum((v - v_pred) ** 2))
        ss_tot = float(np.sum((v - np.mean(v)) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else None

        ki_val, cheng = None, None
        s_fixed = float(substrate[0]) if substrate else None
        if km and s_fixed:
            cheng = 1.0 + s_fixed / float(km)
            ki_val = ic50_f / cheng if cheng > 0 else None

        xs = np.linspace(float(np.min(i_arr)), float(np.max(i_arr)), 50)
        curve = [{"x": float(x), "y": float(four_pl(x, *popt))} for x in xs]
        return {
            "mode": "ic50_4pl",
            "ic50": round(ic50_f, 6), "hill": round(hill_f, 4),
            "bottom": round(bottom_f, 6), "top": round(top_f, 6),
            "r_squared": round(r2, 6) if r2 is not None else None,
            "ki_cheng_prusoff": round(ki_val, 6) if ki_val else None,
            "cheng_prusoff_factor": round(cheng, 4) if cheng else None,
            "cheng_note": None if cheng else "Provide km and substrate (fixed [S]) to convert IC50 to Ki",
            "n_points": int(len(i_arr)),
            "predicted_curve": curve,
            "model": "v(I) = bottom + (top-bottom)/(1 + (I/IC50)^hill)",
        }
