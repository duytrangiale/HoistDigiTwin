"""Feature engineering for the C-MAPSS FD001 data: dropping sensors that
never move, and adding rolling and lag features computed within each
engine's own history. See phase5_plan.md at the repo root for the
reasoning behind the window and lag choices.
"""

from __future__ import annotations

import pandas as pd

from .data import OPERATIONAL_SETTING_COLS


def drop_constant_sensors(df: pd.DataFrame, sensor_cols: list[str], threshold: float = 1e-6) -> list[str]:
    """Returns the sensor columns whose variance exceeds threshold.
    Several FD001 sensors are constant or near constant, since this
    subset has only one operating condition, there is nothing for them
    to vary with. Checked by variance directly rather than a hard coded
    list, though the literature consistently finds about 7 of the 21
    sensors constant here, a useful sanity check on the result."""
    variances = df[sensor_cols].var()
    return [col for col in sensor_cols if variances[col] > threshold]


def add_rolling_and_lag_features(
    df: pd.DataFrame,
    sensor_cols: list[str],
    window: int = 5,
    lags: tuple[int, ...] = (1, 2),
) -> pd.DataFrame:
    """Adds a rolling mean, a rolling standard deviation, and the given
    lags for every sensor column, each computed within one engine's own
    history only, never across engines. An engine's first few cycles have
    fewer than window prior rows, min_periods=1 lets those still get a
    value from however much history exists so far. A lagged value has
    nothing to look back to for an engine's first few cycles either,
    filled with that engine's own earliest available reading rather than
    left empty or, worse, filled from a different engine's data.
    """
    result = df.copy()
    groups = result.groupby("unit_number")

    for col in sensor_cols:
        result[f"{col}_rolling_mean"] = groups[col].transform(
            lambda s: s.rolling(window=window, min_periods=1).mean()
        )
        result[f"{col}_rolling_std"] = groups[col].transform(
            lambda s: s.rolling(window=window, min_periods=1).std().fillna(0.0)
        )
        for lag in lags:
            result[f"{col}_lag{lag}"] = groups[col].transform(lambda s, lag=lag: s.shift(lag).bfill())

    return result


def feature_matrix_columns(surviving_sensor_cols: list[str], lags: tuple[int, ...] = (1, 2)) -> list[str]:
    """The full list of model input columns once add_rolling_and_lag_features
    has run: the operational settings, the surviving sensors themselves,
    and their rolling and lag versions, in a single consistent order so
    training and evaluation always build the same matrix."""
    cols = list(OPERATIONAL_SETTING_COLS) + list(surviving_sensor_cols)
    cols += [f"{c}_rolling_mean" for c in surviving_sensor_cols]
    cols += [f"{c}_rolling_std" for c in surviving_sensor_cols]
    for lag in lags:
        cols += [f"{c}_lag{lag}" for c in surviving_sensor_cols]
    return cols
