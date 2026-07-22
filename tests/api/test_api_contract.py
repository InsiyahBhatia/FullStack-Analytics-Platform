from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_health_post():
    response = client.post("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_churn_prediction_contract():
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
    )
    assert response.status_code == 200
    body = response.json()
    assert "prediction" in body
    assert 0 <= body["probability"] <= 1


def test_metrics_contract():
    response = client.post("/metrics")
    assert response.status_code == 200
    assert set(response.json()["models"].keys()) == {"churn", "default", "fraud"}
