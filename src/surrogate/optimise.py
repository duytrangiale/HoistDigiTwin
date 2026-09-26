"""Searches the surrogate for the operating settings that maximise monthly
tonnes, then verifies the result against the real simulation. See
phase4_plan.md at the repo root for why the search is expected to land at
a corner of the parameter box, and what that does and does not mean.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from skopt import gp_minimize
from skopt.space import Real

from .sampling import HIGHER_IS_BETTER, PARAM_RANGES


def predict_tonnes(model, params: dict) -> float:
    """A single surrogate prediction from a parameter dict."""
    row = pd.DataFrame([params], columns=list(PARAM_RANGES.keys()))
    return float(model.predict(row)[0])


def baseline_params(base_config: dict) -> dict:
    """The typical year settings, expressed in the same units as
    PARAM_RANGES: multipliers at 1.0, everything else at its config.yaml
    value. The natural centre point for the partial dependence sweep and
    the starting point for the sensitivity ranking."""
    return {
        "feed_rate_multiplier": 1.0,
        "skip_payload_tonnes": base_config["skips"]["payload_tonnes"],
        "winder_speed_multiplier": 1.0,
        "breakdown_mtbf_hours": base_config["winder"]["breakdown_mtbf_hours"],
        "scheduled_downtime_hours_per_month": base_config["winder"]["scheduled_downtime_hours_per_month"],
    }


def partial_dependence(
    model,
    param_ranges: dict[str, tuple[float, float]],
    baseline: dict,
    n_points: int = 25,
) -> pd.DataFrame:
    """Sweeps one parameter at a time across its range, holding the rest
    at baseline, and records the surrogate's prediction. Cheap, since the
    surrogate is instant, and worth doing before any search: it either
    confirms the monotonic story in phase4_plan.md or flags a parameter
    that behaves differently than expected.
    """
    rows = []
    for param_name, (lo, hi) in param_ranges.items():
        for value in np.linspace(lo, hi, n_points):
            params = dict(baseline)
            params[param_name] = value
            rows.append(
                {
                    "param_name": param_name,
                    "param_value": value,
                    "predicted_tonnes": predict_tonnes(model, params),
                }
            )
    return pd.DataFrame(rows)


def random_search(
    model,
    param_ranges: dict[str, tuple[float, float]],
    n_evaluations: int,
    seed: int,
) -> pd.DataFrame:
    """Samples n_evaluations points uniformly at random and evaluates the
    surrogate at each. The baseline every other search method here gets
    compared against, both for the answer it finds and for how many
    evaluations it needed to find it."""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n_evaluations):
        params = {name: rng.uniform(lo, hi) for name, (lo, hi) in param_ranges.items()}
        rows.append({"evaluation": i, **params, "predicted_tonnes": predict_tonnes(model, params)})
    result = pd.DataFrame(rows)
    result["best_so_far"] = result["predicted_tonnes"].cummax()
    return result


def bayesian_search(
    model,
    param_ranges: dict[str, tuple[float, float]],
    n_evaluations: int,
    seed: int,
) -> pd.DataFrame:
    """Bayesian optimisation via scikit-optimize. Minimises the negative
    predicted tonnes, since skopt minimises by default. Returns the same
    shape as random_search, evaluation number, every parameter tried, the
    surrogate's prediction, and a running best so far, so both plot on the
    same convergence axes."""
    param_names = list(param_ranges.keys())
    dimensions = [Real(lo, hi, name=name) for name, (lo, hi) in param_ranges.items()]

    def objective(x: list[float]) -> float:
        params = dict(zip(param_names, x))
        return -predict_tonnes(model, params)

    opt_result = gp_minimize(objective, dimensions, n_calls=n_evaluations, random_state=seed)

    rows = []
    for i, (x, neg_tonnes) in enumerate(zip(opt_result.x_iters, opt_result.func_vals)):
        params = dict(zip(param_names, x))
        rows.append({"evaluation": i, **params, "predicted_tonnes": -neg_tonnes})
    result = pd.DataFrame(rows)
    result["best_so_far"] = result["predicted_tonnes"].cummax()
    return result


def corner_optimum(param_ranges: dict[str, tuple[float, float]]) -> dict:
    """The analytically known best point: every parameter pushed to
    whichever bound helps monthly tonnes. Maximum on every parameter
    except scheduled downtime, minimum there. HIGHER_IS_BETTER lives in
    sampling.py since it is a fact about the parameter space itself, also
    used there to build the corner focused training points."""
    return {
        name: (hi if HIGHER_IS_BETTER[name] else lo) for name, (lo, hi) in param_ranges.items()
    }


def sensitivity_breakdown(model, baseline: dict, optimal: dict) -> pd.DataFrame:
    """Changes one parameter at a time from baseline to its optimal value,
    holding the rest at baseline, and reports the tonnage gained from that
    single change alone. Turns "every lever maxed out" into a ranked
    answer to "which single lever matters most," the more useful question
    for someone who cannot upgrade five things simultaneously."""
    baseline_tonnes = predict_tonnes(model, baseline)
    rows = []
    for param_name in baseline:
        changed = dict(baseline)
        changed[param_name] = optimal[param_name]
        predicted = predict_tonnes(model, changed)
        rows.append(
            {
                "param_name": param_name,
                "baseline_value": baseline[param_name],
                "optimal_value": optimal[param_name],
                "predicted_tonnes": predicted,
                "tonnes_gained": predicted - baseline_tonnes,
            }
        )
    return pd.DataFrame(rows).sort_values("tonnes_gained", ascending=False).reset_index(drop=True)
