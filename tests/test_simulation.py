"""Behavioral tests for the hoist circuit simulation. Uses a short horizon
so the suite runs in seconds, full year validation against the researched
and synthetic targets happens separately in notebooks/01_simulation.ipynb.
"""

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from twin.simulation import load_config, run_simulation

SHORT_HORIZON_DAYS = 14


@pytest.fixture
def config():
    cfg = load_config(str(Path(__file__).resolve().parent.parent / "config.yaml"))
    cfg["simulation"]["horizon_days"] = SHORT_HORIZON_DAYS
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
