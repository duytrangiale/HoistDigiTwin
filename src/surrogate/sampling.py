"""Builds labelled training and held out data for the surrogate: a Latin
hypercube design over five operating settings, each point run through the
real twin. See reports/phase3_plan.md at the repo root for the reasoning
behind the parameters, ranges, and horizon.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd
from scipy.stats import qmc

from twin.scenarios import typical_year_scenario
from twin.simulation import SimulationResult, run_simulation

# lower, upper bounds for each parameter, straddling the feed constrained
# and winder bound regimes already found in Phase 1 and 2, so the surrogate
# has a real kink to learn, not just a slope
PARAM_RANGES: dict[str, tuple[float, float]] = {
    "feed_rate_multiplier": (0.5, 1.5),
    "skip_payload_tonnes": (8.0, 16.0),
    "winder_speed_multiplier": (0.7, 1.4),
    "breakdown_mtbf_hours": (100.0, 400.0),
    "scheduled_downtime_hours_per_month": (5.0, 40.0),
}

# whether higher or lower is better for monthly tonnes, confirmed
# empirically in Phase 4 (see phase4_plan.md). Since every parameter is
# weakly helpful or neutral in its better direction and never harmful, the
# true optimum sits at this corner of the box, which is also where the
# design above, spread evenly across the whole range, has the least data.
HIGHER_IS_BETTER: dict[str, bool] = {
    "feed_rate_multiplier": True,
    "skip_payload_tonnes": True,
    "winder_speed_multiplier": True,
    "breakdown_mtbf_hours": True,
    "scheduled_downtime_hours_per_month": False,
}


def generate_design(n_samples: int, param_ranges: dict[str, tuple[float, float]], seed: int) -> pd.DataFrame:
    """A Latin hypercube design over param_ranges, one row per sample,
    columns named after the parameters."""
    sampler = qmc.LatinHypercube(d=len(param_ranges), seed=seed)
    unit_samples = sampler.random(n=n_samples)
    lower = [bounds[0] for bounds in param_ranges.values()]
    upper = [bounds[1] for bounds in param_ranges.values()]
    scaled = qmc.scale(unit_samples, lower, upper)
    return pd.DataFrame(scaled, columns=list(param_ranges.keys()))


def generate_corner_focused_design(
    n_samples: int,
    param_ranges: dict[str, tuple[float, float]],
    higher_is_better: dict[str, bool],
    seed: int,
) -> pd.DataFrame:
    """A Latin hypercube design restricted to the favourable half of each
    parameter's range, the region an unconstrained search always heads
    toward (see phase4_plan.md), and where generate_design's even spread
    across the whole range leaves the least data. Meant to supplement the
    main training set, not replace it."""
    favorable_ranges = {}
    for name, (lo, hi) in param_ranges.items():
        mid = (lo + hi) / 2
        favorable_ranges[name] = (mid, hi) if higher_is_better[name] else (lo, mid)
    return generate_design(n_samples, favorable_ranges, seed)


def config_from_params(base_config: dict, params: dict, horizon_days: int) -> dict:
    """A typical year config with the five surrogate parameters applied.
    Feed rate multiplier scales both sources together, winder speed
    multiplier divides hoist and return time together, since both come
    from the same physical shaft speed.

    Flask capacity scales with skip payload, keeping the same ratio as
    config.yaml's own 15 tonne flask against a 12 tonne skip. A flask with
    a fixed capacity cannot be skipped over: a skip whose payload exceeds
    its flask's capacity waits forever for a load that can never complete,
    since flask.get(payload_tonnes) can never be satisfied. This showed up
    directly during the step 1 smoke test, one sampled payload of 15.9
    tonnes against the fixed 15 tonne flask produced exactly zero output.
    """
    config = typical_year_scenario(base_config)
    config["simulation"]["horizon_days"] = horizon_days

    config["sources"]["source_a"]["feed_rate_tph"] *= params["feed_rate_multiplier"]
    config["sources"]["source_b"]["feed_rate_tph"] *= params["feed_rate_multiplier"]

    config["skips"]["payload_tonnes"] = params["skip_payload_tonnes"]
    flask_to_payload_ratio = base_config["flasks"]["capacity_tonnes"] / base_config["skips"]["payload_tonnes"]
    config["flasks"]["capacity_tonnes"] = params["skip_payload_tonnes"] * flask_to_payload_ratio
    config["skips"]["hoist_time_mean_s"] /= params["winder_speed_multiplier"]
    config["skips"]["return_time_mean_s"] /= params["winder_speed_multiplier"]

    config["winder"]["breakdown_mtbf_hours"] = params["breakdown_mtbf_hours"]
    config["winder"]["scheduled_downtime_hours_per_month"] = params["scheduled_downtime_hours_per_month"]

    return config


def mean_monthly_tonnes(result: SimulationResult, horizon_days: int) -> float:
    """Mean tonnes per 30 day month. Drops a trailing partial month only
    when the horizon is not an exact multiple of 30 days, so a 90 day
    training run keeps all three of its full months, matching how a 365
    day run already drops its trailing partial one in scenarios.py."""
    monthly = result.monthly_tonnes
    if horizon_days % 30 != 0 and len(monthly) > 1:
        monthly = monthly.iloc[:-1]
    return float(monthly.mean()) if len(monthly) > 0 else 0.0


def _run_one_point(args: tuple[int, dict, int, int]) -> tuple[int, float, float]:
    """Runs one replication of one design point. Returns the point index
    so replications of the same point can be grouped and averaged
    afterward. bin_sample_interval_minutes is set to the whole horizon,
    since the surrogate only needs the tonnage total, not a bin level time
    series, and hundreds of runs logging bin levels every 30 minutes would
    waste memory for nothing this phase uses."""
    point_index, config, seed, horizon_days = args
    result = run_simulation(config, seed=seed, bin_sample_interval_minutes=horizon_days * 24 * 60)
    return point_index, mean_monthly_tonnes(result, horizon_days), result.winder_utilisation_pct


def run_design(
    base_config: dict,
    design: pd.DataFrame,
    n_replications: int,
    horizon_days: int,
    seed: int,
    n_workers: int | None = None,
) -> pd.DataFrame:
    """Runs every point in an already built design through the simulator,
    n_replications each, averaged. Shared by build_training_set,
    build_held_out_set, and build_corner_focused_set, which only differ in
    which design they hand it."""
    tasks = []
    for point_index, row in design.iterrows():
        params = row.to_dict()
        config = config_from_params(base_config, params, horizon_days)
        for replication in range(n_replications):
            replication_seed = seed + point_index * 100 + replication
            tasks.append((point_index, config, replication_seed, horizon_days))

    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        results = list(executor.map(_run_one_point, tasks))

    results_df = pd.DataFrame(results, columns=["point_index", "monthly_tonnes", "winder_utilisation_pct"])
    per_point = results_df.groupby("point_index")[["monthly_tonnes", "winder_utilisation_pct"]].mean()

    return design.join(per_point)


def build_training_set(
    base_config: dict,
    n_samples: int = 200,
    n_replications: int = 3,
    horizon_days: int = 90,
    seed: int = 42,
    n_workers: int | None = None,
    save_path: str = "data/processed/surrogate_training_set.csv",
) -> pd.DataFrame:
    """Builds and saves the surrogate's training set: n_samples Latin
    hypercube points, each the mean of n_replications short simulation
    runs."""
    design = generate_design(n_samples, PARAM_RANGES, seed)
    labeled = run_design(base_config, design, n_replications, horizon_days, seed, n_workers)
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    labeled.to_csv(save_path, index=False)
    return labeled


def build_held_out_set(
    base_config: dict,
    n_samples: int = 30,
    n_replications: int = 8,
    horizon_days: int = 90,
    seed: int = 999,
    n_workers: int | None = None,
    save_path: str = "data/processed/surrogate_held_out_set.csv",
) -> pd.DataFrame:
    """The same mechanism as build_training_set, a different seed so the
    points do not overlap the training design, and more replications per
    point for a less noisy target to check predictions against."""
    design = generate_design(n_samples, PARAM_RANGES, seed)
    labeled = run_design(base_config, design, n_replications, horizon_days, seed, n_workers)
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    labeled.to_csv(save_path, index=False)
    return labeled


def build_corner_focused_set(
    base_config: dict,
    n_samples: int = 30,
    n_replications: int = 12,
    horizon_days: int = 90,
    seed: int = 5000,
    n_workers: int | None = None,
    save_path: str = "data/processed/surrogate_corner_training_set.csv",
) -> pd.DataFrame:
    """Extra training points restricted to the favourable half of the
    space, meant to be added to build_training_set's output, not used
    alone. More replications per point than the main training set (12
    against 3), since these points carry more weight for the accuracy of
    the final answer, given Phase 4's search always heads here."""
    design = generate_corner_focused_design(n_samples, PARAM_RANGES, HIGHER_IS_BETTER, seed)
    labeled = run_design(base_config, design, n_replications, horizon_days, seed, n_workers)
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    labeled.to_csv(save_path, index=False)
    return labeled
