"""Tests for Phase 2's scenario builders, src/twin/scenarios.py. The
scenario comparison machinery itself (run_scenario, compare_scenarios)
runs many full replications and belongs in a notebook, not a fast test
suite, but the builder functions that turn a base config into a specific
scenario are plain, fast, and worth checking directly.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from twin.scenarios import skip_outage_scenario, typical_year_scenario
from twin.simulation import load_config

CONFIG_PATH = str(Path(__file__).resolve().parent.parent / "config.yaml")


def test_typical_year_scenario_removes_the_calendar_overrides():
    config = load_config(CONFIG_PATH)
    assert "scheduled_downtime_overrides" in config["winder"]  # confirms the fixture actually has one to remove

    scenario = typical_year_scenario(config)

    assert "scheduled_downtime_overrides" not in scenario["winder"]
    assert config["winder"]["scheduled_downtime_overrides"]  # the original config is untouched


def test_skip_outage_scenario_sets_the_outage_without_mutating_the_base_config():
    config = load_config(CONFIG_PATH)

    scenario = skip_outage_scenario(config, skip_name="west", start_day=10, duration_days=3)

    assert scenario["skip_outages"] == [{"skip": "west", "start_day": 10, "duration_days": 3}]
    assert "skip_outages" not in config
