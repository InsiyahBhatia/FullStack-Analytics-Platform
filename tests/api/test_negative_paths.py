"""Negative-path tests for API endpoints."""

import os
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

API_KEY = os.environ["API_KEYS_DEV"].split(":")[0]
HEADERS = {"X-API-Key": API_KEY}


def test_churn_missing_required_fields():
    response = client.post("/predict/churn", json={}, headers=HEADERS)
    assert response.status_code in (400, 422)


def test_churn_invalid_field_type():
    response = client.post(
        "/predict/churn",
        json={"tenure": "not_a_number", "monthly_charges": 110},
        headers=HEADERS,
    )
    assert response.status_code in (400, 422)


def test_churn_negative_tenure():
    response = client.post(
        "/predict/churn",
        json={
            "tenure": -1,
            "monthly_charges": 110,
            "total_charges": 660,
            "contract_type": "Month-to-month",
            "payment_method": "Electronic check",
            "internet_service": "Fiber optic",
        },
        headers=HEADERS,
    )
    assert response.status_code == 422


def test_default_missing_required_fields():
    response = client.post("/predict/default", json={}, headers=HEADERS)
    assert response.status_code in (400, 422)


def test_fraud_missing_required_fields():
    response = client.post("/predict/fraud", json={}, headers=HEADERS)
    assert response.status_code in (400, 422)


def test_churn_empty_body():
    response = client.post("/predict/churn", headers=HEADERS)
    assert response.status_code in (400, 422)


def test_health_get_not_allowed():
    response = client.get("/health")
    assert response.status_code == 200
