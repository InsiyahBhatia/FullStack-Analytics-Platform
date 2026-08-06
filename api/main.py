"""FinSight ML inference API.

Endpoints:
- POST /predict/churn      (auth required, rate-limited, monitored)
- POST /predict/default    (auth required, rate-limited, monitored)
- POST /predict/fraud      (auth required, rate-limited, monitored)
- GET/POST /health
- POST /metrics
- GET /powerbi/prediction-monitoring
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field

from models.common.feature_engineering import CHURN_SPEC, DEFAULT_SPEC, FRAUD_SPEC, align_inference_payload
from models.common.registry import load_model
from api.middleware.rate_limit import RateLimitMiddleware
from api.middleware.auth import verify_api_key
from api.middleware.security import SecurityHeadersMiddleware
from api.monitoring import log_prediction


app = FastAPI(
    title="FinSight Financial Analytics and ML Platform",
    description="Customer churn, loan default, fraud detection, model health, and prediction monitoring APIs.",
    version="3.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:8501,http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)
app.add_middleware(SecurityHeadersMiddleware)


class ChurnRequest(BaseModel):
    tenure: int = Field(..., ge=0)
    monthly_charges: float = Field(..., ge=0)
    total_charges: float = Field(0, ge=0)
    contract_type: str = Field("Month-to-month", max_length=50)
    payment_method: str = Field("Electronic check", max_length=50)
    internet_service: str = Field("Fiber optic", max_length=50)
    online_security: str = Field("No", max_length=50)
    tech_support: str = Field("No", max_length=50)
    paperless_billing: str = Field("Yes", max_length=50)
    streaming_tv: str = Field("No", max_length=50)


class LoanDefaultRequest(BaseModel):
    fico_score: int = Field(..., ge=300, le=900)
    debt_ratio: float = Field(..., ge=0)
    loan_amount: float = Field(..., gt=0)
    grade: str = Field("C", min_length=1, max_length=1)
    purpose: str = Field("debt_consolidation", max_length=100)
    annual_inc: float | None = Field(None, ge=0)
    emp_length: float | None = Field(None, ge=0, le=50)
    revol_bal: float | None = Field(None, ge=0)
    revol_util: float | None = Field(None, ge=0)
    delinq_2yrs: int | None = Field(None, ge=0, le=50)
    pub_rec: int | None = Field(None, ge=0, le=50)
    open_acc: int | None = Field(None, ge=0, le=100)
    home_ownership: str = Field("OTHER", max_length=50)
    verification_status: str = Field("Not Verified", max_length=50)


class FraudRequest(BaseModel):
    transaction_amt: float = Field(..., gt=0)
    device_type: str = Field("desktop", max_length=50)
    card_type: str = Field("visa", max_length=50)
    browser: str = Field("chrome", max_length=50)
    email_domain: str = Field("gmail.com", max_length=100)
    dist1: float | None = Field(None)
    dist2: float | None = Field(None)
    # Rolling velocity aggregates (per card), normally computed by the streaming layer
    txn_cnt_1h: float | None = Field(None, ge=0)
    txn_cnt_24h: float | None = Field(None, ge=0)
    txn_amt_sum_24h: float | None = Field(None, ge=0)
    txn_amt_std_24h: float | None = Field(None, ge=0)


class PredictionResponse(BaseModel):
    prediction: str
    probability: float
    model: str
    model_version: str
    top_drivers: list[str]
    inference_ms: int
    fallback: bool = False


class MetricsResponse(BaseModel):
    service: str
    status: str
    timestamp: str
    models: dict[str, Any]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _predict_with_artifact(task: str, payload: dict, spec, positive_label: str, negative_label: str) -> PredictionResponse | None:
    started = time.time()
    try:
        local = load_model(task)
    except FileNotFoundError:
        return None

    frame = align_inference_payload(payload, spec)
    probability = float(local.predict_proba(frame)[0][1])
    threshold = float(local.metadata.get("threshold", 0.5))
    return PredictionResponse(
        prediction=positive_label if probability >= threshold else negative_label,
        probability=round(probability, 4),
        model=local.metadata.get("name", f"finsight_{task}"),
        model_version=local.metadata.get("version", "local"),
        top_drivers=local.metadata.get("features", spec.all_features)[:5],
        inference_ms=int((time.time() - started) * 1000),
    )


def _heuristic_churn(req: ChurnRequest, started: float) -> PredictionResponse:
    score = 0.15
    drivers = []
    if req.contract_type == "Month-to-month":
        score += 0.3
        drivers.append("contract_type")
    if req.monthly_charges >= 80:
        score += 0.2
        drivers.append("monthly_charges")
    if req.tenure < 12:
        score += 0.2
        drivers.append("tenure")
    if req.payment_method == "Electronic check":
        score += 0.1
        drivers.append("payment_method")
    probability = min(score, 0.95)
    return PredictionResponse(
        prediction="Will Churn" if probability >= 0.5 else "Will Stay",
        probability=round(probability, 4),
        model="heuristic_churn_baseline",
        model_version="0.1.0",
        top_drivers=drivers or ["tenure", "contract_type", "monthly_charges"],
        inference_ms=int((time.time() - started) * 1000),
        fallback=True,
    )


def _heuristic_default(req: LoanDefaultRequest, started: float) -> PredictionResponse:
    score = 0.1
    drivers = []
    if req.fico_score < 620:
        score += 0.35
        drivers.append("fico_score")
    if req.debt_ratio > 30:
        score += 0.25
        drivers.append("debt_ratio")
    if req.grade.upper() in {"E", "F", "G"}:
        score += 0.2
        drivers.append("grade")
    if req.loan_amount > 25000:
        score += 0.1
        drivers.append("loan_amount")
    probability = min(score, 0.95)
    return PredictionResponse(
        prediction="Likely Default" if probability >= 0.5 else "Likely Performing",
        probability=round(probability, 4),
        model="heuristic_default_baseline",
        model_version="0.1.0",
        top_drivers=drivers or ["fico_score", "debt_ratio", "grade"],
        inference_ms=int((time.time() - started) * 1000),
        fallback=True,
    )


def _heuristic_fraud(req: FraudRequest, started: float) -> PredictionResponse:
    score = 0.03
    drivers = []
    if req.transaction_amt > 500:
        score += 0.3
        drivers.append("transaction_amt")
    if req.device_type.lower() in {"mobile", "unknown"}:
        score += 0.15
        drivers.append("device_type")
    if req.email_domain.lower() not in {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com"}:
        score += 0.2
        drivers.append("email_domain")
    if req.card_type.lower() in {"discover", "unknown"}:
        score += 0.1
        drivers.append("card_type")
    probability = min(score, 0.98)
    return PredictionResponse(
        prediction="Fraud" if probability >= 0.5 else "Legitimate",
        probability=round(probability, 4),
        model="heuristic_fraud_baseline",
        model_version="0.1.0",
        top_drivers=drivers or ["transaction_amt", "device_type", "email_domain"],
        inference_ms=int((time.time() - started) * 1000),
        fallback=True,
    )


@app.get("/health")
@app.post("/health")
async def health() -> dict:
    return {
        "status": "healthy",
        "service": "finsight-ml-api",
        "version": app.version,
        "timestamp": _now(),
    }


@app.post("/predict/churn", response_model=PredictionResponse)
async def predict_churn(req: ChurnRequest, _key: str = Depends(verify_api_key)) -> PredictionResponse:
    started = time.time()
    payload = req.model_dump()
    payload["total_charges"] = payload["total_charges"] or payload["tenure"] * payload["monthly_charges"]
    result = _predict_with_artifact("churn", payload, CHURN_SPEC, "Will Churn", "Will Stay")
    result = result or _heuristic_churn(req, started)
    log_prediction("churn", result)
    return result


@app.post("/predict/default", response_model=PredictionResponse)
async def predict_default(req: LoanDefaultRequest, _key: str = Depends(verify_api_key)) -> PredictionResponse:
    started = time.time()
    result = _predict_with_artifact("default", req.model_dump(), DEFAULT_SPEC, "Likely Default", "Likely Performing")
    result = result or _heuristic_default(req, started)
    log_prediction("default", result)
    return result


@app.post("/predict/fraud", response_model=PredictionResponse)
async def predict_fraud(req: FraudRequest, _key: str = Depends(verify_api_key)) -> PredictionResponse:
    started = time.time()
    result = _predict_with_artifact("fraud", req.model_dump(), FRAUD_SPEC, "Fraud", "Legitimate")
    result = result or _heuristic_fraud(req, started)
    log_prediction("fraud", result)
    return result


@app.post("/metrics", response_model=MetricsResponse)
async def metrics() -> MetricsResponse:
    model_status = {}
    for task in ["churn", "default", "fraud"]:
        try:
            local = load_model(task)
            model_status[task] = {
                "status": "loaded",
                "model": local.metadata.get("name", f"finsight_{task}"),
                "version": local.metadata.get("version", "local"),
                "roc_auc": local.metadata.get("metrics", {}).get("roc_auc"),
            }
        except FileNotFoundError:
            model_status[task] = {"status": "fallback", "model": f"heuristic_{task}_baseline"}
    return MetricsResponse(
        service="finsight-ml-api",
        status="healthy",
        timestamp=_now(),
        models=model_status,
    )


@app.get("/powerbi/prediction-monitoring")
async def prediction_monitoring(_: str = Depends(verify_api_key)) -> dict:
    """Live prediction stats for Power BI — reads from fact_prediction_monitoring."""
    try:
        engine = _get_monitoring_engine()
        from sqlalchemy import text
        with engine.begin() as conn:
            row = conn.execute(text("""
                SELECT
                    COUNT(*) AS total_predictions,
                    COUNT(*) FILTER (WHERE task = 'churn') AS churn_predictions,
                    COUNT(*) FILTER (WHERE task = 'default') AS default_predictions,
                    COUNT(*) FILTER (WHERE task = 'fraud') AS fraud_predictions,
                    ROUND(AVG(prediction_score)::numeric, 4) AS avg_confidence,
                    ROUND(AVG(inference_ms)::numeric, 0) AS avg_latency_ms,
                    COUNT(*) FILTER (WHERE fallback = true) AS fallback_count,
                    MAX(created_at) AS last_prediction_at
                FROM fact_prediction_monitoring
            """)).mappings().one()
            return dict(row)
    except Exception:
        return {
            "total_predictions": 0,
            "note": "fact_prediction_monitoring is empty or unreachable. Make predictions via /predict/* to populate.",
        }


_monitoring_engine = None

def _get_monitoring_engine():
    global _monitoring_engine
    if _monitoring_engine is None:
        from sqlalchemy import create_engine
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5433")
        user = os.getenv("DB_USER", "finsight_user")
        password = os.environ["DB_PASSWORD"]
        db = os.getenv("DB_NAME", "finsight")
        _monitoring_engine = create_engine(
            f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}",
            pool_size=2, max_overflow=3, pool_pre_ping=True,
        )
    return _monitoring_engine
