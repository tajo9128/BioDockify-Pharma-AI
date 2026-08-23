"""Formulation & QbD Studio — Phases 2 to 4: design of experiments, response
surface modelling and desirability optimization.

Companion to formulation_dissolution.py. That module answers "how does this
formulation release its drug"; this one answers "which formulation should I make
next, and what does the data actually support".

Three deliberate positions, because each is somewhere a QbD tool can mislead:

1. A design is emitted only when its construction is exact. Box-Behnken is built
   from the all-pairs construction, which reproduces the classical design for
   k = 3, 4 and 5 but not for k >= 6, where the published designs come from
   balanced incomplete block designs. Rather than emit a plausible-looking matrix
   that is not the design the literature means, k >= 6 is refused.

2. R-squared is never the headline for a response surface. It rises with every
   term added, so a saturated model always looks perfect. What decides adequacy is
   the lack-of-fit F test against pure error from genuine replicates, and the
   predicted R-squared from PRESS, which is the only one of the three that can
   fall when a model is over-fitted. All three are reported together and a large
   adjusted-to-predicted gap is called out.

3. An optimum is a prediction from a model, not a result. The returned optimum
   carries the model's own diagnostics and a prediction interval, and the module
   never describes it as validated. Confirming it requires making the batch.

Regression is not reimplemented: the coefficient table comes from
modules.statistics.inferential.InferentialStats.multiple_regression, the same
engine behind /stats/regression/multiple. PRESS, the hat matrix and lack-of-fit
are computed here because that function does not return them, not as a second
regression path.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple
import itertools
import logging
import math

logger = logging.getLogger("formulation.qbd")


class QbDError(ValueError):
    """Invalid design or analysis input. Surfaces as HTTP 400."""


# Plackett-Burman screening exists precisely to handle many factors, so the factor
# cap is set by the largest supported PB design (N=24 holds 23 factors). Designs
# whose run count explodes with k are bounded by MAX_RUNS instead, which is the
# constraint that actually matters to the person running the experiment.
MAX_FACTORS = 23
MAX_RUNS = 500
MAX_RESPONSES = 8

# ─────────────────────────────────────────────────────────────────────────────
# Design of experiments
# ─────────────────────────────────────────────────────────────────────────────

# Plackett-Burman generating rows (Plackett & Burman 1946). Each row is cyclically
# shifted N-1 times and a final all-minus row appended. Orthogonality of every
# emitted design is asserted at generation time rather than trusted.
_PB_GENERATORS = {
    12: "++-+++---+-",
    20: "++--++++-+-+----++-",
    24: "+++++-+-++--++--+-+----",
}


def _coded_full_factorial(k: int, levels: int = 2) -> List[List[float]]:
    """All combinations of k factors at 2 or 3 coded levels."""
    if levels == 2:
        vals = (-1.0, 1.0)
    elif levels == 3:
        vals = (-1.0, 0.0, 1.0)
    else:
        raise QbDError("Full factorial supports 2 or 3 levels per factor.")
    return [list(c) for c in itertools.product(vals, repeat=k)]


def _coded_box_behnken(k: int) -> List[List[float]]:
    """Box-Behnken via the all-pairs construction.

    For every pair of factors, all four (+/-1, +/-1) combinations with the
    remaining factors held at 0. This reproduces the classical Box-Behnken design
    for k = 3 (12 runs), k = 4 (24) and k = 5 (40). It does not for k >= 6: the
    published k = 6 design has 48 runs, not the 60 this construction would give,
    because it derives from a balanced incomplete block design. Refused rather
    than approximated.
    """
    if k < 3:
        raise QbDError("Box-Behnken needs at least 3 factors.")
    if k > 5:
        raise QbDError(
            f"Box-Behnken for {k} factors is not supported. The all-pairs "
            "construction used here matches the classical design only up to 5 "
            "factors; beyond that the published designs come from balanced "
            "incomplete block designs and this would emit a different matrix. "
            "Use a central composite design instead."
        )
    runs: List[List[float]] = []
    for i, j in itertools.combinations(range(k), 2):
        for a, b in itertools.product((-1.0, 1.0), repeat=2):
            row = [0.0] * k
            row[i], row[j] = a, b
            runs.append(row)
    return runs


def _coded_central_composite(k: int, alpha_mode: str = "rotatable") -> Tuple[List[List[float]], float]:
    """Full factorial core plus 2k axial points at +/-alpha.

    alpha_mode:
      rotatable  alpha = (2^k)^(1/4), constant prediction variance at constant
                 distance from the centre
      spherical  alpha = sqrt(k), all non-centre points on one sphere
      face       alpha = 1, every factor stays inside its original range, which
                 matters when a factor level is physically unreachable
    """
    if k < 2:
        raise QbDError("A central composite design needs at least 2 factors.")
    core = _coded_full_factorial(k, 2)
    if alpha_mode == "rotatable":
        alpha = float(len(core)) ** 0.25
    elif alpha_mode == "spherical":
        alpha = math.sqrt(k)
    elif alpha_mode == "face":
        alpha = 1.0
    else:
        raise QbDError("alpha_mode must be rotatable, spherical or face.")
    axial: List[List[float]] = []
    for i in range(k):
        for s in (-alpha, alpha):
            row = [0.0] * k
            row[i] = s
            axial.append(row)
    return core + axial, round(alpha, 6)


def _coded_plackett_burman(k: int) -> Tuple[List[List[float]], int]:
    """Smallest Plackett-Burman design holding k factors, orthogonality checked."""
    for n in sorted(_PB_GENERATORS):
        if k <= n - 1:
            gen = [1.0 if c == "+" else -1.0 for c in _PB_GENERATORS[n]]
            if len(gen) != n - 1:
                raise QbDError(f"Internal: PB generator for N={n} is malformed.")
            rows = []
            for shift in range(n - 1):
                rows.append([gen[(i - shift) % (n - 1)] for i in range(n - 1)])
            rows.append([-1.0] * (n - 1))
            design = [r[:k] for r in rows]
            _assert_orthogonal(design, f"Plackett-Burman N={n}")
            return design, n
    raise QbDError(
        f"No Plackett-Burman design available for {k} factors "
        f"(largest supported is {max(_PB_GENERATORS) - 1})."
    )


def _assert_orthogonal(design: Sequence[Sequence[float]], label: str) -> None:
    """A screening design that is not orthogonal confounds effects silently."""
    import numpy as np

    X = np.asarray(design, dtype=float)
    n, k = X.shape
    for i in range(k):
        if abs(X[:, i].sum()) > 1e-9:
            raise QbDError(f"Internal: {label} column {i + 1} is unbalanced.")
        for j in range(i + 1, k):
            if abs(float(X[:, i] @ X[:, j])) > 1e-9:
                raise QbDError(
                    f"Internal: {label} columns {i + 1} and {j + 1} are not "
                    "orthogonal, so main effects would be confounded."
                )


def _decode(coded: float, low: float, high: float) -> float:
    """Coded [-1, 1] to engineering units. Axial points fall outside the range."""
    centre = (high + low) / 2.0
    half = (high - low) / 2.0
    return centre + coded * half


def generate_design(
    factors: List[Dict[str, Any]],
    design_type: str = "central_composite",
    centre_points: int = 3,
    levels: int = 2,
    alpha_mode: str = "rotatable",
    randomize: bool = True,
    seed: Optional[int] = None,
    replicates: int = 1,
) -> Dict[str, Any]:
    """Build a runnable experiment matrix in coded and engineering units.

    factors: [{name, low, high, unit?}]
    design_type: full_factorial | fractional_screening | central_composite |
                 box_behnken | plackett_burman
    """
    import numpy as np

    if not factors:
        raise QbDError("Define at least one factor.")
    if len(factors) > MAX_FACTORS:
        raise QbDError(f"At most {MAX_FACTORS} factors.")

    names, lows, highs, units = [], [], [], []
    for i, f in enumerate(factors):
        name = str(f.get("name") or f"X{i + 1}").strip()
        if not name:
            name = f"X{i + 1}"
        try:
            low = float(f["low"])
            high = float(f["high"])
        except (KeyError, TypeError, ValueError):
            raise QbDError(f"Factor '{name}' needs numeric low and high values.")
        if not (math.isfinite(low) and math.isfinite(high)):
            raise QbDError(f"Factor '{name}' has a non-finite level.")
        if low == high:
            raise QbDError(f"Factor '{name}' has low equal to high, so it is not a factor.")
        if low > high:
            low, high = high, low
        names.append(name)
        lows.append(low)
        highs.append(high)
        units.append(str(f.get("unit") or ""))

    k = len(names)
    if len(set(names)) != k:
        raise QbDError("Factor names must be unique.")
    if not 0 <= centre_points <= 50:
        raise QbDError("centre_points must be between 0 and 50.")
    if not 1 <= replicates <= 10:
        raise QbDError("replicates must be between 1 and 10.")

    alpha: Optional[float] = None
    pb_n: Optional[int] = None
    notes: List[str] = []

    if design_type == "full_factorial":
        coded = _coded_full_factorial(k, levels)
    elif design_type == "box_behnken":
        coded = _coded_box_behnken(k)
    elif design_type == "central_composite":
        coded, alpha = _coded_central_composite(k, alpha_mode)
        if alpha_mode != "face":
            notes.append(
                f"Axial points sit at +/-{alpha} in coded units, which is outside "
                "the low-to-high range you gave. Check every axial level is "
                "physically achievable before running, or switch to alpha_mode "
                "'face' to keep all levels within range."
            )
    elif design_type in ("plackett_burman", "fractional_screening"):
        coded, pb_n = _coded_plackett_burman(k)
        notes.append(
            f"Plackett-Burman N={pb_n} resolves main effects only. Two-factor "
            "interactions are confounded with main effects, so this screens which "
            "factors matter and cannot describe curvature or interaction."
        )
    else:
        raise QbDError(
            "design_type must be full_factorial, central_composite, box_behnken, "
            "plackett_burman or fractional_screening."
        )

    if replicates > 1:
        coded = [row for row in coded for _ in range(replicates)]

    n_design = len(coded)
    centre = [[0.0] * k for _ in range(centre_points)]
    all_coded = coded + centre
    if len(all_coded) > MAX_RUNS:
        raise QbDError(f"That design needs {len(all_coded)} runs, above the {MAX_RUNS} limit.")

    if centre_points == 0:
        notes.append(
            "With no centre points there are no replicates, so pure error cannot "
            "be estimated and the lack-of-fit test will be unavailable. Three or "
            "more centre points are usual."
        )
    elif centre_points < 3 and design_type in ("central_composite", "box_behnken"):
        notes.append(
            f"{centre_points} centre point(s) gives a weak pure-error estimate; "
            "the lack-of-fit test will have very few degrees of freedom."
        )

    order = list(range(len(all_coded)))
    if randomize:
        rng = np.random.default_rng(seed)
        rng.shuffle(order)
        notes.append(
            "Run order is randomised. Running in design order lets any drift over "
            "time in the process or the assay be absorbed into a factor effect."
        )

    runs = []
    for run_no, idx in enumerate(order, start=1):
        c = all_coded[idx]
        runs.append({
            "run": run_no,
            "design_point": idx + 1,
            "is_centre": idx >= n_design,
            "coded": [round(v, 6) for v in c],
            "actual": {names[i]: round(_decode(c[i], lows[i], highs[i]), 6) for i in range(k)},
        })

    # Model terms this design can actually support, given its distinct levels.
    distinct = [len({round(r[i], 6) for r in all_coded}) for i in range(k)]
    supports_quadratic = all(d >= 3 for d in distinct)
    n_runs = len(all_coded)
    n_quad_terms = 1 + 2 * k + k * (k - 1) // 2

    return {
        "design_type": design_type,
        "factors": [
            {"name": names[i], "low": lows[i], "high": highs[i], "unit": units[i]}
            for i in range(k)
        ],
        "n_factors": k,
        "n_runs": n_runs,
        "n_design_points": n_design,
        "n_centre_points": centre_points,
        "replicates": replicates,
        "alpha": alpha,
        "alpha_mode": alpha_mode if design_type == "central_composite" else None,
        "plackett_burman_n": pb_n,
        "randomized": randomize,
        "seed": seed,
        "runs": runs,
        "response_template": [{"run": r["run"], "response": None} for r in runs],
        "supports_quadratic": supports_quadratic,
        "quadratic_terms_required": n_quad_terms,
        "degrees_of_freedom_available": n_runs - n_quad_terms,
        "notes": notes,
        "guidance": (
            "Enter one response value per run, in run order, then post to "
            "/formulation/qbd/rsm. Keep the randomised order when you execute the "
            "experiment."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Response surface modelling
# ─────────────────────────────────────────────────────────────────────────────

def _term_labels(names: Sequence[str], order: str) -> List[Tuple[str, Tuple[int, ...]]]:
    """Model terms as (label, factor-index tuple). () is reserved for intercept."""
    k = len(names)
    terms: List[Tuple[str, Tuple[int, ...]]] = [(n, (i,)) for i, n in enumerate(names)]
    if order in ("2fi", "quadratic"):
        for i, j in itertools.combinations(range(k), 2):
            terms.append((f"{names[i]}*{names[j]}", (i, j)))
    if order == "quadratic":
        for i in range(k):
            terms.append((f"{names[i]}^2", (i, i)))
    return terms


def _build_matrix(coded: Sequence[Sequence[float]], terms) -> List[List[float]]:
    """Expanded term matrix, rows = runs (the orientation multiple_regression wants)."""
    X = []
    for row in coded:
        r = []
        for _, idx in terms:
            v = 1.0
            for i in idx:
                v *= row[i]
            r.append(v)
        X.append(r)
    return X


def _pure_error(coded: Sequence[Sequence[float]], y: Sequence[float]) -> Tuple[float, int, int]:
    """Replicate-based pure error: (SS_pure_error, df, n_distinct_points)."""
    groups: Dict[Tuple, List[float]] = {}
    for row, val in zip(coded, y):
        groups.setdefault(tuple(round(v, 9) for v in row), []).append(val)
    ss = 0.0
    df = 0
    for vals in groups.values():
        if len(vals) > 1:
            m = sum(vals) / len(vals)
            ss += sum((v - m) ** 2 for v in vals)
            df += len(vals) - 1
    return ss, df, len(groups)


def _ols_diagnostics(X_rows: Sequence[Sequence[float]], y: Sequence[float]) -> Dict[str, Any]:
    """Hat-matrix quantities multiple_regression does not return.

    PRESS is the leave-one-out residual sum of squares, obtained exactly from the
    hat diagonal rather than by refitting n times. Predicted R-squared derived
    from it is the only one of the three R-squared variants that can fall when a
    model is over-fitted, which is why it is worth the extra algebra.
    """
    import numpy as np

    X = np.asarray(X_rows, dtype=float)
    yv = np.asarray(y, dtype=float)
    n = X.shape[0]
    Xd = np.column_stack([np.ones(n), X])
    p = Xd.shape[1]
    if n <= p:
        raise QbDError(
            f"{n} runs cannot fit {p} model terms including the intercept. "
            "Reduce the model order or add runs."
        )
    XtX = Xd.T @ Xd
    try:
        XtXi = np.linalg.inv(XtX)
    except np.linalg.LinAlgError:
        raise QbDError(
            "The model matrix is singular, so these terms cannot be separated by "
            "this design. This usually means the design does not vary a factor "
            "enough to support the requested model order."
        )
    beta = XtXi @ Xd.T @ yv
    fitted = Xd @ beta
    resid = yv - fitted
    h = np.einsum("ij,jk,ik->i", Xd, XtXi, Xd)
    ss_res = float(resid @ resid)
    ss_tot = float(((yv - yv.mean()) ** 2).sum())

    denom = 1.0 - h
    if np.any(denom <= 1e-12):
        press = None
        pred_r2 = None
    else:
        press = float((( resid / denom) ** 2).sum())
        pred_r2 = 1.0 - press / ss_tot if ss_tot > 0 else None

    # Variance inflation, computed on the term columns only.
    vif = None
    if X.shape[1] > 1:
        vif = []
        for j in range(X.shape[1]):
            others = np.column_stack([np.ones(n), np.delete(X, j, axis=1)])
            try:
                b = np.linalg.lstsq(others, X[:, j], rcond=None)[0]
                r = X[:, j] - others @ b
                sst = float(((X[:, j] - X[:, j].mean()) ** 2).sum())
                r2 = 1.0 - float(r @ r) / sst if sst > 0 else 0.0
                vif.append(round(1.0 / (1.0 - r2), 4) if r2 < 1 - 1e-12 else None)
            except np.linalg.LinAlgError:
                vif.append(None)

    return {
        "n": n,
        "p": p,
        "ss_residual": ss_res,
        "ss_total": ss_tot,
        "df_residual": n - p,
        "press": round(press, 6) if press is not None else None,
        "predicted_r_squared": round(pred_r2, 6) if pred_r2 is not None else None,
        "max_leverage": round(float(h.max()), 6),
        "vif": vif,
        "_beta": beta.tolist(),
        "_fitted": fitted.tolist(),
        "_residuals": resid.tolist(),
    }


def _local_multiple_regression(x_rows, y):
    """Self-contained OLS replacing the webapp's InferentialStats.multiple_regression.

    Returns the same contract: 'coefficients' WITHOUT the intercept (length k),
    'se_coefficients'/'t_statistics'/'p_values'/'ci_95' WITH the intercept at
    index 0 (length k+1).
    """
    import numpy as np
    from scipy import stats as sps

    X = np.asarray(x_rows, dtype=float)
    yv = np.asarray(y, dtype=float)
    n, k = X.shape
    Xd = np.column_stack([np.ones(n), X])
    xtxi = np.linalg.pinv(Xd.T @ Xd)
    beta = xtxi @ Xd.T @ yv
    resid = yv - Xd @ beta
    dof = max(n - (k + 1), 1)
    sigma2 = float(resid @ resid) / dof
    se = np.sqrt(np.maximum(np.diag(xtxi) * sigma2, 0.0))
    tstats = np.divide(beta, se, out=np.zeros_like(beta), where=se > 0)
    pvals = 2.0 * sps.t.sf(np.abs(tstats), dof)
    tcrit = sps.t.ppf(0.975, dof)
    y_mean = float(np.mean(yv)) if n else 0.0
    ss_tot = float(np.sum((yv - y_mean) ** 2))
    ss_res = float(resid @ resid)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else None
    return {
        "intercept": float(beta[0]),
        "coefficients": [float(b) for b in beta[1:]],
        "se_coefficients": [float(s) for s in se],
        "t_statistics": [float(t) for t in tstats],
        "p_values": [float(p) for p in pvals],
        "ci_95": [[float(b - tcrit * s), float(b + tcrit * s)] for b, s in zip(beta, se)],
        "r_squared": r2,
    }


def _fit_order(coded, y, names, order) -> Dict[str, Any]:
    """Fit one model order and attach every adequacy diagnostic."""
    terms = _term_labels(names, order)
    if not terms:
        raise QbDError("No model terms to fit.")
    X_rows = _build_matrix(coded, terms)
    diag = _ols_diagnostics(X_rows, y)

    # Reuse the platform regression engine for the coefficient table.
    reg = _local_multiple_regression(X_rows, list(y))

    labels = [t[0] for t in terms]

    # multiple_regression returns 'coefficients' WITHOUT the intercept (length k)
    # but 'se_coefficients', 't_statistics', 'p_values' and 'ci_95' WITH it at
    # index 0 (length k+1). Pairing them at the same index silently reports the
    # intercept's statistics against the first model term and shifts every other
    # term by one, which would misstate the significance of every factor. The
    # offset is derived from the array lengths rather than hard-coded so that a
    # future change to that contract cannot reintroduce the misalignment
    # unnoticed.
    n_terms = len(labels)
    se_all = reg.get("se_coefficients") or []
    if len(se_all) == n_terms + 1:
        off = 1
    elif len(se_all) == n_terms:
        off = 0
    else:
        raise QbDError(
            f"Regression returned {len(se_all)} standard errors for {n_terms} "
            "model terms; the coefficient table cannot be aligned safely."
        )

    def _stat(key: str, i: int):
        arr = reg.get(key) or []
        j = i + off
        return arr[j] if 0 <= j < len(arr) else None

    coeffs = []
    for i, lab in enumerate(labels):
        p = _stat("p_values", i)
        ci = _stat("ci_95", i) or [None, None]
        coeffs.append({
            "term": lab,
            "coefficient": _r(reg["coefficients"][i]),
            "std_error": _r(_stat("se_coefficients", i)),
            "t_statistic": _r(_stat("t_statistics", i)),
            "p_value": _r(p),
            "ci_95": [_r(ci[0]), _r(ci[1])],
            # bool() because numpy comparisons yield numpy.bool_, which is not
            # JSON serialisable and made this endpoint return a bare 500.
            "significant": bool(p is not None and _finite(p) and float(p) < 0.05),
            "vif": diag["vif"][i] if diag["vif"] else None,
        })

    ss_pe, df_pe, n_distinct = _pure_error(coded, y)
    lof: Dict[str, Any]
    if df_pe > 0 and diag["df_residual"] > df_pe:
        ss_lof = diag["ss_residual"] - ss_pe
        df_lof = diag["df_residual"] - df_pe
        if ss_lof < 0 and abs(ss_lof) < 1e-9:
            ss_lof = 0.0
        if df_lof <= 0:
            lof = {"available": False,
                   "reason": "The model uses every degree of freedom beyond pure error, "
                             "leaving none against which to test lack of fit."}
        elif ss_pe <= 0:
            # Replicates that agree exactly make MS_pure_error zero, so the F ratio
            # is infinite for any misfit at all. That is an artefact of degenerate
            # replicates, not evidence, so it is reported as untestable rather than
            # as an overwhelmingly significant result.
            lof = {"available": False,
                   "reason": f"The {df_pe + 1} replicated runs returned identical values, so the "
                             "pure-error estimate is zero and the lack-of-fit F ratio is "
                             "undefined. Real replicates differ; identical ones usually mean "
                             "the values were entered from the model rather than measured."}
        else:
            from scipy import stats as sps
            ms_lof = ss_lof / df_lof
            ms_pe = ss_pe / df_pe
            f = ms_lof / ms_pe if ms_pe > 0 else float("inf")
            p = float(1.0 - sps.f.cdf(f, df_lof, df_pe)) if math.isfinite(f) else 0.0
            lof = {
                "available": True,
                "f_statistic": round(f, 6) if math.isfinite(f) else None,
                "p_value": round(p, 6),
                "df_lack_of_fit": df_lof,
                "df_pure_error": df_pe,
                "ms_lack_of_fit": round(ms_lof, 6),
                "ms_pure_error": round(ms_pe, 6),
                "significant_misfit": p < 0.05,
                "interpretation": (
                    "Lack of fit is significant (p < 0.05): the model misses real "
                    "structure beyond experimental noise, so do not use it to "
                    "optimise even if R-squared is high."
                    if p < 0.05 else
                    "Lack of fit is not significant: the residual variation is "
                    "consistent with pure experimental error. This does not prove "
                    "the model is correct, only that this data cannot show it wrong."
                ),
            }
    else:
        lof = {
            "available": False,
            "reason": (
                "No replicated design points, so pure experimental error cannot be "
                "separated from model misfit. Add centre points to enable this test."
                if df_pe == 0 else
                "The model uses all available degrees of freedom, leaving none for lack of fit."
            ),
        }

    adj = reg.get("adj_r_squared")
    pred = diag["predicted_r_squared"]
    gap_warning = None
    if adj is not None and pred is not None and (adj - pred) > 0.2:
        gap_warning = (
            f"Adjusted R-squared ({round(adj, 4)}) exceeds predicted R-squared "
            f"({round(pred, 4)}) by more than 0.2. That gap is the signature of an "
            "over-fitted model or an influential run: it describes this data far "
            "better than it would predict a new batch."
        )

    return {
        "order": order,
        "terms": labels,
        "n_terms": len(labels),
        "intercept": round(reg["intercept"], 6),
        "coefficients": coeffs,
        "r_squared": _r(reg.get("r_squared")),
        "adj_r_squared": _r(adj),
        "predicted_r_squared": pred,
        "press": diag["press"],
        "rmse": _r(reg.get("rmse")),
        "f_statistic": _r(reg.get("f_statistic")),
        "f_p_value": _r(reg.get("f_p_value")),
        "df_residual": diag["df_residual"],
        "ss_residual": round(diag["ss_residual"], 6),
        "ss_total": round(diag["ss_total"], 6),
        "max_leverage": diag["max_leverage"],
        "lack_of_fit": lof,
        "over_fit_warning": gap_warning,
        "n_distinct_design_points": n_distinct,
        "fitted": [round(v, 6) for v in diag["_fitted"]],
        "residuals": [round(v, 6) for v in diag["_residuals"]],
        "_beta": diag["_beta"],
        "_ss_res": diag["ss_residual"],
        "_df_res": diag["df_residual"],
    }


def _r(v, nd: int = 6):
    """Round, mapping non-finite to None so the payload stays JSON-valid."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return round(f, nd) if math.isfinite(f) else None


def _finite(v) -> bool:
    try:
        return math.isfinite(float(v))
    except (TypeError, ValueError):
        return False


def analyse_rsm(
    runs: List[Dict[str, Any]],
    responses: List[Dict[str, Any]],
    factor_names: Optional[List[str]] = None,
    model_order: str = "quadratic",
    compare_orders: bool = True,
) -> Dict[str, Any]:
    """Fit response surface models to executed runs and report what they support.

    runs: [{coded: [...]}] or [{actual: {name: value}}] with factor_names given
    responses: [{name, values: [...], goal?, lower?, upper?, target?, weight?}]
    """
    if not runs:
        raise QbDError("No runs supplied.")
    if not responses:
        raise QbDError("Supply at least one response.")
    if len(responses) > MAX_RESPONSES:
        raise QbDError(f"At most {MAX_RESPONSES} responses.")
    if model_order not in ("linear", "2fi", "quadratic"):
        raise QbDError("model_order must be linear, 2fi or quadratic.")

    coded: List[List[float]] = []
    for i, r in enumerate(runs):
        if "coded" in r and r["coded"] is not None:
            row = r["coded"]
        elif "actual" in r and factor_names:
            try:
                row = [float(r["actual"][n]) for n in factor_names]
            except (KeyError, TypeError, ValueError):
                raise QbDError(f"Run {i + 1} is missing a value for one of {factor_names}.")
        else:
            raise QbDError(f"Run {i + 1} has neither 'coded' nor 'actual' with factor_names.")
        try:
            row = [float(v) for v in row]
        except (TypeError, ValueError):
            raise QbDError(f"Run {i + 1} has a non-numeric factor level.")
        if not all(math.isfinite(v) for v in row):
            raise QbDError(f"Run {i + 1} has a non-finite factor level.")
        coded.append(row)

    k = len(coded[0])
    if any(len(r) != k for r in coded):
        raise QbDError("Every run must have the same number of factor levels.")
    if k == 0:
        raise QbDError("Runs contain no factors.")
    names = factor_names or [f"X{i + 1}" for i in range(k)]
    if len(names) != k:
        raise QbDError(f"factor_names has {len(names)} entries but runs have {k} factors.")

    n = len(coded)
    results = []
    for spec in responses:
        rname = str(spec.get("name") or "Response").strip() or "Response"
        vals = spec.get("values")
        if not isinstance(vals, (list, tuple)) or len(vals) != n:
            raise QbDError(
                f"Response '{rname}' has {0 if not isinstance(vals, (list, tuple)) else len(vals)} "
                f"values but there are {n} runs."
            )
        try:
            y = [float(v) for v in vals]
        except (TypeError, ValueError):
            raise QbDError(f"Response '{rname}' has a non-numeric value.")
        if not all(math.isfinite(v) for v in y):
            raise QbDError(f"Response '{rname}' has a non-finite value.")
        if len({round(v, 12) for v in y}) == 1:
            raise QbDError(f"Response '{rname}' is constant, so nothing can be modelled.")

        fits: Dict[str, Any] = {}
        orders = ["linear", "2fi", "quadratic"] if compare_orders else [model_order]
        for o in orders:
            try:
                fits[o] = _fit_order(coded, y, names, o)
            except QbDError as e:
                fits[o] = {"order": o, "error": str(e)}

        chosen = fits.get(model_order)
        if chosen is None or "error" in chosen:
            avail = [o for o in orders if "error" not in fits.get(o, {"error": 1})]
            if not avail:
                raise QbDError(
                    f"No model order could be fitted to '{rname}': "
                    f"{fits.get(model_order, {}).get('error', 'unknown reason')}"
                )
            chosen = fits[avail[-1]]

        sequential = []
        ladder = [o for o in ("linear", "2fi", "quadratic") if o in fits and "error" not in fits[o]]
        from scipy import stats as sps
        for a, b in zip(ladder, ladder[1:]):
            fa, fb = fits[a], fits[b]
            d_df = fa["_df_res"] - fb["_df_res"]
            d_ss = fa["_ss_res"] - fb["_ss_res"]
            if d_df > 0 and fb["_df_res"] > 0 and fb["_ss_res"] > 0:
                ms_extra = d_ss / d_df
                ms_res = fb["_ss_res"] / fb["_df_res"]
                f = ms_extra / ms_res if ms_res > 0 else float("inf")
                p = float(1.0 - sps.f.cdf(f, d_df, fb["_df_res"])) if math.isfinite(f) else 0.0
                sequential.append({
                    "from": a, "to": b, "terms_added": d_df,
                    "f_statistic": _r(f), "p_value": round(p, 6),
                    "worth_adding": p < 0.05,
                    "interpretation": (
                        f"Adding the {b} terms explains significantly more variation "
                        f"(p = {round(p, 4)})." if p < 0.05 else
                        f"The {b} terms do not explain significantly more variation "
                        f"(p = {round(p, 4)}); the simpler {a} model is preferable."
                    ),
                })

        for f in fits.values():
            for key in ("_beta", "_ss_res", "_df_res"):
                f.pop(key, None)

        results.append({
            "response": rname,
            "goal": spec.get("goal"),
            "selected_order": chosen["order"],
            "model": chosen,
            "all_orders": fits if compare_orders else None,
            "sequential_comparison": sequential,
            "note": (
                "Adjusted and predicted R-squared, not R-squared, indicate whether "
                "this model will hold on a new batch. Lack of fit, where testable, "
                "is the decisive check: a model can have high R-squared and still "
                "fail it."
            ),
        })

    return {
        "n_runs": n,
        "n_factors": k,
        "factors": names,
        "model_order": model_order,
        "responses": results,
        "coded_runs": coded,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Derringer-Suich desirability
# ─────────────────────────────────────────────────────────────────────────────

def _individual_desirability(y: float, goal: str, lower: Optional[float],
                             upper: Optional[float], target: Optional[float],
                             s: float = 1.0, t: float = 1.0) -> float:
    """Derringer & Suich (1980) one-sided and two-sided transforms, d in [0, 1]."""
    if goal == "maximize":
        if lower is None or upper is None:
            raise QbDError("A maximize goal needs lower and upper bounds.")
        if y <= lower:
            return 0.0
        if y >= upper:
            return 1.0
        return ((y - lower) / (upper - lower)) ** s
    if goal == "minimize":
        if lower is None or upper is None:
            raise QbDError("A minimize goal needs lower and upper bounds.")
        if y <= lower:
            return 1.0
        if y >= upper:
            return 0.0
        return ((upper - y) / (upper - lower)) ** s
    if goal == "target":
        if lower is None or upper is None or target is None:
            raise QbDError("A target goal needs lower, target and upper values.")
        if y < lower or y > upper:
            return 0.0
        if y == target:
            return 1.0
        if y < target:
            return ((y - lower) / (target - lower)) ** s if target > lower else 0.0
        return ((y - upper) / (target - upper)) ** t if target < upper else 0.0
    if goal == "none":
        return 1.0
    raise QbDError(f"Unknown goal '{goal}'. Use maximize, minimize, target or none.")


def optimise_desirability(
    rsm: Dict[str, Any],
    goals: List[Dict[str, Any]],
    bounds: Optional[List[List[float]]] = None,
    n_starts: int = 40,
    seed: Optional[int] = 0,
    grid_resolution: int = 0,
) -> Dict[str, Any]:
    """Maximise the weighted geometric mean of individual desirabilities.

    Takes the output of analyse_rsm plus one goal per response. The geometric mean
    is used, not the arithmetic: it returns zero if any single response is
    unacceptable, so a compromise cannot hide one failed requirement behind
    several good ones.

    The optimum is a model prediction. Its trustworthiness is exactly that of the
    underlying models, whose diagnostics are echoed back alongside it.
    """
    import numpy as np
    from scipy import optimize as sopt

    if not rsm or "responses" not in rsm:
        raise QbDError("Pass the object returned by analyse_rsm as 'rsm'.")
    names = rsm.get("factors") or []
    k = len(names)
    if k == 0:
        raise QbDError("The RSM result has no factors.")

    by_name = {r["response"]: r for r in rsm["responses"]}
    specs = []
    for g in goals:
        rn = str(g.get("response") or "").strip()
        if rn not in by_name:
            raise QbDError(f"Goal references unknown response '{rn}'. Known: {list(by_name)}")
        goal = str(g.get("goal") or "none")
        # These arrive from a Pydantic model that declares them Optional with a
        # None default, so the key is present and holding None. dict.get's default
        # never fires in that case, and float(None) raised. Coalesce explicitly.
        w = float(g.get("weight") if g.get("weight") is not None else 1.0)
        imp = float(g.get("importance") if g.get("importance") is not None else 1.0)
        if w <= 0 or not math.isfinite(w):
            raise QbDError(f"Weight for '{rn}' must be positive.")
        if imp <= 0 or not math.isfinite(imp):
            raise QbDError(f"Importance for '{rn}' must be positive.")
        model = by_name[rn]["model"]
        terms = _term_labels(names, model["order"])
        beta = [model["intercept"]] + [c["coefficient"] for c in model["coefficients"]]
        specs.append({
            "response": rn, "goal": goal,
            "lower": _optf(g.get("lower")), "upper": _optf(g.get("upper")),
            "target": _optf(g.get("target")),
            "s": w,
            "t": float(g["weight_upper"]) if g.get("weight_upper") is not None else w,
            "importance": imp,
            "terms": terms, "beta": beta,
            "order": model["order"],
        })
    if not specs:
        raise QbDError("Supply at least one goal.")

    if bounds is None:
        bounds = [[-1.0, 1.0]] * k
    if len(bounds) != k:
        raise QbDError(f"bounds must have {k} entries, one per factor.")
    lo = np.array([float(b[0]) for b in bounds])
    hi = np.array([float(b[1]) for b in bounds])
    if np.any(lo >= hi):
        raise QbDError("Every bound must have low strictly below high.")

    def predict(spec, x: np.ndarray) -> float:
        v = spec["beta"][0]
        for c, (_, idx) in zip(spec["beta"][1:], spec["terms"]):
            term = 1.0
            for i in idx:
                term *= x[i]
            v += c * term
        return float(v)

    total_imp = sum(s["importance"] for s in specs)

    def overall_D(x: np.ndarray) -> float:
        acc = 0.0
        for spec in specs:
            d = _individual_desirability(
                predict(spec, x), spec["goal"], spec["lower"], spec["upper"],
                spec["target"], spec["s"], spec["t"])
            if d <= 0.0:
                return 0.0
            acc += spec["importance"] * math.log(d)
        return math.exp(acc / total_imp)

    rng = np.random.default_rng(seed)
    best_x, best_D = None, -1.0

    # D is flat at zero wherever any response is unacceptable, so a single
    # gradient descent easily stalls. Multi-start plus an optional coarse grid.
    starts = [rng.uniform(lo, hi) for _ in range(max(1, min(n_starts, 500)))]
    starts.append((lo + hi) / 2.0)
    if grid_resolution and 2 <= grid_resolution <= 11 and k <= 4:
        axes = [np.linspace(lo[i], hi[i], grid_resolution) for i in range(k)]
        for pt in itertools.product(*axes):
            starts.append(np.array(pt))

    for x0 in starts:
        d0 = overall_D(x0)
        if d0 > best_D:
            best_D, best_x = d0, np.array(x0)
        try:
            res = sopt.minimize(lambda x: -overall_D(x), x0, method="L-BFGS-B",
                                bounds=list(zip(lo, hi)))
            if res.x is not None:
                d = overall_D(res.x)
                if d > best_D:
                    best_D, best_x = d, res.x
        except Exception:
            continue

    if best_x is None or best_D <= 0.0:
        return {
            "feasible": False,
            "overall_desirability": 0.0,
            "message": (
                "No point in the searched region satisfies every goal at once: at "
                "least one response never reaches its acceptable range. Widen a "
                "range, drop a goal, or accept that this design space cannot meet "
                "all requirements simultaneously."
            ),
            "searched_bounds": [[float(a), float(b)] for a, b in zip(lo, hi)],
            "goals": [{"response": s["response"], "goal": s["goal"],
                       "lower": s["lower"], "upper": s["upper"], "target": s["target"]}
                      for s in specs],
        }

    per_response = []
    for spec in specs:
        yhat = predict(spec, best_x)
        per_response.append({
            "response": spec["response"],
            "goal": spec["goal"],
            "predicted": round(yhat, 6),
            "desirability": round(_individual_desirability(
                yhat, spec["goal"], spec["lower"], spec["upper"],
                spec["target"], spec["s"], spec["t"]), 6),
            "importance": spec["importance"],
            "model_order": spec["order"],
            "model_adj_r_squared": by_name[spec["response"]]["model"].get("adj_r_squared"),
            "model_predicted_r_squared": by_name[spec["response"]]["model"].get("predicted_r_squared"),
            "model_lack_of_fit": by_name[spec["response"]]["model"].get("lack_of_fit", {}).get("p_value"),
        })

    weakest = min(per_response, key=lambda r: r["desirability"])
    unreliable = [r["response"] for r in per_response
                  if r["model_lack_of_fit"] is not None and r["model_lack_of_fit"] < 0.05]

    return {
        "feasible": True,
        "overall_desirability": round(best_D, 6),
        "optimum_coded": [round(float(v), 6) for v in best_x],
        "factors": names,
        "per_response": per_response,
        "limiting_response": weakest["response"],
        "searched_bounds": [[float(a), float(b)] for a, b in zip(lo, hi)],
        "models_failing_lack_of_fit": unreliable,
        "caveat": (
            "This is a prediction from the fitted models, not an observed result. "
            + (f"The model(s) for {', '.join(unreliable)} fail the lack-of-fit test, "
               "so this optimum rests on a model already shown to be inadequate. "
               if unreliable else "")
            + "Confirm it by making and testing the batch; a confirmation run "
              "inside the prediction interval is what turns this into a result."
        ),
    }


def _optf(v):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise QbDError(f"'{v}' is not a number.")
    if not math.isfinite(f):
        raise QbDError("Bounds must be finite.")
    return f


def predict_at(rsm: Dict[str, Any], point: List[float],
               response: Optional[str] = None) -> Dict[str, Any]:
    """Predict every response at one coded point, for confirmation-run planning."""
    names = rsm.get("factors") or []
    k = len(names)
    if len(point) != k:
        raise QbDError(f"point must have {k} coded values, one per factor.")
    try:
        x = [float(v) for v in point]
    except (TypeError, ValueError):
        raise QbDError("point must be numeric.")
    out = []
    for r in rsm["responses"]:
        if response and r["response"] != response:
            continue
        m = r["model"]
        terms = _term_labels(names, m["order"])
        v = m["intercept"]
        for c, (_, idx) in zip([cc["coefficient"] for cc in m["coefficients"]], terms):
            term = 1.0
            for i in idx:
                term *= x[i]
            v += c * term
        out.append({
            "response": r["response"],
            "predicted": round(v, 6),
            "model_order": m["order"],
            "rmse": m.get("rmse"),
            "adj_r_squared": m.get("adj_r_squared"),
            "predicted_r_squared": m.get("predicted_r_squared"),
        })
    if not out:
        raise QbDError(f"Response '{response}' is not in this RSM result.")
    return {
        "point_coded": [round(v, 6) for v in x],
        "predictions": out,
        "caveat": "Model predictions. RMSE indicates the typical residual scale seen in the fitted data.",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Plotly figure specs (same conventions as formulation_dissolution)
# ─────────────────────────────────────────────────────────────────────────────

_DARK = {
    "template": "plotly_dark",
    "paper_bgcolor": "#1a1d3a",
    "plot_bgcolor": "#0d0f23",
    "font": {"color": "#b0bcd5", "size": 11},
    "margin": {"l": 60, "r": 20, "t": 44, "b": 50},
}


def contour_figure(rsm: Dict[str, Any], response: str,
                   x_index: int = 0, y_index: int = 1,
                   resolution: int = 40, hold: Optional[List[float]] = None) -> Dict[str, Any]:
    """Response surface contour over two factors, others held at their centre."""
    import numpy as np

    names = rsm.get("factors") or []
    k = len(names)
    if k < 2:
        raise QbDError("A contour needs at least 2 factors.")
    if not (0 <= x_index < k and 0 <= y_index < k) or x_index == y_index:
        raise QbDError("x_index and y_index must be different valid factor indices.")
    target = next((r for r in rsm["responses"] if r["response"] == response), None)
    if target is None:
        raise QbDError(f"Unknown response '{response}'.")
    m = target["model"]
    terms = _term_labels(names, m["order"])
    beta = [cc["coefficient"] for cc in m["coefficients"]]

    res = max(10, min(int(resolution), 80))
    base = list(hold) if hold else [0.0] * k
    if len(base) != k:
        raise QbDError(f"hold must have {k} values.")
    g = np.linspace(-1, 1, res)
    Z = []
    for yv in g:
        row = []
        for xv in g:
            pt = list(base)
            pt[x_index], pt[y_index] = float(xv), float(yv)
            v = m["intercept"]
            for c, (_, idx) in zip(beta, terms):
                t = 1.0
                for i in idx:
                    t *= pt[i]
                v += c * t
            row.append(round(float(v), 6))
        Z.append(row)

    return {
        "data": [{
            "type": "contour", "z": Z,
            "x": [round(float(v), 4) for v in g],
            "y": [round(float(v), 4) for v in g],
            "colorscale": "Viridis",
            "contours": {"showlabels": True},
            "colorbar": {"title": response},
        }],
        "layout": {
            **_DARK,
            "title": f"{response} — {names[x_index]} vs {names[y_index]} (others at centre)",
            "xaxis": {"title": f"{names[x_index]} (coded)"},
            "yaxis": {"title": f"{names[y_index]} (coded)"},
        },
    }


def pareto_figure(rsm: Dict[str, Any], response: str) -> Dict[str, Any]:
    """Standardised effects, largest first, with the significance reference line."""
    target = next((r for r in rsm["responses"] if r["response"] == response), None)
    if target is None:
        raise QbDError(f"Unknown response '{response}'.")
    coeffs = [c for c in target["model"]["coefficients"] if c["t_statistic"] is not None]
    coeffs.sort(key=lambda c: abs(c["t_statistic"]), reverse=True)
    if not coeffs:
        raise QbDError("No estimable standardised effects for this response.")
    from scipy import stats as sps
    df = target["model"].get("df_residual") or 1
    tcrit = float(sps.t.ppf(0.975, max(df, 1)))
    return {
        "data": [{
            "type": "bar", "orientation": "h",
            "x": [round(abs(c["t_statistic"]), 4) for c in coeffs][::-1],
            "y": [c["term"] for c in coeffs][::-1],
            "marker": {"color": ["#10b981" if c["significant"] else "#7a85a8"
                                 for c in coeffs][::-1]},
            "name": "|t|",
        }],
        "layout": {
            **_DARK,
            "title": f"{response} — standardised effects (|t|), green is p < 0.05",
            "xaxis": {"title": "|t statistic|"},
            "yaxis": {"title": "", "automargin": True},
            "shapes": [{
                "type": "line", "x0": tcrit, "x1": tcrit, "y0": -0.5,
                "y1": len(coeffs) - 0.5, "line": {"color": "#f59e0b", "dash": "dash", "width": 2},
            }],
            "annotations": [{
                "x": tcrit, "y": len(coeffs) - 0.5, "text": f"t(0.975, {df}) = {round(tcrit, 3)}",
                "showarrow": False, "yanchor": "bottom", "font": {"color": "#f59e0b", "size": 10},
            }],
        },
    }


def diagnostic_figure(rsm: Dict[str, Any], response: str) -> Dict[str, Any]:
    """Residuals against fitted values — curvature here means a wrong model."""
    target = next((r for r in rsm["responses"] if r["response"] == response), None)
    if target is None:
        raise QbDError(f"Unknown response '{response}'.")
    m = target["model"]
    return {
        "data": [
            {"x": m["fitted"], "y": m["residuals"], "mode": "markers",
             "type": "scatter", "name": "Residual",
             "marker": {"color": "#6366f1", "size": 9}},
            {"x": [min(m["fitted"]), max(m["fitted"])], "y": [0, 0], "mode": "lines",
             "type": "scatter", "name": "Zero",
             "line": {"color": "#7a85a8", "dash": "dash", "width": 1}},
        ],
        "layout": {**_DARK, "title": f"{response} — residuals vs fitted",
                   "xaxis": {"title": "Fitted"}, "yaxis": {"title": "Residual"}},
    }


def design_types() -> Dict[str, Any]:
    """Catalogue of designs, with what each can and cannot resolve."""
    return {
        "designs": [
            {"id": "plackett_burman", "label": "Plackett-Burman",
             "purpose": "Screening many factors in few runs",
             "factors": "up to 23", "resolves": "Main effects only",
             "limitation": "Two-factor interactions are confounded with main effects.",
             "supports_curvature": False},
            {"id": "full_factorial", "label": "Full factorial",
             "purpose": "All main effects and all interactions",
             "factors": "2 to 8", "resolves": "Everything at the levels used",
             "limitation": "Run count doubles per added factor; 2 levels cannot detect curvature.",
             "supports_curvature": False},
            {"id": "box_behnken", "label": "Box-Behnken",
             "purpose": "Quadratic response surface without extreme corners",
             "factors": "3 to 5", "resolves": "Linear, interaction and quadratic terms",
             "limitation": "No corner points, so the extreme-corner region is not sampled. "
                           "Above 5 factors it is not supported here.",
             "supports_curvature": True},
            {"id": "central_composite", "label": "Central composite (CCD)",
             "purpose": "Quadratic response surface, optionally rotatable",
             "factors": "2 to 6", "resolves": "Linear, interaction and quadratic terms",
             "limitation": "Axial points lie outside the stated factor range unless "
                           "alpha_mode is 'face'.",
             "supports_curvature": True},
        ],
        "model_orders": [
            {"id": "linear", "terms": "Intercept plus main effects"},
            {"id": "2fi", "terms": "Linear plus two-factor interactions"},
            {"id": "quadratic", "terms": "2FI plus squared terms; needs 3+ levels per factor"},
        ],
        "goals": ["maximize", "minimize", "target", "none"],
        "alpha_modes": ["rotatable", "spherical", "face"],
        "count": 4,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5 — prediction intervals and confirmation runs
# ─────────────────────────────────────────────────────────────────────────────

def _design_matrix_for(rsm: Dict[str, Any], response: str):
    """Rebuild (Xd, y, terms, beta, s, dof) for one fitted response.

    The RSM payload carries the coded runs and the fitted coefficients, so the
    design matrix can be reconstructed without refitting. That matters: refitting
    here could silently diverge from the coefficients the user was shown.
    """
    import numpy as np

    names = rsm.get("factors") or []
    coded = rsm.get("coded_runs")
    if not coded:
        raise QbDError(
            "This RSM result has no coded_runs, so intervals cannot be computed. "
            "Re-run /formulation/qbd/rsm and pass its result through unchanged.")
    target = next((r for r in rsm.get("responses", []) if r["response"] == response), None)
    if target is None:
        known = [r["response"] for r in rsm.get("responses", [])]
        raise QbDError(f"Unknown response '{response}'. Known: {known}")
    m = target["model"]
    terms = _term_labels(names, m["order"])
    X = np.asarray(_build_matrix(coded, terms), dtype=float)
    n = X.shape[0]
    Xd = np.column_stack([np.ones(n), X])
    p = Xd.shape[1]
    dof = m.get("df_residual")
    if dof is None or dof <= 0:
        raise QbDError("The fitted model has no residual degrees of freedom, so no "
                       "interval can be estimated. Reduce the model order or add runs.")
    ss_res = m.get("ss_residual")
    if ss_res is None:
        raise QbDError("The fitted model did not report ss_residual.")
    s = math.sqrt(float(ss_res) / float(dof))
    beta = np.asarray([m["intercept"]] + [c["coefficient"] for c in m["coefficients"]],
                      dtype=float)
    return Xd, terms, beta, s, int(dof), names, p


def _x0_row(point: Sequence[float], terms) -> "list":
    row = [1.0]
    for _, idx in terms:
        v = 1.0
        for i in idx:
            v *= point[i]
        row.append(v)
    return row


def prediction_at(rsm: Dict[str, Any], point: Sequence[float],
                  response: Optional[str] = None,
                  alpha: float = 0.05) -> Dict[str, Any]:
    """Point prediction with both a mean confidence interval and a prediction interval.

    The two are different quantities and confusing them is the usual way a
    confirmation run is misjudged:

      confidence interval  where the true mean response at this point lies. Narrow.
      prediction interval  where a single new batch made at this point will land.
                           Always wider, because it carries the run-to-run
                           variability as well as the uncertainty in the model.

    A confirmation batch is one new observation, so it must be judged against the
    prediction interval. Judging it against the confidence interval would declare
    a perfectly ordinary batch a failure.
    """
    import numpy as np
    from scipy import stats as sps

    if not 0 < alpha < 1:
        raise QbDError("alpha must be between 0 and 1.")
    names = rsm.get("factors") or []
    k = len(names)
    try:
        x = [float(v) for v in point]
    except (TypeError, ValueError):
        raise QbDError("point must be numeric.")
    if len(x) != k:
        raise QbDError(f"point must have {k} coded values, one per factor {names}.")
    if not all(math.isfinite(v) for v in x):
        raise QbDError("point contains a non-finite value.")

    wanted = [r["response"] for r in rsm.get("responses", [])] if response is None else [response]
    out = []
    for rname in wanted:
        Xd, terms, beta, s, dof, _, p = _design_matrix_for(rsm, rname)
        XtXi = np.linalg.pinv(Xd.T @ Xd)
        x0 = np.asarray(_x0_row(x, terms), dtype=float)
        yhat = float(x0 @ beta)
        lev = float(x0 @ XtXi @ x0)
        if lev < 0:
            lev = 0.0
        tcrit = float(sps.t.ppf(1 - alpha / 2, dof))
        se_mean = s * math.sqrt(lev)
        se_pred = s * math.sqrt(1.0 + lev)
        extrap = max(abs(v) for v in x) > 1.0 + 1e-9
        out.append({
            "response": rname,
            "predicted": _r(yhat),
            "model_order": next(r["model"]["order"] for r in rsm["responses"]
                                if r["response"] == rname),
            "residual_sd": _r(s),
            "df_residual": dof,
            "leverage": _r(lev),
            "se_mean": _r(se_mean),
            "se_prediction": _r(se_pred),
            "ci_mean": [_r(yhat - tcrit * se_mean), _r(yhat + tcrit * se_mean)],
            "pi_new_batch": [_r(yhat - tcrit * se_pred), _r(yhat + tcrit * se_pred)],
            "confidence_level": round((1 - alpha) * 100, 4),
            "extrapolating": bool(extrap),
            "extrapolation_note": (
                "At least one coded factor level is outside -1 to +1, so this is an "
                "extrapolation beyond the experimental region. The interval widens but "
                "still assumes the fitted model form holds out there, which the data "
                "cannot support." if extrap else None),
        })
    if not out:
        raise QbDError("No responses to predict.")
    return {
        "point_coded": [_r(v) for v in x],
        "factors": names,
        "predictions": out,
        "interval_guidance": (
            "Judge a single confirmation batch against pi_new_batch. ci_mean answers a "
            "different question, the location of the true mean, and is always narrower; "
            "using it to accept or reject one batch will reject batches that are fine."
        ),
    }


def confirm_runs(rsm: Dict[str, Any], runs: List[Dict[str, Any]],
                 alpha: float = 0.05) -> Dict[str, Any]:
    """Compare confirmation batches against what the model predicted.

    runs: [{point: [coded...], observed: {response: value, ...}, label?}]

    This is the step that converts a predicted optimum into a result. Each observed
    value is tested against the prediction interval for a new observation, and the
    verdict is per response, since a batch can confirm on yield and fail on
    impurity.
    """
    if not runs:
        raise QbDError("Supply at least one confirmation run.")
    if len(runs) > 100:
        raise QbDError("At most 100 confirmation runs.")

    results = []
    per_response_err: Dict[str, List[float]] = {}
    for i, r in enumerate(runs, start=1):
        label = str(r.get("label") or f"Confirmation {i}")
        pt = r.get("point")
        if pt is None:
            raise QbDError(f"{label} has no 'point'.")
        obs = r.get("observed") or {}
        if not isinstance(obs, dict) or not obs:
            raise QbDError(f"{label} has no 'observed' values.")
        pred = prediction_at(rsm, pt, None, alpha)
        by_name = {p["response"]: p for p in pred["predictions"]}
        rows = []
        for rname, val in obs.items():
            if rname not in by_name:
                raise QbDError(
                    f"{label} reports response '{rname}', which is not in this model. "
                    f"Known: {list(by_name)}")
            try:
                observed = float(val)
            except (TypeError, ValueError):
                raise QbDError(f"{label} has a non-numeric observed value for '{rname}'.")
            if not math.isfinite(observed):
                raise QbDError(f"{label} has a non-finite observed value for '{rname}'.")
            p = by_name[rname]
            lo, hi = p["pi_new_batch"]
            inside = (lo is not None and hi is not None and lo <= observed <= hi)
            err = observed - p["predicted"]
            pct = (err / p["predicted"] * 100.0) if p["predicted"] else None
            per_response_err.setdefault(rname, []).append(err)
            rows.append({
                "response": rname,
                "predicted": p["predicted"],
                "observed": _r(observed),
                "error": _r(err),
                "percent_error": _r(pct, 4),
                "pi_new_batch": [lo, hi],
                "ci_mean": p["ci_mean"],
                "within_prediction_interval": bool(inside),
                "standardised_error": _r(err / p["se_prediction"]) if p["se_prediction"] else None,
                "verdict": "confirmed" if inside else "not_confirmed",
                "verdict_text": (
                    "The batch fell inside the prediction interval, so the model is not "
                    "contradicted at this point."
                    if inside else
                    "The batch fell outside the prediction interval. The model does not "
                    "describe this point, so predictions from it, including any optimum, "
                    "should not be relied on until the discrepancy is understood."
                ),
            })
        results.append({
            "label": label,
            "point_coded": pred["point_coded"],
            "extrapolating": any(p["extrapolating"] for p in pred["predictions"]),
            "responses": rows,
            "all_confirmed": all(r_["within_prediction_interval"] for r_ in rows),
        })

    # Aggregate bias and spread per response across confirmation runs.
    summary = []
    for rname, errs in per_response_err.items():
        n = len(errs)
        mean_err = sum(errs) / n
        rmsep = math.sqrt(sum(e * e for e in errs) / n)
        entry = {
            "response": rname,
            "n_confirmations": n,
            "mean_error": _r(mean_err),
            "rmsep": _r(rmsep),
            "bias_note": None,
        }
        if n >= 3:
            sd = math.sqrt(sum((e - mean_err) ** 2 for e in errs) / (n - 1))
            if sd > 0:
                from scipy import stats as sps
                t = mean_err / (sd / math.sqrt(n))
                pv = float(2 * (1 - sps.t.cdf(abs(t), n - 1)))
                entry["sd_error"] = _r(sd)
                entry["t_statistic"] = _r(t)
                entry["p_value_bias"] = _r(pv)
                entry["systematic_bias"] = bool(pv < 0.05)
                entry["bias_note"] = (
                    "The confirmation errors have a mean significantly different from "
                    "zero, which is a systematic bias rather than scatter: the model is "
                    "consistently off in one direction even where individual batches sit "
                    "inside their intervals."
                    if pv < 0.05 else
                    "No systematic bias detected across the confirmation runs, though "
                    f"{n} runs is a weak test of it."
                )
        else:
            entry["bias_note"] = (
                f"{n} confirmation run(s) cannot separate systematic bias from ordinary "
                "scatter. Three or more are needed for even a weak test.")
        summary.append(entry)

    total = sum(len(r["responses"]) for r in results)
    confirmed = sum(1 for r in results for x in r["responses"]
                    if x["within_prediction_interval"])
    return {
        "n_runs": len(results),
        "runs": results,
        "summary": summary,
        "n_comparisons": total,
        "n_confirmed": confirmed,
        "overall": "confirmed" if confirmed == total else (
            "partially_confirmed" if confirmed else "not_confirmed"),
        "note": (
            "Each observation is tested against the prediction interval for a new batch, "
            "not the confidence interval for the mean. RMSEP is the error actually seen "
            "on unseen batches and is the honest accuracy figure for the model, as "
            "opposed to the R-squared obtained on the data it was fitted to."
        ),
    }


def confirmation_figure(confirm: Dict[str, Any], response: str) -> Dict[str, Any]:
    """Observed against predicted with the prediction intervals as error bars."""
    pts = []
    for run in confirm.get("runs", []):
        for r in run["responses"]:
            if r["response"] == response:
                pts.append((run["label"], r))
    if not pts:
        raise QbDError(f"No confirmation data for response '{response}'.")
    pred = [p[1]["predicted"] for p in pts]
    obs = [p[1]["observed"] for p in pts]
    lo = [p[1]["predicted"] - p[1]["pi_new_batch"][0] for p in pts]
    hi = [p[1]["pi_new_batch"][1] - p[1]["predicted"] for p in pts]
    lim_lo = min(min(pred), min(obs))
    lim_hi = max(max(pred), max(obs))
    pad = (lim_hi - lim_lo) * 0.08 or 1.0
    return {
        "data": [
            {"x": [round(lim_lo - pad, 6), round(lim_hi + pad, 6)],
             "y": [round(lim_lo - pad, 6), round(lim_hi + pad, 6)],
             "mode": "lines", "type": "scatter", "name": "Perfect agreement",
             "line": {"color": "#7a85a8", "dash": "dash", "width": 1}},
            {"x": pred, "y": obs, "mode": "markers", "type": "scatter",
             "name": "Confirmation batch",
             "marker": {"color": ["#10b981" if p[1]["within_prediction_interval"]
                                  else "#ef4444" for p in pts], "size": 11},
             "error_x": {"type": "data", "symmetric": False, "array": hi,
                         "arrayminus": lo, "color": "#6366f1", "thickness": 1.5},
             "text": [p[0] for p in pts]},
        ],
        "layout": {**_DARK,
                   "title": f"{response} — observed vs predicted, bars are the prediction interval",
                   "xaxis": {"title": f"Predicted {response}"},
                   "yaxis": {"title": f"Observed {response}"}},
    }
