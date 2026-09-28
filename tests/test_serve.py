"""Tests for Phase 7's API, src/serve/api.py. Imports the real app and its
two already trained models directly, no server process needed, FastAPI's
TestClient calls the route functions in process.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fastapi.testclient import TestClient

from serve.api import app

client = TestClient(app)


def test_health_check_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_predict_tonnes_returns_a_positive_prediction():
    response = client.post("/predict/tonnes", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["predicted_monthly_tonnes"] > 0
    assert body["predicted_annual_tonnes"] == pytest.approx(body["predicted_monthly_tonnes"] * 12)


def test_predict_tonnes_rejects_settings_outside_the_trained_range():
    # feed_rate_multiplier's real range is 0.5 to 1.5, see
    # src/surrogate/sampling.py's PARAM_RANGES
    response = client.post("/predict/tonnes", json={"feed_rate_multiplier": 5.0})
    assert response.status_code == 422


def test_predict_tonnes_increases_with_a_faster_winder():
    slow = client.post("/predict/tonnes", json={"winder_speed_multiplier": 0.7}).json()
    fast = client.post("/predict/tonnes", json={"winder_speed_multiplier": 1.4}).json()
    assert fast["predicted_monthly_tonnes"] > slow["predicted_monthly_tonnes"]


def test_predict_winder_rul_says_healthy_for_a_fresh_reading():
    response = client.post("/predict/winder-rul", json={"current_reading": 98, "elapsed_hours": 5})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["predicted_remaining_hours"] > 0


def test_predict_winder_rul_says_schedule_maintenance_for_a_dying_reading():
    response = client.post("/predict/winder-rul", json={"current_reading": 2, "elapsed_hours": 300})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "schedule maintenance soon"
