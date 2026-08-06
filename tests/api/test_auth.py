"""Tests for API authentication middleware."""

import os
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_missing_api_key_returns_401():
    response = client.post("/predict/churn", json={"tenure": 6})
    assert response.status_code == 401
    assert "Missing" in response.json()["detail"]


def test_invalid_api_key_returns_403():
    response = client.post(
        "/predict/churn",
        json={"tenure": 6},
        headers={"X-API-Key": "sk-invalid-key"},
    )
    assert response.status_code == 403
    assert "Invalid" in response.json()["detail"]


def test_valid_api_key_passes_auth():
    response = client.post(
        "/predict/churn",
        json={
            "tenure": 6,
            "monthly_charges": 110,
            "total_charges": 660,
            "contract_type": "Month-to-month",
            "payment_method": "Electronic check",
            "internet_service": "Fiber optic",
        },
        headers={"X-API-Key": os.environ["API_KEYS_DEV"].split(":")[0]},
    )
    assert response.status_code == 200


def test_health_endpoint_no_auth_required():
    response = client.post("/health")
    assert response.status_code == 200


def test_metrics_endpoint_no_auth_required():
    response = client.post("/metrics")
    assert response.status_code == 200
