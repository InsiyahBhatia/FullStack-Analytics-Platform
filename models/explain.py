"""Generate SHAP explainability artifacts for a trained FinSight model."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from models.common.feature_engineering import SPECS, clean_training_frame, normalize_churn, normalize_fraud, normalize_loans
from models.common.registry import load_model


def load_task_frame(task: str, data_dir: Path, sample_rows: int) -> pd.DataFrame:
    if task == "churn":
        raw = pd.read_csv(data_dir / "raw" / "churn" / "telco_customer_churn.csv")
        return clean_training_frame(normalize_churn(raw), SPECS[task], sample_rows)
    if task == "default":
        # Match train_default: read the same first 150k rows the model trained on
        # (the raw file is 2.2M rows / 1.6GB; the model never saw the tail).
        raw = pd.read_csv(data_dir / "raw" / "lending" / "lending_club.csv", low_memory=False, nrows=150000)
        return clean_training_frame(normalize_loans(raw), SPECS[task], sample_rows)
    tx = pd.read_csv(data_dir / "raw" / "fraud" / "train_transaction.csv")
    identity_path = data_dir / "raw" / "fraud" / "train_identity.csv"
    identity = pd.read_csv(identity_path) if identity_path.exists() else None
    # Downcast float64 -> float32 to halve memory for the 590k-row IEEE-CIS frame
    # (mirrors models/train_all.py). The full stream is still required: velocity
    # aggregates must be computed over every transaction, then sample_rows are taken.
    for _df in (tx, identity):
        if _df is not None:
            float_cols = _df.select_dtypes(include=["float64"]).columns
            _df[float_cols] = _df[float_cols].astype("float32")
    return clean_training_frame(normalize_fraud(tx, identity), SPECS[task], sample_rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=["churn", "default", "fraud"], required=True)
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--sample-rows", type=int, default=1000)
    args = parser.parse_args()

    import shap

    spec = SPECS[args.task]
    local = load_model(args.task)
    frame = load_task_frame(args.task, Path(args.data_dir), args.sample_rows)
    x = frame[spec.all_features]
    transformed = local.model.named_steps["preprocessor"].transform(x)
    estimator = local.model.named_steps["model"]
    out = Path("models/artifacts") / args.task / "shap"
    out.mkdir(parents=True, exist_ok=True)

    explainer = shap.Explainer(estimator, transformed)
    values = explainer(transformed)

    shap.summary_plot(values, transformed, show=False)
    plt.tight_layout()
    plt.savefig(out / "summary_plot.png", dpi=160)
    plt.close()

    shap.plots.waterfall(values[0], show=False)
    plt.tight_layout()
    plt.savefig(out / "waterfall_plot.png", dpi=160)
    plt.close()

    # Dependence plot for the most impactful feature. Uses the raw array + the
    # classic API: shap 0.49's shap.plots.scatter(values[:, 0]) raises
    # "object of type 'NoneType' has no len()" on sliced TreeExplainer output.
    top_feature = int(np.argmax(np.abs(values.values).mean(axis=0)))
    shap.dependence_plot(top_feature, values.values, transformed, show=False)
    plt.tight_layout()
    plt.savefig(out / "dependence_plot.png", dpi=160)
    plt.close()

    print(f"SHAP artifacts written to {out}")


if __name__ == "__main__":
    main()
