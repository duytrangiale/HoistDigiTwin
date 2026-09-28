"""Runs many replications of a scenario and summarises the results. A
scenario is just a config dict, so Phase 2 can build several scenarios by
copying config.yaml and overriding a few values, and compare them with this
same function. See simulation.py for a single run.
"""

from __future__ import annotations

import copy
import multiprocessing
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
    downtime_by_replication: pd.DataFrame  # rows: replication, columns: hours/count per downtime kind


def _summarize_downtime(downtime_df: pd.DataFrame) -> dict[str, float]:
    """Total hours and event count for each kind of winder downtime in one
    replication. Phase 6 only, breakdown and planned_predictive come from
    health_maintenance_process, see phase6_plan.md."""
    summary = {}
    for kind in ["scheduled", "breakdown", "planned_predictive"]:
        rows = downtime_df[downtime_df["kind"] == kind]
        summary[f"{kind}_hours"] = rows["duration_s"].sum() / 3600
        summary[f"{kind}_count"] = float(len(rows))
    return summary


def _run_one_replication(args: tuple[dict, int, object]) -> tuple[pd.Series, float, dict[str, float]]:
    config, seed, predictive_model = args
    result = run_simulation(config, seed=seed, predictive_model=predictive_model)
    # the horizon is 365 days, not a multiple of 30, so the last month is a
    # partial month and would understate a typical month if kept
    monthly = result.monthly_tonnes
    if len(monthly) > 1:
        monthly = monthly.iloc[:-1]
    return monthly, result.winder_utilisation_pct, _summarize_downtime(result.downtime_log)


def run_scenario(
    config: dict,
    n_replications: int = 20,
    base_seed: int = 0,
    n_workers: int | None = None,
    predictive_model=None,
) -> ScenarioResult:
    """Runs the simulation n_replications times, each with a different
    seed, and summarises monthly tonnes with a 95 percent confidence
    interval. Replications run in parallel across CPU cores, since each one
    is independent and CPU bound, which is what makes hundreds of them
    practical rather than a multi minute wait.

    predictive_model is only relevant when config sets
    winder.maintenance_policy to "predictive" (see phase6_plan.md), passed
    through unchanged to every replication, since it was already trained
    once, outside of this function.
    """
    seeds = [base_seed + i for i in range(n_replications)]
    args = [(config, s, predictive_model) for s in seeds]

    # spawn, not the default fork: forking a worker after xgboost or numpy
    # has already created background threads in this parent process leaves
    # the child with a broken copy of that thread pool. A single predictive
    # policy replication that takes about 11 seconds on its own was measured
    # taking well past a minute under fork, spawn starts each worker as a
    # clean interpreter instead, avoiding the problem entirely.
    with ProcessPoolExecutor(max_workers=n_workers, mp_context=multiprocessing.get_context("spawn")) as executor:
        results = list(executor.map(_run_one_replication, args))

    monthly_by_replication = pd.DataFrame([monthly for monthly, _, _ in results]).reset_index(drop=True)
    utilisations = [util for _, util, _ in results]
    downtime_by_replication = pd.DataFrame([downtime for _, _, downtime in results]).reset_index(drop=True)

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
        downtime_by_replication=downtime_by_replication,
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


def reactive_policy_scenario(base_config: dict) -> dict:
    """The typical year, with the winder's breakdowns driven by a real
    health signal instead of breakdown_mtbf_hours's fixed random rate
    (see phase6_plan.md for why that matters), but nothing acts on it, the
    winder only gets repaired once it actually breaks."""
    config = typical_year_scenario(base_config)
    config["winder"]["maintenance_policy"] = "reactive"
    return config


def predictive_policy_scenario(base_config: dict) -> dict:
    """The same health driven winder as reactive_policy_scenario, but
    watched: pass a trained model to run_scenario's predictive_model
    argument to actually use it, a fitted model does not belong inside a
    plain config dict."""
    config = typical_year_scenario(base_config)
    config["winder"]["maintenance_policy"] = "predictive"
    return config


def compare_maintenance_policies(
    base_config: dict,
    predictive_model,
    n_replications: int = 25,
    base_seed: int = 200,
) -> pd.DataFrame:
    """Compares the reactive and predictive maintenance policies, same
    base_seed for both so replication i faces the same underlying life
    draws in each, common random numbers, the same idea compare_scenarios
    already uses. Kept separate from compare_scenarios rather than reusing
    it directly, since the comparison that matters here is not only
    tonnes, it is also breakdown count and downtime by kind, which
    compare_scenarios does not track.

    Once the predictive policy first steps in early on some life, that
    life ends sooner than it would have reactively, so the next life's
    draw happens at a different point in time in each run from there.
    The two runs are not driven by identical events after that point, and
    that is expected, it is exactly the decision being measured, not a
    flaw in the comparison. Averaging over many replications still gives
    a fair answer.

    Returns one row per policy: mean monthly tonnes with its own 95
    percent confidence interval, mean breakdown count, mean hours of each
    downtime kind, and, on the predictive row, the paired difference
    against reactive for both annual tonnes and total downtime hours,
    each with its own 95 percent confidence interval and p value.
    """
    reactive_config = reactive_policy_scenario(base_config)
    predictive_config = predictive_policy_scenario(base_config)

    results = {
        "reactive": run_scenario(reactive_config, n_replications=n_replications, base_seed=base_seed),
        "predictive": run_scenario(
            predictive_config,
            n_replications=n_replications,
            base_seed=base_seed,
            predictive_model=predictive_model,
        ),
    }

    def _total_downtime_hours(result: ScenarioResult) -> pd.Series:
        d = result.downtime_by_replication
        return d["scheduled_hours"] + d["breakdown_hours"] + d["planned_predictive_hours"]

    rows = []
    for name, result in results.items():
        d = result.downtime_by_replication
        rows.append(
            {
                "policy": name,
                "mean_monthly_tonnes": result.mean_monthly_tonnes,
                "ci_low": result.ci_low,
                "ci_high": result.ci_high,
                "mean_annual_tonnes": result.mean_monthly_tonnes * 12,
                "mean_breakdown_count": d["breakdown_count"].mean(),
                "mean_planned_predictive_count": d["planned_predictive_count"].mean(),
                "mean_scheduled_hours": d["scheduled_hours"].mean(),
                "mean_breakdown_hours": d["breakdown_hours"].mean(),
                "mean_planned_predictive_hours": d["planned_predictive_hours"].mean(),
                "mean_total_downtime_hours": _total_downtime_hours(result).mean(),
            }
        )
    table = pd.DataFrame(rows).set_index("policy")

    def _paired_stats(diff: pd.Series) -> tuple[float, float, float, float]:
        mean_diff = float(diff.mean())
        if n_replications > 1:
            sem = stats.sem(diff)
            ci_low, ci_high = stats.t.interval(0.95, n_replications - 1, loc=mean_diff, scale=sem)
            _, p_value = stats.ttest_1samp(diff, 0)
        else:
            ci_low = ci_high = mean_diff
            p_value = float("nan")
        return mean_diff, float(ci_low), float(ci_high), float(p_value)

    tonnes_diff = (
        results["predictive"].monthly_tonnes_by_replication.sum(axis=1)
        - results["reactive"].monthly_tonnes_by_replication.sum(axis=1)
    )
    downtime_diff = _total_downtime_hours(results["predictive"]) - _total_downtime_hours(results["reactive"])

    tonnes_mean_diff, tonnes_ci_low, tonnes_ci_high, tonnes_p = _paired_stats(tonnes_diff)
    downtime_mean_diff, downtime_ci_low, downtime_ci_high, downtime_p = _paired_stats(downtime_diff)

    table.loc["predictive", "paired_annual_tonnes_diff_vs_reactive"] = tonnes_mean_diff
    table.loc["predictive", "paired_tonnes_diff_ci_low"] = tonnes_ci_low
    table.loc["predictive", "paired_tonnes_diff_ci_high"] = tonnes_ci_high
    table.loc["predictive", "paired_tonnes_diff_p_value"] = tonnes_p
    table.loc["predictive", "paired_downtime_hours_diff_vs_reactive"] = downtime_mean_diff
    table.loc["predictive", "paired_downtime_diff_ci_low"] = downtime_ci_low
    table.loc["predictive", "paired_downtime_diff_ci_high"] = downtime_ci_high
    table.loc["predictive", "paired_downtime_diff_p_value"] = downtime_p

    return table


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
