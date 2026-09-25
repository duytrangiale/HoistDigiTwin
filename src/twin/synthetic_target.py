"""Builds the synthetic twelve month reference used to validate the
simulation, since no real historical hoisting data is available. This is a
synthetic reference for demonstrating the calibration methodology, not
measured data. See reports/simulation_validation.md for the research behind
the baseline tonnage and the seasonal pattern.

config.yaml's winder.scheduled_downtime_overrides is set to reproduce this
same shape from the simulation side, standing in for what would, with real
data, be actual known downtime events fed into the model.
"""

from __future__ import annotations

import random

import pandas as pd

MONTH_NAMES = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]

BASE_MONTHLY_TONNES = 237_000  # the simulation's own baseline output, see reports/simulation_validation.md
SEASONAL_DIP_FACTORS = {"Jan": 0.60, "Dec": 0.65}  # Christmas and New Year shutdown
BAD_MONTH = "Jul"  # one deliberately bad month, an extended unplanned repair
BAD_MONTH_FACTOR = 0.55
NOISE_PCT = 0.04  # random month to month noise on every other month


def build_synthetic_target(seed: int = 7) -> pd.Series:
    """Returns a twelve month tonnage series, indexed January to December,
    standing in for a real historical record. Deterministic given the seed,
    so this exact series can be regenerated without committing a data file."""
    rng = random.Random(seed)
    values = []
    for month in MONTH_NAMES:
        factor = SEASONAL_DIP_FACTORS.get(month, 1.0)
        if month == BAD_MONTH:
            factor *= BAD_MONTH_FACTOR
        noise = 1 + rng.uniform(-NOISE_PCT, NOISE_PCT)
        values.append(BASE_MONTHLY_TONNES * factor * noise)
    return pd.Series(values, index=MONTH_NAMES, name="synthetic_target_tonnes")
