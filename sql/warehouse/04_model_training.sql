CREATE TABLE IF NOT EXISTS fact_model_training (
    id              SERIAL PRIMARY KEY,
    model_name      VARCHAR(100) NOT NULL,
    task            VARCHAR(50) NOT NULL,
    algorithm       VARCHAR(50) NOT NULL,
    version         VARCHAR(20) NOT NULL,
    accuracy        NUMERIC(6,4) NOT NULL,
    precision_score NUMERIC(6,4) NOT NULL,
    recall_score    NUMERIC(6,4) NOT NULL,
    f1_score        NUMERIC(6,4) NOT NULL,
    roc_auc         NUMERIC(6,4) NOT NULL,
    threshold       NUMERIC(6,4) NOT NULL,
    training_seconds NUMERIC(8,2) NOT NULL,
    features        TEXT NOT NULL,
    target          VARCHAR(100) NOT NULL,
    trained_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE fact_model_training IS 'ML model training results and performance metrics';
