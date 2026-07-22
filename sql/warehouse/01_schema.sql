-- ============================================================
-- FinSight: Data Warehouse Schema (PostgreSQL)
-- Matches live database as of 2026-07-15.
-- Auto-generated from ETL output; mirrors flat staging tables.
-- ============================================================

-- ============================================================
-- 1. CHURN – IBM Telco customer churn
-- ============================================================
CREATE TABLE IF NOT EXISTS fact_churn (
    churn_id            BIGSERIAL           PRIMARY KEY,
    customer_id         VARCHAR(50),
    tenure              INT,
    monthly_charges     NUMERIC,
    total_charges       NUMERIC,
    contract_type       VARCHAR(50),
    payment_method      VARCHAR(100),
    paperless_billing   VARCHAR(20),
    multiple_lines      VARCHAR(20),
    internet_service    VARCHAR(20),
    online_security     VARCHAR(20),
    online_backup       VARCHAR(20),
    device_protection   VARCHAR(20),
    tech_support        VARCHAR(20),
    streaming_tv        VARCHAR(20),
    streaming_movies    VARCHAR(20),
    churn_label         TEXT,
    churn_probability   NUMERIC,
    churn_flag          INT,
    avg_daily_charge    NUMERIC,
    tenure_group        VARCHAR(20),
    created_at          TIMESTAMPTZ         DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_churn_customer ON fact_churn(customer_id);

-- ============================================================
-- 2. LOANS – Lending Club records
-- ============================================================
CREATE TABLE IF NOT EXISTS fact_loan (
    loan_id             BIGSERIAL           PRIMARY KEY,
    customer_id         BIGINT,
    loan_id_orig        BIGINT,
    loan_amount         NUMERIC             NOT NULL,
    interest_rate       NUMERIC,
    grade               CHAR(1),
    sub_grade           VARCHAR(2),
    purpose             VARCHAR(100),
    term                VARCHAR(10),
    dti                 NUMERIC,
    credit_score        INT,
    loan_status         TEXT,
    issue_date          DATE,
    default_flag        INT,
    annual_income       NUMERIC,
    employment_length   VARCHAR(20),
    home_ownership      VARCHAR(20),
    debt_ratio          NUMERIC,
    high_risk           INT,
    interest_rate_bucket VARCHAR(10),
    source_system       VARCHAR(20),
    created_at          TIMESTAMPTZ         DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_loan_status ON fact_loan(loan_status);
CREATE INDEX IF NOT EXISTS idx_loan_grade ON fact_loan(grade);

-- ============================================================
-- 3. TRANSACTIONS – IEEE Fraud data
-- ============================================================
CREATE TABLE IF NOT EXISTS fact_transaction (
    transaction_id      BIGINT              PRIMARY KEY,
    customer_id         BIGINT,
    card_id             BIGINT,
    transaction_amt     NUMERIC             NOT NULL,
    product_cd          VARCHAR(10),
    transaction_dt      TIMESTAMPTZ,
    device_type         VARCHAR(50),
    device_info         VARCHAR(255),
    email_domain        VARCHAR(100),
    p_email_domain      VARCHAR(100),
    addr1               BIGINT,
    addr2               BIGINT,
    dist1               NUMERIC,
    dist2               NUMERIC,
    p_addr1             BIGINT,
    p_addr2             BIGINT,
    c_id                BIGINT,
    m1_m9               JSONB,
    v1_v339             JSONB,
    id_01_id_38         JSONB,
    is_fraud            INT,
    card1               BIGINT,
    card2               BIGINT,
    card3               BIGINT,
    card4               VARCHAR(50),
    card5               BIGINT,
    card6               VARCHAR(50),
    transaction_amt_log NUMERIC,
    source_system       VARCHAR(20),
    created_at          TIMESTAMPTZ         DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_txn_customer ON fact_transaction(customer_id);
CREATE INDEX IF NOT EXISTS idx_txn_fraud ON fact_transaction(is_fraud);
CREATE INDEX IF NOT EXISTS idx_txn_date ON fact_transaction(transaction_dt);

-- ============================================================
-- 4. ETL METADATA – pipeline audit trail
-- ============================================================
CREATE TABLE IF NOT EXISTS etl_metadata (
    run_id          BIGSERIAL       PRIMARY KEY,
    dag_id          VARCHAR(100)    NOT NULL,
    task_id         VARCHAR(100)    NOT NULL,
    source_table    VARCHAR(100),
    target_table    VARCHAR(100),
    records_read    BIGINT,
    records_written BIGINT,
    records_failed  BIGINT,
    status          VARCHAR(20),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    error_message   TEXT,
    spark_app_id    VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_etl_status ON etl_metadata(status, started_at DESC);
