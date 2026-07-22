"""Reusable training, MLflow logging, SHAP, and benchmark utilities."""

from __future__ import annotations

import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from models.common.feature_engineering import FeatureSpec, build_preprocessor, feature_names
from models.common.registry import save_model


def _optional_classifier(package: str, class_name: str, fallback):
    try:
        module = __import__(package, fromlist=[class_name])
        return getattr(module, class_name)
    except Exception:
        return fallback


def candidate_models(task: str) -> dict:
    xgb = _optional_classifier("xgboost", "XGBClassifier", RandomForestClassifier)
    lgbm = _optional_classifier("lightgbm", "LGBMClassifier", RandomForestClassifier)
    catboost = _optional_classifier("catboost", "CatBoostClassifier", RandomForestClassifier)

    if task == "churn":
        return {
            "logistic_regression": LogisticRegression(max_iter=1000, class_weight="balanced"),
            "random_forest": RandomForestClassifier(n_estimators=180, class_weight="balanced", random_state=42),
            "xgboost": xgb(eval_metric="logloss", random_state=42) if xgb is not RandomForestClassifier else xgb(random_state=42),
            "lightgbm": lgbm(random_state=42) if lgbm is not RandomForestClassifier else lgbm(random_state=42),
        }
    if task == "default":
        return {
            "xgboost": xgb(eval_metric="logloss", random_state=42) if xgb is not RandomForestClassifier else xgb(random_state=42),
            "catboost": catboost(verbose=False, random_seed=42) if catboost is not RandomForestClassifier else catboost(random_state=42),
            "random_forest": RandomForestClassifier(n_estimators=220, class_weight="balanced", random_state=42),
        }
    if task == "fraud":
        return {
            "isolation_forest": IsolationForest(contamination=0.04, random_state=42),
            "xgboost": xgb(eval_metric="logloss", scale_pos_weight=10, random_state=42) if xgb is not RandomForestClassifier else xgb(class_weight="balanced", random_state=42),
            "lightgbm": lgbm(class_weight="balanced", random_state=42) if lgbm is not RandomForestClassifier else lgbm(class_weight="balanced", random_state=42),
        }
    raise ValueError(f"Unknown task: {task}")


def build_training_pipeline(task: str, spec: FeatureSpec, estimator):
    if isinstance(estimator, IsolationForest):
        return Pipeline([("preprocessor", build_preprocessor(spec)), ("model", estimator)])
    if task in {"default", "fraud"}:
        try:
            from imblearn.over_sampling import SMOTE
            from imblearn.pipeline import Pipeline as ImbPipeline
            from imblearn.under_sampling import RandomUnderSampler

            return ImbPipeline(
                [
                    ("preprocessor", build_preprocessor(spec)),
                    ("smote", SMOTE(random_state=42)),
                    ("under", RandomUnderSampler(random_state=42)),
                    ("model", estimator),
                ]
            )
        except Exception:
            pass
    return Pipeline([("preprocessor", build_preprocessor(spec)), ("model", estimator)])


def evaluate_binary(y_true, y_score, threshold: float = 0.5) -> dict:
    y_pred = (np.asarray(y_score) >= threshold).astype(int)
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, y_score)), 4),
        "threshold": threshold,
    }


def tune_threshold(y_true, y_score) -> float:
    thresholds = np.arange(0.1, 0.91, 0.02)
    scores = [(thr, f1_score(y_true, np.asarray(y_score) >= thr, zero_division=0)) for thr in thresholds]
    return float(max(scores, key=lambda item: item[1])[0])


def train_candidates(task: str, df: pd.DataFrame, spec: FeatureSpec, output_dir: str = "models/artifacts") -> dict:
    x = df[spec.all_features]
    y = df[spec.target].astype(int)
    stratify = y if y.nunique() == 2 and y.value_counts().min() >= 2 else None
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=42, stratify=stratify
    )

    results = []
    best = None
    best_score = -1.0

    for name, estimator in candidate_models(task).items():
        started = time.time()
        pipeline = build_training_pipeline(task, spec, estimator)
        if isinstance(estimator, IsolationForest):
            pipeline.fit(x_train)
            raw = pipeline.decision_function(x_test)
            y_score = 1 - ((raw - raw.min()) / max(raw.max() - raw.min(), 1e-9))
        else:
            pipeline.fit(x_train, y_train)
            y_score = pipeline.predict_proba(x_test)[:, 1]

        threshold = tune_threshold(y_test, y_score)
        metrics = evaluate_binary(y_test, y_score, threshold)
        metrics["training_seconds"] = round(time.time() - started, 2)
        row = {"task": task, "algorithm": name, **metrics}
        results.append(row)

        if metrics["roc_auc"] > best_score:
            best_score = metrics["roc_auc"]
            best = (name, pipeline, threshold, metrics)

    if best is None:
        raise RuntimeError(f"No model candidates trained for {task}")

    best_name, best_pipeline, threshold, best_metrics = best
    metadata = {
        "name": f"finsight_{task}",
        "task": task,
        "algorithm": best_name,
        "version": "1.0.0",
        "threshold": threshold,
        "metrics": best_metrics,
        "features": spec.all_features,
        "target": spec.target,
    }

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    save_model(task, best_pipeline, metadata)
    export_feature_importance(task, best_pipeline, spec, output_dir)
    pd.DataFrame(results).to_csv(root / f"{task}_benchmarks.csv", index=False)
    (root / f"{task}_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return {"best": metadata, "results": results}


def log_to_mlflow(task: str, model_path: Path, metadata: dict) -> None:
    try:
        import mlflow
        import mlflow.sklearn
    except Exception:
        return

    import os
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(f"finsight_{task}")
    model = joblib.load(model_path)
    with mlflow.start_run(run_name=f"{task}_{metadata['algorithm']}"):
        mlflow.log_params({"task": task, "algorithm": metadata["algorithm"], "target": metadata["target"]})
        mlflow.log_metrics(metadata["metrics"])
        mlflow.log_dict(metadata, "metadata.json")
        mlflow.sklearn.log_model(
            model, artifact_path="model", registered_model_name=f"finsight_{task}",
            skops_trusted_types=[
                "collections.OrderedDict", "lightgbm.basic.Booster",
                "lightgbm.sklearn.LGBMClassifier", "numpy.dtype",
                "sklearn.compose._column_transformer._RemainderColsList",
                "sklearn.compose._column_transformer.ColumnTransformer",
                "sklearn.pipeline.Pipeline", "sklearn.preprocessing._encoders.OneHotEncoder",
                "sklearn.preprocessing._data.StandardScaler",
                "sklearn.impute._simple.SimpleImputer",
                "catboost.core.CatBoostClassifier",
                "xgboost.core.Booster", "xgboost.sklearn.XGBClassifier",
                "imblearn.over_sampling._smote.base.SMOTE",
                "imblearn.pipeline.Pipeline",
                "imblearn.under_sampling._prototype_selection._random_under_sampler.RandomUnderSampler",
            ],
        )


def export_feature_importance(task: str, pipeline: Pipeline, spec: FeatureSpec, output_dir: str = "models/artifacts") -> Path:
    estimator = pipeline.named_steps["model"]
    names = feature_names(pipeline.named_steps["preprocessor"], spec)
    if hasattr(estimator, "feature_importances_"):
        values = estimator.feature_importances_
    elif hasattr(estimator, "coef_"):
        values = np.abs(estimator.coef_[0])
    else:
        values = np.zeros(len(names))
    frame = pd.DataFrame({"feature": names, "importance": values}).sort_values("importance", ascending=False)
    out = Path(output_dir) / task / "feature_importance.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out, index=False)
    return out
