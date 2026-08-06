"""Train all FinSight ML models from local raw CSV files."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from models.common.feature_engineering import (
    CHURN_SPEC,
    DEFAULT_SPEC,
    FRAUD_SPEC,
    FRAUD_VELOCITY_FEATURES,
    clean_training_frame,
    normalize_churn,
    normalize_fraud,
    normalize_loans,
)
from models.common.registry import ARTIFACT_ROOT
from models.common.training import log_to_mlflow, train_candidates


def train_churn(data_dir: Path, max_rows: int | None, **train_kwargs) -> dict:
    raw = pd.read_csv(data_dir / "raw" / "churn" / "telco_customer_churn.csv")
    frame = clean_training_frame(normalize_churn(raw), CHURN_SPEC, max_rows)
    return train_candidates("churn", frame, CHURN_SPEC, **train_kwargs)


def train_default(data_dir: Path, max_rows: int | None, **train_kwargs) -> dict:
    raw = pd.read_csv(data_dir / "raw" / "lending" / "lending_club.csv", low_memory=False, nrows=max_rows)
    frame = clean_training_frame(normalize_loans(raw), DEFAULT_SPEC, None)
    return train_candidates("default", frame, DEFAULT_SPEC, **train_kwargs)


def train_fraud(data_dir: Path, max_rows: int | None, **train_kwargs) -> dict:
    tx = pd.read_csv(data_dir / "raw" / "fraud" / "train_transaction.csv", nrows=max_rows)
    identity_path = data_dir / "raw" / "fraud" / "train_identity.csv"
    identity = pd.read_csv(identity_path) if identity_path.exists() else None
    # Downcast float64 -> float32 to roughly halve memory for the full 590k-row
    # IEEE-CIS frame (V features are float64; float32 precision is more than enough).
    for _df in (tx, identity):
        if _df is not None:
            float_cols = _df.select_dtypes(include=["float64"]).columns
            _df[float_cols] = _df[float_cols].astype("float32")
    frame = clean_training_frame(normalize_fraud(tx, identity), FRAUD_SPEC, None)
    # Attach the transaction timestamp so train_candidates can split the fraud stream
    # chronologically (test = most recent 20%), keeping velocity features causal.
    if "TransactionDT" in tx.columns:
        frame["transaction_dt"] = pd.to_numeric(tx["TransactionDT"], errors="coerce").reindex(frame.index)
        frame = frame.sort_values("transaction_dt")
        # Causal velocity for the training portion: recompute the velocity columns
        # using only transactions at or before the chronological split boundary, so
        # training features never incorporate future (test-period) transactions.
        # Test rows keep full-history velocity, matching production serving.
        split_at = max(2, int(len(frame) * 0.8))
        boundary_dt = frame.iloc[split_at - 1]["transaction_dt"]
        if pd.notna(boundary_dt):
            train_labels = frame.index[:split_at]
            causal = clean_training_frame(
                normalize_fraud(tx, identity, velocity_cutoff_dt=float(boundary_dt)), FRAUD_SPEC, None
            )
            for col in FRAUD_VELOCITY_FEATURES:
                frame.loc[train_labels, col] = causal[col].reindex(train_labels).to_numpy()
    return train_candidates("fraud", frame, FRAUD_SPEC, time_col="transaction_dt", **train_kwargs)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=["all", "churn", "default", "fraud"], default="all")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--max-rows", type=int, default=150000)
    parser.add_argument("--cv-folds", type=int, default=5)
    parser.add_argument("--no-tune", action="store_true", help="Skip hyperparameter search on the winning candidate")
    parser.add_argument("--tune-iter", type=int, default=6)
    parser.add_argument("--log-mlflow", action="store_true")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    tasks = ["churn", "default", "fraud"] if args.task == "all" else [args.task]
    runners = {"churn": train_churn, "default": train_default, "fraud": train_fraud}
    train_kwargs = {
        "n_splits": args.cv_folds,
        "tune_winner": not args.no_tune,
        "tune_iter": args.tune_iter,
    }

    failed = []
    for task in tasks:
        try:
            result = runners[task](data_dir, args.max_rows, **train_kwargs)
            metrics = result["best"]["metrics"]
            cv_auc = metrics.get("cv_roc_auc", metrics["roc_auc"])
            print(f"{task}: {result['best']['algorithm']} ROC-AUC={metrics['roc_auc']} (CV={cv_auc})")
            if args.log_mlflow:
                log_to_mlflow(task, ARTIFACT_ROOT / task / "model.joblib", result["best"])
        except Exception as e:
            print(f"{task}: FAILED ({e})")
            failed.append(task)

    if failed:
        raise SystemExit(f"Training failed for: {', '.join(failed)}")


if __name__ == "__main__":
    main()
