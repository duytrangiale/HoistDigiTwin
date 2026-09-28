"""Generates the twin's own training data for a remaining life model, and
turns it into features. This mirrors src/pdm/data.py and
src/pdm/features.py on purpose, the modelling technique from Phase 5 is
the same, only the dataset is the twin's own simulated health signal
instead of NASA's jet engine sensors. See phase6_plan.md.
"""

from __future__ import annotations

import random

import pandas as pd
import simpy
from xgboost import XGBRegressor

from pdm.models import train_xgboost

from .components import Winder, health_maintenance_process

FEATURE_COLS = ["observed_health", "rolling_mean", "elapsed_hours"]


def simulate_health_log(health_cfg: dict, n_lives: int, rng: random.Random) -> pd.DataFrame:
    """Runs health_maintenance_process on its own, no hoist circuit
    needed, for at least n_lives complete lives, and returns one row per
    health reading: which life it belongs to, how far into that life it
    was taken, the true and observed health, and the true remaining
    hours until that life ends. This is the twin's own stand in for
    src/pdm/data.py's compute_rul, on data generated here rather than
    read from a file.
    """
    env = simpy.Environment()
    winder = Winder(env)  # nothing else competes for it, so it is never actually contended
    downtime_log: list = []
    health_log: list = []

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
        )
    )

    # a generous horizon: a life plus its repair averages about
    # mean_life_hours + unplanned_repair_mttr_hours, doubled here so running
    # out of simulated time before n_lives complete lives is essentially
    # never a concern
    avg_hours_per_life = health_cfg["mean_life_hours"] + health_cfg["unplanned_repair_mttr_hours"]
    env.run(until=n_lives * avg_hours_per_life * 2 * 3600)

    breakdown_starts_s = [start for start, _, kind in downtime_log if kind == "breakdown"]
    if len(breakdown_starts_s) < n_lives:
        raise ValueError(
            f"only {len(breakdown_starts_s)} complete lives simulated, need {n_lives}, "
            "increase the horizon in simulate_health_log"
        )

    rows = []
    life_id = 0
    for time_s, true_health, observed_health, elapsed_hours in health_log:
        while life_id < n_lives and time_s > breakdown_starts_s[life_id]:
            life_id += 1
        if life_id >= n_lives:
            break
        rows.append(
            {
                "life_id": life_id,
                "elapsed_hours": elapsed_hours,
                "true_health": true_health,
                "observed_health": observed_health,
            }
        )

    log_df = pd.DataFrame(rows)
    life_hours = log_df.groupby("life_id")["elapsed_hours"].transform("max")
    log_df["remaining_hours"] = life_hours - log_df["elapsed_hours"]
    return log_df


def build_features(log_df: pd.DataFrame, window: int = 3) -> tuple[pd.DataFrame, list[str]]:
    """Adds a rolling mean of the observed health reading, computed
    within each life only, the same per unit discipline
    src/pdm/features.py uses for engines, so a life's rolling mean never
    reaches into the life before it. Returns the log with the new column
    added, plus the list of column names to use as model inputs.
    """
    df = log_df.copy()
    df["rolling_mean"] = df.groupby("life_id")["observed_health"].transform(
        lambda s: s.rolling(window=window, min_periods=1).mean()
    )
    return df, FEATURE_COLS


def train_twin_rul_model(
    log_df: pd.DataFrame,
    n_validation_lives: int = 100,
    window: int = 3,
    seed: int = 42,
) -> tuple[XGBRegressor, pd.DataFrame, pd.Series, pd.Series]:
    """Builds features, holds out a set of whole lives for validation,
    the same discipline Phase 5 used for engines so a life's own reading
    never appears in both training and validation, and trains an
    XGBoost regressor with the same train_xgboost function Phase 5
    already built. Returns the trained model, the held out features and
    true remaining hours, and the training targets too, so a caller can
    build a fair naive baseline (the training mean) without peeking at
    validation data to get it.

    n_jobs=1: this model gets called once per health reading, one row at
    a time, inside a live simulation that scenarios.py itself already
    runs many of in parallel with ProcessPoolExecutor. Left at XGBoost's
    default of using every core for even a single row, several
    replications doing that at once oversubscribe the machine badly, a
    single replication that otherwise takes about 11 seconds was measured
    taking well over 100 when run this way alongside a handful of others.
    """
    featured_df, feature_cols = build_features(log_df, window=window)

    rng = random.Random(seed)
    life_ids = sorted(featured_df["life_id"].unique())
    rng.shuffle(life_ids)
    validation_ids = set(life_ids[:n_validation_lives])

    is_validation = featured_df["life_id"].isin(validation_ids)
    train_df = featured_df[~is_validation]
    val_df = featured_df[is_validation]

    X_train, y_train = train_df[feature_cols], train_df["remaining_hours"]
    X_val, y_val = val_df[feature_cols], val_df["remaining_hours"]

    model = train_xgboost(X_train, y_train, n_jobs=1)
    return model, X_val, y_val, y_train
