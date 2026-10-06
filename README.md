# FinSight: Banking Analytics Platform

End-to-end financial analytics and ML platform covering data engineering, model training, real-time inference, prediction monitoring, and dashboards.

**Stack:** Airflow, PostgreSQL, Power BI, XGBoost, LightGBM, CatBoost, FastAPI, MLflow, Docker, Streamlit, Redis Streams

## How it works

Raw CSVs go through an Airflow ETL pipeline into PostgreSQL. From there, a feature store is computed and ML models are trained. The trained models are served through a FastAPI endpoint, which Streamlit calls for interactive predictions. Power BI reads from PostgreSQL directly for dashboards.

```
CSV Datasets (3 sources, ~2.8M rows total)
  |
Apache Airflow (daily at 2am, parallel ETL tasks)
  |
PostgreSQL 16 (fact_churn, fact_loan, fact_transaction)
  |
Feature Store (composite risk score: 0.4 x fraud + 0.3 x default + 0.3 x churn)
  |
ML Training (3-4 candidates per task, 5-fold CV tournament, cost-aware threshold tuning, ROC-AUC selection)
  |
MLflow (experiment tracking, model registry, artifact store)
  |
FastAPI (HMAC auth, Redis rate limiter, prediction monitoring)
  |
Power BI (8 pages, 50+ DAX measures, TMDL semantic model)
Streamlit (10 pages: executive & business intelligence, ML diagnostics, real-time predictors, batch scoring)

Redis Streams -> Producer -> Consumer -> fact_streaming_transaction -> Power BI Real-Time page
```

## Quick Start

```bash
# One command (PowerShell)
.\scripts\bootstrap.ps1

# Or manually:
docker compose -f docker/docker-compose.yml -f docker/docker-compose.local.yml up -d

python etl/scripts/run_local_etl.py --source churn
python etl/scripts/run_local_etl.py --source lending --sample 50000
python etl/scripts/run_local_etl.py --source fraud   --sample 50000
python etl/scripts/feature_store.py

python -m models.train_all --task all --max-rows 150000 --log-mlflow
python etl/scripts/load_model_training.py

# Launch interactive dashboards & predictors
streamlit run streamlit/app.py

# Open FinSight/FinSight.pbip in Power BI Desktop
```

See [docs/setup_runbook.md](docs/setup_runbook.md) for detailed setup and troubleshooting.

## Module Documentation

| Module | README | Covers |
|---|---|---|
| Data Engineering | [etl/README.md](etl/README.md) | Airflow DAG, Pandas/PySpark ETL, feature store |
| Data Warehouse | [sql/README.md](sql/README.md) | Star schema, ER diagram, table definitions |
| Machine Learning | [models/README.md](models/README.md) | Training pipeline, MLflow, SMOTE, threshold tuning |
| API | [api/README.md](api/README.md) | FastAPI endpoints, auth, rate limiting, monitoring |
| Streaming | [streaming/README.md](streaming/README.md) | Redis Streams producer/consumer |
| Power BI | [FinSight/README.md](FinSight/README.md) | Semantic model, DAX measures, dashboard pages |
| Streamlit | [streamlit/README.md](streamlit/README.md) | 10 pages: business intelligence, model diagnostics, live predictors, batch scoring |
| Infrastructure | [docker/README.md](docker/README.md) | Docker Compose services and ports |

## Data Sources

| Dataset | Records | Source | Used For |
|---------|---------|--------|----------|
| IBM Telco Churn | 7,043 | IBM | Customer churn prediction |
| Lending Club | 2.2M, sampled to 50K | Kaggle | Loan default prediction |
| IEEE-CIS Fraud | 590K, sampled to 50K | Kaggle/IEEE | Fraud detection |

## ML Models

| Task | Algorithm | ROC-AUC (test) | ROC-AUC (CV) | Decision Threshold |
|------|-----------|----------------|--------------|-------------------|
| Customer Churn | Logistic Regression | 0.839 | 0.844 | 0.32 |
| Loan Default | CatBoost | 0.701 | 0.699 | 0.52 |
| Fraud Detection | XGBoost | 0.857 | 0.904 | 0.72 |

Per task, 3-4 candidate algorithms compete in a 5-fold stratified cross-validation tournament and the winner is selected by out-of-fold ROC-AUC, then refined with a `RandomizedSearchCV` hyperparameter search. Churn and default thresholds maximize F1; the fraud threshold uses a cost-aware objective (FN=$500 vs FP=$15).

**Overfitting reduction:** churn and default rely on the CV tournament plus winner tuning (train ≈ CV ≈ test, gap ≤ 1 pt). Fraud adds a causal chronological split (`velocity_cutoff_dt` so training features can never see the future), regularized XGBoost (`min_child_weight`, `gamma`, `reg_lambda`, `n_estimators` capped at 300), and full-scale training on all 590k rows — train 0.914 ≈ CV 0.904, so its residual train↔test gap (~5.7 pts) is temporal drift, not overfit.

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET/POST | `/health` | No | Health check |
| POST | `/predict/churn` | Yes | Churn prediction |
| POST | `/predict/default` | Yes | Loan default prediction |
| POST | `/predict/fraud` | Yes | Fraud detection |
| POST | `/metrics` | No | Model health per task |
| GET | `/powerbi/prediction-monitoring` | No | Live stats for Power BI |

Middleware: HMAC auth on `/predict/*`, Redis sliding-window rate limiter (100 req/min), prediction logging to PostgreSQL, GZip compression.

## Power BI Dashboard

![Executive Overview](screenshots/pbi_01_executive_overview.jpg)

| Page | What it shows |
|------|--------------|
| Executive Overview | Total customers, churn rate, default rate, fraud rate, revenue |
| Lending Analytics | Default by grade, loan volume, risk exposure |
| Fraud Analytics | Fraud by device and card type, transaction volume, loss percentage |
| Customer Churn | Churn by contract type, revenue at risk, retention rate |
| Customer Detail | Individual customer drillthrough with full risk profile |
| ETL Monitoring | Pipeline run history, success rate, records processed |
| ML Monitoring | Predictions per model, average confidence, latency, fallback rate |
| Real-Time Monitoring | Live transaction volume, rolling fraud rate, recent alerts |

Semantic model: 13 tables (6 fact, 2 dimension, 2 ML monitoring, 3 streaming), connected via PostgreSQL in Import mode.

## Streamlit Analytics & ML Workbench

The Streamlit application (`http://localhost:8501`) provides an interactive interface for both business stakeholders and ML engineers. It bridges warehouse data and live model inference into 10 question-driven pages:

### 1. Business Intelligence & Strategic Decision Dashboards

Each business dashboard frames data around high-impact executive questions, calculates financial exposure, and provides concrete operational answers:

#### Executive Summary: Cross-Vertical Risk Exposure
> **Business Question:** *Where is the financial institution exposed across churn, credit default, fraud, and data pipeline health, and where should leadership act first?*

Provides a unified KPI banner across all banking domains, paired with a prioritized action list highlighting specific loss drivers (e.g. month-to-month contracts driving 48% churn, Grade C loans representing majority credit losses, and suspicious domain transaction clusters).

![Streamlit Executive Summary](screenshots/streamlit_01_executive_summary.png)

#### Customer Churn & Retention Analytics
> **Business Question:** *Who leaves, how much recurring revenue is lost, and which accounts should retention teams call?*

Analyzes churn rate (32.2%), customer departures (1,609), and annual lost revenue ($1.23M). Breaks down risk across contract types (Month-to-month contracts churn at 48% vs 13.6% for annual commitments), payment methods, and internet service types, generating high-priority customer outreach targets.

![Streamlit Customer Churn](screenshots/streamlit_02_churn_retention.png)

#### Lending Portfolio Risk & Default Pricing
> **Business Question:** *Where is credit capital at risk, and are loan interest rates priced high enough to cover expected losses?*

Monitors $43.57M in defaulted principal across 20,000 active loans. Evaluates default velocity across borrower credit grades (A through G), debt-to-income tiers, and verification status to ensure lending interest margins cover loss-given-default.

![Streamlit Lending Risk](screenshots/streamlit_03_lending_risk.png)

#### Transaction Fraud Detection & Operations
> **Business Question:** *Where are fraud losses clustering, and can fraud operations teams handle the alert workload?*

Tracks $156,021 in net fraud exposure across 30,000 transactions (4.0% fraud rate). Identifies risk concentration across device categories, browser types, card brands, and suspicious email domains, with threshold controls to balance precision against analyst review capacity.

![Streamlit Fraud Analysis](screenshots/streamlit_04_fraud_analysis.png)

#### Data Health & ETL Pipeline Reliability
> **Business Question:** *Are the data pipelines feeding models and executive reports reliable, fast, and healthy?*

Monitors 60 pipeline runs across 12.5M ingested records with a 91.7% success rate. Features dual-axis run duration vs. success rate tracking and granular failure rate breakdowns across warehouse tables (`fact_churn`, `fact_loan`, `fact_transaction`).

![Streamlit Data Health](screenshots/streamlit_05_data_health.png)

---

### 2. Machine Learning Operations & Real-Time Predictors

#### Model Diagnostic Performance & Holdout Calibration
Evaluates deployed models on strictly held-out test splits with validation-fitted decision thresholds and probability calibration. Features interactive inspection of ROC/PR curves, confusion matrices, calibration reliability diagrams, feature importances, and 5-fold CV tournament leaderboards.

![Streamlit Model Performance](screenshots/streamlit_06_model_performance.png)

#### Interactive Real-Time Predictors
Business users and loan officers can test hypothetical scenarios through live forms that hit authenticated FastAPI endpoints (`/predict/*`) in real time, returning calibrated probabilities, dynamic risk gauges, threshold comparisons, and key feature drivers:

| Task | Model | Live Output & Capabilities |
|------|-------|----------------------------|
| **Customer Churn** | Logistic Regression | Evaluates tenure, charges, contract type, and add-on services with probability gauge, risk classification, and decision threshold (0.32). |
| **Loan Default** | CatBoost | Assesses FICO score (300-900), debt ratio, loan principal, and borrower income with calibrated probability and risk tier (52% threshold). |
| **Fraud Detection** | XGBoost | Real-time transaction scoring by amount, device type, card type, browser, email domain, and 1h/24h velocity features (72% cost-tuned threshold). |

![Streamlit Churn Predictor](screenshots/streamlit_07_churn_predictor.png)

![Streamlit Loan Default Predictor](screenshots/streamlit_08_loan_default_predictor.png)

![Streamlit Fraud Predictor](screenshots/streamlit_09_fraud_predictor.png)

#### High-Throughput Batch Scoring
Enables batch evaluation of up to 5,000 records at a time by uploading a CSV. Displays real-time progress, error validation, prediction distribution histograms, and downloadable scored CSV files.

![Streamlit Batch Scoring](screenshots/streamlit_10_batch_scoring.png)

## Feature Store

Computed daily from all three fact tables and written to the `feature_store` table.

| Feature | Source | Current Value |
|---------|--------|---------------|
| Churn Rate | fact_churn | 26.54% |
| Default Rate | fact_loan | 18.06% |
| Fraud Rate | fact_transaction | 2.71% |
| Composite Risk Score | Weighted | 0.1446 |

Formula: `composite_risk_score = 0.40 * fraud_rate + 0.30 * default_rate + 0.30 * churn_rate`

## Services

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.local.yml up -d
```

| Service | URL |
|---------|-----|
| PostgreSQL | localhost:5433 |
| Redis | localhost:6379 |
| Airflow | localhost:8080 |
| FastAPI | localhost:8000 |
| MLflow | localhost:5000 |
| Streamlit | localhost:8501 |

## Project Structure

```
FinSight/
├── airflow/dags/
│   ├── finsight_local_pipeline.py     # Pandas ETL + ML training DAG
│   └── finsight_pipeline.py           # Extended DAG definition
├── api/
│   ├── main.py                        # FastAPI application
│   ├── monitoring.py                  # Prediction logging
│   └── middleware/                    # Auth and rate limiting
├── docker/                            # Dockerfiles and Compose configs
├── etl/scripts/
│   ├── run_local_etl.py               # Pandas ETL for all three sources
│   ├── pyspark_pipeline.py            # PySpark ETL
│   └── feature_store.py               # Feature store generation
├── models/
│   ├── artifacts/                     # model.joblib and metadata.json per task
│   ├── common/                        # Feature engineering, training, registry
│   └── train_all.py                   # Training entry point
├── streaming/                         # Redis Streams producer and consumer
├── sql/warehouse/                     # Schema DDL files
├── streamlit/app.py                   # ML Workbench
├── scripts/                           # Bootstrap, download, prepare scripts
├── FinSight/                          # Power BI project (TMDL + PBIR)
└── docs/                              # Architecture and setup docs
```

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Orchestration | Apache Airflow 2.8 |
| Data Processing | Pandas / PySpark |
| Storage | PostgreSQL 16 |
| Cache and Streaming | Redis 7 |
| ML Training | scikit-learn, XGBoost, LightGBM, CatBoost |
| ML Tracking | MLflow 2.9 |
| API | FastAPI |
| Frontend | Streamlit |
| BI | Power BI (PBIP / PBIR / TMDL) |
| Containers | Docker Compose |
