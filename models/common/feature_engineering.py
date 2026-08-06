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
    categorical_features=[
        "contract_type",
        "payment_method",
        "internet_service",
        "online_security",
        "tech_support",
        "paperless_billing",
        "streaming_tv",
    ],
)

DEFAULT_SPEC = FeatureSpec(
    task="default",
    target="default_flag",
    numeric_features=[
        "fico_score",
        "debt_ratio",
        "loan_amount",
        "annual_inc",
        "emp_length",
        "revol_bal",
        "revol_util",
        "delinq_2yrs",
        "pub_rec",
        "open_acc",
    ],
    categorical_features=["grade", "purpose", "home_ownership", "verification_status"],
)

# IEEE-CIS counting features (address/card match counts C1..C14).
FRAUD_C_FEATURES = [f"C{i}" for i in range(1, 15)]

# Curated subset of the 339 Vesta engineered behavioral features (V1..V339).
# These are the features with comparatively low null rates and high reported
# predictive weight in IEEE-CIS benchmarks; the full V set adds little signal
# for a large preprocessing and SMOTE cost.
FRAUD_V_FEATURES = [
    "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9", "V10",
    "V11", "V12", "V13", "V14", "V15", "V16", "V17", "V18", "V19", "V20",
    "V22", "V23", "V24", "V25", "V26", "V28", "V30", "V31", "V32", "V33",
]

# Rolling velocity aggregates computed from the transaction stream (per card).
FRAUD_VELOCITY_FEATURES = ["txn_cnt_1h", "txn_cnt_24h", "txn_amt_sum_24h", "txn_amt_std_24h"]

FRAUD_SPEC = FeatureSpec(
    task="fraud",
    target="is_fraud",
    numeric_features=[
        "transaction_amt",
        "dist1",
        "dist2",
        *FRAUD_VELOCITY_FEATURES,
        *FRAUD_C_FEATURES,
        *FRAUD_V_FEATURES,
    ],
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


def _missing_numeric(series: pd.Series | None, index) -> pd.Series:
    """Return a NaN column when a raw numeric column is absent."""
    if series is None:
        return pd.Series(np.nan, index=index)
    return pd.to_numeric(series, errors="coerce")


def _fill_categoricals(df: pd.DataFrame, columns: list[str], default: str = "unknown") -> None:
    """Gracefully fill missing categorical feature columns (feature columns only; target stays strict)."""
    for col in columns:
        if col not in df.columns:
            df[col] = default
        else:
            df[col] = df[col].fillna(default).astype(str)


def normalize_churn(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    rename = {
        "customerID": "customer_id",
        "MonthlyCharges": "monthly_charges",
        "TotalCharges": "total_charges",
        "Contract": "contract_type",
        "PaymentMethod": "payment_method",
        "InternetService": "internet_service",
        "OnlineSecurity": "online_security",
        "TechSupport": "tech_support",
        "PaperlessBilling": "paperless_billing",
        "StreamingTV": "streaming_tv",
        "Churn": "churn_label",
    }
    df = df.rename(columns=rename)
    df["total_charges"] = _missing_numeric(df.get("total_charges"), df.index)
    _fill_categoricals(df, CHURN_SPEC.categorical_features)
    df["churn_flag"] = df["churn_label"].astype(str).str.lower().eq("yes").astype(int)
    return df[CHURN_SPEC.all_features + [CHURN_SPEC.target]]


def _parse_emp_length(series: pd.Series) -> pd.Series:
    """Parse Lending Club employment strings ('< 1 year', '5 years', '10+ years') to float years."""
    s = series.astype(str).str.strip()
    years = pd.to_numeric(s.str.extract(r"(\d+)", expand=False), errors="coerce")
    years[s.str.startswith("<")] = 0.0
    return years


def normalize_loans(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["fico_score"] = (_missing_numeric(df.get("fico_range_low"), df.index) + _missing_numeric(df.get("fico_range_high"), df.index)) / 2
    df["debt_ratio"] = _missing_numeric(df.get("dti"), df.index)
    df["loan_amount"] = _missing_numeric(df.get("loan_amnt"), df.index)
    df["annual_inc"] = _missing_numeric(df.get("annual_inc"), df.index)
    df["emp_length"] = _parse_emp_length(df["emp_length"]) if "emp_length" in df.columns else pd.Series(np.nan, index=df.index)
    df["revol_bal"] = _missing_numeric(df.get("revol_bal"), df.index)
    df["revol_util"] = _missing_numeric(df.get("revol_util"), df.index)
    df["delinq_2yrs"] = _missing_numeric(df.get("delinq_2yrs"), df.index)
    df["pub_rec"] = _missing_numeric(df.get("pub_rec"), df.index)
    df["open_acc"] = _missing_numeric(df.get("open_acc"), df.index)
    _fill_categoricals(df, DEFAULT_SPEC.categorical_features, default="OTHER")
    default_statuses = {
        "Charged Off",
        "Default",
        "Does not meet the credit policy. Status:Charged Off",
        "Late (31-120 days)",
    }
    df["default_flag"] = df["loan_status"].isin(default_statuses).astype(int)
    return df[DEFAULT_SPEC.all_features + [DEFAULT_SPEC.target]]


def _rolling_velocity(group: pd.DataFrame, window_sec: int) -> dict[str, np.ndarray]:
    """Rolling count/sum/std of transaction amounts over a trailing window per group.

    `group` must be pre-sorted by the (numeric, seconds) transaction time column.
    """
    ts = group["_dt_sec"].to_numpy(dtype=float)
    amt = group["_transaction_amt"].to_numpy(dtype=float)
    n = len(ts)
    cnt = np.full(n, np.nan)
    amt_sum = np.full(n, np.nan)
    amt_std = np.full(n, np.nan)
    valid = ~np.isnan(ts)
    nv = int(valid.sum())
    if nv > 0:
        ts_v = ts[valid]
        idx = np.searchsorted(ts_v, ts_v - window_sec, side="left")
        positions = np.arange(1, nv + 1)
        win_n = positions - idx
        cnt[valid] = win_n
        x = np.nan_to_num(amt[valid], nan=0.0)
        csum = np.cumsum(x)
        csq = np.cumsum(x * x)
        pre = np.concatenate([[0.0], csum])[idx]
        sums = csum - pre
        amt_sum[valid] = sums
        pre2 = np.concatenate([[0.0], csq])[idx]
        var = np.maximum((csq - pre2 - (sums ** 2) / win_n) / win_n, 0.0)
        amt_std[valid] = np.sqrt(var)
    return {"cnt": cnt, "amt_sum": amt_sum, "amt_std": amt_std}


def _add_fraud_velocity(df: pd.DataFrame, entity_col: str = "card1", dt_col: str = "transaction_dt", cutoff_dt: float | None = None) -> pd.DataFrame:
    """Compute rolling velocity aggregates per card over 1h / 24h trailing windows.

    IEEE-CIS `TransactionDT` is seconds since a reference point, so window sizes
    are 3600s and 86400s. Each row's velocity only aggregates transactions at or
    before its own timestamp (a causal, trailing window). Rows without a usable
    entity key or timestamp get NaN and are handled by the imputer downstream.

    ``cutoff_dt``: when set, velocity is computed using only transactions with
    ``dt <= cutoff_dt``; rows after the cutoff get NaN. This is used to compute
    causal (past-only) velocity for training rows in ``train_fraud`` so training
    features never incorporate future transactions.
    """
    out = df.copy()
    if entity_col not in out.columns or dt_col not in out.columns or "transaction_amt" not in out.columns:
        for col in FRAUD_VELOCITY_FEATURES:
            out[col] = np.nan
        return out
    # Reset to a unique positional index so the label-based alignment below is
    # safe even if the input frame has duplicate indices; row order is restored
    # at the end via an order-preserving column.
    out["_row_order"] = np.arange(len(out))
    out = out.reset_index(drop=True)
    out["_dt_sec"] = pd.to_numeric(out[dt_col], errors="coerce")
    out["_transaction_amt"] = pd.to_numeric(out["transaction_amt"], errors="coerce")
    out = out.sort_values("_dt_sec")
    if cutoff_dt is not None and np.isfinite(float(cutoff_dt)):
        compute = out[out["_dt_sec"].notna() & (out["_dt_sec"] <= float(cutoff_dt))].copy()
    else:
        compute = out
    grouped = compute.groupby(entity_col, group_keys=False)
    v1h = grouped.apply(lambda g: pd.DataFrame(_rolling_velocity(g, 3600), index=g.index), include_groups=False)
    v24h = grouped.apply(lambda g: pd.DataFrame(_rolling_velocity(g, 86400), index=g.index), include_groups=False)
    out["txn_cnt_1h"] = v1h["cnt"]
    out["txn_cnt_24h"] = v24h["cnt"]
    out["txn_amt_sum_24h"] = v24h["amt_sum"]
    out["txn_amt_std_24h"] = v24h["amt_std"]
    out = out.drop(columns=["_dt_sec", "_transaction_amt"])
    out = out.sort_values("_row_order").drop(columns=["_row_order"])
    return out


def normalize_fraud(transaction: pd.DataFrame, identity: pd.DataFrame | None = None, velocity_cutoff_dt: float | None = None) -> pd.DataFrame:
    df = transaction.copy()
    if identity is not None and "TransactionID" in identity.columns:
        identity = identity.drop_duplicates(subset=["TransactionID"])
        df = df.merge(identity, on="TransactionID", how="left")
    rename = {
        "TransactionAmt": "transaction_amt",
        "TransactionDT": "transaction_dt",
        "DeviceType": "device_type",
        "card4": "card_type",
        "id_31": "browser",
        "P_emaildomain": "email_domain",
        "isFraud": "is_fraud",
    }
    df = df.rename(columns=rename)
    _fill_categoricals(df, FRAUD_SPEC.categorical_features)
    df = _add_fraud_velocity(df, cutoff_dt=velocity_cutoff_dt)
    for col in FRAUD_SPEC.numeric_features:
        if col not in df.columns:
            df[col] = np.nan
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
    if spec.categorical_features:
        cat = preprocessor.named_transformers_["categorical"].named_steps["encoder"]
        names.extend(cat.get_feature_names_out(spec.categorical_features).tolist())
    return names
