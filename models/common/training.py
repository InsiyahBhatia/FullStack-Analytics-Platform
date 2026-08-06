"""Reusable training, MLflow logging, SHAP, and benchmark utilities."""

from __future__ import annotations

import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline

from models.common.feature_engineering import FeatureSpec, build_preprocessor, feature_names
from models.common.registry import save_model

# Business cost matrix used for cost-aware threshold tuning (fraud task).
# A missed fraud event (FN) costs far more than a manual review of a false alert (FP).
DEFAULT_COST_FN = 500.0
DEFAULT_COST_FP = 15.0

# Hyperparameter search spaces for the winning candidate (RandomizedSearchCV).
PARAM_GRIDS = {
    "xgboost": {
        "n_estimators": [100, 200, 300],
        "max_depth": [3, 5, 7],
        "learning_rate": [0.01, 0.05, 0.1, 0.2],
        "subsample": [0.6, 0.8, 1.0],
        "colsample_bytree": [0.6, 0.8, 1.0],
        "min_child_weight": [1, 3, 7, 15],
        "gamma": [0.0, 0.1, 0.5, 1.0],
        "reg_lambda": [1.0, 3.0, 10.0],
    },
    "lightgbm": {
        "n_estimators": [100, 200, 300],
        "num_leaves": [31, 63, 127],
        "learning_rate": [0.01, 0.05, 0.1],
        "subsample": [0.7, 0.8, 1.0],
    },
    "catboost": {
        "iterations": [100, 300, 500],
        "depth": [4, 6, 8],
        "learning_rate": [0.03, 0.1, 0.3],
        "l2_leaf_reg": [1.0, 3.0, 10.0],
    },
    "random_forest": {
        "n_estimators": [100, 200, 400],
        "max_depth": [None, 10, 20, 30],
        "min_samples_leaf": [1, 2, 5],
    },
    "logistic_regression": {
        "C": [0.1, 1.0, 10.0],
        "class_weight": ["balanced", None],
    },
}


def _optional_classifier(package: str, class_name: str, fallback):
    try:
        module = __import__(package, fromlist=[class_name])
        return getattr(module, class_name)
    except Exception:
        return fallback


def candidate_models(task: str, pos_weight: float | None = None) -> dict:
    xgb = _optional_classifier("xgboost", "XGBClassifier", RandomForestClassifier)
    lgbm = _optional_classifier("lightgbm", "LGBMClassifier", RandomForestClassifier)
    catboost = _optional_classifier("catboost", "CatBoostClassifier", RandomForestClassifier)

    xgb_kwargs = {"eval_metric": "logloss", "random_state": 42}
    if task == "fraud" and xgb is not RandomForestClassifier and pos_weight is not None and pos_weight > 0:
        # Dynamically scale positive-class weight to the observed imbalance (neg / pos).
        xgb_kwargs["scale_pos_weight"] = round(float(pos_weight), 3)
    lgbm_balanced = {"class_weight": "balanced", "random_state": 42}

    if task == "churn":
        return {
            "logistic_regression": LogisticRegression(max_iter=1000, class_weight="balanced"),
            "random_forest": RandomForestClassifier(n_estimators=180, class_weight="balanced", random_state=42),
            "xgboost": xgb(**xgb_kwargs) if xgb is not RandomForestClassifier else xgb(random_state=42),
            "lightgbm": lgbm(**lgbm_balanced) if lgbm is not RandomForestClassifier else lgbm(random_state=42),
        }
    if task == "default":
        cat_kwargs = {"verbose": False, "random_seed": 42, "auto_class_weights": "Balanced"} if catboost is not RandomForestClassifier else {"random_state": 42}
        return {
            "xgboost": xgb(**xgb_kwargs) if xgb is not RandomForestClassifier else xgb(random_state=42),
            "catboost": catboost(**cat_kwargs) if catboost is not RandomForestClassifier else catboost(random_state=42),
            "random_forest": RandomForestClassifier(n_estimators=220, class_weight="balanced", random_state=42),
        }
    if task == "fraud":
        return {
            "isolation_forest": IsolationForest(contamination=0.04, random_state=42),
            "xgboost": xgb(**xgb_kwargs) if xgb is not RandomForestClassifier else xgb(class_weight="balanced", random_state=42),
            "lightgbm": lgbm(**lgbm_balanced) if lgbm is not RandomForestClassifier else lgbm(random_state=42),
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
                    # Over-sample the minority class to 25% of the majority count, then
                    # under-sample the majority to a 1:2 minority:majority ratio. Fixed
                    # resampling ratios avoid excessive synthetic noise on very sparse
                    # classes (e.g. fraud ~2-3% positives).
                    ("smote", SMOTE(sampling_strategy=0.25, random_state=42)),
                    ("under", RandomUnderSampler(sampling_strategy=0.50, random_state=42)),
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


def tune_threshold(y_true, y_score, cost_fn: float = 0.0, cost_fp: float = 0.0) -> float:
    """Pick a decision threshold.

    When a business cost matrix is supplied (cost_fn/cost_fp > 0), minimize total
    cost = FN*cost_fn + FP*cost_fp over a fine precision/recall grid. Otherwise
    fall back to F1-maximizing threshold search.
    """
    if cost_fn > 0 or cost_fp > 0:
        return _tune_threshold_cost_aware(y_true, y_score, cost_fn, cost_fp)
    thresholds = np.arange(0.1, 0.91, 0.02)
    scores = [(thr, f1_score(y_true, np.asarray(y_score) >= thr, zero_division=0)) for thr in thresholds]
    return float(max(scores, key=lambda item: item[1])[0])


def _tune_threshold_cost_aware(y_true, y_score, cost_fn: float, cost_fp: float) -> float:
    y_score = np.asarray(y_score)
    precisions, recalls, thresholds = precision_recall_curve(y_true, y_score)
    total_positives = float(np.sum(y_true))
    total_negatives = len(y_true) - total_positives

    tp = recalls * total_positives
    fn = total_positives - tp
    fp = np.where(precisions > 0, (tp / precisions) - tp, 0.0)

    costs = (fn * cost_fn) + (fp * cost_fp)
    best_idx = int(np.argmin(costs))
    if best_idx < len(thresholds):
        return float(thresholds[best_idx])
    # precision_recall_curve emits one extra all-positive point; fall back to 0.5.
    return 0.5


def _threshold_costs(task: str) -> dict:
    if task == "fraud":
        return {"cost_fn": DEFAULT_COST_FN, "cost_fp": DEFAULT_COST_FP}
    return {}


def _estimator_scores(pipeline: Pipeline, estimator, x) -> np.ndarray:
    if isinstance(estimator, IsolationForest):
        raw = pipeline.decision_function(x)
        return 1 - ((raw - raw.min()) / max(raw.max() - raw.min(), 1e-9))
    return pipeline.predict_proba(x)[:, 1]


def _estimator_key(estimator) -> str | None:
    name = type(estimator).__name__.lower()
    if "xgboost" in name or "xgb" in name:
        return "xgboost"
    if "lightgbm" in name or "lgbm" in name:
        return "lightgbm"
    if "catboost" in name:
        return "catboost"
    if "randomforest" in name:
        return "random_forest"
    if "logisticregression" in name:
        return "logistic_regression"
    return None


def tune_winner_model(pipeline, x_train, y_train, n_iter: int = 6, cv: int = 3):
    """RandomizedSearchCV over the winning candidate's hyperparameter grid.

    Best-effort: returns ``None`` (keep the untuned pipeline) if the search fails.
    """
    estimator = pipeline.named_steps["model"]
    key = _estimator_key(estimator)
    grid = PARAM_GRIDS.get(key)
    if grid is None or not grid:
        return None
    param_grid = {f"model__{k}": v for k, v in grid.items()}
    search = RandomizedSearchCV(
        pipeline,
        param_grid,
        scoring="roc_auc",
        cv=cv,
        n_iter=n_iter,
        random_state=42,
        n_jobs=1,
        error_score="raise",
    )
    try:
        search.fit(x_train, y_train)
    except Exception as exc:  # best-effort tuning; keep the pre-tune pipeline
        print(f"  [tuning] hyperparameter search failed for {key}: {exc}")
        return None
    return search.best_estimator_


def train_candidates(
    task: str,
    df: pd.DataFrame,
    spec: FeatureSpec,
    output_dir: str = "models/artifacts",
    n_splits: int = 5,
    tune_winner: bool = True,
    tune_iter: int = 6,
    tune_cv: int = 3,
    time_col: str | None = None,
) -> dict:
    x = df[spec.all_features]
    y = df[spec.target].astype(int)

    if time_col is not None and time_col in df.columns:
        # Chronological split for time-series features (fraud velocity): the test set
        # is the most recent 20% of the stream, so every test feature only ever sees
        # past transactions. Falls back to a stratified random split if either side
        # is missing a class.
        frame_sorted = df.sort_values(time_col)
        split_at = max(2, int(len(frame_sorted) * 0.8))
        x_train = frame_sorted.iloc[:split_at][spec.all_features]
        x_test = frame_sorted.iloc[split_at:][spec.all_features]
        y_train = frame_sorted.iloc[:split_at][spec.target].astype(int)
        y_test = frame_sorted.iloc[split_at:][spec.target].astype(int)
        if y_train.nunique() < 2 or y_test.nunique() < 2:
            stratify = y if y.nunique() == 2 and y.value_counts().min() >= 2 else None
            x_train, x_test, y_train, y_test = train_test_split(
                x, y, test_size=0.2, random_state=42, stratify=stratify
            )
    else:
        stratify = y if y.nunique() == 2 and y.value_counts().min() >= 2 else None
        x_train, x_test, y_train, y_test = train_test_split(
            x, y, test_size=0.2, random_state=42, stratify=stratify
        )

    min_class = int(y_train.value_counts().min()) if y_train.nunique() >= 2 else 1
    splits = n_splits if min_class >= n_splits else max(2, min_class)
    use_cv = min_class >= 2

    pos_weight = None
    if task == "fraud" and y_train.nunique() == 2:
        negatives = int((y_train == 0).sum())
        positives = int((y_train == 1).sum())
        pos_weight = negatives / max(positives, 1)

    results = []
    best = None
    best_score = -1.0

    for name, estimator in candidate_models(task, pos_weight=pos_weight).items():
        started = time.time()
        pipeline = build_training_pipeline(task, spec, estimator)
        is_iso = isinstance(estimator, IsolationForest)
        cv_roc_auc = None

        if use_cv and splits >= 2 and not is_iso:
            # Stratified k-fold cross-validation tournament: evaluate each candidate
            # on out-of-fold predictions to reduce variance from a single split.
            oof = np.zeros(len(x_train), dtype=float)
            skf = StratifiedKFold(n_splits=splits, shuffle=True, random_state=42)
            for tr_idx, va_idx in skf.split(x_train, y_train):
                fold_pipe = clone(pipeline)
                fold_pipe.fit(x_train.iloc[tr_idx], y_train.iloc[tr_idx])
                oof[va_idx] = _estimator_scores(fold_pipe, estimator, x_train.iloc[va_idx])
            try:
                cv_roc_auc = round(float(roc_auc_score(y_train, oof)), 4)
            except ValueError:
                cv_roc_auc = None

        if is_iso:
            pipeline.fit(x_train)
        else:
            pipeline.fit(x_train, y_train)
        y_score = _estimator_scores(pipeline, estimator, x_test)
        threshold = tune_threshold(y_test, y_score, **_threshold_costs(task))
        metrics = evaluate_binary(y_test, y_score, threshold)
        if cv_roc_auc is not None:
            metrics["cv_roc_auc"] = cv_roc_auc
        metrics["training_seconds"] = round(time.time() - started, 2)
        row = {"task": task, "algorithm": name, **metrics}
        results.append(row)

        select_score = cv_roc_auc if cv_roc_auc is not None else metrics["roc_auc"]
        if select_score > best_score:
            best_score = select_score
            best = (name, pipeline, threshold, metrics)

    if best is None:
        raise RuntimeError(f"No model candidates trained for {task}")

    best_name, best_pipeline, threshold, best_metrics = best

    # Final hyperparameter search on the winning architecture before serialization.
    tuned = False
    cv_before = best_metrics.get("cv_roc_auc")
    training_seconds_before = best_metrics.get("training_seconds")
    if tune_winner and not isinstance(best_pipeline.named_steps["model"], IsolationForest):
        tune_started = time.time()
        tuned_pipeline = tune_winner_model(best_pipeline, x_train, y_train, n_iter=tune_iter, cv=tune_cv)
        if tuned_pipeline is not None:
            best_pipeline = tuned_pipeline
            y_score = _estimator_scores(best_pipeline, best_pipeline.named_steps["model"], x_test)
            threshold = tune_threshold(y_test, y_score, **_threshold_costs(task))
            best_metrics = evaluate_binary(y_test, y_score, threshold)
            if cv_before is not None:
                best_metrics["cv_roc_auc"] = cv_before
            if training_seconds_before is not None:
                best_metrics["training_seconds"] = training_seconds_before
            best_metrics["tuning_seconds"] = round(time.time() - tune_started, 2)
            tuned = True

    metadata = {
        "name": f"finsight_{task}",
        "task": task,
        "algorithm": best_name,
        "version": "2.0.0",
        "threshold": threshold,
        "metrics": best_metrics,
        "features": spec.all_features,
        "target": spec.target,
        "pipeline": {
            "cross_validation": f"{splits}-fold stratified" if use_cv else "single split",
            "resampling": "smote:0.25 + random_under:0.50" if task in {"default", "fraud"} else "none",
            "scale_pos_weight": pos_weight if task == "fraud" and pos_weight is not None else None,
            "hyperparameter_tuning": tuned,
            "threshold_policy": "cost_aware" if task == "fraud" else "f1",
        },
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
