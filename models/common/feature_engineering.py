"""Feature contracts and preprocessing builders for FinSight ML models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


@dataclass(frozen=True)
class FeatureSpec:
    task: str
    target: str
    numeric_features: list[str]
    categorical_features: list[str]
    positive_label: int = 1

    @property
    def all_features(self) -> list[str]:
        return self.numeric_features + self.categorical_features


CHURN_SPEC = FeatureSpec(
    task="churn",
    target="churn_flag",
    numeric_features=["tenure", "monthly_charges", "total_charges"],
    categorical_features=["contract_type", "payment_method", "internet_service"],
)

DEFAULT_SPEC = FeatureSpec(
    task="default",
    target="default_flag",
    numeric_features=["fico_score", "debt_ratio", "loan_amount"],
    categorical_features=["grade", "purpose"],
)

FRAUD_SPEC = FeatureSpec(
    task="fraud",
    target="is_fraud",
    numeric_features=["transaction_amt"],
    categorical_features=["device_type", "card_type", "browser", "email_domain"],
)

SPECS = {
    "churn": CHURN_SPEC,
    "default": DEFAULT_SPEC,
    "fraud": FRAUD_SPEC,
}


def build_preprocessor(spec: FeatureSpec) -> ColumnTransformer:
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, spec.numeric_features),
            ("categorical", categorical_pipeline, spec.categorical_features),
        ],
        remainder="drop",
    )


def normalize_churn(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    rename = {
        "customerID": "customer_id",
        "MonthlyCharges": "monthly_charges",
        "TotalCharges": "total_charges",
        "Contract": "contract_type",
        "PaymentMethod": "payment_method",
        "InternetService": "internet_service",
        "Churn": "churn_label",
    }
    df = df.rename(columns=rename)
    df["total_charges"] = pd.to_numeric(df["total_charges"], errors="coerce")
    df["churn_flag"] = df["churn_label"].astype(str).str.lower().eq("yes").astype(int)
    return df[CHURN_SPEC.all_features + [CHURN_SPEC.target]]


def normalize_loans(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["fico_score"] = (
        pd.to_numeric(df.get("fico_range_low"), errors="coerce")
        + pd.to_numeric(df.get("fico_range_high"), errors="coerce")
    ) / 2
    df["debt_ratio"] = pd.to_numeric(df.get("dti"), errors="coerce")
    df["loan_amount"] = pd.to_numeric(df.get("loan_amnt"), errors="coerce")
    default_statuses = {
        "Charged Off",
        "Default",
        "Does not meet the credit policy. Status:Charged Off",
        "Late (31-120 days)",
    }
    df["default_flag"] = df["loan_status"].isin(default_statuses).astype(int)
    return df[DEFAULT_SPEC.all_features + [DEFAULT_SPEC.target]]


def normalize_fraud(transaction: pd.DataFrame, identity: pd.DataFrame | None = None) -> pd.DataFrame:
    df = transaction.copy()
    if identity is not None and "TransactionID" in identity.columns:
        df = df.merge(identity, on="TransactionID", how="left")
    rename = {
        "TransactionAmt": "transaction_amt",
        "DeviceType": "device_type",
        "card4": "card_type",
        "id_31": "browser",
        "P_emaildomain": "email_domain",
        "isFraud": "is_fraud",
    }
    df = df.rename(columns=rename)
    for col in FRAUD_SPEC.categorical_features:
        if col not in df.columns:
            df[col] = "unknown"
    return df[FRAUD_SPEC.all_features + [FRAUD_SPEC.target]]


def clean_training_frame(df: pd.DataFrame, spec: FeatureSpec, max_rows: int | None = None) -> pd.DataFrame:
    frame = df[spec.all_features + [spec.target]].copy()
    frame = frame.replace([np.inf, -np.inf], np.nan)
    frame = frame.dropna(subset=[spec.target])
    frame[spec.target] = frame[spec.target].astype(int)
    if max_rows and len(frame) > max_rows:
        frame = frame.sample(max_rows, random_state=42)
    return frame


def align_inference_payload(payload: dict, spec: FeatureSpec) -> pd.DataFrame:
    row = {feature: payload.get(feature) for feature in spec.all_features}
    return pd.DataFrame([row], columns=spec.all_features)


def feature_names(preprocessor: ColumnTransformer, spec: FeatureSpec) -> list[str]:
    names: list[str] = list(spec.numeric_features)
    cat = preprocessor.named_transformers_["categorical"].named_steps["encoder"]
    names.extend(cat.get_feature_names_out(spec.categorical_features).tolist())
    return names
