import pandas as pd

from models.common.feature_engineering import CHURN_SPEC, align_inference_payload, normalize_churn


def test_normalize_churn_contract():
    raw = pd.DataFrame(
        {
            "customerID": ["C1"],
            "tenure": [12],
            "MonthlyCharges": [100.0],
            "TotalCharges": ["1200.0"],
            "Contract": ["Month-to-month"],
            "PaymentMethod": ["Electronic check"],
            "InternetService": ["Fiber optic"],
            "Churn": ["Yes"],
        }
    )
    frame = normalize_churn(raw)
    assert frame.loc[0, "churn_flag"] == 1
    assert list(frame.columns) == CHURN_SPEC.all_features + [CHURN_SPEC.target]


def test_align_inference_payload_keeps_feature_order():
    payload = {"monthly_charges": 80, "tenure": 5, "total_charges": 400, "contract_type": "One year"}
    frame = align_inference_payload(payload, CHURN_SPEC)
    assert list(frame.columns) == CHURN_SPEC.all_features
    assert frame.loc[0, "tenure"] == 5
