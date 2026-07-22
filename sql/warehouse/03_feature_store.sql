-- ============================================================
-- FinSight: Feature Store — aggregated customer-level features
-- Built by the Airflow pipeline after ETL completes.
-- ============================================================

CREATE TABLE IF NOT EXISTS feature_store (
    feature_id              BIGSERIAL       PRIMARY KEY,
    feature_asof_date       DATE            NOT NULL,
    -- Churn features
    total_customers         INT,
    avg_tenure              NUMERIC,
    avg_monthly_charges     NUMERIC,
    avg_total_charges       NUMERIC,
    churn_rate              NUMERIC,
    month_to_month_pct      NUMERIC,
    -- Lending features
    total_loans             INT,
    avg_loan_amount         NUMERIC,
    avg_interest_rate       NUMERIC,
    default_rate            NUMERIC,
    avg_debt_ratio          NUMERIC,
    high_risk_pct           NUMERIC,
    -- Fraud features
    total_transactions      INT,
    fraud_count             INT,
    fraud_rate              NUMERIC,
    avg_transaction_amt     NUMERIC,
    -- Composite risk score (weighted blend)
    customer_risk_score     NUMERIC,
    created_at              TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fs_date ON feature_store(feature_asof_date DESC);
