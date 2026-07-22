# System Architecture

This document explains how the components of FinSight fit together.

## Component Map

Airflow handles all data movement. PostgreSQL is the central store that everything reads from or writes to. Power BI reads from PostgreSQL directly. MLflow tracks training runs. FastAPI serves model predictions. Streamlit is a UI layer on top of the API.

```
Airflow (ETL + ML training)
    |
    v
PostgreSQL (data warehouse)
    |
    +----> Power BI (dashboards)
    |
    +----> FastAPI (inference API)
                |
                +----> Streamlit (ML workbench)

MLflow tracks all training runs and registers models.
```

## Airflow

The DAG `finsight_local_pipeline` runs at 2:00 AM daily.

```
start
 ├── etl_churn    (7,043 rows)   --+
 ├── etl_lending  (50,000 rows)  --+--> check_metadata --> generate_features --> train_models --> load_training_metadata --> end
 └── etl_fraud    (50,000 rows)  --+
```

The three ETL tasks run in parallel. The rest of the pipeline is sequential.

| Task | What it does |
|------|-------------|
| `etl_churn` | Reads Telco CSV, cleans, loads into `fact_churn` |
| `etl_lending` | Reads Lending Club CSV (50K rows), loads into `fact_loan` |
| `etl_fraud` | Merges transaction and identity CSVs, loads into `fact_transaction` |
| `check_metadata` | Verifies `etl_metadata` has rows for all three completed tasks |
| `generate_features` | Aggregates all three fact tables and writes the `feature_store` |
| `train_models` | Trains XGBoost, LightGBM, CatBoost for churn, default, and fraud |
| `load_training_metadata` | Reads `metadata.json` artifacts and inserts them into `fact_model_training` |

## PostgreSQL

All components read from or write to PostgreSQL (port 5433, database `finsight`).

| Table | Written By | Read By |
|-------|-----------|---------|
| `fact_churn` | Airflow ETL | Power BI, FastAPI |
| `fact_loan` | Airflow ETL | Power BI, FastAPI |
| `fact_transaction` | Airflow ETL | Power BI, FastAPI |
| `etl_metadata` | Airflow (all tasks) | Power BI ETL Monitoring page |
| `feature_store` | Airflow `generate_features` | Power BI, ML training |
| `fact_model_training` | Airflow `load_training_metadata` | Power BI ML Monitoring page |
| `fact_prediction_monitoring` | FastAPI (every prediction) | Power BI ML Monitoring page |
| `fact_streaming_transaction` | Streaming consumer | Power BI Real-Time page |
| `vw_streaming_summary` | SQL view | Power BI |
| `vw_streaming_realtime` | SQL view | Power BI |

## MLflow

MLflow tracks every training run under three experiments: `finsight_churn`, `finsight_fraud`, `finsight_default`.

Each run logs: task name, algorithm, accuracy, precision, recall, F1, ROC-AUC, decision threshold, training time in seconds, the serialized model, and the full metadata dict.

Power BI does not connect to MLflow. Instead, Airflow saves a `metadata.json` file after training and then writes the key metrics into `fact_model_training`, which Power BI reads from PostgreSQL.

```
train_models task
    |
    +-- trains candidates, picks best by ROC-AUC
    |
    +-- saves model.joblib and metadata.json to disk
    |
    +-- logs run to MLflow (params, metrics, model artifact)
    |
load_training_metadata task
    |
    +-- reads metadata.json
    +-- inserts row into fact_model_training
    +-- Power BI reads this table
```

## Power BI

Connects to PostgreSQL in Import mode and refreshes on demand.

| Page | Key Metrics |
|------|-------------|
| Executive Overview | Customers, revenue, churn rate, default rate, fraud rate |
| Lending Analytics | Default by grade and purpose, risk exposure, approval rate |
| Fraud Analytics | Fraud by device and card type, severity, loss percentage |
| Customer Churn | Churn by contract type, revenue at risk |
| Customer Detail | Individual customer drillthrough |
| ETL Monitoring | Pipeline success rate, run duration, records processed |
| ML Monitoring | Predictions per model, confidence, latency, fallback rate |
| Real-Time Monitoring | Live transaction volume, rolling fraud rate |

## Real-Time Streaming

Separate from the batch pipeline. A producer generates fake transactions at 1-5 per second (about 3% fraud). A consumer reads from the Redis stream and writes batches to PostgreSQL.

```
Producer (1-5 txns/sec)
    |
Redis Stream (XADD finsight:transactions)
    |
Consumer (XREADGROUP, batch insert 10 records)
    |
PostgreSQL: fact_streaming_transaction
    |-- vw_streaming_summary (per-minute aggregation)
    |-- vw_streaming_realtime (5-minute rolling window)
    +-- Power BI Real-Time Monitoring page
```

## Docker Services

| Service | Port | Description |
|---------|------|-------------|
| postgres | 5433 | Data warehouse |
| redis | 6379 | Rate limiting, caching, streaming |
| airflow-webserver | 8080 | Airflow UI |
| airflow-scheduler | - | DAG scheduling |
| fastapi | 8000 | ML inference API |
| mlflow | 5000 | Experiment tracking UI |
| frontend (Streamlit) | 8501 | ML workbench |
| streaming-producer | - | Fake transaction generator |
| streaming-consumer | - | Redis to PostgreSQL writer |

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Orchestration | Apache Airflow | 2.8 |
| Data Processing | Pandas / PySpark | - |
| Storage | PostgreSQL | 16 |
| Cache and Broker | Redis | 7 |
| ML Training | scikit-learn, XGBoost, LightGBM, CatBoost | - |
| ML Tracking | MLflow | 2.9 |
| API | FastAPI | - |
| Frontend | Streamlit | - |
| BI | Power BI (PBIP / PBIR / TMDL) | - |
| Containers | Docker Compose | - |
