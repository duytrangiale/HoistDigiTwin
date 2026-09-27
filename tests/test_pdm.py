"""Tests for the C-MAPSS data loading and feature pipeline. Uses a tiny
synthetic file in the real C-MAPSS format, not the actual 100 engine
download, so the suite stays fast and does not depend on the data being
present on disk.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pdm.data import COLUMN_NAMES, SENSOR_COLS, compute_rul, load_raw
from pdm.features import add_rolling_and_lag_features


def _write_synthetic_cmapss_file(path: Path, engine_lengths: dict[int, int]) -> None:
    """Writes a space delimited file in the real C-MAPSS column layout:
    unit number, cycle, 3 operational settings, 21 sensor readings. Every
    sensor's value is set to unit * 1000 + cycle, deliberately distinct
    per engine, so a test can tell whether a computation accidentally
    mixed one engine's data into another's."""
    rows = []
    for unit, n_cycles in engine_lengths.items():
        for cycle in range(1, n_cycles + 1):
            op_settings = [0.0, 0.0, 100.0]
            sensors = [unit * 1000 + cycle] * len(SENSOR_COLS)
            rows.append([unit, cycle, *op_settings, *sensors])
    pd.DataFrame(rows, columns=COLUMN_NAMES).to_csv(path, sep=" ", header=False, index=False)


@pytest.fixture
def synthetic_data_dir(tmp_path):
    _write_synthetic_cmapss_file(tmp_path / "train_FD001.txt", {1: 4, 2: 6})
    _write_synthetic_cmapss_file(tmp_path / "test_FD001.txt", {1: 3, 2: 5})
    pd.DataFrame({"RUL": [10, 20]}).to_csv(tmp_path / "RUL_FD001.txt", sep=" ", header=False, index=False)
    return tmp_path


def test_load_raw_parses_expected_shape_and_columns(synthetic_data_dir):
    data = load_raw(str(synthetic_data_dir))
    assert list(data["train"].columns) == COLUMN_NAMES
    assert len(data["train"]) == 4 + 6
    assert len(data["test"]) == 3 + 5
    assert data["rul"]["RUL"].tolist() == [10, 20]


def test_compute_rul_caps_correctly(synthetic_data_dir):
    train_df = load_raw(str(synthetic_data_dir))["train"]
    labeled = compute_rul(train_df, cap=3)

    # engine 1 has 4 cycles, so uncapped RUL would be 3, 2, 1, 0, already
    # at or under the cap, nothing here should actually be clipped
    engine1 = labeled[labeled["unit_number"] == 1].sort_values("time_in_cycles")
    assert engine1["RUL"].tolist() == [3, 2, 1, 0]

    # engine 2 has 6 cycles, uncapped RUL would be 5, 4, 3, 2, 1, 0, so the
    # first two values must actually get clipped down to the cap
    engine2 = labeled[labeled["unit_number"] == 2].sort_values("time_in_cycles")
    assert engine2["RUL"].tolist() == [3, 3, 3, 2, 1, 0]


def test_rolling_and_lag_features_do_not_leak_across_engines(synthetic_data_dir):
    train_df = load_raw(str(synthetic_data_dir))["train"]
    featured = add_rolling_and_lag_features(train_df, ["sensor_1"], window=5, lags=(1,))

    engine2_first_row = featured[(featured["unit_number"] == 2) & (featured["time_in_cycles"] == 1)]

    # engine 2's own first reading is 2001 (2 * 1000 + 1). If the rolling
    # window or the lag reached back into engine 1's last reading (1004)
    # instead of stopping at engine 2's own start, this would not be 2001.
    assert engine2_first_row["sensor_1_lag1"].iloc[0] == 2001
    assert engine2_first_row["sensor_1_rolling_mean"].iloc[0] == 2001
