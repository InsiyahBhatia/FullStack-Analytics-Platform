-- ============================================================
-- FinSight: Streaming Views for Real-Time Monitoring
-- ============================================================
-- These views provide dynamic, rolling time windows for the
-- Real-Time Monitoring page in Power BI.
--
-- vw_streaming_summary:  Per-minute aggregation (last 2 hours)
-- vw_streaming_realtime: 5-minute rolling window
-- ============================================================

-- Drop first to allow column renames
DROP VIEW IF EXISTS vw_streaming_realtime CASCADE;
DROP VIEW IF EXISTS vw_streaming_summary CASCADE;

-- Per-minute transaction summary (last 2 hours)
CREATE OR REPLACE VIEW vw_streaming_summary AS
SELECT
    date_trunc('minute'::text, transaction_ts) AS minute_bucket,
    count(*) AS total_transactions,
    sum(CASE WHEN is_fraud THEN 1 ELSE 0 END) AS fraud_count,
    round(avg(amount), 2) AS avg_amount,
    round(sum(amount), 2) AS total_amount
FROM fact_streaming_transaction
WHERE transaction_ts >= (now() - interval '2 hours')
GROUP BY (date_trunc('minute'::text, transaction_ts))
ORDER BY (date_trunc('minute'::text, transaction_ts)) DESC;

-- 5-minute real-time rolling window
CREATE OR REPLACE VIEW vw_streaming_realtime AS
SELECT
    now() AS window_end,
    count(*) AS transactions_last_5min,
    sum(CASE WHEN is_fraud THEN 1 ELSE 0 END) AS fraud_last_5min,
    round(avg(amount), 2) AS avg_amount_5min
FROM fact_streaming_transaction
WHERE transaction_ts >= (now() - interval '5 minutes');
