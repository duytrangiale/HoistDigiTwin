"""Builds the hoist circuit from config.yaml, runs it, and packages the
results. See components.py for the entities and reports/simulation_validation.md
for the modelling decisions behind this file.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

import pandas as pd
import simpy
import yaml

from .components import (
    Bin,
    Flask,
    PredictiveMaintenanceConfig,
    Skip,
    Source,
    Winder,
    breakdown_process,
    feed_bins_process,
    feed_flasks_process,
    health_maintenance_process,
    record_bin_levels_process,
    scheduled_maintenance_process,
    source_switch_process,
)

# not imported at module level: maintenance_model.py pulls in src/pdm/models.py,
# which imports torch, costly enough (about 2 seconds) that every replication
# process in scenarios.py's ProcessPoolExecutor would otherwise pay it even
# when maintenance_policy is not "predictive". Imported only where it is
# actually needed, inside run_simulation's predictive branch below.

SECONDS_PER_HOUR = 3600
SECONDS_PER_DAY = 24 * SECONDS_PER_HOUR
SECONDS_PER_MONTH = 30 * SECONDS_PER_DAY  # matches scheduled_maintenance_process


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


@dataclass
class SimulationResult:
    """Packaged outputs of one simulation run."""

    total_tonnes: float
    monthly_tonnes: pd.Series  # index: month number starting at 0
    cycle_log: pd.DataFrame  # one row per completed skip cycle
    bin_level_log: pd.DataFrame  # one row per bin level sample
    downtime_log: pd.DataFrame  # one row per maintenance or breakdown event
    winder_utilisation_pct: float
    winder_downtime_pct: float
    horizon_seconds: float


def run_simulation(
    config: dict,
    seed: int | None = None,
    predictive_model=None,
    bin_sample_interval_minutes: float = 30.0,
    bin_feed_step_minutes: float = 15.0,
    flask_feed_step_minutes: float = 2.0,
) -> SimulationResult:
    """Runs one replication of the hoist circuit and returns its outputs.

    seed overrides config["seed"], so scenarios.py can run many replications
    of the same config with different seeds without editing the file.

    predictive_model is only used when config["winder"]["maintenance_policy"]
    is "predictive" (see phase6_plan.md), a model already trained by
    src/twin/maintenance_model.py's train_twin_rul_model. It is trained once,
    outside of any replication, and simply reused here, the same way a real
    predictive maintenance model is trained offline and then deployed
    unchanged.

    The bins and flasks use different feed check intervals on purpose. A
    bin holds 200 tonnes against a feed rate of a few hundred tonnes an
    hour, so checking it every ten minutes barely matters. A flask holds
    only about one skip payload, so it can run dry within a couple of
    minutes if it is not checked often, starving a skip that is ready to
    load. Coarsening both at the same rate was tried and measurably starved
    the skips, cutting simulated monthly tonnage by more than half.
    """
    rng = random.Random(seed if seed is not None else config["seed"])
    env = simpy.Environment()

    horizon_seconds = config["simulation"]["horizon_days"] * SECONDS_PER_DAY

    sources = [
        Source("source_a", config["sources"]["source_a"]["feed_rate_tph"]),
        Source("source_b", config["sources"]["source_b"]["feed_rate_tph"]),
    ]
    sources[0].active = True
    switch_interval_hours = config["sources"]["switch_interval_hours"]

    bins = [
        Bin(env, f"bin_{i}", config["bins"]["capacity_tonnes"])
        for i in range(config["bins"]["count"])
    ]

    flask_capacity = config["flasks"]["capacity_tonnes"]
    flask_west = Flask(env, "flask_west", flask_capacity)
    flask_east = Flask(env, "flask_east", flask_capacity)

    winder = Winder(env)

    # a known, planned unavailability for one skip, expressed as a window in
    # time, the same pattern used for calendar aware winder downtime
    outage_windows: dict[str, list[tuple[float, float]]] = {"skip_west": [], "skip_east": []}
    for outage in config.get("skip_outages", []):
        skip_name = f"skip_{outage['skip']}"
        start_s = outage["start_day"] * SECONDS_PER_DAY
        end_s = start_s + outage["duration_days"] * SECONDS_PER_DAY
        outage_windows[skip_name].append((start_s, end_s))

    cycle_log: list = []
    skip_cfg = config["skips"]
    skip_west = Skip(
        env,
        "skip_west",
        flask_west,
        winder,
        skip_cfg["payload_tonnes"],
        skip_cfg["load_time_mean_s"],
        skip_cfg["hoist_time_mean_s"],
        skip_cfg["dump_time_mean_s"],
        skip_cfg["return_time_mean_s"],
        skip_cfg["cycle_time_cv"],
        rng,
        cycle_log,
        outage_windows_s=outage_windows["skip_west"],
    )
    skip_east = Skip(
        env,
        "skip_east",
        flask_east,
        winder,
        skip_cfg["payload_tonnes"],
        skip_cfg["load_time_mean_s"],
        skip_cfg["hoist_time_mean_s"],
        skip_cfg["dump_time_mean_s"],
        skip_cfg["return_time_mean_s"],
        skip_cfg["cycle_time_cv"],
        rng,
        cycle_log,
        outage_windows_s=outage_windows["skip_east"],
    )

    bin_level_log: list = []
    downtime_log: list = []
    health_log: list = []

    env.process(source_switch_process(env, sources, switch_interval_hours))
    env.process(feed_bins_process(env, sources, bins, bin_feed_step_minutes))
    env.process(feed_flasks_process(env, bins, flask_west, flask_feed_step_minutes))
    env.process(feed_flasks_process(env, bins, flask_east, flask_feed_step_minutes))
    env.process(skip_west.run())
    env.process(skip_east.run())
    env.process(
        scheduled_maintenance_process(
            env,
            winder,
            config["winder"]["scheduled_downtime_hours_per_month"],
            downtime_log,
            monthly_overrides=config["winder"].get("scheduled_downtime_overrides"),
        )
    )
    maintenance_policy = config["winder"].get("maintenance_policy")
    if maintenance_policy:
        # Phase 6 only: health_maintenance_process replaces the plain
        # exponential breakdown_process with a winder that genuinely wears
        # out, see phase6_plan.md. Left off by default, so every config
        # written before this phase keeps using breakdown_process exactly
        # as before.
        health_cfg = config["winder"]["health"]
        predictive_cfg = None
        if maintenance_policy == "predictive":
            if predictive_model is None:
                raise ValueError("maintenance_policy is 'predictive' but no predictive_model was given")
            from .maintenance_model import FEATURE_COLS

            predictive_cfg = PredictiveMaintenanceConfig(
                model=predictive_model,
                feature_cols=FEATURE_COLS,
                rolling_window=health_cfg["rolling_window"],
                lead_time_hours=health_cfg["predictive_lead_time_hours"],
                planned_repair_mttr_hours=health_cfg["planned_repair_mttr_hours"],
            )
        env.process(
            health_maintenance_process(
                env,
                winder,
                health_cfg["mean_life_hours"],
                health_cfg["weibull_shape"],
                health_cfg["noise_sd"],
                health_cfg["check_interval_hours"],
                health_cfg["unplanned_repair_mttr_hours"],
                rng,
                downtime_log,
                health_log,
                predictive=predictive_cfg,
            )
        )
    else:
        env.process(
            breakdown_process(
                env,
                winder,
                config["winder"]["breakdown_mtbf_hours"],
                config["winder"]["breakdown_mttr_hours"],
                rng,
                downtime_log,
            )
        )
    env.process(record_bin_levels_process(env, bins, bin_sample_interval_minutes, bin_level_log))

    env.run(until=horizon_seconds)

    cycle_df = pd.DataFrame(
        [
            {
                "dump_time_s": r.dump_time_s,
                "skip_name": r.skip_name,
                "tonnes": r.tonnes,
                "cycle_time_s": r.cycle_time_s,
            }
            for r in cycle_log
        ]
    )
    bin_level_df = pd.DataFrame(bin_level_log, columns=["time_s", "bin_name", "level_tonnes"])
    downtime_df = pd.DataFrame(downtime_log, columns=["start_s", "duration_s", "kind"])

    total_tonnes = cycle_df["tonnes"].sum() if not cycle_df.empty else 0.0
    if not cycle_df.empty:
        month_index = (cycle_df["dump_time_s"] // SECONDS_PER_MONTH).astype(int)
        monthly_tonnes = cycle_df.groupby(month_index)["tonnes"].sum()
        monthly_tonnes.index.name = "month"
    else:
        monthly_tonnes = pd.Series(dtype=float)

    return SimulationResult(
        total_tonnes=total_tonnes,
        monthly_tonnes=monthly_tonnes,
        cycle_log=cycle_df,
        bin_level_log=bin_level_df,
        downtime_log=downtime_df,
        winder_utilisation_pct=winder.busy_hoisting_seconds / horizon_seconds * 100,
        winder_downtime_pct=winder.down_seconds / horizon_seconds * 100,
        horizon_seconds=horizon_seconds,
    )
