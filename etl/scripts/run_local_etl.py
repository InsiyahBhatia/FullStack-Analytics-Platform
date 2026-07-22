"""
FinSight — Local ETL (pandas-based)

Runs ETL for a given source dataset using pandas + SQLAlchemy.
No Hadoop/Spark dependency needed for local dev.

Usage:
    python etl/scripts/run_local_etl.py --source churn
    python etl/scripts/run_local_etl.py --source lending --sample 100000
    python etl/scripts/run_local_etl.py --source fraud --sample 100000
"""

import argparse
import logging
import os
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("finsight.etl")

RAW = Path(os.environ.get("FINSIGHT_DATA_DIR", r"D:\FinSight\data\raw"))
DB_USER = os.environ.get("DB_USER", "finsight_user")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "finsight_dev_2026")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5433")
DB_NAME = os.environ.get("DB_NAME", "finsight")
DB_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def get_engine():
    return create_engine(DB_URL, pool_pre_ping=True)


def log_metadata(engine, dag_id, task_id, source, target, records_written, status="SUCCESS", started_at=None, completed_at=None):
    now = datetime.now()
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO etl_metadata
                    (dag_id, task_id, source_table, target_table,
                     records_read, records_written, status, started_at, completed_at)
                VALUES (:dag, :task, :src, :tgt, :read, :written, :status, :started, :completed)
            """),
            {
                "dag": dag_id,
                "task": task_id,
                "src": source,
                "tgt": target,
                "read": records_written,
                "written": records_written,
                "status": status,
                "started": started_at or now,
                "completed": completed_at or now,
            },
        )


# ── Churn ─────────────────────────────────────────────────────

def etl_churn(engine, sample=None):
    started_at = datetime.now()
    path = RAW / "churn" / "telco_customer_churn.csv"
    logger.info(f"Reading {path}")
    df = pd.read_csv(path)
    if sample:
        df = df.sample(n=min(sample, len(df)), random_state=42)
    logger.info(f"Loaded {len(df)} rows")

    df["churn_label"] = df["Churn"].apply(lambda x: "Yes" if x == "Yes" else "No")
    df["churn_flag"] = (df["Churn"] == "Yes").astype(int)
    df["tenure"] = df["tenure"].fillna(0).astype(int)
    df["MonthlyCharges"] = pd.to_numeric(df["MonthlyCharges"], errors="coerce").fillna(0)
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce").fillna(0)
    df["avg_daily_charge"] = np.where(df["tenure"] > 0, df["MonthlyCharges"] / 30.0, 0)
    df["tenure_group"] = pd.cut(
        df["tenure"],
        bins=[-1, 6, 12, 24, 48, 999],
        labels=["0-6 months", "6-12 months", "12-24 months", "24-48 months", "48+ months"],
    )

    fact = df[[
        "customerID", "tenure", "MonthlyCharges", "TotalCharges",
        "Contract", "PaymentMethod", "PaperlessBilling", "MultipleLines",
        "InternetService", "OnlineSecurity", "OnlineBackup",
        "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies",
        "churn_label", "churn_flag", "avg_daily_charge", "tenure_group",
    ]].copy()
    fact.columns = [
        "customer_id", "tenure", "monthly_charges", "total_charges",
        "contract_type", "payment_method", "paperless_billing", "multiple_lines",
        "internet_service", "online_security", "online_backup",
        "device_protection", "tech_support", "streaming_tv", "streaming_movies",
        "churn_label", "churn_flag", "avg_daily_charge", "tenure_group",
    ]

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE fact_churn"))
        fact.to_sql("fact_churn", conn, if_exists="append", index=False, method="multi")
    logger.info(f"Written {len(fact)} rows to fact_churn")
    log_metadata(engine, "local_etl", "etl_churn", "telco_customer_churn.csv", "fact_churn", len(fact), started_at=started_at, completed_at=datetime.now())
    return len(fact)


# ── Lending ───────────────────────────────────────────────────

def etl_lending(engine, sample=None):
    started_at = datetime.now()
    path = RAW / "lending" / "lending_club.csv"
    logger.info(f"Reading {path}")
    usecols = [
        "id", "loan_amnt", "int_rate", "annual_inc", "emp_length",
        "home_ownership", "grade", "purpose", "term", "loan_status",
        "dti", "fico_range_low", "fico_range_high", "issue_d",
    ]
    df = pd.read_csv(
        path,
        usecols=usecols,
        nrows=sample,
        low_memory=False,
    )
    logger.info(f"Loaded {len(df)} rows")

    df = df.drop_duplicates(subset=["id"])
    if df["int_rate"].dtype == object:
        df["int_rate"] = df["int_rate"].str.replace("%", "").astype(float)
    df["int_rate"] = df["int_rate"].astype(float) / 100
    df["annual_inc"] = pd.to_numeric(df["annual_inc"], errors="coerce").fillna(0)
    df["dti"] = pd.to_numeric(df["dti"], errors="coerce").fillna(0)
    df["fico_range_low"] = pd.to_numeric(df["fico_range_low"], errors="coerce")
    df["fico_range_high"] = pd.to_numeric(df["fico_range_high"], errors="coerce")
    df["credit_score"] = df[["fico_range_low", "fico_range_high"]].mean(axis=1).fillna(600).astype(int)
    df["loan_amnt"] = pd.to_numeric(df["loan_amnt"], errors="coerce").fillna(0)
    df["loan_status"] = df["loan_status"].replace({
        "Late (16-30 days)": "Late",
        "Late (31-120 days)": "Late",
    })
    df["default_flag"] = df["loan_status"].isin(["Charged Off", "Default"]).astype(int)
    df["debt_ratio"] = np.where(
        df["annual_inc"] > 0, df["loan_amnt"] / df["annual_inc"], 0
    )
    df["high_risk"] = (df["credit_score"] < 600).astype(int)
    df["interest_rate_bucket"] = pd.cut(
        df["int_rate"],
        bins=[-1, 0.07, 0.14, 1],
        labels=["low", "medium", "high"],
    )
    df["issue_date"] = pd.to_datetime(df["issue_d"], format="%b-%Y", errors="coerce")

    fact = df[[
        "id", "loan_amnt", "int_rate", "annual_inc", "emp_length",
        "home_ownership", "grade", "purpose", "term", "loan_status",
        "dti", "credit_score", "issue_date", "default_flag",
        "debt_ratio", "high_risk", "interest_rate_bucket",
    ]].copy()
    fact.columns = [
        "loan_id_orig", "loan_amount", "interest_rate", "annual_income", "employment_length",
        "home_ownership", "grade", "purpose", "term", "loan_status",
        "dti", "credit_score", "issue_date", "default_flag",
        "debt_ratio", "high_risk", "interest_rate_bucket",
    ]
    fact["source_system"] = "lending"

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE fact_loan"))
        fact.to_sql("fact_loan", conn, if_exists="append", index=False, method="multi")
    logger.info(f"Written {len(fact)} rows to fact_loan")
    log_metadata(engine, "local_etl", "etl_lending", "lending_club.csv", "fact_loan", len(fact), started_at=started_at, completed_at=datetime.now())
    return len(fact)


# ── Fraud ─────────────────────────────────────────────────────

def etl_fraud(engine, sample=None):
    started_at = datetime.now()
    txn_path = RAW / "fraud" / "train_transaction.csv"
    id_path = RAW / "fraud" / "train_identity.csv"

    logger.info(f"Reading transactions from {txn_path}")
    txn = pd.read_csv(txn_path, nrows=sample, low_memory=False)

    logger.info(f"Reading identity from {id_path}")
    identity = pd.read_csv(id_path, low_memory=False)

    df = txn.merge(identity, on="TransactionID", how="left")
    df = df.drop_duplicates(subset=["TransactionID"])
    logger.info(f"Merged: {len(df)} rows (deduped)")

    df["TransactionAmt"] = pd.to_numeric(df["TransactionAmt"], errors="coerce").fillna(0)
    df["dist1"] = pd.to_numeric(df["dist1"], errors="coerce").fillna(0)
    df["dist2"] = pd.to_numeric(df["dist2"], errors="coerce").fillna(0)
    df["transaction_amt_log"] = np.where(df["TransactionAmt"] > 0, np.log10(df["TransactionAmt"]) + 1, 0)
    FRAUD_EPOCH = pd.Timestamp("2017-12-01 00:00:00", tz="UTC")
    df["transaction_dt"] = df["TransactionDT"].apply(
        lambda s: FRAUD_EPOCH + pd.Timedelta(seconds=s)
    )

    fact = df[[
        "TransactionID", "TransactionAmt", "ProductCD",
        "card1", "card2", "card3", "card4", "card5", "card6",
        "addr1", "addr2", "dist1", "dist2",
        "DeviceType", "DeviceInfo", "isFraud", "transaction_amt_log",
        "transaction_dt",
    ]].copy()
    fact.columns = [
        "transaction_id", "transaction_amt", "product_cd",
        "card1", "card2", "card3", "card4", "card5", "card6",
        "addr1", "addr2", "dist1", "dist2",
        "device_type", "device_info", "is_fraud", "transaction_amt_log",
        "transaction_dt",
    ]
    fact["source_system"] = "fraud"

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE fact_transaction"))
        fact.to_sql("fact_transaction", conn, if_exists="append", index=False, method="multi")
    logger.info(f"Written {len(fact)} rows to fact_transaction")
    log_metadata(engine, "local_etl", "etl_fraud", "train_transaction.csv", "fact_transaction", len(fact), started_at=started_at, completed_at=datetime.now())
    return len(fact)


# ── Main ──────────────────────────────────────────────────────

ETL_MAP = {
    "churn": etl_churn,
    "lending": etl_lending,
    "fraud": etl_fraud,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, choices=["churn", "lending", "fraud"])
    parser.add_argument("--sample", type=int, help="Max rows to process")
    args = parser.parse_args()

    engine = get_engine()
    fn = ETL_MAP[args.source]
    kwargs = {}
    if args.sample:
        kwargs["sample"] = args.sample

    rows = fn(engine, **kwargs)
    logger.info(f"Pipeline complete: {rows} rows for {args.source}")


if __name__ == "__main__":
    main()
