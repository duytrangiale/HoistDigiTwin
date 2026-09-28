"""Tests for Phase 4's search over the surrogate. Uses a tiny fake model
with a known, hand computable relationship to its inputs, rather than a
real trained surrogate, so these stay fast and do not depend on
data/processed/ being populated.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from surrogate.optimise import corner_optimum, predict_tonnes, sensitivity_breakdown
from surrogate.sampling import HIGHER_IS_BETTER, PARAM_RANGES


class _LinearModel:
    """predicted tonnes is just a weighted sum of the inputs, a fully known
    answer to check the real functions against by hand."""

    def __init__(self, coefficients: dict[str, float]):
        self.coefficients = coefficients

    def predict(self, X: pd.DataFrame):
        return (X * pd.Series(self.coefficients)).sum(axis=1).to_numpy()


def test_corner_optimum_matches_higher_is_better():
    corner = corner_optimum(PARAM_RANGES)
    for name, (lo, hi) in PARAM_RANGES.items():
        expected = hi if HIGHER_IS_BETTER[name] else lo
        assert corner[name] == expected


def test_predict_tonnes_orders_columns_to_match_param_ranges():
    # coefficients distinct enough that a column order mistake changes the
    # predicted value
    coefficients = {name: i + 1 for i, name in enumerate(PARAM_RANGES)}
    model = _LinearModel(coefficients)
    params = {name: 2.0 for name in PARAM_RANGES}
    expected = sum(coefficients.values()) * 2.0
    assert predict_tonnes(model, params) == pytest.approx(expected)


def test_sensitivity_breakdown_ranks_by_tonnes_gained():
    # skip_payload_tonnes has by far the largest coefficient here, so
    # moving only it from baseline to optimal should be ranked first
    coefficients = {
        "feed_rate_multiplier": 1.0,
        "skip_payload_tonnes": 10.0,
        "winder_speed_multiplier": 1.0,
        "breakdown_mtbf_hours": 0.01,
        "scheduled_downtime_hours_per_month": -1.0,
    }
    model = _LinearModel(coefficients)
    baseline = {name: 0.0 for name in PARAM_RANGES}
    optimal = {name: 1.0 for name in PARAM_RANGES}

    result = sensitivity_breakdown(model, baseline, optimal)

    assert result.iloc[0]["param_name"] == "skip_payload_tonnes"
    assert result.iloc[0]["tonnes_gained"] == pytest.approx(10.0)
    # scheduled downtime's coefficient is negative, moving it should cost
    # tonnes, not gain them
    downtime_row = result[result["param_name"] == "scheduled_downtime_hours_per_month"].iloc[0]
    assert downtime_row["tonnes_gained"] == pytest.approx(-1.0)
