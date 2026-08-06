"""
Feature Engineering Pipeline

Generates customer-level features from raw tables and writes to feature_store.
Runs as a PySpark step in Airflow, then materializes via PostgreSQL.
"""

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import (
    col, count, sum, avg, when, lit, round, datediff, current_date,
    countDistinct, max as spark_max, min as spark_min, row_number
)
from pyspark.sql.window import Window
import logging
import os

logger = logging.getLogger("finsight.features")

JDBC_URL = f"jdbc:postgresql://{os.environ.get('DB_HOST', 'postgres')}:{os.environ.get('DB_PORT', '5432')}/finsight"
JDBC_PROPS = {
    "user": os.environ["DB_USER"],
    "password": os.environ["DB_PASSWORD"],
    "driver": "org.postgresql.Driver",
}


def build_features(spark: SparkSession, asof_date: str) -> DataFrame:
    customers = spark.read.jdbc(JDBC_URL, "dim_customer", properties=JDBC_PROPS)

    loans = spark.read.jdbc(JDBC_URL, "fact_loan", properties=JDBC_PROPS)
    transactions = spark.read.jdbc(JDBC_URL, "fact_transaction", properties=JDBC_PROPS)
    churn = spark.read.jdbc(JDBC_URL, "fact_churn", properties=JDBC_PROPS)
    predictions = spark.read.jdbc(JDBC_URL, "fact_prediction", properties=JDBC_PROPS)

    # Loan features
    loan_features = (
        loans
        .groupBy("customer_id")
        .agg(
            count("*").alias("loan_count_total"),
            sum(when(col("default_flag") == 1, lit(1)).otherwise(lit(0))).alias("default_count"),
            avg("loan_amount").alias("avg_loan_amount"),
            avg("dti").alias("dti_latest"),
            avg("credit_score").alias("credit_score_latest"),
            spark_max("issue_date").alias("last_loan_date"),
        )
    )

    # Fraud features — 90-day window
    fraud_features = (
        transactions
        .groupBy("customer_id")
        .agg(
            count("*").alias("fraud_count_90d"),
            sum(when(col("is_fraud") == 1, lit(1)).otherwise(lit(0))).alias("fraud_total"),
            avg(col("transaction_amt")).alias("avg_monthly_spend"),
        )
    )

    # Churn features
    churn_features = (
        churn
        .select(
            "customer_id",
            "churn_probability",
            "monthly_charges",
        )
    )

    # Prediction features — latest probabilities
    w = Window.partitionBy("customer_id", "task").orderBy(col("inference_ts").desc())
    latest_preds = (
        predictions
        .withColumn("rn", row_number().over(w))
        .filter(col("rn") == 1)
        .drop("rn")
    )

    default_probs = (
        latest_preds
        .filter(col("task") == "loan_default")
        .select("customer_id", col("prediction_score").alias("default_probability"))
    )

    churn_probs = (
        latest_preds
        .filter(col("task") == "customer_churn")
        .select("customer_id", col("prediction_score").alias("churn_probability"))
    )

    composite = 0.4 * col("fraud_total").cast("double") / (
        when(col("fraud_count_90d") > 0, col("fraud_count_90d")).otherwise(lit(1))
    ) + 0.3 * col("default_probability") + 0.3 * col("churn_probability")

    # Merge all feature sets
    result = (
        customers.alias("c")
        .join(loan_features.alias("l"), col("c.customer_id") == col("l.customer_id"), "left_outer")
        .join(fraud_features.alias("f"), col("c.customer_id") == col("f.customer_id"), "left_outer")
        .join(churn_features.alias("ch"), col("c.customer_id") == col("ch.customer_id"), "left_outer")
        .join(default_probs.alias("dp"), col("c.customer_id") == col("dp.customer_id"), "left_outer")
        .join(churn_probs.alias("cp"), col("c.customer_id") == col("cp.customer_id"), "left_outer")
        .select(
            col("c.customer_id"),
            lit(asof_date).alias("feature_asof_date"),
            round(composite, 4).alias("customer_risk_score"),
            col("f.avg_monthly_spend"),
            col("f.fraud_count_90d"),
            col("l.loan_count_total"),
            col("dp.default_probability"),
            col("cp.churn_probability"),
            col("l.dti_latest"),
            col("l.credit_score_latest"),
        )
        .fillna(0)
    )

    return result


def write_feature_store(df: DataFrame):
    (
        df.write
        .mode("overwrite")
        .format("jdbc")
        .option("url", JDBC_URL)
        .option("dbtable", "feature_store")
        .option("user", JDBC_PROPS["user"])
        .option("password", JDBC_PROPS["password"])
        .option("driver", JDBC_PROPS["driver"])
        .option("batchsize", 5000)
        .option("numPartitions", 8)
        .save()
    )
    logger.info(f"Feature store written: {df.count()} rows")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    args = parser.parse_args()

    spark = (
        SparkSession.builder
        .appName("FinSight-FeatureStore")
        .config("spark.sql.adaptive.enabled", "true")
        .getOrCreate()
    )

    try:
        features = build_features(spark, args.date)
        write_feature_store(features)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
