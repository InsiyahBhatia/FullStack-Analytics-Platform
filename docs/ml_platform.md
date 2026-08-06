# FinSight ML Platform

FinSight is now structured as an end-to-end financial analytics and machine learning platform:

```mermaid
flowchart LR
    CSV["CSV datasets"] --> Spark["PySpark ETL"]
    Spark --> Postgres["PostgreSQL warehouse"]
    Postgres --> Features["Feature engineering"]
    Features --> Train["ML training pipelines"]
    Train --> MLflow["MLflow tracking and registry"]
    Train --> Artifacts["Local model artifacts"]
    MLflow --> API["FastAPI inference layer"]
    Artifacts --> API
    API --> Streamlit["Streamlit workbench"]
    API --> PowerBI["Power BI dashboard"]
    API --> Monitor["Prediction monitoring"]
```

## Models

| Task | Target | Algorithms | Metrics |
|---|---|---|---|
| Customer churn | `churn_flag` | Logistic Regression, Random Forest, XGBoost, LightGBM | Accuracy, Precision, Recall, F1, ROC-AUC |
| Loan default | `default_flag` | XGBoost, CatBoost, Random Forest | Precision, Recall, F1, ROC-AUC |
| Fraud detection | `is_fraud` | Isolation Forest, XGBoost, LightGBM | Precision, Recall, F1, ROC-AUC |

## Feature Engineering

Churn:
- `tenure`
- `monthly_charges`
- `total_charges`
- `contract_type`
- `payment_method`
- `internet_service`

Loans:
- `fico_score`
- `debt_ratio`
- `loan_amount`
- `grade`
- `purpose`

Fraud:
- `transaction_amt`
- `device_type`
- `card_type`
- `browser`
- `email_domain`

## Training

Run all models:

```bash
python -m models.train_all --task all --max-rows 150000
```

Run one model:

```bash
python -m models.train_all --task churn
python -m models.train_all --task default
python -m models.train_all --task fraud
```

Log to MLflow:

```bash
python -m models.train_all --task all --log-mlflow
```

Artifacts are written to:

```text
models/artifacts/
  churn/model.joblib
  default/model.joblib
  fraud/model.joblib
```

## Explainability

Generate SHAP artifacts:

```bash
python -m models.explain --task churn
python -m models.explain --task default
python -m models.explain --task fraud
```

Expected artifacts:

- `summary_plot.png`
- `waterfall_plot.png`
- `dependence_plot.png`
- `feature_importance.csv`

## API

Endpoints:

- `POST /predict/churn`
- `POST /predict/default`
- `POST /predict/fraud`
- `GET /health`
- `POST /health`
- `POST /metrics`

Example:

```json
{
  "tenure": 12,
  "monthly_charges": 100,
  "total_charges": 1200,
  "contract_type": "Month-to-month",
  "payment_method": "Electronic check",
  "internet_service": "Fiber optic"
}
```

Response:

```json
{
  "prediction": "Will Churn",
  "probability": 0.93,
  "model": "finsight_churn",
  "model_version": "1.0.0",
  "top_drivers": ["contract_type", "monthly_charges", "tenure"],
  "inference_ms": 12,
  "fallback": false
}
```

## MLOps

Implemented:

- MLflow experiment tracking
- Model metadata
- Local artifact registry
- Optional MLflow model registration
- Metrics logging
- Parameters logging
- SHAP explainability artifacts
- Prediction monitoring SQL view

## Class Imbalance Strategy

Fraud and default datasets are imbalanced. The pipeline implements:

- Calibrated resampling via `imblearn`: SMOTE (minority up-sampled to 25% of majority) then `RandomUnderSampler` (1:2 minority:majority ratio).
- Dynamic class weighting: XGBoost `scale_pos_weight = neg/pos` (fraud), LightGBM `class_weight="balanced"`, CatBoost `auto_class_weights="Balanced"`.
- Cost-aware threshold tuning for fraud (FN=$500 vs FP=$15, via `precision_recall_curve`); F1 grid for churn and default.

## Success Criteria

Target benchmark goals:

- Churn ROC-AUC greater than 0.85
- Default ROC-AUC greater than 0.85
- Fraud ROC-AUC greater than 0.90

Actual results (v2 pipeline, artifacts in `models/artifacts/`):

| Task | Algorithm | ROC-AUC (test) | ROC-AUC (CV) | Train/Test gap | Overfitting reduced by |
|---|---|---:|---:|---:|---|
| Churn | Logistic Regression | 0.839 | 0.844 | +0.007 | 5-fold stratified CV tournament + winner tuning (train ≈ CV ≈ test) |
| Loan default | CatBoost | 0.701 | 0.699 | +0.008 | 5-fold CV tournament, calibrated SMOTE/undersampling, winner hyperparameter search |
| Fraud | XGBoost | 0.857 | 0.904 | +0.057 (drift) | Causal chronological split (`velocity_cutoff_dt`), regularized XGBoost (`min_child_weight`, `gamma`, `reg_lambda`, `n_estimators` ≤ 300), all 590k rows |

Actual metrics are written to:

```text
models/artifacts/churn_benchmarks.csv
models/artifacts/default_benchmarks.csv
models/artifacts/fraud_benchmarks.csv
```
