"""
FinSight — Main Orchestration DAG

Schedule: daily at midnight
Triggers: S3 Sensor → ETL → ML Training → Report → Email
"""

from datetime import datetime, timedelta
try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator
    from airflow.operators.dummy import DummyOperator
    from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor
    from airflow.providers.amazon.aws.operators.emr import (
        EmrAddStepsOperator,
        EmrCreateJobFlowOperator,
        EmrTerminateJobFlowOperator,
    )
    from airflow.providers.postgres.operators.postgres import PostgresOperator
    from airflow.providers.amazon.aws.operators.sns import SnsPublishOperator
    from airflow.utils.trigger_rule import TriggerRule
except ImportError:
    class Dummy:
        def __init__(self, *args, **kwargs):
            pass
    DAG = PythonOperator = DummyOperator = S3KeySensor = Dummy
    EmrAddStepsOperator = EmrCreateJobFlowOperator = EmrTerminateJobFlowOperator = Dummy
    PostgresOperator = SnsPublishOperator = TriggerRule = Dummy

DEFAULT_ARGS = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": True,
    "email": ["alerts@finsight.com"],
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=2),
}

SPARK_STEPS = [
    {
        "Name": "Extract & Clean Lending Data",
        "ActionOnFailure": "CONTINUE",
        "HadoopJarStep": {
            "Jar": "command-runner.jar",
            "Args": [
                "spark-submit",
                "--deploy-mode", "cluster",
                "s3://finsight-code/etl/scripts/pyspark_pipeline.py",
                "--source", "lending",
                "--date", "{{ ds }}",
            ],
        },
    },
    {
        "Name": "Extract & Clean Fraud Data",
        "ActionOnFailure": "CONTINUE",
        "HadoopJarStep": {
            "Jar": "command-runner.jar",
            "Args": [
                "spark-submit",
                "--deploy-mode", "cluster",
                "s3://finsight-code/etl/scripts/pyspark_pipeline.py",
                "--source", "fraud",
                "--date", "{{ ds }}",
            ],
        },
    },
    {
        "Name": "Extract & Clean Churn Data",
        "ActionOnFailure": "CONTINUE",
        "HadoopJarStep": {
            "Jar": "command-runner.jar",
            "Args": [
                "spark-submit",
                "--deploy-mode", "cluster",
                "s3://finsight-code/etl/scripts/pyspark_pipeline.py",
                "--source", "churn",
                "--date", "{{ ds }}",
            ],
        },
    },
    {
        "Name": "Feature Engineering & Store",
        "ActionOnFailure": "CONTINUE",
        "HadoopJarStep": {
            "Jar": "command-runner.jar",
            "Args": [
                "spark-submit",
                "--deploy-mode", "cluster",
                "s3://finsight-code/etl/scripts/feature_engineering.py",
                "--date", "{{ ds }}",
            ],
        },
    },
    {
        "Name": "Model Training (Batch)",
        "ActionOnFailure": "CONTINUE",
        "HadoopJarStep": {
            "Jar": "command-runner.jar",
            "Args": [
                "spark-submit",
                "--deploy-mode", "cluster",
                "s3://finsight-code/models/train_all.py",
                "--date", "{{ ds }}",
            ],
        },
    },
]

with DAG(
    dag_id="finsight_pipeline",
    default_args=DEFAULT_ARGS,
    description="FinSight: Daily Banking Analytics Pipeline",
    schedule_interval="0 0 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["finsight", "etl", "ml"],
    doc_md=__doc__,
) as dag:

    start = DummyOperator(task_id="start")

    wait_for_lending = S3KeySensor(
        task_id="wait_for_lending_data",
        bucket_key="raw/lending/{{ ds }}/loan_data.csv",
        bucket_name="finsight-data-lake",
        timeout=3600,
        poke_interval=300,
    )

    wait_for_fraud = S3KeySensor(
        task_id="wait_for_fraud_data",
        bucket_key="raw/fraud/{{ ds }}/fraud_data.csv",
        bucket_name="finsight-data-lake",
        timeout=3600,
        poke_interval=300,
    )

    wait_for_churn = S3KeySensor(
        task_id="wait_for_churn_data",
        bucket_key="raw/churn/{{ ds }}/churn_data.csv",
        bucket_name="finsight-data-lake",
        timeout=3600,
        poke_interval=300,
    )

    create_emr_cluster = EmrCreateJobFlowOperator(
        task_id="create_emr_cluster",
        job_flow_overrides={
            "Name": "finsight-etl-{{ ds }}",
            "ReleaseLabel": "emr-6.15.0",
            "Applications": [{"Name": "Spark"}],
            "Instances": {
                "InstanceGroups": [
                    {
                        "Name": "Master",
                        "InstanceRole": "MASTER",
                        "InstanceType": "m5.xlarge",
                        "InstanceCount": 1,
                    },
                    {
                        "Name": "Core",
                        "InstanceRole": "CORE",
                        "InstanceType": "r5.2xlarge",
                        "InstanceCount": 4,
                    },
                ],
                "KeepJobFlowAliveWhenNoSteps": True,
                "TerminationProtected": False,
            },
            "VisibleToAllUsers": True,
            "JobFlowRole": "EMR_EC2_DefaultRole",
            "ServiceRole": "EMR_DefaultRole",
        },
    )

    run_spark_jobs = EmrAddStepsOperator(
        task_id="run_spark_jobs",
        job_flow_id="{{ task_instance.xcom_pull(task_ids='create_emr_cluster', key='return_value') }}",
        steps=SPARK_STEPS,
    )

    terminate_cluster = EmrTerminateJobFlowOperator(
        task_id="terminate_emr_cluster",
        job_flow_id="{{ task_instance.xcom_pull(task_ids='create_emr_cluster', key='return_value') }}",
        trigger_rule=TriggerRule.ALL_DONE,
    )

    run_migrations = PostgresOperator(
        task_id="run_schema_migrations",
        postgres_conn_id="finsight_warehouse",
        sql="""
        -- idempotent: ensure partition exists for today
        CREATE TABLE IF NOT EXISTS fact_transaction_{{ ds_nodash }}
            PARTITION OF fact_transaction
            FOR VALUES FROM ('{{ ds }}'::date) TO ('{{ tomorrow_ds }}'::date);
        """,
    )

    load_feature_store = PostgresOperator(
        task_id="load_feature_store",
        postgres_conn_id="finsight_warehouse",
        sql="sql/warehouse/refresh_feature_store.sql",
    )

    refresh_materialized_view = PostgresOperator(
        task_id="refresh_kpi_view",
        postgres_conn_id="finsight_warehouse",
        sql="REFRESH MATERIALIZED VIEW mv_executive_kpis;",
    )

    generate_report = PythonOperator(
        task_id="generate_daily_report",
        python_callable=lambda: __import__(
            "etl.scripts.reporting", fromlist=["generate_pdf"]
        ).generate_pdf("{{ ds }}"),
    )

    send_alert = SnsPublishOperator(
        task_id="send_daily_alert",
        target_arn="arn:aws:sns:us-east-1:123456789012:finsight-alerts",
        subject="FinSight Daily Pipeline Report — {{ ds }}",
        message="{{ task_instance.xcom_pull(task_ids='generate_daily_report') }}",
    )

    end = DummyOperator(task_id="end")

    # ── DAG Topology ────────────────────────────────────────────
    start >> [wait_for_lending, wait_for_fraud, wait_for_churn]

    (
        [wait_for_lending, wait_for_fraud, wait_for_churn]
        >> create_emr_cluster
        >> run_spark_jobs
        >> terminate_cluster
    )

    (
        terminate_cluster
        >> run_migrations
        >> load_feature_store
        >> refresh_materialized_view
        >> generate_report
        >> send_alert
        >> end
    )
