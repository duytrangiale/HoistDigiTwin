"""Runs many replications of a scenario and summarises the results. A
scenario is just a config dict, so Phase 2 can build several scenarios by
copying config.yaml and overriding a few values, and compare them with this
same function. See simulation.py for a single run.
"""

from __future__ import annotations

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
