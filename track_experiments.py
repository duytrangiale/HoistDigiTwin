"""Logs the model comparisons from Phase 3/4 (the surrogate) and Phase 5
(predictive maintenance) to MLflow, so every run's parameters and metrics
are comparable in one place instead of only living in each phase's own
notebook. Local only, mlruns/ is gitignored, see README.md for how to
browse the results. Reuses the exact training functions each phase's own
notebook already uses, nothing here is a new model or a new number.

Run with: python track_experiments.py
Then: mlflow ui
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import mlflow
import numpy as np
import pandas as pd

from pdm.data import build_inference_windows, build_training_windows, compute_rul, load_raw, train_validation_split
from pdm.evaluate import cmapss_score, rmse
from pdm.features import add_rolling_and_lag_features, drop_constant_sensors, feature_matrix_columns
from pdm.models import predict_lstm, train_linear_baseline, train_lstm
from pdm.models import train_xgboost as train_pdm_xgboost
from surrogate.sampling import PARAM_RANGES
from surrogate.train import evaluate_on_held_out, train_gaussian_process
from surrogate.train import train_xgboost as train_surrogate_xgboost


def log_surrogate_runs() -> None:
    """Phase 3's two model types, each on the original 200 point design
    and again on the corner focused design Phase 4 added, four runs in
    total, all checked against the same held out set."""
    mlflow.set_experiment("surrogate")
    feature_cols = list(PARAM_RANGES.keys())
    held_out_df = pd.read_csv(PROJECT_ROOT / "data/processed/surrogate_held_out_set.csv")
    X_held, y_held = held_out_df[feature_cols], held_out_df["monthly_tonnes"]

    for augmented in (False, True):
        suffix = "_augmented" if augmented else ""
        train_df = pd.read_csv(PROJECT_ROOT / f"data/processed/surrogate_training_set{suffix}.csv")
        X_train, y_train = train_df[feature_cols], train_df["monthly_tonnes"]

        for model_name, train_fn in [
            ("xgboost", train_surrogate_xgboost),
            ("gaussian_process", train_gaussian_process),
        ]:
            with mlflow.start_run(run_name=f"{model_name}{'_augmented' if augmented else '_baseline'}"):
                mlflow.log_param("model", model_name)
                mlflow.log_param("augmented", augmented)
                mlflow.log_param("training_points", len(train_df))
                model = train_fn(X_train, y_train)
                metrics = evaluate_on_held_out(model, X_held, y_held)
                mlflow.log_metric("held_out_rmse", metrics["rmse"])
                mlflow.log_metric("held_out_r2", metrics["r2"])
                mlflow.log_metric("held_out_rmse_pct_of_mean", metrics["rmse_pct_of_mean"])


def log_pdm_runs() -> None:
    """Phase 5's three models, all checked against the official held out
    test set, RUL_FD001.txt, the one time reported result."""
    mlflow.set_experiment("predictive_maintenance")

    data = load_raw(str(PROJECT_ROOT / "data" / "raw"))
    train_df = compute_rul(data["train"], cap=125)
    test_df = data["test"]
    y_true_test = data["rul"]["RUL"].to_numpy()

    sensor_cols = [c for c in train_df.columns if c.startswith("sensor_")]
    surviving_sensors = drop_constant_sensors(train_df, sensor_cols)
    train_featured = add_rolling_and_lag_features(train_df, surviving_sensors, window=5, lags=(1, 2))
    feature_cols = feature_matrix_columns(surviving_sensors, lags=(1, 2))

    fit_units, val_units = train_validation_split(train_df, n_validation_engines=20, seed=42)
    fit_df = train_featured[train_featured["unit_number"].isin(fit_units)]
    val_df = train_featured[train_featured["unit_number"].isin(val_units)]
    X_fit, y_fit = fit_df[feature_cols], fit_df["RUL"]

    test_featured = add_rolling_and_lag_features(test_df, surviving_sensors, window=5, lags=(1, 2))
    last_row_per_engine = test_featured.sort_values("time_in_cycles").groupby("unit_number").tail(1)
    last_row_per_engine = last_row_per_engine.sort_values("unit_number")
    X_test_flat = last_row_per_engine[feature_cols]

    with mlflow.start_run(run_name="linear_baseline"):
        mlflow.log_param("model", "linear_regression")
        model = train_linear_baseline(X_fit, y_fit)
        pred = model.predict(X_test_flat)
        mlflow.log_metric("test_rmse", rmse(y_true_test, pred))
        mlflow.log_metric("test_cmapss_score", cmapss_score(y_true_test, pred))

    with mlflow.start_run(run_name="xgboost"):
        mlflow.log_param("model", "xgboost")
        model = train_pdm_xgboost(X_fit, y_fit)
        pred = model.predict(X_test_flat)
        mlflow.log_metric("test_rmse", rmse(y_true_test, pred))
        mlflow.log_metric("test_cmapss_score", cmapss_score(y_true_test, pred))

    raw_feature_cols = ["op_setting_1", "op_setting_2", "op_setting_3"] + surviving_sensors
    X_fit_seq, y_fit_seq = build_training_windows(fit_df, raw_feature_cols, rul_col="RUL", window_length=30)
    X_val_seq, y_val_seq = build_training_windows(val_df, raw_feature_cols, rul_col="RUL", window_length=30)
    X_test_seq, test_units = build_inference_windows(test_df, raw_feature_cols, window_length=30)
    assert test_units == sorted(test_units), "test engines must be in ascending order to match RUL_FD001.txt"

    with mlflow.start_run(run_name="lstm"):
        mlflow.log_param("model", "lstm")
        mlflow.log_param("hidden_size", 64)
        mlflow.log_param("num_layers", 2)
        mlflow.log_param("n_epochs", 30)
        lstm_model, scaler, train_losses, val_losses = train_lstm(
            X_fit_seq, y_fit_seq, X_val_seq, y_val_seq, n_epochs=30, seed=42
        )
        mlflow.log_metric("best_epoch", int(np.argmin(val_losses)) + 1)
        pred = predict_lstm(lstm_model, scaler, X_test_seq)
        mlflow.log_metric("test_rmse", rmse(y_true_test, pred))
        mlflow.log_metric("test_cmapss_score", cmapss_score(y_true_test, pred))


if __name__ == "__main__":
    log_surrogate_runs()
    log_pdm_runs()
    print("Done. Run `mlflow ui` and open http://127.0.0.1:5000 to browse the results.")
