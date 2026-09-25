"""Runs many replications of a scenario and summarises the results. A
scenario is just a config dict, so Phase 2 can build several scenarios by
copying config.yaml and overriding a few values, and compare them with this
same function. See simulation.py for a single run.
"""

from __future__ import annotations

import copy
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from .simulation import run_simulation


@dataclass
class ScenarioResult:
    """Summary statistics across replications of one scenario."""

    n_replications: int
    mean_monthly_tonnes: float
    ci_low: float
    ci_high: float
    monthly_tonnes_by_replication: pd.DataFrame  # rows: replication, columns: month index
    mean_winder_utilisation_pct: float


def _run_one_replication(args: tuple[dict, int]) -> tuple[pd.Series, float]:
    config, seed = args
    result = run_simulation(config, seed=seed)
    # the horizon is 365 days, not a multiple of 30, so the last month is a
    # partial month and would understate a typical month if kept
    monthly = result.monthly_tonnes
    if len(monthly) > 1:
        monthly = monthly.iloc[:-1]
    return monthly, result.winder_utilisation_pct


def run_scenario(
    config: dict,
    n_replications: int = 20,
    base_seed: int = 0,
    n_workers: int | None = None,
) -> ScenarioResult:
    """Runs the simulation n_replications times, each with a different
    seed, and summarises monthly tonnes with a 95 percent confidence
    interval. Replications run in parallel across CPU cores, since each one
    is independent and CPU bound, which is what makes hundreds of them
    practical rather than a multi minute wait.
    """
    seeds = [base_seed + i for i in range(n_replications)]
    args = [(config, s) for s in seeds]

    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        results = list(executor.map(_run_one_replication, args))

    monthly_by_replication = pd.DataFrame([monthly for monthly, _ in results]).reset_index(drop=True)
    utilisations = [util for _, util in results]

    replication_means = monthly_by_replication.mean(axis=1)
    mean = float(replication_means.mean())
    if n_replications > 1:
        sem = stats.sem(replication_means)
        ci_low, ci_high = stats.t.interval(0.95, n_replications - 1, loc=mean, scale=sem)
    else:
        ci_low = ci_high = mean

    return ScenarioResult(
        n_replications=n_replications,
        mean_monthly_tonnes=mean,
        ci_low=float(ci_low),
        ci_high=float(ci_high),
        monthly_tonnes_by_replication=monthly_by_replication,
        mean_winder_utilisation_pct=float(np.mean(utilisations)),
    )


def typical_year_scenario(base_config: dict) -> dict:
    """A normal year: current skip and winder parameters, flat scheduled
    downtime every month, no calendar specific events. config.yaml itself
    carries Phase 1's calendar overrides for calibrating against the
    synthetic twelve month target, which describe one specific invented
    past year, not ongoing operation, so every scenario here starts from a
    copy with those removed instead."""
    config = copy.deepcopy(base_config)
    config["winder"].pop("scheduled_downtime_overrides", None)
    return config


def skip_outage_scenario(
    base_config: dict,
    skip_name: str = "west",
    start_day: int = 100,
    duration_days: int = 7,
) -> dict:
    """The typical year, with one skip out of service for a stretch. The
    other skip keeps running and has the winder to itself for that time."""
    config = typical_year_scenario(base_config)
    config["skip_outages"] = [
        {"skip": skip_name, "start_day": start_day, "duration_days": duration_days}
    ]
    return config


def higher_feed_more_breakdowns_scenario(
    base_config: dict,
    feed_multiplier: float = 1.3,
    mtbf_multiplier: float = 0.5,
) -> dict:
    """The typical year, with both source feed rates raised and the winder
    breaking down more often. Tests whether more ore actually helps when
    the winder, not the feed, is the bottleneck (see
    reports/simulation_validation.md)."""
    config = typical_year_scenario(base_config)
    config["sources"]["source_a"]["feed_rate_tph"] *= feed_multiplier
    config["sources"]["source_b"]["feed_rate_tph"] *= feed_multiplier
    config["winder"]["breakdown_mtbf_hours"] *= mtbf_multiplier
    return config


def compare_scenarios(
    scenarios: dict[str, dict],
    n_replications: int = 25,
    base_seed: int = 100,
    baseline_name: str = "baseline",
) -> pd.DataFrame:
    """Runs run_scenario on every named scenario, using the same base_seed
    for all of them, so replication i faces the same random breakdown
    timings and cycle time jitter in every scenario. This is common random
    numbers, a standard variance reduction technique: it means the
    difference between two scenarios is mostly the effect being tested,
    not unrelated random noise.

    Each scenario's own confidence interval, on its own, is not enough to
    tell whether it differs from baseline: two overlapping intervals do not
    prove there is no real difference, and non overlapping intervals are
    only a rough guide. Since every scenario shares the same seeds as
    baseline, replication i can be paired directly against baseline's
    replication i, giving a proper paired confidence interval and
    significance test for the difference itself.

    Returns one row per scenario: mean monthly tonnes, its own 95 percent
    confidence interval, the implied mean annual tonnes, mean winder
    utilisation, percent change in mean monthly tonnes against
    baseline_name, and the paired annual difference against baseline with
    its own 95 percent confidence interval and p value (NaN for the
    baseline row itself).
    """
    results = {
        name: run_scenario(config, n_replications=n_replications, base_seed=base_seed)
        for name, config in scenarios.items()
    }

    rows = []
    for name, result in results.items():
        rows.append(
            {
                "scenario": name,
                "mean_monthly_tonnes": result.mean_monthly_tonnes,
                "ci_low": result.ci_low,
                "ci_high": result.ci_high,
                "mean_annual_tonnes": result.mean_monthly_tonnes * 12,
                "mean_winder_utilisation_pct": result.mean_winder_utilisation_pct,
            }
        )
    table = pd.DataFrame(rows).set_index("scenario")

    baseline_mean = table.loc[baseline_name, "mean_monthly_tonnes"]
    table["pct_change_vs_baseline"] = (table["mean_monthly_tonnes"] - baseline_mean) / baseline_mean * 100

    baseline_annual = results[baseline_name].monthly_tonnes_by_replication.sum(axis=1)
    paired_mean_diff = {}
    paired_ci_low = {}
    paired_ci_high = {}
    paired_p_value = {}
    for name, result in results.items():
        if name == baseline_name:
            paired_mean_diff[name] = float("nan")
            paired_ci_low[name] = float("nan")
            paired_ci_high[name] = float("nan")
            paired_p_value[name] = float("nan")
            continue
        scenario_annual = result.monthly_tonnes_by_replication.sum(axis=1)
        diff = scenario_annual - baseline_annual
        mean_diff = diff.mean()
        if n_replications > 1:
            sem = stats.sem(diff)
            ci_low, ci_high = stats.t.interval(0.95, n_replications - 1, loc=mean_diff, scale=sem)
            _, p_value = stats.ttest_rel(scenario_annual, baseline_annual)
        else:
            ci_low = ci_high = mean_diff
            p_value = float("nan")
        paired_mean_diff[name] = float(mean_diff)
        paired_ci_low[name] = float(ci_low)
        paired_ci_high[name] = float(ci_high)
        paired_p_value[name] = float(p_value)

    table["paired_annual_diff_vs_baseline"] = pd.Series(paired_mean_diff)
    table["paired_diff_ci_low"] = pd.Series(paired_ci_low)
    table["paired_diff_ci_high"] = pd.Series(paired_ci_high)
    table["paired_diff_p_value"] = pd.Series(paired_p_value)

    return table
