"""
Pydantic schemas for request/response serialization and validation.
Shared across API routes.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import date, datetime


class CustomerCreate(BaseModel):
    source_system: str = Field(..., pattern="^(lending|fraud|churn)$")
    source_customer_id: str
    customer_name: Optional[str] = None
    age: Optional[int] = Field(None, ge=0, le=120)
    annual_income: Optional[float] = Field(None, ge=0)
    employment_length: Optional[str] = None
    home_ownership: Optional[str] = Field(None, pattern="^(RENT|MORTGAGE|OWN|OTHER)$")
    tenure: Optional[int] = Field(None, ge=0)

    @field_validator("annual_income")
    @classmethod
    def clamp_income(cls, v):
        if v is not None and v > 1e9:
            raise ValueError("annual_income exceeds reasonable maximum")
        return v


class FraudPrediction(BaseModel):
    transaction_id: str
    customer_id: int = 0
    transaction_amt: float = Field(..., gt=0)
    product_cd: str = Field("W", min_length=1, max_length=5)
    card1: Optional[int] = None
    card2: Optional[int] = None
    card3: Optional[int] = None
    card4: Optional[str] = None
    card5: Optional[int] = None
    card6: Optional[str] = None
    addr1: Optional[int] = None
    addr2: Optional[int] = None
    dist1: Optional[float] = None
    dist2: Optional[float] = None
    device_type: Optional[str] = None
    device_info: Optional[str] = None
    email_domain: Optional[str] = None
    p_email_domain: Optional[str] = None


class FraudPredictionResponse(BaseModel):
    transaction_id: str
    is_fraud: int
    fraud_probability: float
    model: str
    model_version: str
    inference_ms: int
    timestamp: str


class LoanDefaultPrediction(BaseModel):
    customer_id: int = 0
    annual_income: float = Field(..., gt=0)
    dti: float = Field(..., ge=0, le=100)
    credit_score: int = Field(..., ge=300, le=850)
    employment_length: str = Field(..., max_length=50)
    loan_amount: float = Field(..., gt=0)
    loan_purpose: str = Field(..., max_length=100)
    grade: str = Field(..., min_length=1, max_length=1, pattern="^[A-G]$")

    @field_validator("grade")
    @classmethod
    def uppercase_grade(cls, v):
        return v.upper()


class LoanDefaultResponse(BaseModel):
    prediction: str
    default_probability: float
    model: str
    model_version: str
    feature_importance: dict
    inference_ms: int


class ChurnPrediction(BaseModel):
    customer_id: int = 0
    tenure: int = Field(..., ge=0)
    monthly_charges: float = Field(..., ge=0)
    total_charges: float = Field(..., ge=0)
    contract_type: str = Field(..., pattern="^(Month-to-month|One year|Two year)$")
    payment_method: str
    internet_service: str = Field(..., pattern="^(DSL|Fiber optic|No)$")
    online_security: str = Field(..., pattern="^(Yes|No)$")
    online_backup: Optional[str] = Field(None, pattern="^(Yes|No)$")
    device_protection: Optional[str] = Field(None, pattern="^(Yes|No)$")
    tech_support: str = Field(..., pattern="^(Yes|No)$")
    streaming_tv: Optional[str] = Field(None, pattern="^(Yes|No)$")
    streaming_movies: Optional[str] = Field(None, pattern="^(Yes|No)$")


class ChurnPredictionResponse(BaseModel):
    churn: str
    churn_probability: float
    model: str
    model_version: str
    top_reason: str
    retention_action: str


class BatchPredictionRequest(BaseModel):
    records: list[FraudPrediction | LoanDefaultPrediction | ChurnPrediction] = Field(..., max_length=1000)


class BatchPredictionResponse(BaseModel):
    total: int
    success: int
    failed: int
    predictions: list[dict]


class KPIResponse(BaseModel):
    total_customers: int
    loans_approved: int
    loans_rejected: int
    fraud_cases: int
    revenue: float
    churn_rate_pct: float
    reporting_date: str
    cached_at: str


class ReportRequest(BaseModel):
    report_type: str = Field(..., pattern="^(fraud_summary|loan_performance|churn_analysis|executive_daily)$")
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    format: str = Field("json", pattern="^(json|pdf|csv)$")


class FeatureStoreResponse(BaseModel):
    customer_id: int
    feature_asof_date: date
    customer_risk_score: Optional[float] = None
    avg_monthly_spend: Optional[float] = None
    fraud_count_90d: Optional[int] = None
    loan_count_total: Optional[int] = None
    default_probability: Optional[float] = None
    churn_probability: Optional[float] = None
    composite_risk: Optional[float] = None


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    timestamp: str = None
