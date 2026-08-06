# FinSight — Setup Runbook

Step-by-step guide to run FinSight from scratch to a fully operational platform.

---

## Quick Start (One Command)

```powershell
.\scripts\bootstrap.ps1
```

This runs everything automatically. See [Manual Steps](#manual-steps) if you prefer control.

---

## Prerequisites

| Requirement | Version | Check |
|-------------|---------|-------|
| Docker Desktop | Latest | `docker version` |
| Python | 3.11+ | `python --version` |
| pip packages | See below | `pip list` |
| PostgreSQL client | Optional | `psql --version` |

Install Python dependencies:

```powershell
pip install pandas numpy scikit-learn==1.6.1 lightgbm catboost xgboost imbalanced-learn joblib fastapi uvicorn pydantic redis httpx mlflow psycopg2-binary sqlalchemy
```

---

## Manual Steps

### Step 1: Configure Environment

Copy the example environment file and fill in your values:

```powershell
Copy-Item .env.example .env
# Edit .env with your local credentials
```

See `.env.example` for all required variables.

### Step 2: Start Infrastructure

```powershell
docker compose -f docker/docker-compose.yml -f docker/docker-compose.local.yml up -d --build
```

Wait for all services to be healthy (~60s):

```powershell
docker ps --format "table {{.Names}}\t{{.Status}}"
```

Expected output:

```
finsight-frontend      Up (healthy)
finsight-api           Up (healthy)
finsight-mlflow        Up
finsight-webserver     Up
finsight-scheduler     Up
finsight-postgres      Up (healthy)
finsight-redis         Up (healthy)
```

### Step 3: Verify Database

```powershell
# DB credentials are read from your .env file
psql -h localhost -p 5433 -U $env:DB_USER -d finsight -c "\dt public.*"
```

Expected: 7 tables

```
                List of relations
 Schema |        Name         | Type  |    Owner
--------+---------------------+-------+-------------
 public | etl_metadata        | table | finsight_user
 public | fact_churn          | table | finsight_user
 public | fact_loan           | table | finsight_user
 public | fact_model_training | table | finsight_user
 public | fact_prediction_monitoring | table | finsight_user
 public | fact_transaction    | table | finsight_user
 public | feature_store       | table | finsight_user
```

### Step 4: Run ETL

**Option A — Via Airflow (recommended):**

1. Open http://localhost:8080 and log in with the credentials set in your `.env` file
2. Find `finsight_local_pipeline` DAG
3. Click ▶ to trigger manually
4. Wait for all tasks to turn green (~2–5 min)

**Option B — Direct (faster for first run):**

```powershell
python etl/scripts/run_local_etl.py --source churn
python etl/scripts/run_local_etl.py --source lending --sample 50000
python etl/scripts/run_local_etl.py --source fraud --sample 50000
python etl/scripts/feature_store.py
```

**Verify ETL:**

```powershell
psql -h localhost -p 5433 -U $env:DB_USER -d finsight -c "
  SELECT 'fact_churn' AS tbl, count(*) FROM fact_churn
  UNION ALL SELECT 'fact_loan', count(*) FROM fact_loan
  UNION ALL SELECT 'fact_transaction', count(*) FROM fact_transaction
  UNION ALL SELECT 'feature_store', count(*) FROM feature_store;"
```

Expected: ~7043 + 50000 + 50000 + 1 = 107,044 rows

### Step 5: Train Models

```powershell
python -m models.train_all --task all --max-rows 150000 --log-mlflow
```

Expected output:

```
churn: logistic_regression ROC-AUC=0.8391
default: catboost ROC-AUC=0.7006
fraud: xgboost ROC-AUC=0.8572
```

Artifacts saved to `models/artifacts/{churn,default,fraud}/`

### Step 6: Load Training Metadata

```powershell
python etl/scripts/load_model_training.py
```

**Verify:**

```powershell
psql -h localhost -p 5433 -U $env:DB_USER -d finsight -c "
  SELECT model_name, algorithm, accuracy, roc_auc, f1_score
  FROM fact_model_training ORDER BY roc_auc DESC;"
```

Expected: 3 rows

### Step 7: Test API

```powershell
# Health check (no auth required)
curl http://localhost:8000/health

# Churn prediction (requires API key from .env)
curl -X POST http://localhost:8000/predict/churn `
  -H "Content-Type: application/json" `
  -H "X-API-Key: $env:API_KEY" `
  -d '{"tenure":12,"monthly_charges":85.5,"total_charges":1026,"contract_type":"Month-to-month","payment_method":"Electronic check","internet_service":"Fiber optic"}'

# Model health metrics
curl http://localhost:8000/metrics
```

### Step 8: Open Power BI

1. Open `FinSight/FinSight.pbip` in Power BI Desktop
2. Click **Transform Data** to verify all 10 tables load
3. Navigate to each page:
   - Executive Overview
   - Lending Analytics
   - Fraud Analytics
   - Customer Churn
   - Customer Detail
   - ETL Monitoring
   - ML Monitoring

---

## Service URLs

| Service | URL | Auth |
|---------|-----|------|
| API | http://localhost:8000 | `X-API-Key` header (set in `.env`) |
| MLflow | http://localhost:5000 | None |
| Airflow | http://localhost:8080 | Credentials set in `.env` |
| Streamlit | http://localhost:8501 | None |
| PostgreSQL | localhost:5433 | Credentials set in `.env` |

> All credentials are configured via the `.env` file. See `.env.example` for the required variables.

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `docker compose up` fails | Port conflict | Kill process on port: `netstat -ano \| findstr :5433` |
| Airflow init fails | DB not ready | Wait 30s, retry: `docker compose ... up airflow-init` |
| ETL fails: "relation does not exist" | Schema not created | Restart postgres: `docker compose ... restart postgres` |
| Training fails: "No module named models" | PYTHONPATH wrong | Run from project root: `cd D:\FinSight` |
| API returns 401 | Missing or incorrect API key | Set `X-API-Key` header to value from your `.env` |
| Power BI: "date" error in TMDL | Invalid DataType | Ensure `feature_store.tmdl` uses `dateTime` not `date` |
| MLflow: DNS rebinding error | localhost inside Docker | Use container hostname: `http://finsight-mlflow:5000` |

---

## Reset / Teardown

```powershell
# Stop everything
docker compose -f docker/docker-compose.yml -f docker/docker-compose.local.yml down -v

# Full reset (also removes trained models)
docker compose -f docker/docker-compose.yml -f docker/docker-compose.local.yml down -v --remove-orphans
Remove-Item -Recurse -Force models\artifacts\churn, models\artifacts\default, models\artifacts\fraud
```

---

## Bootstrap Script Options

```powershell
# Full run (default)
.\scripts\bootstrap.ps1

# Skip training (if models already exist)
.\scripts\bootstrap.ps1 -SkipTraining

# Skip ETL (if data already loaded)
.\scripts\bootstrap.ps1 -SkipETL

# Full reset + rebuild
.\scripts\bootstrap.ps1 -Reset

# Custom timeout
.\scripts\bootstrap.ps1 -MaxWaitSeconds 300
```
