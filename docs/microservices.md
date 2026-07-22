# FinSight — Microservice Communication Design

## Service Map

```
┌────────────────────┐        HTTP/REST         ┌───────────────────────┐
│                    │◀─────────────────────────▶│                       │
│   Streamlit UI     │                           │  Power BI Gateway     │
│   (8501)           │                           │  (DirectQuery)        │
└────────┬───────────┘                           └─────────┬─────────────┘
         │                                                 │
         │ HTTP                                     SQL/TDS│
         ▼                                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    API Gateway / ALB (HTTPS :443)                     │
│                                                                      │
│  Routes:                                                             │
│  /predict/fraud    → fastapi:8000                                    │
│  /predict/churn    → fastapi:8000                                    │
│  /predict/default  → fastapi:8000                                    │
│  /dashboard/*      → fastapi:8000                                    │
│  /reports/*        → fastapi:8000                                    │
│  /features/*       → fastapi:8000                                    │
└──────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        FastAPI Service                               │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │  Auth        │  │  Rate Limit  │  │  Request Log │               │
│  │  Middleware   │  │  Middleware   │  │  Middleware   │               │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘               │
│         │                 │                 │                        │
│  ┌──────▼─────────────────▼─────────────────▼───────────────────┐   │
│  │                    Router Layer                                │   │
│  │  /predict  │  /dashboard  │  /reports  │  /features           │   │
│  └──────────────────────────┬────────────────────────────────────┘   │
│                              │                                        │
│  ┌──────────────────────────▼────────────────────────────────────┐   │
│  │                    Service Layer                                │   │
│  │                                                                 │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │   │
│  │  │  FraudService │  │  LoanService │  │  ChurnService│         │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │   │
│  │         │                 │                 │                  │   │
│  │  ┌──────▼─────────────────▼─────────────────▼──────┐          │   │
│  │  │         ModelRegistry (MLflow Client)            │          │   │
│  │  └────────────────────┬────────────────────────────┘          │   │
│  └───────────────────────┼────────────────────────────────────────┘   │
│                          │                                            │
└──────────────────────────┼────────────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  PostgreSQL RDS │ │  Redis Cache    │ │  S3 (Artifacts) │
│  (Warehouse)     │ │  (TTL: 1h)     │ │  (PDF Reports)  │
│  Port: 5432      │ │  Port: 6379    │ │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

## Communication Protocols

| Interaction                   | Protocol        | Data Format | Sync/Async |
|-------------------------------|-----------------|-------------|------------|
| UI → FastAPI                  | HTTP/1.1        | JSON        | Sync       |
| Power BI → RDS                | TDS (SQL)       | Tabular     | Sync       |
| FastAPI → PostgreSQL          | libpq           | Binary      | Sync       |
| FastAPI → Redis               | RESP            | String      | Sync       |
| FastAPI → MLflow              | HTTP/REST       | JSON        | Sync       |
| FastAPI → S3                  | S3 API (HTTPS)  | Binary      | Async      |
| Airflow → EMR                 | EMR API (HTTPS) | JSON        | Sync       |
| EMR → S3                      | S3 API (HTTPS)  | Parquet     | Async      |
| EMR → RDS                     | JDBC            | Binary      | Sync       |
| Airflow → SNS                 | SNS API (HTTPS) | JSON        | Async      |

## API Contract Specification

### POST /predict/fraud

```json
// Request
{
  "transaction_amt": 12500.50,
  "product_cd": "W",
  "card1": 12345,
  "card2": 67890,
  "addr1": 345,
  "dist1": 2.5,
  "device_type": "mobile",
  "device_info": "iPhone15,3",
  "email_domain": "outlook.com",
  "p_email_domain": "gmail.com"
}

// Response (200)
{
  "transaction_id": "txn_abc123",
  "is_fraud": 0,
  "fraud_probability": 0.023,
  "model": "xgb_fraud_v3",
  "model_version": "3.2.1",
  "inference_ms": 45,
  "timestamp": "2026-07-15T12:30:00Z"
}

// Response (422) — validation error
{
  "detail": [
    {
      "loc": ["body", "transaction_amt"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### POST /predict/default

```json
// Request
{
  "customer_id": "CUST_001",
  "annual_income": 85000.00,
  "dti": 18.5,
  "credit_score": 720,
  "employment_length": "5 years",
  "loan_amount": 250000.00,
  "loan_purpose": "home_improvement",
  "grade": "A"
}

// Response (200)
{
  "prediction": "No Default",
  "default_probability": 0.08,
  "model": "lgbm_default_v2",
  "model_version": "2.1.0",
  "feature_importance": {
    "credit_score": 0.35,
    "dti": 0.25,
    "loan_amount": 0.20,
    "annual_income": 0.12,
    "employment_length": 0.08
  },
  "inference_ms": 32
}
```

### POST /predict/churn

```json
// Request
{
  "customer_id": "CUST_042",
  "tenure": 12,
  "monthly_charges": 89.99,
  "total_charges": 1079.88,
  "contract_type": "Month-to-month",
  "payment_method": "Electronic check",
  "internet_service": "Fiber optic",
  "online_security": "No",
  "tech_support": "No"
}

// Response (200)
{
  "churn": "Yes",
  "churn_probability": 0.87,
  "model": "rf_churn_v1",
  "top_reason": "Month-to-month contract + No tech support",
  "retention_action": "Offer annual contract + free tech support trial"
}
```

### GET /dashboard/kpis

```json
// Response (200)
{
  "total_customers": 245000,
  "loans_approved": 182000,
  "loans_rejected": 43000,
  "fraud_cases": 1247,
  "revenue": 1845000000.00,
  "churn_rate_pct": 26.5,
  "reporting_date": "2026-07-15",
  "cached_at": "2026-07-15T06:00:00Z"
}
```

## Redis Cache Strategy

```
Cache Key Pattern                     TTL     Example
──────────────────────────────────────────────────────────────
prediction:{model}:{feature_hash}     1h      prediction:fraud:a1b2c3
dashboard:kpis                        5m      dashboard:kpis
features:{customer_id}                2h      features:CUST_001
model:{name}:{version}:metadata      24h      model:xgb_fraud_v3:metadata
```

## Error Handling

```
┌──────────┐     ┌──────────────┐     ┌──────────────────┐
│  Client  │────▶│  FastAPI     │────▶│  Service Layer   │
└──────────┘     └──────┬───────┘     └────────┬─────────┘
                        │                       │
                        │  400 Bad Request      │  500 Internal
                        │◀──────────────────────│  ── retry 3x
                        │                       │  ── fallback to cache
                        │  503 Service Unavail  │  ── circuit breaker
                        │◀──────────────────────│
                        │                       │
                        │  200 OK (stale cache) │  Timeout → stale data
                        │◀──────────────────────│
```

## Circuit Breaker — State Machine

```
         ┌──────────┐
         │  CLOSED  │  Normal operation. Requests pass through.
         └────┬─────┘
              │  Failure threshold exceeded (5 errors / 30s)
              ▼
         ┌──────────┐
         │   OPEN   │  Requests fail fast. Cooldown 60s.
         └────┬─────┘
              │  Timeout expires
              ▼
         ┌───────────┐
         │ HALF-OPEN │  1 probe request allowed.
         └────┬──────┘
              │
     ┌────────┴────────┐
     ▼                 ▼
  Success → CLOSED   Fail → OPEN
```

## Retry & Backoff

```
            Attempt 1 ─▶ 0s
            Attempt 2 ─▶ 1s
            Attempt 3 ─▶ 2s
            Attempt 4 ─▶ 4s
            Attempt 5 ─▶ 8s  ◀── cap at 8s
            ───────────────────
            Total window: 15s
            Jitter: ±500ms
```

## Service Dependencies Table

| Service       | Depends On        | Impact if Down               |
|---------------|-------------------|------------------------------|
| FastAPI       | PostgreSQL, Redis | Predictions use stale cache   |
| FastAPI       | MLflow            | Model loading degraded        |
| Airflow       | PostgreSQL        | No new pipeline runs          |
| Airflow       | EMR / S3          | ETL fails                     |
| Streamlit     | FastAPI           | UI shows cached data          |
| Power BI      | PostgreSQL        | Dashboards stale              |
| MLflow        | PostgreSQL, S3    | Can't log new experiments     |
| PostgreSQL    | —                 | Everything degraded           |
| Redis         | —                 | Cache miss → direct DB query  |
