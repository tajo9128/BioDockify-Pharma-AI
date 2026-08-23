"""Pharmacovigilance disproportionality analysis.

RESEARCH and ACADEMIC module — signal detection is hypothesis-generating only and
never establishes causality.

Extends the prototype's odds-ratio helper with the two measures actually used for
spontaneous-report signal detection: the Proportional Reporting Ratio with its
chi-square, and the Reporting Odds Ratio with a confidence interval.

Contingency table
-----------------
                       Event of interest   Other events
Drug of interest              a                 b
All other drugs               c                 d

References
----------
PRR : Evans SJW, Waller PC, Davis S. Pharmacoepidemiol Drug Saf. 2001;10(6):483-486.
ROR : Rothman KJ, Lanes S, Sacks ST. Pharmacoepidemiol Drug Saf. 2004;13(8):519-523.
EBGM background : Szarfman A et al. Drug Saf. 2002;25(6):381-392.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

SIGNAL_NOTICE = (
    "Disproportionality analysis is hypothesis-generating only. A signal is not "
    "evidence of causality and is subject to reporting bias, confounding, and "
    "differences in exposure."
)

Z_95 = 1.959963984540054


class SafetySignalInputError(ValueError):
    """Invalid caller-supplied contingency input."""


def _count(value: Any, name: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise SafetySignalInputError(f"{name} must be a whole number") from exc
    if number < 0:
        raise SafetySignalInputError(f"{name} must not be negative")
    if number > 10_000_000:
        raise SafetySignalInputError(f"{name} exceeds the supported range")
    return number


def analyze_contingency(
    a: int,
    b: int,
    c: int,
    d: int,
    *,
    label: Optional[str] = None,
    min_cases: int = 3,
    prr_threshold: float = 2.0,
    chi_square_threshold: float = 4.0,
) -> Dict[str, Any]:
    """Compute PRR, ROR, and odds ratio for one drug-event pair."""
    a_n, b_n, c_n, d_n = (
        _count(a, "a"), _count(b, "b"), _count(c, "c"), _count(d, "d")
    )
    if (a_n + b_n) == 0 or (c_n + d_n) == 0:
        raise SafetySignalInputError("Each row of the table must contain at least one report")
    if (a_n + c_n) == 0:
        raise SafetySignalInputError("The event column must contain at least one report")

    total = a_n + b_n + c_n + d_n

    # ── Proportional Reporting Ratio with chi-square (Evans 2001) ──
    drug_total = a_n + b_n
    other_total = c_n + d_n
    prop_drug = a_n / drug_total
    prop_other = c_n / other_total

    prr: Optional[float] = None
    prr_ci: Optional[List[float]] = None
    if prop_other > 0 and a_n > 0:
        prr = prop_drug / prop_other
        se_log_prr = math.sqrt(
            1.0 / a_n - 1.0 / drug_total + 1.0 / c_n - 1.0 / other_total
        ) if c_n > 0 else None
        if se_log_prr and se_log_prr > 0:
            log_prr = math.log(prr)
            prr_ci = [
                round(math.exp(log_prr - Z_95 * se_log_prr), 4),
                round(math.exp(log_prr + Z_95 * se_log_prr), 4),
            ]

    # Yates-uncorrected chi-square on the 2x2 table.
    chi_square: Optional[float] = None
    row1, row2 = drug_total, other_total
    col1, col2 = a_n + c_n, b_n + d_n
    if row1 and row2 and col1 and col2:
        expected_a = row1 * col1 / total
        chi_square = sum(
            (observed - expected) ** 2 / expected
            for observed, expected in (
                (a_n, expected_a),
                (b_n, row1 * col2 / total),
                (c_n, row2 * col1 / total),
                (d_n, row2 * col2 / total),
            )
            if expected > 0
        )

    # ── Reporting Odds Ratio with Haldane-Anscombe continuity correction ──
    correction_applied = 0 in (a_n, b_n, c_n, d_n)
    ac, bc, cc, dc = (
        (a_n + 0.5, b_n + 0.5, c_n + 0.5, d_n + 0.5)
        if correction_applied else (float(a_n), float(b_n), float(c_n), float(d_n))
    )
    ror = (ac * dc) / (bc * cc)
    se_log_ror = math.sqrt(1.0 / ac + 1.0 / bc + 1.0 / cc + 1.0 / dc)
    log_ror = math.log(ror)
    ror_ci = [
        round(math.exp(log_ror - Z_95 * se_log_ror), 4),
        round(math.exp(log_ror + Z_95 * se_log_ror), 4),
    ]

    # ── Signal criteria ──
    prr_criterion = (
        prr is not None
        and a_n >= min_cases
        and prr >= prr_threshold
        and chi_square is not None
        and chi_square >= chi_square_threshold
    )
    ror_criterion = ror_ci[0] > 1.0 and a_n >= min_cases

    if prr_criterion and ror_criterion:
        strength = "signal_by_both_criteria"
    elif prr_criterion or ror_criterion:
        strength = "signal_by_one_criterion"
    else:
        strength = "no_signal"

    interpretation: List[str] = []
    if a_n < min_cases:
        interpretation.append(
            f"Only {a_n} case(s) reported; below the {min_cases}-case minimum, so any "
            "apparent disproportionality is unstable."
        )
    if correction_applied:
        interpretation.append(
            "A zero cell was present, so a 0.5 continuity correction was applied to the "
            "reporting odds ratio."
        )
    if strength == "no_signal":
        interpretation.append("Configured disproportionality thresholds were not met.")
    else:
        interpretation.append(
            "Disproportionate reporting was detected. This warrants case-level review, "
            "not a causal conclusion."
        )

    return {
        "label": (str(label)[:120] if label else None),
        "table": {"a": a_n, "b": b_n, "c": c_n, "d": d_n, "total": total},
        "cases": a_n,
        "prr": round(prr, 4) if prr is not None else None,
        "prr_95_ci": prr_ci,
        "chi_square": round(chi_square, 4) if chi_square is not None else None,
        "ror": round(ror, 4),
        "ror_95_ci": ror_ci,
        "continuity_correction_applied": correction_applied,
        "criteria": {
            "min_cases": min_cases,
            "prr_threshold": prr_threshold,
            "chi_square_threshold": chi_square_threshold,
            "ror_rule": "lower bound of the 95% confidence interval above 1",
        },
        "prr_criterion_met": prr_criterion,
        "ror_criterion_met": ror_criterion,
        "signal": strength,
        "interpretation": " ".join(interpretation),
        "notice": SIGNAL_NOTICE,
        "reference": "Evans 2001 (PRR); Rothman 2004 (ROR)",
    }


def analyze_event_series(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze several drug-event pairs and return forest-plot-ready rows."""
    if not events:
        raise SafetySignalInputError("Provide at least one drug-event pair")
    if len(events) > 500:
        raise SafetySignalInputError("A maximum of 500 pairs can be analyzed at once")

    rows: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []

    for index, item in enumerate(events):
        if not isinstance(item, dict):
            errors.append({"index": str(index), "error": "entry is not an object"})
            continue
        try:
            rows.append(analyze_contingency(
                item.get("a"), item.get("b"), item.get("c"), item.get("d"),
                label=item.get("label") or item.get("event"),
                min_cases=int(item.get("min_cases", 3)),
                prr_threshold=float(item.get("prr_threshold", 2.0)),
                chi_square_threshold=float(item.get("chi_square_threshold", 4.0)),
            ))
        except (SafetySignalInputError, TypeError, ValueError) as exc:
            errors.append({
                "index": str(index),
                "label": str(item.get("label") or item.get("event") or "")[:120],
                "error": str(exc),
            })

    signals = [row for row in rows if row["signal"] != "no_signal"]
    ranked = sorted(
        signals,
        key=lambda row: (row["prr"] if row["prr"] is not None else row["ror"]),
        reverse=True,
    )

    return {
        "analyzed": len(rows),
        "rejected": len(errors),
        "errors": errors[:50],
        "signal_count": len(signals),
        "rows": rows,
        "ranked_signals": [
            {
                "label": row["label"],
                "cases": row["cases"],
                "prr": row["prr"],
                "ror": row["ror"],
                "ror_95_ci": row["ror_95_ci"],
                "signal": row["signal"],
            }
            for row in ranked[:50]
        ],
        "multiplicity_caveat": (
            "Screening many drug-event pairs inflates the chance of spurious signals. "
            "No multiplicity adjustment is applied here."
        ),
        "notice": SIGNAL_NOTICE,
    }
