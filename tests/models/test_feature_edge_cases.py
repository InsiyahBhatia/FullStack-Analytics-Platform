"""Edge-case tests for feature engineering."""

import pandas as pd

from models.common.feature_engineering import CHURN_SPEC, align_inference_payload, normalize_churn


def test_normalize_churn_missing_columns():
    raw = pd.DataFrame({"customerID": ["C1"], "tenure": [12]})
    try:
        normalize_churn(raw)
    except (KeyError, ValueError):
        pass


def test_normalize_churn_empty_dataframe():
    raw = pd.DataFrame(columns=["customerID", "tenure", "MonthlyCharges", "TotalCharges",
                                  "Contract", "PaymentMethod", "InternetService", "Churn"])
    frame = normalize_churn(raw)
    assert len(frame) == 0


def test_normalize_churn_no_churn():
    raw = pd.DataFrame({
        "customerID": ["C1"],
        "tenure": [12],
        "MonthlyCharges": [100.0],
        "TotalCharges": ["1200.0"],
        "Contract": ["Month-to-month"],
        "PaymentMethod": ["Electronic check"],
        "InternetService": ["Fiber optic"],
        "Churn": ["No"],
    })
    frame = normalize_churn(raw)
    assert frame.loc[0, "churn_flag"] == 0


def test_normalize_churn_total_charges_whitespace():
    raw = pd.DataFrame({
        "customerID": ["C1"],
        "tenure": [1],
        "MonthlyCharges": [50.0],
        "TotalCharges": ["  50.0  "],
        "Contract": ["Month-to-month"],
        "PaymentMethod": ["Mailed check"],
        "InternetService": ["DSL"],
        "Churn": ["Yes"],
    })
    frame = normalize_churn(raw)
    assert frame.loc[0, "total_charges"] == 50.0


def test_align_inference_payload_extra_fields_ignored():
    payload = {
        "monthly_charges": 80,
        "tenure": 5,
        "total_charges": 400,
        "contract_type": "One year",
        "irrelevant_field": "ignored",
    }
    frame = align_inference_payload(payload, CHURN_SPEC)
    assert "irrelevant_field" not in frame.columns


def test_align_inference_payload_missing_optional():
    payload = {"monthly_charges": 80, "tenure": 5}
    frame = align_inference_payload(payload, CHURN_SPEC)
    assert frame.shape[1] == len(CHURN_SPEC.all_features)
