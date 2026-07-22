"""Train all FinSight ML models from local raw CSV files."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from models.common.feature_engineering import (
    CHURN_SPEC,
    DEFAULT_SPEC,
    FRAUD_SPEC,
    clean_training_frame,
    normalize_churn,
    normalize_fraud,
    normalize_loans,
)
from models.common.registry import ARTIFACT_ROOT
from models.common.training import log_to_mlflow, train_candidates


def train_churn(data_dir: Path, max_rows: int | None) -> dict:
    raw = pd.read_csv(data_dir / "raw" / "churn" / "telco_customer_churn.csv")
    frame = clean_training_frame(normalize_churn(raw), CHURN_SPEC, max_rows)
    return train_candidates("churn", frame, CHURN_SPEC)


def train_default(data_dir: Path, max_rows: int | None) -> dict:
    raw = pd.read_csv(data_dir / "raw" / "lending" / "lending_club.csv", low_memory=False, nrows=max_rows)
    frame = clean_training_frame(normalize_loans(raw), DEFAULT_SPEC, None)
    return train_candidates("default", frame, DEFAULT_SPEC)


def train_fraud(data_dir: Path, max_rows: int | None) -> dict:
    tx = pd.read_csv(data_dir / "raw" / "fraud" / "train_transaction.csv", nrows=max_rows)
    identity_path = data_dir / "raw" / "fraud" / "train_identity.csv"
    identity = pd.read_csv(identity_path) if identity_path.exists() else None
    frame = clean_training_frame(normalize_fraud(tx, identity), FRAUD_SPEC, None)
    return train_candidates("fraud", frame, FRAUD_SPEC)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=["all", "churn", "default", "fraud"], default="all")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--max-rows", type=int, default=150000)
    parser.add_argument("--log-mlflow", action="store_true")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    tasks = ["churn", "default", "fraud"] if args.task == "all" else [args.task]
    runners = {"churn": train_churn, "default": train_default, "fraud": train_fraud}

    for task in tasks:
        try:
            result = runners[task](data_dir, args.max_rows)
            print(f"{task}: {result['best']['algorithm']} ROC-AUC={result['best']['metrics']['roc_auc']}")
            if args.log_mlflow:
                log_to_mlflow(task, ARTIFACT_ROOT / task / "model.joblib", result["best"])
        except Exception as e:
            print(f"{task}: FAILED ({e})")


if __name__ == "__main__":
    main()
