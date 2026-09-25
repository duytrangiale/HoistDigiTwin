"""Tests for the surrogate's save, load, and predict mechanics. Uses a
small synthetic dataset built directly with numpy rather than the real
simulator, so this suite stays fast and does not depend on run order or
Phase 3's own generated training data existing yet.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from surrogate.train import load_model, save_model, train_xgboost


def _synthetic_dataset(n: int = 40, n_features: int = 5, seed: int = 0) -> tuple[pd.DataFrame, pd.Series]:
    rng = np.random.default_rng(seed)
    X = pd.DataFrame(rng.uniform(0, 1, size=(n, n_features)), columns=[f"x{i}" for i in range(n_features)])
    y = pd.Series(X.sum(axis=1) * 1000 + rng.normal(0, 10, size=n))
    return X, y


def test_surrogate_saves_loads_and_predicts(tmp_path):
    X, y = _synthetic_dataset()
    model = train_xgboost(X, y, n_estimators=30)

    model_path = tmp_path / "surrogate_test_model.joblib"
    save_model(model, str(model_path))
    loaded_model = load_model(str(model_path))

    sample = X.iloc[[0]]
    prediction = loaded_model.predict(sample)[0]

    assert np.isfinite(prediction)
    # the synthetic relationship is a scaled sum of the inputs, so a model
    # that actually learned something should land close to the true label
    # for a point it was trained on, not just output some finite number
    assert abs(prediction - y.iloc[0]) < 500
