"""Loads the NASA C-MAPSS FD001 dataset: full run to failure histories for
training, truncated histories plus the true remaining life for testing.
See phase5_plan.md at the repo root for the reasoning behind every choice
in this file.
"""

from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import pandas as pd

OPERATIONAL_SETTING_COLS = ["op_setting_1", "op_setting_2", "op_setting_3"]
SENSOR_COLS = [f"sensor_{i}" for i in range(1, 22)]
COLUMN_NAMES = ["unit_number", "time_in_cycles"] + OPERATIONAL_SETTING_COLS + SENSOR_COLS


def _read_space_delimited(path: Path, names: list[str]) -> pd.DataFrame:
    return pd.read_csv(path, sep=r"\s+", header=None, names=names)


def load_raw(data_dir: str = "data/raw") -> dict[str, pd.DataFrame]:
    """Reads train_FD001.txt, test_FD001.txt, and RUL_FD001.txt, giving
    every column its proper name instead of a bare position index."""
    data_dir_path = Path(data_dir)
    train_df = _read_space_delimited(data_dir_path / "train_FD001.txt", COLUMN_NAMES)
    test_df = _read_space_delimited(data_dir_path / "test_FD001.txt", COLUMN_NAMES)
    rul_df = _read_space_delimited(data_dir_path / "RUL_FD001.txt", ["RUL"])
    return {"train": train_df, "test": test_df, "rul": rul_df}


def compute_rul(train_df: pd.DataFrame, cap: int = 125) -> pd.DataFrame:
    """Adds a capped remaining useful life column to the training data.
    Training trajectories run all the way to failure, so each engine's own
    last recorded cycle is its failure point, and RUL counts down from
    there. Capped at 125 cycles, the standard C-MAPSS convention: a fresh
    engine is not meaningfully "500 cycles from failure" versus "480,"
    degradation has not started yet, only the decline near failure is
    real signal for the model to learn.
    """
    result = train_df.copy()
    max_cycle_per_unit = result.groupby("unit_number")["time_in_cycles"].transform("max")
    rul = max_cycle_per_unit - result["time_in_cycles"]
    result["RUL"] = rul.clip(upper=cap)
    return result


def train_validation_split(
    train_df: pd.DataFrame, n_validation_engines: int = 20, seed: int = 42
) -> tuple[list[int], list[int]]:
    """Splits the 100 training engines into a fitting set and an internal
    validation set, by unit number, never by row, so a validation engine's
    cycles are never seen during fitting. This is separate from the
    official test set, which stays untouched until the final comparison.
    Returns (fit_units, validation_units)."""
    units = sorted(train_df["unit_number"].unique())
    rng = random.Random(seed)
    validation_units = sorted(rng.sample(units, n_validation_engines))
    fit_units = sorted(u for u in units if u not in validation_units)
    return fit_units, validation_units


def build_training_windows(
    df: pd.DataFrame,
    feature_cols: list[str],
    rul_col: str = "RUL",
    window_length: int = 30,
) -> tuple[np.ndarray, np.ndarray]:
    """Every complete window of window_length consecutive cycles from each
    engine, labelled with the RUL at the window's last cycle.

    For one engine with window_length 30, this produces one window per
    possible "current cycle" from cycle 30 onward: the window ending at
    cycle 30 covers cycles 1 to 30, the window ending at cycle 31 covers
    cycles 2 to 31, and so on, each labelled with the RUL at its own last
    cycle. An engine's first 29 cycles cannot end a complete window yet,
    so no window is generated for them, rather than padding them with
    invented history. Looping per engine and slicing only that engine's
    own array also means a window can never straddle two engines, by
    construction, not by convention.
    """
    X_windows: list[np.ndarray] = []
    y_windows: list[float] = []

    for _, group in df.groupby("unit_number"):
        group = group.sort_values("time_in_cycles")
        values = group[feature_cols].to_numpy()
        labels = group[rul_col].to_numpy()
        n_cycles = len(group)

        # last_cycle_index is the position, within this engine's own rows,
        # of the most recent cycle in the window: it starts at
        # window_length - 1, the earliest point where window_length rows
        # exist, and goes up to the engine's final row.
        for last_cycle_index in range(window_length - 1, n_cycles):
            first_cycle_index = last_cycle_index - window_length + 1
            window = values[first_cycle_index : last_cycle_index + 1]
            label = labels[last_cycle_index]
            X_windows.append(window)
            y_windows.append(label)

    return np.stack(X_windows), np.array(y_windows)


def build_inference_windows(
    df: pd.DataFrame,
    feature_cols: list[str],
    window_length: int = 30,
) -> tuple[np.ndarray, list[int]]:
    """Exactly one window per engine, its last window_length cycles. Every
    engine here needs exactly one prediction, so a trajectory shorter than
    window_length is zero padded at the start instead of being dropped,
    the only place in this module that pads rather than relies on real
    history alone. Returns the windows and the engine unit numbers in the
    same order, so predictions can be matched back to the right engine.
    """
    X_windows: list[np.ndarray] = []
    unit_numbers: list[int] = []
    n_features = len(feature_cols)
    for unit, group in df.groupby("unit_number"):
        group = group.sort_values("time_in_cycles")
        values = group[feature_cols].to_numpy()
        if len(values) >= window_length:
            window = values[-window_length:]
        else:
            pad = np.zeros((window_length - len(values), n_features))
            window = np.vstack([pad, values])
        X_windows.append(window)
        unit_numbers.append(unit)
    return np.stack(X_windows), unit_numbers
