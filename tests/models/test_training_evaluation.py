"""Tests for validation-based threshold tuning, calibration and extended metrics."""

import json

import numpy as np
import pandas as pd

from models.common import registry
from models.common.evaluation import CalibratedPipeline, extended_metrics, fit_calibrator, ks_statistic, lift_at
from models.common.feature_engineering import CHURN_SPEC
from models.common.training import train_candidates


def _churn_frame(n: int = 1500, seed: int = 0) -> pd.DataFrame:
    rng = np.random.RandomState(seed)
    tenure = rng.randint(0, 72, n)
    monthly = rng.uniform(20, 120, n)
    contract = rng.choice(["Month-to-month", "One year", "Two year"], n, p=[0.6, 0.2, 0.2])
    logit = -0.05 * tenure + 0.02 * monthly + (contract == "Month-to-month") * 1.2 - 0.8
    churn = (rng.uniform(size=n) < 1 / (1 + np.exp(-logit))).astype(int)
    return pd.DataFrame(
        {
            "tenure": tenure,
            "monthly_charges": monthly,
            "total_charges": tenure * monthly,
            "contract_type": contract,
            "payment_method": rng.choice(["Electronic check", "Mailed check"], n),
            "internet_service": rng.choice(["DSL", "Fiber optic", "No"], n),
            "online_security": rng.choice(["No", "Yes"], n),
            "tech_support": rng.choice(["No", "Yes"], n),
            "paperless_billing": rng.choice(["Yes", "No"], n),
            "streaming_tv": rng.choice(["No", "Yes"], n),
            "churn_flag": churn,
        }
    )


def test_extended_metrics_perfect_ranking():
    y = np.array([0, 0, 0, 0, 1, 1])
    s = np.array([0.1, 0.2, 0.2, 0.3, 0.8, 0.9])
    m = extended_metrics(y, s, 0.5)
    assert (m["tp"], m["fp"], m["tn"], m["fn"]) == (2, 0, 4, 0)
    assert m["pr_auc"] == 1.0
    assert ks_statistic(y, s) == 1.0
    assert lift_at(y, s, 0.34) == 3.0


def test_calibrator_outputs_probabilities():
    rng = np.random.RandomState(1)
    raw = rng.uniform(size=800)
    y = (rng.uniform(size=800) < raw**2).astype(int)
    cal, method = fit_calibrator(raw, y)
    assert method in {"isotonic", "sigmoid"}


def test_train_candidates_uses_validation_holdout(tmp_path, monkeypatch):
    monkeypatch.setattr(registry, "ARTIFACT_ROOT", tmp_path / "artifacts")
    monkeypatch.setattr("models.common.training.save_model", lambda *a, **k: None)
    out = train_candidates(
        "churn", _churn_frame(), CHURN_SPEC, output_dir=str(tmp_path / "artifacts"),
        n_splits=3, tune_winner=False,
    )
    meta = out["best"]
    assert meta["pipeline"]["threshold_fit"] == "validation_holdout"
    assert meta["pipeline"]["validation_rows"] > 0
    m = meta["metrics"]
    assert 0.5 < m["roc_auc"] <= 1.0
    assert m["tp"] + m["fp"] + m["tn"] + m["fn"] == meta["pipeline"]["test_rows"]
    curves = json.loads((tmp_path / "artifacts" / "churn" / "curves.json").read_text())
    assert {"roc", "pr"} <= set(curves)


def test_calibrated_pipeline_exposes_named_steps():
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    rng = np.random.RandomState(2)
    x = rng.normal(size=(300, 3))
    y = (x[:, 0] + rng.normal(size=300) > 0).astype(int)
    pipe = Pipeline([("preprocessor", StandardScaler()), ("model", LogisticRegression())]).fit(x, y)
    cal, method = fit_calibrator(pipe.predict_proba(x)[:, 1], y)
    wrapped = CalibratedPipeline(pipe, cal, method)
    assert "model" in wrapped.named_steps
    proba = wrapped.predict_proba(x)
    assert proba.shape == (300, 2) and np.allclose(proba.sum(axis=1), 1)
