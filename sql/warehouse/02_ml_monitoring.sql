CREATE TABLE IF NOT EXISTS fact_prediction_monitoring (
    prediction_id BIGSERIAL PRIMARY KEY,
    task VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    prediction_label VARCHAR(50) NOT NULL,
    prediction_score NUMERIC NOT NULL,
    top_drivers JSONB,
    inference_ms INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE OR REPLACE VIEW vw_prediction_monitoring AS
SELECT
    task,
    model_name,
    model_version,
    COUNT(*) AS predictions,
    AVG(prediction_score) AS average_score,
    AVG(inference_ms) AS average_inference_ms,
    MAX(created_at) AS latest_prediction_at
FROM fact_prediction_monitoring
GROUP BY task, model_name, model_version;
