"""The public API behind the dashboard, wrapping two already trained
models. Deliberately does not import torch, shap, or run the discrete
event simulation live, all too heavy or too slow for a free, small
hosted service, measured and explained in phase7_plan.md. Only
surrogate.sampling is imported for its PARAM_RANGES constant, confirmed
not to pull in torch, since twin.simulation only imports the predictive
maintenance code lazily, inside the branch that actually needs it.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
MODELS_DIR = PROJECT_ROOT / "models"

import joblib
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from surrogate.sampling import PARAM_RANGES

# the three columns the winder RUL model was trained on, see
# src/twin/maintenance_model.py's FEATURE_COLS. Not imported directly,
# since that module pulls in src/pdm/models.py, which imports torch.
WINDER_FEATURE_COLS = ["observed_health", "rolling_mean", "elapsed_hours"]

app = FastAPI(
    title="HoistDigiTwin API",
    description="Serves the Phase 3/4 surrogate and the Phase 6 winder health model behind the dashboard.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # a public, read only demo with no sensitive data
    allow_methods=["*"],
    allow_headers=["*"],
)

surrogate_model = joblib.load(MODELS_DIR / "surrogate.joblib")
winder_rul_model = joblib.load(MODELS_DIR / "winder_rul.joblib")


class TonnesRequest(BaseModel):
    feed_rate_multiplier: float = Field(1.0, ge=PARAM_RANGES["feed_rate_multiplier"][0], le=PARAM_RANGES["feed_rate_multiplier"][1])
    skip_payload_tonnes: float = Field(12.0, ge=PARAM_RANGES["skip_payload_tonnes"][0], le=PARAM_RANGES["skip_payload_tonnes"][1])
    winder_speed_multiplier: float = Field(1.0, ge=PARAM_RANGES["winder_speed_multiplier"][0], le=PARAM_RANGES["winder_speed_multiplier"][1])
    breakdown_mtbf_hours: float = Field(200.0, ge=PARAM_RANGES["breakdown_mtbf_hours"][0], le=PARAM_RANGES["breakdown_mtbf_hours"][1])
    scheduled_downtime_hours_per_month: float = Field(
        20.0,
        ge=PARAM_RANGES["scheduled_downtime_hours_per_month"][0],
        le=PARAM_RANGES["scheduled_downtime_hours_per_month"][1],
    )


class TonnesResponse(BaseModel):
    predicted_monthly_tonnes: float
    predicted_annual_tonnes: float


class WinderRulRequest(BaseModel):
    current_reading: float = Field(..., ge=0, le=100, description="the winder's current health reading, 0 to 100")
    elapsed_hours: float = Field(..., ge=0, description="hours since the winder's last repair")


class WinderRulResponse(BaseModel):
    predicted_remaining_hours: float
    status: str


@app.get("/health")
def health() -> dict:
    """A lightweight wake up ping, also used by the frontend to detect
    when the free hosted backend has gone to sleep."""
    return {"status": "ok"}


@app.post("/predict/tonnes", response_model=TonnesResponse)
def predict_tonnes(request: TonnesRequest) -> TonnesResponse:
    X = pd.DataFrame([request.model_dump()])[list(PARAM_RANGES.keys())]
    monthly = float(surrogate_model.predict(X)[0])
    return TonnesResponse(predicted_monthly_tonnes=monthly, predicted_annual_tonnes=monthly * 12)


@app.post("/predict/winder-rul", response_model=WinderRulResponse)
def predict_winder_rul(request: WinderRulRequest) -> WinderRulResponse:
    # a single point in time reading with no history yet behaves the same
    # way the first reading of a real life does in training, the rolling
    # mean is just that one reading, see build_features's min_periods=1
    X = pd.DataFrame(
        [{"observed_health": request.current_reading, "rolling_mean": request.current_reading, "elapsed_hours": request.elapsed_hours}]
    )[WINDER_FEATURE_COLS]
    remaining_hours = float(winder_rul_model.predict(X)[0])

    if remaining_hours < 24:
        status = "schedule maintenance soon"
    elif remaining_hours < 72:
        status = "watch"
    else:
        status = "healthy"

    return WinderRulResponse(predicted_remaining_hours=remaining_hours, status=status)
