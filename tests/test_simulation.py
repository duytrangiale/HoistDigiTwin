"""Behavioral tests for the hoist circuit simulation. Uses a short horizon
so the suite runs in seconds, full year validation against the researched
and synthetic targets happens separately in notebooks/01_simulation.ipynb.
"""

import copy
import random
import sys
from pathlib import Path

import pandas as pd
import pytest
import simpy

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from twin.components import PredictiveMaintenanceConfig, Winder, health_maintenance_process
from twin.maintenance_model import build_features
from twin.simulation import load_config, run_simulation

SHORT_HORIZON_DAYS = 14


@pytest.fixture
def config():
    cfg = load_config(str(Path(__file__).resolve().parent.parent / "config.yaml"))
    cfg["simulation"]["horizon_days"] = SHORT_HORIZON_DAYS
    # config.yaml's January override is 288 hours, 12 of the 14 test days,
    # a Phase 1 calibration artifact these tests should not inherit
    cfg["winder"].pop("scheduled_downtime_overrides", None)
    return cfg


def test_same_seed_gives_same_result(config):
    r1 = run_simulation(config, seed=42)
    r2 = run_simulation(config, seed=42)
    assert r1.total_tonnes == r2.total_tonnes
    assert r1.cycle_log["cycle_time_s"].tolist() == r2.cycle_log["cycle_time_s"].tolist()


def test_tonnes_are_never_negative(config):
    result = run_simulation(config, seed=1)
    assert result.total_tonnes >= 0
    assert (result.cycle_log["tonnes"] >= 0).all()


def test_higher_feed_rate_never_lowers_tonnes(config):
    # starts from a reduced feed rate so the system is genuinely feed
    # constrained here, rather than already winder bound, so this test
    # would actually catch a broken monotonicity, not just pass by luck
    low_feed = copy.deepcopy(config)
    low_feed["sources"]["source_a"]["feed_rate_tph"] *= 0.5
    low_feed["sources"]["source_b"]["feed_rate_tph"] *= 0.5

    r_low = run_simulation(low_feed, seed=3)
    r_high = run_simulation(config, seed=3)
    assert r_high.total_tonnes >= r_low.total_tonnes


def test_skip_never_exceeds_its_payload(config):
    result = run_simulation(config, seed=5)
    assert (result.cycle_log["tonnes"] <= config["skips"]["payload_tonnes"]).all()


def test_skip_outage_produces_almost_no_cycles_during_the_window(config):
    config = copy.deepcopy(config)
    config["skip_outages"] = [{"skip": "west", "start_day": 5, "duration_days": 3}]
    result = run_simulation(config, seed=7)

    DAY = 24 * 3600
    window_start, window_end = 5 * DAY, 8 * DAY
    west = result.cycle_log[result.cycle_log["skip_name"] == "skip_west"]
    in_window = west[(west["dump_time_s"] >= window_start) & (west["dump_time_s"] < window_end)]
    # at most one cycle already in flight when the window opens is allowed
    # to finish, the same non-preemptive handling used for breakdowns
    assert len(in_window) <= 1


def test_skip_outage_reduces_total_tonnes(config):
    outage_config = copy.deepcopy(config)
    outage_config["skip_outages"] = [{"skip": "west", "start_day": 5, "duration_days": 3}]

    # same seed for both runs, so the comparison isolates the outage's
    # effect rather than being muddied by unrelated random variation
    r_baseline = run_simulation(config, seed=7)
    r_outage = run_simulation(outage_config, seed=7)
    assert r_outage.total_tonnes < r_baseline.total_tonnes


# Phase 6: health_maintenance_process and its predictive branch, see phase6_plan.md.
# These run the health process on its own, no hoist circuit needed, the same
# way src/twin/maintenance_model.py's simulate_health_log does.


def test_health_life_lengths_average_close_to_configured_mean():
    mean_life_hours = 200
    rng = random.Random(42)
    env = simpy.Environment()
    winder = Winder(env)
    downtime_log: list = []
    health_log: list = []
    env.process(
        health_maintenance_process(
            env,
            winder,
            mean_life_hours=mean_life_hours,
            weibull_shape=2.5,
            noise_sd=3,
            check_interval_hours=24,
            unplanned_repair_mttr_hours=4,
            rng=rng,
            downtime_log=downtime_log,
            health_log=health_log,
        )
    )
    # generous: enough lives that the sample mean is a meaningful check
    # rather than noise, see simulate_health_log for the same horizon logic
    env.run(until=300 * (mean_life_hours + 4) * 2 * 3600)

    life_lengths = []
    prev_end_s = 0.0
    for start_s, duration_s, _ in downtime_log:
        life_lengths.append((start_s - prev_end_s) / 3600)
        prev_end_s = start_s + duration_s

    assert len(life_lengths) >= 250
    mean_life = sum(life_lengths) / len(life_lengths)
    assert abs(mean_life - mean_life_hours) < 20


class _AlwaysInterveneModel:
    """A stub for testing the intervention branch itself, not prediction
    accuracy, always reports zero remaining life, so the predictive
    policy steps in at the very first health check of every life."""

    def predict(self, X):
        return [0.0] * len(X)


def test_predictive_intervention_always_preempts_a_natural_breakdown():
    predictive_cfg = PredictiveMaintenanceConfig(
        model=_AlwaysInterveneModel(),
        feature_cols=["observed_health", "rolling_mean", "elapsed_hours"],
        rolling_window=3,
        lead_time_hours=24,
        planned_repair_mttr_hours=2,
    )
    rng = random.Random(42)
    env = simpy.Environment()
    winder = Winder(env)
    downtime_log: list = []
    health_log: list = []
    env.process(
        health_maintenance_process(
            env,
            winder,
            mean_life_hours=200,
            weibull_shape=2.5,
            noise_sd=3,
            check_interval_hours=24,
            unplanned_repair_mttr_hours=4,
            rng=rng,
            downtime_log=downtime_log,
            health_log=health_log,
            predictive=predictive_cfg,
        )
    )
    env.run(until=20 * (200 + 4) * 2 * 3600)

    assert len(downtime_log) >= 15
    # every single life ended with a planned repair, never a real
    # breakdown, since this model always says no time is left
    kinds = {kind for _, _, kind in downtime_log}
    assert kinds == {"planned_predictive"}


def test_build_features_rolling_mean_does_not_leak_across_lives():
    log_df = pd.DataFrame(
        {
            "life_id": [0, 0, 0, 1, 1],
            "elapsed_hours": [24.0, 48.0, 72.0, 24.0, 48.0],
            "true_health": [80.0, 60.0, 40.0, 85.0, 65.0],
            "observed_health": [80.0, 60.0, 40.0, 85.0, 65.0],
            "remaining_hours": [48.0, 24.0, 0.0, 46.0, 23.0],
        }
    )
    featured_df, feature_cols = build_features(log_df, window=3)

    life1_first_row = featured_df[(featured_df["life_id"] == 1) & (featured_df["elapsed_hours"] == 24.0)]
    # life 1's own first reading is 85. If the rolling mean reached back
    # into life 0's last reading (40) instead of starting fresh, this
    # would not be 85.
    assert life1_first_row["rolling_mean"].iloc[0] == 85.0
