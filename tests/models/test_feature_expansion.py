"""Tests for the expanded feature sets and normalizers (roadmap v2)."""

import numpy as np
import pandas as pd
import pytest

from models.common.feature_engineering import (
    CHURN_SPEC,
    DEFAULT_SPEC,
    FRAUD_SPEC,
    FRAUD_C_FEATURES,
    FRAUD_V_FEATURES,
    normalize_churn,
    normalize_fraud,
    normalize_loans,
)


# ── Churn ──────────────────────────────────────────────────────────────────


def _churn_raw():
    return pd.DataFrame(
        {
            "customerID": ["C1", "C2"],
            "tenure": [12, 3],
            "MonthlyCharges": [100.0, 60.0],
            "TotalCharges": ["1200.0", "180.0"],
            "Contract": ["Month-to-month", "Two year"],
            "PaymentMethod": ["Electronic check", "Mailed check"],
            "InternetService": ["Fiber optic", "DSL"],
            "OnlineSecurity": ["No", "Yes"],
            "TechSupport": ["No", "Yes"],
            "PaperlessBilling": ["Yes", "No"],
            "StreamingTV": ["No", "Yes"],
            "Churn": ["Yes", "No"],
        }
    )


def test_churn_spec_includes_service_features():
    for col in ["online_security", "tech_support", "paperless_billing", "streaming_tv"]:
        assert col in CHURN_SPEC.categorical_features


def test_normalize_churn_service_features():
    frame = normalize_churn(_churn_raw())
    assert list(frame.columns) == CHURN_SPEC.all_features + [CHURN_SPEC.target]
    assert frame.loc[0, "online_security"] == "No"
    assert frame.loc[1, "tech_support"] == "Yes"
    assert frame.loc[1, "paperless_billing"] == "No"
    assert frame.loc[1, "streaming_tv"] == "Yes"


def test_normalize_churn_missing_service_features_graceful():
    raw = _churn_raw().drop(columns=["OnlineSecurity", "TechSupport", "PaperlessBilling", "StreamingTV"])
    frame = normalize_churn(raw)
    assert (frame["online_security"] == "unknown").all()
    assert frame.loc[0, "churn_flag"] == 1


# ── Loan Default ───────────────────────────────────────────────────────────


def _loans_raw():
    return pd.DataFrame(
        {
            "fico_range_low": [650, 700, 620, 680],
            "fico_range_high": [654, 704, 624, 684],
            "dti": [18.5, 25.0, 32.0, 15.0],
            "loan_amnt": [12000, 25000, 8000, 30000],
            "grade": ["B", "C", "E", "A"],
            "purpose": ["debt_consolidation", "credit_card", "small_business", "other"],
            "loan_status": ["Fully Paid", "Charged Off", "Current", "Fully Paid"],
            "annual_inc": [75000, 48000, 42000, 110000],
            "emp_length": ["10+ years", "< 1 year", "5 years", "3 years"],
            "revol_bal": [12000, 8000, 15000, 5000],
            "revol_util": [35.0, 48.2, 60.1, 12.0],
            "delinq_2yrs": [0, 2, 1, 0],
            "pub_rec": [0, 1, 0, 0],
            "open_acc": [12, 8, 6, 15],
            "home_ownership": ["MORTGAGE", "RENT", "RENT", "OWN"],
            "verification_status": ["Source Verified", "Not Verified", "Verified", "Source Verified"],
        }
    )


def test_default_spec_has_expanded_features():
    for col in ["annual_inc", "emp_length", "revol_bal", "revol_util", "delinq_2yrs", "pub_rec", "open_acc"]:
        assert col in DEFAULT_SPEC.numeric_features
    for col in ["home_ownership", "verification_status"]:
        assert col in DEFAULT_SPEC.categorical_features


def test_normalize_loans_expanded_features():
    frame = normalize_loans(_loans_raw())
    assert list(frame.columns) == DEFAULT_SPEC.all_features + [DEFAULT_SPEC.target]
    # emp_length string parsing: "< 1 year" -> 0, "5 years" -> 5, "10+ years" -> 10
    assert frame.loc[0, "emp_length"] == 10
    assert frame.loc[1, "emp_length"] == 0
    assert frame.loc[2, "emp_length"] == 5
    assert frame.loc[0, "annual_inc"] == 75000
    assert frame.loc[1, "delinq_2yrs"] == 2
    assert frame.loc[0, "revol_util"] == 35.0
    assert frame.loc[0, "home_ownership"] == "MORTGAGE"
    assert frame.loc[0, "verification_status"] == "Source Verified"
    assert frame.loc[0, "default_flag"] == 0
    assert frame.loc[1, "default_flag"] == 1


def test_normalize_loans_missing_new_columns_graceful():
    raw = _loans_raw().drop(columns=["annual_inc", "revol_util", "home_ownership", "verification_status"])
    frame = normalize_loans(raw)
    assert frame["annual_inc"].isna().all()
    assert frame["revol_util"].isna().all()
    assert (frame["home_ownership"] == "OTHER").all()
    assert (frame["verification_status"] == "OTHER").all()


# ── Fraud ──────────────────────────────────────────────────────────────────


def test_fraud_spec_has_expanded_features():
    for col in ["dist1", "dist2", "txn_cnt_1h", "txn_cnt_24h", "txn_amt_sum_24h", "txn_amt_std_24h"]:
        assert col in FRAUD_SPEC.numeric_features
    assert len(FRAUD_C_FEATURES) == 14
    for col in FRAUD_C_FEATURES + FRAUD_V_FEATURES:
        assert col in FRAUD_SPEC.numeric_features
    assert len(FRAUD_V_FEATURES) == 30


def _fraud_raw():
    # Card 101: 3 transactions 100-400s apart. Card 202: 3 transactions 900-1200s.
    return pd.DataFrame(
        {
            "TransactionID": [f"T{i}" for i in range(6)],
            "TransactionDT": [100, 200, 400, 900, 1000, 1200],
            "TransactionAmt": [50.0, 30.0, 20.0, 500.0, 10.0, 25.0],
            "card1": [101, 101, 101, 202, 202, 202],
            "card4": ["visa", "visa", "visa", "mastercard", "mastercard", "mastercard"],
            "addr1": [1, 1, 1, 2, 2, 2],
            "isFraud": [0, 0, 1, 0, 0, 0],
        }
    )


def test_normalize_fraud_velocity_features():
    frame = normalize_fraud(_fraud_raw())
    assert list(frame.columns) == FRAUD_SPEC.all_features + [FRAUD_SPEC.target]
    # Card 101 rows are 100s apart -> 1h windows accumulate prior transactions
    assert frame.loc[0, "txn_cnt_1h"] == 1
    assert frame.loc[1, "txn_cnt_1h"] == 2
    assert frame.loc[2, "txn_cnt_1h"] == 3
    assert frame.loc[2, "txn_cnt_24h"] == 3
    assert frame.loc[2, "txn_amt_sum_24h"] == pytest.approx(100.0)  # 50 + 30 + 20
    assert frame.loc[2, "txn_amt_std_24h"] == pytest.approx(12.4722, abs=1e-3)  # population std of [50, 30, 20]
    # Card 202 starts fresh
    assert frame.loc[3, "txn_cnt_1h"] == 1
    assert frame.loc[5, "txn_amt_sum_24h"] == pytest.approx(535.0)
    # dist1/dist2 and C/V columns absent from raw -> NaN (imputed downstream)
    assert frame["dist1"].isna().all()
    assert frame["C1"].isna().all()
    assert frame["V1"].isna().all()
    assert frame.loc[0, "device_type"] == "unknown"


def test_normalize_fraud_velocity_out_of_order_input():
    raw = _fraud_raw().iloc[::-1].reset_index(drop=True)  # reversed order
    frame = normalize_fraud(raw)
    # Reversed label 3 = original row 2 (card 101, 3rd txn); windows are computed
    # on the time-sorted stream, then rows are restored to input order.
    assert frame.loc[3, "txn_cnt_1h"] == 3
    assert frame.loc[3, "txn_amt_sum_24h"] == pytest.approx(100.0)
    assert frame.loc[0, "txn_cnt_1h"] == 3  # card 202, 3rd txn (dt=1200)


def test_normalize_fraud_velocity_cutoff():
    raw = _fraud_raw()  # dt 100..1200 across two cards
    frame = normalize_fraud(raw, velocity_cutoff_dt=500)
    # Rows at or before the cutoff keep causal velocity computed from past-only data
    assert frame.loc[0, "txn_cnt_1h"] == 1
    assert frame.loc[2, "txn_cnt_1h"] == 3
    assert frame.loc[2, "txn_amt_sum_24h"] == pytest.approx(100.0)
    # Rows after the cutoff get NaN velocity (excluded from the causal history)
    assert np.isnan(frame.loc[3, "txn_cnt_1h"])
    assert np.isnan(frame.loc[5, "txn_amt_sum_24h"])
    assert np.isnan(frame.loc[5, "txn_amt_sum_24h"])


def test_normalize_fraud_velocity_duplicate_index():
    raw = _fraud_raw()
    dup = pd.concat([raw, raw.iloc[[2]]])  # index label 2 now duplicated
    frame = normalize_fraud(dup)
    assert len(frame) == 7
    assert frame["txn_cnt_24h"].notna().all()
    # Original rows keep their labels; the appended duplicate (dt=400, card 101)
    # is the last row and sees 4 prior card-101 transactions within 1h.
    assert frame.loc[2, "txn_cnt_1h"] == 3
    assert frame.iloc[6]["txn_cnt_1h"] == 4


def _simple_spec():
    from models.common.feature_engineering import FeatureSpec

    return FeatureSpec(task="churn", target="target", numeric_features=["feature_a"], categorical_features=[])


def test_train_candidates_chronological_split(monkeypatch, tmp_path):
    from models.common import registry
    from models.common.training import train_candidates

    monkeypatch.setattr(registry, "ARTIFACT_ROOT", tmp_path / "artifacts")
    n = 400
    rng = pd.Series(range(n))
    df = pd.DataFrame(
        {
            "feature_a": (rng % 10 + 1).astype(float),
            "transaction_dt": range(n),
            "target": (rng % 5 == 0).astype(int),  # positives spread across the stream
        }
    )
    spec = _simple_spec()
    kwargs = dict(output_dir=str(tmp_path / "out"), n_splits=3, tune_winner=False)

    # Chronological split path: test set is the most recent 20% of the stream.
    result = train_candidates("churn", df, spec, time_col="transaction_dt", **kwargs)
    assert result["best"]["metrics"]["roc_auc"] > 0

    # Degenerate chronological split (no positives in the test window) falls back
    # to a stratified random split instead of raising.
    df2 = df.copy()
    df2["target"] = ((df2["transaction_dt"] < 200) & (df2["transaction_dt"] % 5 == 0)).astype(int)
    result2 = train_candidates("churn", df2, spec, time_col="transaction_dt", **kwargs)
    assert result2["best"]["metrics"]["roc_auc"] > 0
