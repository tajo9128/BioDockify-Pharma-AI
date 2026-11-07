"""Pharmacoeconomics Mini-Lab — additive module (Pharmacy Practice department).

  · Cost-effectiveness: ICER (incremental cost / incremental effect)
  · QALYs (utility × duration), NNT, cost per QALY vs threshold (WTP)
  · Budget impact: population, market share shift, annual cost delta
  · Sensitivity: acceptability curve sample + one-way ranges
"""
from __future__ import annotations

from typing import Any, Dict


def cost_effectiveness(cost_new: float, cost_comparator: float,
                       effect_new: float, effect_comparator: float,
                       wtp_threshold: float = 100000.0) -> Dict[str, Any]:
    """ICER + dominance assessment vs willingness-to-pay (₹/QALY or any currency)."""
    if effect_new == effect_comparator:
        return {"error": "identical effects — ICER undefined; run cost-minimisation instead"}
    d_cost = cost_new - cost_comparator
    d_effect = effect_new - effect_comparator
    icer = d_cost / d_effect
    if d_cost <= 0 and d_effect > 0:
        verdict = "DOMINANT — cheaper AND more effective"
    elif d_cost > 0 and d_effect < 0:
        verdict = "DOMINATED — costlier AND less effective; reject"
    else:
        verdict = (f"cost-effective at WTP {wtp_threshold:,.0f}" if icer <= wtp_threshold
                   else f"NOT cost-effective at WTP {wtp_threshold:,.0f}")
    return {"incremental_cost": round(d_cost, 2),
            "incremental_effect": round(d_effect, 4),
            "icer_per_qaly_or_unit": round(icer, 2),
            "wtp_threshold": wtp_threshold,
            "verdict": verdict,
            "note": "Typical WTP thresholds: ₹1–3 lakh/QALY (India informal), $50k–150k/QALY (US), £20–30k (NICE)."}


def qaly_calc(utility_before: float, utility_after: float, years: float,
              discount: float = 0.03) -> Dict[str, Any]:
    """QALYs gained with optional annual discounting."""
    if not (0 <= utility_before <= 1 and 0 <= utility_after <= 1):
        return {"error": "utilities must be 0–1 (EQ-5D/HUI scale)"}
    if years <= 0:
        return {"error": "years > 0 required"}
    undiscounted = (utility_after - utility_before) * years
    disc = 0.0
    for t in range(1, int(years) + 1):
        disc += (utility_after - utility_before) / ((1 + discount) ** t)
    return {"qaly_gained_undiscounted": round(undiscounted, 4),
            "qaly_gained_discounted": round(disc, 4),
            "discount_rate": discount,
            "note": "Discounting per Indian HTA guidelines (3%) / NICE (3.5%)."}


def nnt_cost(arr_control: float, arr_treatment: float,
             cost_per_patient_treatment: float, cost_per_patient_control: float = 0.0) -> Dict[str, Any]:
    """NNT and cost per additional responder."""
    if arr_treatment <= arr_control:
        return {"error": "treatment ARR must exceed control (else NNT meaningless/negative)"}
    ard = arr_treatment - arr_control
    nnt = 1 / ard
    cost_per_responder = (cost_per_patient_treatment - cost_per_patient_control) * nnt
    return {"absolute_risk_reduction": round(ard, 4),
            "nnt": round(nnt, 1),
            "cost_per_additional_responder": round(cost_per_responder, 2),
            "note": "ARR inputs as proportions (0–1). Cost per responder = Δcost × NNT."}


def budget_impact(population: int, patients_diagnosed_pct: float,
                  treated_pct_current: float, treated_pct_new: float,
                  cost_per_patient_current: float, cost_per_patient_new: float,
                  years: int = 1) -> Dict[str, Any]:
    """Annual/plan budget impact of a market-share formulary change."""
    if population <= 0:
        return {"error": "population > 0"}
    diagnosed = population * patients_diagnosed_pct / 100
    cur_users = diagnosed * treated_pct_current / 100
    new_users = diagnosed * treated_pct_new / 100
    annual_current = cur_users * cost_per_patient_current
    annual_new = new_users * cost_per_patient_new
    delta = annual_new - annual_current
    return {"eligible_patients": round(diagnosed),
            "current_users": round(cur_users), "projected_users": round(new_users),
            "annual_cost_current": round(annual_current, 2),
            "annual_cost_new": round(annual_new, 2),
            "annual_budget_delta": round(delta, 2),
            f"total_{years}_year_delta": round(delta * years, 2),
            "verdict": ("saves money" if delta < 0 else "budget increase — plan funding/price negotiation"),
            "note": "Static model; add indication expansion/price erosion over time for submission-grade BIA."}


def sensitivity(cost_new: float, cost_comp: float, eff_new: float, eff_comp: float,
                wtp_low: float = 0, wtp_high: float = 200000, steps: int = 8) -> Dict[str, Any]:
    """One-way ICER across effect-multiplicity + acceptability grid at WTPs."""
    rows = []
    for i in range(steps + 1):
        wtp = wtp_low + (wtp_high - wtp_low) * i / steps
        icer = (cost_new - cost_comp) / (eff_new - eff_comp) if eff_new != eff_comp else float("inf")
        rows.append({"wtp": round(wtp), "icer": round(icer, 1) if abs(icer) != float("inf") else "∞",
                     "acceptable": icer <= wtp})
    # effect one-way (±30% on incremental effect)
    de = eff_new - eff_comp
    effect_rows = []
    for mult in (0.7, 0.85, 1.0, 1.15, 1.3):
        e = eff_comp + de * mult
        if eff_new != e:
            effect_rows.append({"effect_mult": mult, "icer": round((cost_new - cost_comp) / (e - eff_comp), 1)})
    return {"wtp_grid": rows, "effect_variation": effect_rows,
            "note": "Deterministic sensitivity only; PSA (Monte-Carlo) needs distributions — use the Statistics module's bootstrap tools."}
