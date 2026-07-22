"""
Prediction monitoring — logs every API prediction to PostgreSQL.

Writes to `fact_prediction_monitoring` for Power BI dashboard consumption.
Runs asynchronously so it doesn't block the API response.
"""

import os
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_DB_URL = None


def _get_engine():
    global _DB_URL
    if _DB_URL is None:
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5433")
        user = os.getenv("DB_USER", "finsight_user")
        password = os.getenv("DB_PASSWORD", "finsight_dev_2026")
        db = os.getenv("DB_NAME", "finsight")
        _DB_URL = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    from sqlalchemy import create_engine
    return create_engine(_DB_URL, pool_size=2, max_overflow=5, pool_pre_ping=True)


_INSERT_SQL = """
INSERT INTO fact_prediction_monitoring
    (task, model_name, model_version, prediction_label, prediction_score,
     top_drivers, inference_ms, fallback, created_at)
VALUES
    (:task, :model_name, :model_version, :prediction_label, :prediction_score,
     :top_drivers, :inference_ms, :fallback, :created_at)
"""


def log_prediction(task: str, prediction_response) -> None:
    """Write a prediction record to fact_prediction_monitoring. Non-blocking."""
    try:
        engine = _get_engine()
        with engine.begin() as conn:
            conn.execute(
                __import__("sqlalchemy").text(_INSERT_SQL),
                {
                    "task": task,
                    "model_name": prediction_response.model,
                    "model_version": prediction_response.model_version,
                    "prediction_label": prediction_response.prediction,
                    "prediction_score": prediction_response.probability,
                    "top_drivers": json.dumps(prediction_response.top_drivers),
                    "inference_ms": prediction_response.inference_ms,
                    "fallback": prediction_response.fallback,
                    "created_at": datetime.now(timezone.utc),
                },
            )
    except Exception as exc:
        logger.warning(f"Failed to log prediction: {exc}")
