"""Formulation & QbD Studio — Phase 6a: mixture (simplex) designs and Scheffé models.

A formulation is a mixture: the excipient fractions sum to one, so the factors are
not independent and a factorial or central composite design cannot be used. Raising
one component necessarily lowers another, which is why mixture experiments need
their own designs and their own model form.

Three things this module is careful about, each a place where mixture analysis is
commonly reported wrongly:

1. Scheffé polynomials have no intercept. Because the components sum to one, the
   intercept is not identifiable: it is perfectly collinear with the sum of the
   component terms. Fitting an intercept anyway produces a singular or arbitrary
   solution, so the models here are fitted without one.

2. R-squared is computed against the mean model, not against zero. For a
   no-intercept fit the familiar 1 - SS_res / sum(y^2) is inflated and sits near 1
   for almost any data, because it credits the model for predicting the mean. The
   corrected form, 1 - SS_res / sum((y - ybar)^2), is reported instead. It can be
   negative, which correctly signals a model worse than simply quoting the mean.

3. Coefficients are not effects. In a Scheffé model each linear coefficient is the
   predicted response at the pure vertex of that component, and each cross term is a
   deviation from additive blending, not an interaction in the factorial sense.
   Comparing a linear coefficient against zero is meaningless, so significance is
   reported for the blending terms and withheld for the linear terms.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple
import itertools
import logging
import math

logger = logging.getLogger("formulation.mixture")


class MixtureError(ValueError):
    """Invalid mixture design or analysis input. Surfaces as HTTP 400."""


MAX_COMPONENTS = 8
MAX_RUNS = 400

_DARK = {
    "template": "plotly_dark",
    "paper_bgcolor": "#1a1d3a",
    "plot_bgcolor": "#0d0f23",
    "font": {"color": "#b0bcd5", "size": 11},
    "margin": {"l": 60, "r": 20, "t": 44, "b": 50},
}


# ─────────────────────────────────────────────────────────────────────────────
# Designs
# ─────────────────────────────────────────────────────────────────────────────

def _simplex_lattice(q: int, m: int) -> List[List[float]]:
    """Simplex-lattice {q, m}: every proportion a_i/m with the a_i summing to m.

    Point count is C(q + m - 1, m), so it grows quickly in both arguments.
    """
    pts: List[List[float]] = []
    for combo in itertools.combinations_with_replacement(range(q), m):
        row = [0.0] * q
        for c in combo:
            row[c] += 1.0 / m
        pts.append([round(v, 10) for v in row])
    # combinations_with_replacement already yields each composition once.
    return pts


def _simplex_centroid(q: int) -> List[List[float]]:
    """Simplex-centroid: every non-empty subset blended in equal parts, 2^q - 1 points."""
    pts: List[List[float]] = []
    for r in range(1, q + 1):
        for subset in itertools.combinations(range(q), r):
            row = [0.0] * q
            for i in subset:
                row[i] = 1.0 / r
            pts.append([round(v, 10) for v in row])
    return pts


def _axial(q: int, delta: float = 0.5) -> List[List[float]]:
    """Axial points between each vertex and the overall centroid.

    Included because a lattice or centroid design puts almost every point on the
    boundary of the simplex, leaving the interior, where real formulations live,
    barely sampled.
    """
    centre = [1.0 / q] * q
    pts = []
    for i in range(q):
        row = []
        for j in range(q):
            target = 1.0 if j == i else 0.0
            row.append(round(centre[j] + delta * (target - centre[j]), 10))
        pts.append(row)
    return pts


def generate_mixture_design(
    components: List[Dict[str, Any]],
    design_type: str = "simplex_centroid",
    degree: int = 2,
    include_axial: bool = True,
    centre_replicates: int = 3,
    total: float = 1.0,
    randomize: bool = True,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """Build a mixture experiment matrix in proportions and in real amounts.

    components: [{name, unit?}]
    design_type: simplex_lattice | simplex_centroid
    total: the batch total the proportions are scaled to, e.g. 1.0, 100 for percent,
           or 500 for mg per tablet.
    """
    import numpy as np

    if not components:
        raise MixtureError("Define at least two components.")
    names, units = [], []
    for i, c in enumerate(components):
        nm = str(c.get("name") or f"C{i + 1}").strip() or f"C{i + 1}"
        names.append(nm)
        units.append(str(c.get("unit") or ""))
    q = len(names)
    if q < 2:
        raise MixtureError("A mixture needs at least two components.")
    if q > MAX_COMPONENTS:
        raise MixtureError(f"At most {MAX_COMPONENTS} components.")
    if len(set(names)) != q:
        raise MixtureError("Component names must be unique.")
    if not (math.isfinite(total) and total > 0):
        raise MixtureError("total must be a positive number.")
    if not 0 <= centre_replicates <= 20:
        raise MixtureError("centre_replicates must be between 0 and 20.")

    notes: List[str] = []
    if design_type == "simplex_lattice":
        if not 1 <= degree <= 4:
            raise MixtureError("degree must be between 1 and 4 for a simplex lattice.")
        pts = _simplex_lattice(q, degree)
        if degree < 2:
            notes.append(
                "A degree-1 lattice contains only the pure components, so it can fit "
                "the linear Scheffé model but cannot detect any blending effect.")
    elif design_type == "simplex_centroid":
        pts = _simplex_centroid(q)
    else:
        raise MixtureError("design_type must be simplex_lattice or simplex_centroid.")

    if include_axial:
        existing = {tuple(p) for p in pts}
        for a in _axial(q):
            if tuple(a) not in existing:
                pts.append(a)
                existing.add(tuple(a))
    else:
        notes.append(
            "Without axial points nearly every run sits on the boundary of the simplex, "
            "so the interior of the design space, where most real formulations sit, is "
            "only sampled at the centroid.")

    centre = [round(1.0 / q, 10)] * q
    n_unique = len(pts)
    if centre_replicates:
        for _ in range(centre_replicates):
            pts.append(list(centre))
    else:
        notes.append(
            "With no replicated centroid there is no pure-error estimate, so lack of fit "
            "cannot be tested.")

    if len(pts) > MAX_RUNS:
        raise MixtureError(f"That design needs {len(pts)} runs, above the {MAX_RUNS} limit.")

    order = list(range(len(pts)))
    if randomize:
        rng = np.random.default_rng(seed)
        rng.shuffle(order)
        notes.append("Run order is randomised so time-related drift cannot be mistaken "
                     "for a component effect.")

    runs = []
    for run_no, idx in enumerate(order, start=1):
        p = pts[idx]
        s = sum(p)
        if abs(s - 1.0) > 1e-6:
            raise MixtureError(f"Internal: design point {idx} sums to {s}, not 1.")
        runs.append({
            "run": run_no,
            "design_point": idx + 1,
            "is_centroid": idx >= n_unique or all(abs(v - centre[0]) < 1e-9 for v in p),
            "proportions": {names[i]: round(p[i], 6) for i in range(q)},
            "amounts": {names[i]: round(p[i] * total, 6) for i in range(q)},
            "proportion_vector": [round(v, 10) for v in p],
        })

    n_terms = {1: q, 2: q + q * (q - 1) // 2,
               3: q + q * (q - 1) // 2 + q * (q - 1) * (q - 2) // 6}
    return {
        "design_type": design_type,
        "components": [{"name": names[i], "unit": units[i]} for i in range(q)],
        "n_components": q,
        "degree": degree if design_type == "simplex_lattice" else None,
        "n_runs": len(pts),
        "n_unique_points": n_unique,
        "centre_replicates": centre_replicates,
        "include_axial": include_axial,
        "total": total,
        "randomized": randomize,
        "seed": seed,
        "runs": runs,
        "terms_required": {"linear": n_terms[1], "quadratic": n_terms[2],
                           "special_cubic": n_terms.get(3)},
        "degrees_of_freedom_quadratic": len(pts) - n_terms[2],
        "notes": notes,
        "constraint": "Every run's proportions sum to 1 by construction; amounts sum to total.",
        "guidance": (
            "Enter one response per run, then post to /formulation/mixture/analyse. "
            "If a component has a hard lower or upper bound, this unconstrained simplex "
            "will propose blends you cannot make; constrained (pseudo-component) designs "
            "are not implemented here, so screen the run list before executing it."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Scheffé analysis
# ─────────────────────────────────────────────────────────────────────────────

def _scheffe_terms(names: Sequence[str], model: str):
    q = len(names)
    terms: List[Tuple[str, Tuple[int, ...]]] = [(n, (i,)) for i, n in enumerate(names)]
    if model in ("quadratic", "special_cubic"):
        for i, j in itertools.combinations(range(q), 2):
            terms.append((f"{names[i]}*{names[j]}", (i, j)))
    if model == "special_cubic":
        for i, j, k in itertools.combinations(range(q), 3):
            terms.append((f"{names[i]}*{names[j]}*{names[k]}", (i, j, k)))
    return terms


def analyse_mixture(runs: List[Dict[str, Any]], responses: List[Dict[str, Any]],
                    component_names: Optional[List[str]] = None,
                    model: str = "quadratic") -> Dict[str, Any]:
    """Fit Scheffé mixture models, without an intercept, and report adequacy.

    runs: [{proportion_vector: [...]}] or [{proportions: {name: value}}]
    responses: [{name, values: [...]}]
    """
    import numpy as np
    from scipy import stats as sps

    if model not in ("linear", "quadratic", "special_cubic"):
        raise MixtureError("model must be linear, quadratic or special_cubic.")
    if not runs:
        raise MixtureError("No runs supplied.")
    if not responses:
        raise MixtureError("Supply at least one response.")

    X_prop: List[List[float]] = []
    for i, r in enumerate(runs, start=1):
        if r.get("proportion_vector"):
            vec = r["proportion_vector"]
        elif r.get("proportions") and component_names:
            try:
                vec = [float(r["proportions"][n]) for n in component_names]
            except (KeyError, TypeError, ValueError):
                raise MixtureError(f"Run {i} is missing a proportion for one of {component_names}.")
        else:
            raise MixtureError(
                f"Run {i} needs 'proportion_vector', or 'proportions' with component_names.")
        try:
            vec = [float(v) for v in vec]
        except (TypeError, ValueError):
            raise MixtureError(f"Run {i} has a non-numeric proportion.")
        if any((not math.isfinite(v)) or v < -1e-9 for v in vec):
            raise MixtureError(f"Run {i} has a negative or non-finite proportion.")
        s = sum(vec)
        if abs(s - 1.0) > 1e-4:
            raise MixtureError(
                f"Run {i} proportions sum to {round(s, 6)}, not 1. Mixture components must "
                "be expressed as fractions of the batch; divide by the batch total first.")
        X_prop.append(vec)

    q = len(X_prop[0])
    if any(len(v) != q for v in X_prop):
        raise MixtureError("Every run must list the same number of components.")
    names = component_names or [f"C{i + 1}" for i in range(q)]
    if len(names) != q:
        raise MixtureError(f"component_names has {len(names)} entries but runs have {q}.")

    n = len(X_prop)
    terms = _scheffe_terms(names, model)
    p = len(terms)
    if n <= p:
        raise MixtureError(
            f"{n} runs cannot fit the {model} Scheffé model, which needs {p} terms "
            f"(and more runs than terms to estimate error). Use a simpler model.")

    # No intercept: with sum(x)=1 the intercept is collinear with the linear terms.
    X = np.asarray([[math.prod(row[i] for i in idx) for _, idx in terms] for row in X_prop],
                   dtype=float)

    out = []
    for spec in responses:
        rname = str(spec.get("name") or "Response").strip() or "Response"
        vals = spec.get("values")
        if not isinstance(vals, (list, tuple)) or len(vals) != n:
            raise MixtureError(
                f"Response '{rname}' has "
                f"{len(vals) if isinstance(vals, (list, tuple)) else 0} values but there "
                f"are {n} runs.")
        try:
            y = np.asarray([float(v) for v in vals], dtype=float)
        except (TypeError, ValueError):
            raise MixtureError(f"Response '{rname}' has a non-numeric value.")
        if not np.all(np.isfinite(y)):
            raise MixtureError(f"Response '{rname}' has a non-finite value.")
        if len(set(np.round(y, 12))) == 1:
            raise MixtureError(f"Response '{rname}' is constant, so nothing can be modelled.")

        XtX = X.T @ X
        try:
            XtXi = np.linalg.inv(XtX)
        except np.linalg.LinAlgError:
            raise MixtureError(
                "The mixture model matrix is singular: this design cannot separate the "
                "requested terms. A simplex-lattice of degree 1, or a design without "
                "axial or centroid points, often cannot support the quadratic model.")
        beta = XtXi @ X.T @ y
        fitted = X @ beta
        resid = y - fitted
        dof = n - p
        ss_res = float(resid @ resid)
        # Corrected against the mean model. See the module docstring.
        ss_tot = float(((y - y.mean()) ** 2).sum())
        ss_tot_uncorrected = float((y ** 2).sum())
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else None
        r2_uncorrected = 1.0 - ss_res / ss_tot_uncorrected if ss_tot_uncorrected > 0 else None
        adj = (1.0 - (1.0 - r2) * (n - 1) / dof) if (r2 is not None and dof > 0) else None
        s = math.sqrt(ss_res / dof) if dof > 0 else None
        tcrit = float(sps.t.ppf(0.975, dof)) if dof > 0 else None

        coeffs = []
        for i, (lab, idx) in enumerate(terms):
            se = float(math.sqrt(max(XtXi[i, i], 0.0)) * s) if s else None
            tv = (float(beta[i]) / se) if se else None
            pv = float(2 * (1 - sps.t.cdf(abs(tv), dof))) if (tv is not None and dof > 0) else None
            is_linear = len(idx) == 1
            coeffs.append({
                "term": lab,
                "kind": "vertex" if is_linear else ("binary_blend" if len(idx) == 2
                                                    else "ternary_blend"),
                "coefficient": _r(beta[i]),
                "std_error": _r(se),
                "t_statistic": None if is_linear else _r(tv),
                "p_value": None if is_linear else _r(pv),
                "ci_95": [_r(float(beta[i]) - tcrit * se), _r(float(beta[i]) + tcrit * se)]
                if (se and tcrit) else [None, None],
                "significant": None if is_linear else bool(pv is not None and pv < 0.05),
                "meaning": (
                    f"Predicted response for pure {lab}. Testing it against zero is not "
                    "meaningful, so no p-value is given."
                    if is_linear else
                    "Departure from additive blending between these components. A "
                    "significant value means the blend is not simply the weighted average "
                    "of its parts; positive is synergy, negative is antagonism."
                ),
            })

        # Pure error from replicated design points, so lack of fit can be tested.
        groups: Dict[Tuple, List[float]] = {}
        for row, val in zip(X_prop, y.tolist()):
            groups.setdefault(tuple(round(v, 9) for v in row), []).append(val)
        ss_pe, df_pe = 0.0, 0
        for vs in groups.values():
            if len(vs) > 1:
                mu = sum(vs) / len(vs)
                ss_pe += sum((v - mu) ** 2 for v in vs)
                df_pe += len(vs) - 1
        if df_pe > 0 and dof > df_pe and ss_pe > 0:
            ss_lof = max(ss_res - ss_pe, 0.0)
            df_lof = dof - df_pe
            f = (ss_lof / df_lof) / (ss_pe / df_pe) if df_lof > 0 else None
            pv = float(1 - sps.f.cdf(f, df_lof, df_pe)) if f is not None else None
            lof = {"available": True, "f_statistic": _r(f), "p_value": _r(pv),
                   "df_lack_of_fit": df_lof, "df_pure_error": df_pe,
                   "significant_misfit": bool(pv is not None and pv < 0.05),
                   "interpretation": (
                       "Lack of fit is significant: this Scheffé model misses real "
                       "blending structure. Try the special cubic, or reconsider whether a "
                       "component is acting outside the range studied."
                       if pv is not None and pv < 0.05 else
                       "Lack of fit is not significant; deviations are within replicate "
                       "scatter.")}
        else:
            lof = {"available": False,
                   "reason": ("No replicated blends, so pure error cannot be separated from "
                              "misfit. Replicate the centroid to enable this test."
                              if df_pe == 0 else
                              "Identical replicates or no spare degrees of freedom, so the "
                              "F ratio is undefined.")}

        out.append({
            "response": rname,
            "model": model,
            "n_runs": n,
            "n_terms": p,
            "df_residual": dof,
            "coefficients": coeffs,
            "r_squared": _r(r2),
            "adj_r_squared": _r(adj),
            "r_squared_uncorrected": _r(r2_uncorrected),
            "rmse": _r(s),
            "ss_residual": _r(ss_res),
            "fitted": [_r(v) for v in fitted.tolist()],
            "residuals": [_r(v) for v in resid.tolist()],
            "lack_of_fit": lof,
            "r_squared_note": (
                "r_squared is corrected against the mean model. r_squared_uncorrected is "
                "the 1 - SS_res / sum(y^2) form that many tools print for no-intercept "
                "fits; it is shown only so the difference is visible, and it is not a "
                "measure of fit. A negative corrected value means the model predicts worse "
                "than the response mean."
            ),
        })

    return {
        "n_runs": n,
        "n_components": q,
        "components": names,
        "model": model,
        "responses": out,
        "proportion_runs": X_prop,
        "model_form": {
            "linear": "y = sum(bi * xi)",
            "quadratic": "y = sum(bi * xi) + sum over i<j (bij * xi * xj)",
            "special_cubic": "quadratic plus sum over i<j<k (bijk * xi * xj * xk)",
            "no_intercept": "There is no intercept: with sum(xi) = 1 it is not identifiable.",
        },
    }


def _r(v, nd: int = 6):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return round(f, nd) if math.isfinite(f) else None


def predict_mixture(result: Dict[str, Any], proportions: Sequence[float],
                    response: Optional[str] = None) -> Dict[str, Any]:
    """Predict the response for a blend, refusing blends that are not mixtures."""
    names = result.get("components") or []
    q = len(names)
    try:
        x = [float(v) for v in proportions]
    except (TypeError, ValueError):
        raise MixtureError("proportions must be numeric.")
    if len(x) != q:
        raise MixtureError(f"proportions must have {q} values for {names}.")
    if any(v < -1e-9 for v in x):
        raise MixtureError("proportions cannot be negative.")
    s = sum(x)
    if abs(s - 1.0) > 1e-4:
        raise MixtureError(f"proportions sum to {round(s, 6)}, not 1.")

    out = []
    for r in result["responses"]:
        if response and r["response"] != response:
            continue
        terms = _scheffe_terms(names, r["model"])
        v = 0.0
        for c, (_, idx) in zip([c["coefficient"] for c in r["coefficients"]], terms):
            v += c * math.prod(x[i] for i in idx)
        out.append({"response": r["response"], "predicted": _r(v),
                    "model": r["model"], "rmse": r["rmse"]})
    if not out:
        raise MixtureError(f"Response '{response}' is not in this result.")
    return {"proportions": {names[i]: _r(x[i]) for i in range(q)},
            "predictions": out,
            "caveat": "Model prediction for a blend, not an observed result."}


def ternary_figure(result: Dict[str, Any], response: str,
                   resolution: int = 22,
                   fixed: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """Ternary contour over three components; any others held at fixed values."""
    names = result.get("components") or []
    q = len(names)
    if q < 3:
        raise MixtureError("A ternary plot needs at least three components.")
    target = next((r for r in result["responses"] if r["response"] == response), None)
    if target is None:
        raise MixtureError(f"Unknown response '{response}'.")
    terms = _scheffe_terms(names, target["model"])
    beta = [c["coefficient"] for c in target["coefficients"]]

    fixed = fixed or {}
    free = [i for i, n in enumerate(names) if n not in fixed]
    if len(free) != 3:
        raise MixtureError(
            f"Exactly three components must be free; {len(free)} are. Fix the others via "
            "'fixed', for example {\"" + names[-1] + "\": 0.1}.")
    held = sum(float(v) for v in fixed.values())
    if held < 0 or held >= 1:
        raise MixtureError("Fixed components must sum to at least 0 and less than 1.")
    budget = 1.0 - held

    res = max(6, min(int(resolution), 40))
    a_s, b_s, c_s, zs = [], [], [], []
    for i in range(res + 1):
        for j in range(res + 1 - i):
            k = res - i - j
            fa, fb, fc = i / res, j / res, k / res
            x = [0.0] * q
            for nm, v in fixed.items():
                x[names.index(nm)] = float(v)
            x[free[0]] = fa * budget
            x[free[1]] = fb * budget
            x[free[2]] = fc * budget
            v = 0.0
            for c, (_, idx) in zip(beta, terms):
                v += c * math.prod(x[t] for t in idx)
            a_s.append(round(fa, 6)); b_s.append(round(fb, 6)); c_s.append(round(fc, 6))
            zs.append(_r(v))

    return {
        "data": [{
            "type": "scatterternary", "mode": "markers",
            "a": a_s, "b": b_s, "c": c_s,
            "marker": {"color": zs, "colorscale": "Viridis", "size": 7,
                       "showscale": True, "colorbar": {"title": response}},
            "text": [f"{response} = {z}" for z in zs],
            "hoverinfo": "text",
            "name": response,
        }],
        "layout": {
            **_DARK,
            "title": (f"{response} over {names[free[0]]}, {names[free[1]]}, {names[free[2]]}"
                      + (f" (others fixed: {fixed})" if fixed else "")),
            "ternary": {
                "sum": 1,
                "aaxis": {"title": names[free[0]]},
                "baxis": {"title": names[free[1]]},
                "caxis": {"title": names[free[2]]},
                "bgcolor": "#0d0f23",
            },
        },
    }


def design_catalogue() -> Dict[str, Any]:
    """Mixture designs and models available, with their limits."""
    return {
        "designs": [
            {"id": "simplex_centroid", "label": "Simplex-centroid",
             "points": "2^q - 1 blends plus optional axial and centroid replicates",
             "supports": "linear and quadratic Scheffé; special cubic for q >= 3",
             "limitation": "Almost all points lie on the simplex boundary unless axial "
                           "points are included."},
            {"id": "simplex_lattice", "label": "Simplex-lattice {q, m}",
             "points": "C(q + m - 1, m) blends",
             "supports": "polynomials up to degree m",
             "limitation": "Degree 1 contains only pure components and cannot detect "
                           "blending at all."},
        ],
        "models": [
            {"id": "linear", "form": "y = sum(bi xi)",
             "meaning": "Additive blending; each bi is the pure-component response."},
            {"id": "quadratic", "form": "y = sum(bi xi) + sum_{i<j}(bij xi xj)",
             "meaning": "Adds pairwise deviation from additivity."},
            {"id": "special_cubic", "form": "quadratic + sum_{i<j<k}(bijk xi xj xk)",
             "meaning": "Adds three-way blending; needs interior design points."},
        ],
        "not_implemented": {
            "constrained mixture regions": "Components with hard lower or upper bounds "
                                           "require pseudo-component transformation and an "
                                           "extreme-vertices design; the simplex designs "
                                           "here will propose infeasible blends if bounds "
                                           "exist.",
            "mixture-process variables": "Designs crossing a mixture with process factors "
                                         "such as compression force are not supported.",
        },
        "max_components": MAX_COMPONENTS,
    }
