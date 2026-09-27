"""Metrics and plots for comparing remaining useful life models. See
phase5_plan.md at the repo root for the reasoning behind reporting both
RMSE and the C-MAPSS score, rather than either one alone.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap


def rmse(y_true, y_pred) -> float:
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    return float(np.sqrt(np.mean((y_pred - y_true) ** 2)))


def cmapss_score(y_true, y_pred) -> float:
    """The official C-MAPSS scoring function (Saxena et al. 2008). RMSE
    treats an early guess and a late guess of the same size as equally
    wrong, this does not. d = predicted - true: d < 0 means the
    prediction was early, less time was predicted than the engine
    actually had, just some unnecessary caution. d >= 0 means it was
    late, more time was predicted than the engine actually had, which
    risks running it past real failure. The late case uses a smaller
    denominator in the exponent (10 against 13), so it grows faster for
    the same sized miss, exactly the asymmetry the real cost of being
    wrong calls for.
    """
    d = np.asarray(y_pred) - np.asarray(y_true)
    scores = np.where(d < 0, np.exp(-d / 13) - 1, np.exp(d / 10) - 1)
    return float(scores.sum())


def predicted_vs_true_plot(y_true, y_pred, title: str = "", ax=None):
    """A scatter of predicted against true RUL, with a diagonal reference
    line. A tight diagonal means the model is trustworthy."""
    if ax is None:
        _, ax = plt.subplots(figsize=(5, 5))
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    ax.scatter(y_true, y_pred, alpha=0.5, s=15)
    upper = max(y_true.max(), y_pred.max()) * 1.05
    ax.plot([0, upper], [0, upper], color="grey", linestyle="--", linewidth=1)
    ax.set_xlabel("true RUL")
    ax.set_ylabel("predicted RUL")
    ax.set_title(title)
    return ax


def comparison_table(results: dict[str, dict]) -> pd.DataFrame:
    """results is {model_name: {"y_true": ..., "y_pred": ...}}. One row
    per model, RMSE and the C-MAPSS score side by side, since they can
    disagree about which model looks better."""
    rows = []
    for name, r in results.items():
        rows.append(
            {
                "model": name,
                "RMSE": rmse(r["y_true"], r["y_pred"]),
                "C-MAPSS score": cmapss_score(r["y_true"], r["y_pred"]),
            }
        )
    return pd.DataFrame(rows).set_index("model")


def compute_shap_values(model, X: pd.DataFrame, sample_size: int = 2000, seed: int = 42):
    """Explains a tree model's predictions on a random sample of rows.
    Plain feature importance only says which sensor matters on average,
    SHAP also says which direction, whether a high reading pushes the
    predicted remaining life up or down, the question a mining
    stakeholder actually asks next. Sampled rather than run on every row,
    since SHAP's exact computation for tree models still grows with the
    number of rows explained, and this is a portfolio scale project.
    """
    sample = X.sample(min(sample_size, len(X)), random_state=seed)
    explainer = shap.TreeExplainer(model)
    return explainer(sample)


def shap_importance_table(shap_values, n_top: int = 15) -> pd.DataFrame:
    """Ranks features by mean absolute SHAP value, from an already
    computed shap.Explanation, so the same explanation can also feed
    shap's own richer plots (for example shap.summary_plot) without
    paying to recompute it."""
    mean_abs = np.abs(shap_values.values).mean(axis=0)
    result = pd.DataFrame({"feature": shap_values.feature_names, "mean_abs_shap": mean_abs})
    return result.sort_values("mean_abs_shap", ascending=False).head(n_top).reset_index(drop=True)
