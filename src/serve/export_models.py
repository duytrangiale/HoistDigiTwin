"""Produces the exact model files the deployed API in api.py needs,
saved into models/ at the repo root. That folder is tracked by git on
purpose, the one exception to the data/ rule, since Render builds the
API from a fresh checkout with no persistent disk, so whatever it loads
at startup has to already be committed. See phase7_plan.md.

Run this whenever the underlying training data or model choice changes,
so models/ never drifts out of sync with the code that produced it.
"""

from __future__ import annotations

import random
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from surrogate.train import save_model  # noqa: E402
from twin.maintenance_model import simulate_health_log, train_twin_rul_model  # noqa: E402
from twin.simulation import load_config  # noqa: E402

MODELS_DIR = PROJECT_ROOT / "models"


def export_surrogate() -> None:
    """Copies the most accurate surrogate found in Phase 4: the Gaussian
    process retrained on extra corner points. It beat XGBoost both
    overall (2.0 percent error against 6.8) and at the exact optimum
    corner (1.4 percent against 6.3), see phase4_plan.md.
    """
    source = PROJECT_ROOT / "data" / "processed" / "surrogate_gaussian_process_augmented.joblib"
    destination = MODELS_DIR / "surrogate.joblib"
    MODELS_DIR.mkdir(exist_ok=True)
    shutil.copy2(source, destination)
    print(f"copied {source.name} -> {destination}")


def export_winder_rul_model(seed: int = 42) -> None:
    """Trains the twin's own remaining life model fresh, the same way
    notebooks/06_combined.ipynb does, and saves it. Phase 6 only ever
    used this model in memory inside a notebook, this is the first time
    it is persisted to a file.
    """
    config = load_config(str(PROJECT_ROOT / "config.yaml"))
    health_cfg = config["winder"]["health"]

    rng = random.Random(seed)
    log_df = simulate_health_log(health_cfg, n_lives=800, rng=rng)
    model, X_val, y_val, y_train = train_twin_rul_model(log_df, n_validation_lives=150, seed=seed)

    MODELS_DIR.mkdir(exist_ok=True)
    destination = MODELS_DIR / "winder_rul.joblib"
    save_model(model, str(destination))
    print(f"trained and saved winder RUL model -> {destination}")


if __name__ == "__main__":
    export_surrogate()
    export_winder_rul_model()
