"""
FinSight — Local ETL Pipeline (no AWS)

Schedule: daily at 2am
Flow: start → [etl_churn, etl_lending, etl_fraud] → refresh_metadata → generate_features → train_models → load_training_metadata → end

Usage:
    docker compose -f docker-compose.yml -f docker-compose.local.yml up airflow-init airflow-scheduler airflow-webserver
    # then trigger manually or wait for schedule
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator

logger = logging.getLogger("finsight.local_pipeline")

DEFAULT_ARGS = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 0,
    "execution_timeout": timedelta(hours=1),
}


def run_etl(source: str):
    from etl.scripts.run_local_etl import get_engine, ETL_MAP
    engine = get_engine()
    fn = ETL_MAP[source]
    sample = 50000 if source in ("lending", "fraud") else None
    kwargs = {"sample": sample} if sample else {}
    rows = fn(engine, **kwargs)
    logger.info(f"ETL complete: {source} → {rows} rows")
    return rows


def run_etl_churn():
    return run_etl("churn")


def run_etl_lending():
    return run_etl("lending")


def run_etl_fraud():
    return run_etl("fraud")


def refresh_metadata():
    from etl.scripts.run_local_etl import get_engine
    from sqlalchemy import text
    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM etl_metadata"))
        count = result.scalar()
        logger.info(f"etl_metadata rows: {count}")
    return count


def build_feature_store():
    from etl.scripts.feature_store import generate_features
    from etl.scripts.run_local_etl import get_engine
    engine = get_engine()
    rows = generate_features(engine)
    logger.info(f"Feature store updated: {rows} row(s)")
    return rows


def train_models():
    """Train all ML models using the same logic as models/train_all.py."""
    import sys
    sys.path.insert(0, "/opt/airflow")
    from models.train_all import train_churn, train_default, train_fraud
    from models.common.registry import ARTIFACT_ROOT

    data_dir = Path("/opt/airflow/data")
    max_rows = 150000

    results = {}
    for task, runner in [("churn", train_churn), ("default", train_default), ("fraud", train_fraud)]:
        logger.info(f"Training {task} model...")
        result = runner(data_dir, max_rows)
        best = result["best"]
        results[task] = best["metrics"]["roc_auc"]
        logger.info(f"{task}: {best['algorithm']} ROC-AUC={best['metrics']['roc_auc']}")

    logger.info(f"All models trained: {results}")
    return results


def load_training_metadata():
    """Load model training metadata into fact_model_training table."""
    import sys
    import json
    import glob as glob_mod
    sys.path.insert(0, "/opt/airflow")

    from etl.scripts.run_local_etl import get_engine
    from sqlalchemy import text

    engine = get_engine()
    artifacts_dir = Path("/opt/airflow/models/artifacts")

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM fact_model_training"))
        count = 0
        for path in artifacts_dir.glob("*_metadata.json"):
            with open(path) as f:
                m = json.load(f)
            conn.execute(text("""
                INSERT INTO fact_model_training
                (model_name, task, algorithm, version, accuracy, precision_score,
                 recall_score, f1_score, roc_auc, threshold, training_seconds, features, target)
                VALUES (:name, :task, :algorithm, :version, :accuracy, :precision,
                        :recall, :f1, :roc_auc, :threshold, :training_seconds, :features, :target)
            """), {
                "name": m["name"], "task": m["task"], "algorithm": m["algorithm"],
                "version": m["version"], "accuracy": m["metrics"]["accuracy"],
                "precision": m["metrics"]["precision"], "recall": m["metrics"]["recall"],
                "f1": m["metrics"]["f1"], "roc_auc": m["metrics"]["roc_auc"],
                "threshold": m["threshold"], "training_seconds": m["metrics"]["training_seconds"],
                "features": json.dumps(m["features"]), "target": m["target"],
            })
            count += 1
            logger.info(f"  loaded {m['name']}")

    logger.info(f"Training metadata loaded: {count} models")
    return count


with DAG(
    dag_id="finsight_local_pipeline",
    default_args=DEFAULT_ARGS,
    description="FinSight: Local ETL Pipeline (no AWS dependencies)",
    schedule_interval="0 2 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["finsight", "etl", "local"],
) as dag:

    start = EmptyOperator(task_id="start")

    etl_churn = PythonOperator(
        task_id="etl_churn",
        python_callable=run_etl_churn,
        doc="Extract, transform and load churn data into fact_churn",
    )

    etl_lending = PythonOperator(
        task_id="etl_lending",
        python_callable=run_etl_lending,
        doc="Extract, transform and load lending data into fact_loan",
    )

    etl_fraud = PythonOperator(
        task_id="etl_fraud",
        python_callable=run_etl_fraud,
        doc="Extract, transform and load fraud data into fact_transaction",
    )

    check_metadata = PythonOperator(
        task_id="check_metadata",
        python_callable=refresh_metadata,
        doc="Verify etl_metadata has been populated correctly",
    )

    generate_features = PythonOperator(
        task_id="generate_features",
        python_callable=build_feature_store,
        doc="Aggregate features from all fact tables into feature_store",
    )

    train_models_task = PythonOperator(
        task_id="train_models",
        python_callable=train_models,
        doc="Train churn, default, and fraud ML models (saves to models/artifacts/)",
    )

    load_metadata_task = PythonOperator(
        task_id="load_training_metadata",
        python_callable=load_training_metadata,
        doc="Load model training results into fact_model_training for Power BI",
    )

    end = EmptyOperator(task_id="end")

    start >> [etl_churn, etl_lending, etl_fraud] >> check_metadata >> generate_features >> train_models_task >> load_metadata_task >> end
