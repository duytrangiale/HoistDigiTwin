"""Trains and evaluates the surrogate: an XGBoost baseline and a Gaussian
process, both mapping the five operating settings from sampling.py to mean
monthly tonnes. See reports/phase3_plan.md at the repo root for the
reasoning behind using two model types and evaluating against a held out
set rather than cross validation alone.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel, WhiteKernel
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import KFold
from sklearn.model_selection import cross_validate as sk_cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor


def train_xgboost(X: pd.DataFrame, y: pd.Series, **params) -> XGBRegressor:
    """Fits an XGBoost regressor. Defaults are conservative, shallow trees
    and a modest number of them, since the training set is only a few
    hundred points and the targets are themselves noisy, averaged over a
    handful of replications rather than exact."""
    defaults = dict(n_estimators=200, max_depth=3, learning_rate=0.05, subsample=0.8, random_state=42)
    defaults.update(params)
    model = XGBRegressor(**defaults)
    model.fit(X, y)
    return model


def train_gaussian_process(X: pd.DataFrame, y: pd.Series) -> Pipeline:
    """Fits a Gaussian process, standardising inputs first since Gaussian
    processes are sensitive to input scale in a way trees are not. The
    kernel has one length scale per input, so the fitted model can learn
    that some of the five parameters matter more than others, plus a white
    noise term, since the targets carry real observation noise from
    averaging only a handful of replications, not the noiseless
    measurements a plain RBF kernel assumes."""
    n_features = X.shape[1]
    kernel = ConstantKernel(1.0, (1e-3, 1e3)) * RBF(
        length_scale=[1.0] * n_features, length_scale_bounds=(1e-2, 1e3)
    ) + WhiteKernel(noise_level=1.0, noise_level_bounds=(1e-5, 1e5))
    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "gp",
                GaussianProcessRegressor(
                    kernel=kernel, normalize_y=True, n_restarts_optimizer=5, random_state=42
                ),
            ),
        ]
    )
    model.fit(X, y)
    return model


def cross_validate(model, X: pd.DataFrame, y: pd.Series, k: int = 5) -> dict:
    """k fold cross validation on the training set. Works on an already
    fitted model too, scikit-learn clones and refits it per fold."""
    kfold = KFold(n_splits=k, shuffle=True, random_state=42)
    scores = sk_cross_validate(model, X, y, cv=kfold, scoring=["neg_root_mean_squared_error", "r2"])
    rmse_per_fold = -scores["test_neg_root_mean_squared_error"]
    r2_per_fold = scores["test_r2"]
    return {
        "rmse_per_fold": rmse_per_fold,
        "r2_per_fold": r2_per_fold,
        "mean_rmse": float(rmse_per_fold.mean()),
        "mean_r2": float(r2_per_fold.mean()),
    }


def evaluate_on_held_out(model, X_held_out: pd.DataFrame, y_held_out: pd.Series) -> dict:
    """Checks predictions against the held out set's less noisy targets,
    the actual test of whether the surrogate can be trusted, not just how
    well it fits its own training data."""
    predictions = model.predict(X_held_out)
    rmse = float(np.sqrt(mean_squared_error(y_held_out, predictions)))
    r2 = float(r2_score(y_held_out, predictions))
    rmse_pct_of_mean = float(rmse / y_held_out.mean() * 100)
    return {
        "rmse": rmse,
        "r2": r2,
        "rmse_pct_of_mean": rmse_pct_of_mean,
        "predictions": predictions,
    }


def save_model(model, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)


def load_model(path: str):
    return joblib.load(path)
