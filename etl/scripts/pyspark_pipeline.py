"""
FinSight — PySpark ETL Pipeline

Reads raw CSV, cleans, transforms, and writes to PostgreSQL warehouse.

Usage:
    python etl/scripts/pyspark_pipeline.py --source churn --date 2026-07-15
    python etl/scripts/pyspark_pipeline.py --source lending --date 2026-07-15 --sample 100000
    python etl/scripts/pyspark_pipeline.py --source fraud --date 2026-07-15 --sample 100000
"""

import argparse
import logging
import os
from pathlib import Path

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import (
    col, when, lit, coalesce, round, to_date, regexp_replace,
    trim, lower, count, avg, sum as spark_sum, row_number, substring,
    mean, stddev, split, expr, log10, monotonically_increasing_id
)
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType,
    DoubleType, DecimalType, TimestampType
)
from pyspark.sql.window import Window

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("finsight.etl")

RAW = Path(os.environ.get("FINSIGHT_DATA_DIR", r"D:\FinSight\data\raw"))
JDBC_URL = f"jdbc:postgresql://{os.environ.get('DB_HOST', 'localhost')}:{os.environ.get('DB_PORT', '5433')}/finsight"
JDBC_PROPS = {
    "user": os.environ["DB_USER"],
    "password": os.environ["DB_PASSWORD"],
    "driver": "org.postgresql.Driver",
}


def create_spark(app_name: str = "FinSight-ETL") -> SparkSession:
    return (
        SparkSession.builder
        .appName(app_name)
        .master("local[*]")
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.driver.memory", "4g")
        .config("spark.driver.maxResultSize", "2g")
        .config("spark.sql.parquet.compression.codec", "snappy")
        .config("spark.jars.packages", "org.postgresql:postgresql:42.7.1")
        .getOrCreate()
    )


# ── Churn ─────────────────────────────────────────────────────

def extract_churn(spark: SparkSession) -> DataFrame:
    path = str(RAW / "churn" / "telco_customer_churn.csv")
    logger.info(f"Reading churn from {path}")
    return (
        spark.read
        .option("header", "true")
        .option("inferSchema", "true")
        .option("mode", "PERMISSIVE")
        .csv(path)
    )


def transform_churn(df: DataFrame) -> DataFrame:
    return (
        df
        .dropDuplicates(["customerID"])
        .select(
            col("customerID").alias("source_customer_id"),
            col("tenure").cast("int"),
            col("MonthlyCharges").cast("decimal(8,2)").alias("monthly_charges"),
            col("TotalCharges").cast("decimal(10,2)").alias("total_charges"),
            col("Contract").alias("contract_type"),
            col("PaymentMethod").alias("payment_method"),
            col("PaperlessBilling").alias("paperless_billing"),
            col("MultipleLines").alias("multiple_lines"),
            col("InternetService").alias("internet_service"),
            col("OnlineSecurity").alias("online_security"),
            col("OnlineBackup").alias("online_backup"),
            col("DeviceProtection").alias("device_protection"),
            col("TechSupport").alias("tech_support"),
            col("StreamingTV").alias("streaming_tv"),
            col("StreamingMovies").alias("streaming_movies"),
            when(col("Churn") == "Yes", lit("Yes")).otherwise(lit("No")).alias("churn_label"),
            when(col("Churn") == "Yes", lit(1)).otherwise(lit(0)).alias("churn_flag"),
            when(col("tenure").cast("int") <= 6, lit("0-6 months"))
            .when(col("tenure").cast("int") <= 12, lit("6-12 months"))
            .when(col("tenure").cast("int") <= 24, lit("12-24 months"))
            .when(col("tenure").cast("int") <= 48, lit("24-48 months"))
            .otherwise(lit("48+ months")).alias("tenure_group"),
            when(col("tenure").cast("int") > 0,
                 round(col("MonthlyCharges").cast("decimal") / lit(30.0), 4))
            .otherwise(lit(0)).alias("avg_daily_charge"),
            lit("churn").alias("source_system"),
        )
        .withColumn("customer_id", monotonically_increasing_id() + 1)
    )


# ── Lending ───────────────────────────────────────────────────

def extract_lending(spark: SparkSession, sample: int = None) -> DataFrame:
    path = str(RAW / "lending" / "lending_club.csv")
    logger.info(f"Reading lending from {path}")
    df = (
        spark.read
        .option("header", "true")
        .option("inferSchema", "true")
        .option("mode", "PERMISSIVE")
        .csv(path)
    )
    if sample:
        logger.info(f"Sampling {sample} rows")
        fraction = min(1.0, sample / df.count())
        df = df.sample(withReplacement=False, fraction=fraction).limit(sample)
    return df


def transform_lending(df: DataFrame) -> DataFrame:
    return (
        df
        .dropDuplicates(["id"])
        .select(
            col("id").cast("string").alias("source_customer_id"),
            col("loan_amnt").cast("decimal(12,2)").alias("loan_amount"),
            regexp_replace(col("int_rate"), "%", "").cast("decimal(5,3)").alias("interest_rate"),
            col("annual_inc").cast("decimal(12,2)").alias("annual_income"),
            col("emp_length").alias("employment_length"),
            col("home_ownership").alias("home_ownership"),
            col("grade").alias("grade"),
            col("purpose").alias("purpose"),
            col("term").alias("term"),
            col("loan_status").alias("loan_status"),
            col("dti").cast("decimal(5,2)").alias("dti"),
            coalesce(col("fico_range_low"), col("fico_range_high"), lit(600))
            .cast("int").alias("credit_score"),
            to_date(col("issue_d"), "MMM-yyyy").alias("issue_date"),
            when(col("loan_status").isin("Charged Off", "Default"), lit(1))
            .otherwise(lit(0)).alias("default_flag"),
            when(col("annual_inc").cast("decimal") > 0,
                 round(col("loan_amnt").cast("decimal") / col("annual_inc").cast("decimal"), 4))
            .otherwise(lit(0)).alias("debt_ratio"),
            when(coalesce(col("fico_range_low"), col("fico_range_high"), lit(600)).cast("int") < 600,
                 lit(1)).otherwise(lit(0)).alias("high_risk"),
            when(col("int_rate").cast("decimal") < 7, lit("low"))
            .when(col("int_rate").cast("decimal") < 14, lit("medium"))
            .otherwise(lit("high")).alias("interest_rate_bucket"),
            lit("lending").alias("source_system"),
        )
        .withColumn("customer_id", monotonically_increasing_id() + 1000000)
    )


# ── Fraud ─────────────────────────────────────────────────────

def extract_fraud(spark: SparkSession, sample: int = None) -> DataFrame:
    txn_path = str(RAW / "fraud" / "train_transaction.csv")
    id_path = str(RAW / "fraud" / "train_identity.csv")
    logger.info(f"Reading fraud transaction from {txn_path}")

    txn = (
        spark.read
        .option("header", "true")
        .option("inferSchema", "true")
        .option("mode", "PERMISSIVE")
        .csv(txn_path)
    )

    id_df = (
        spark.read
        .option("header", "true")
        .option("inferSchema", "true")
        .option("mode", "PERMISSIVE")
        .csv(id_path)
    )

    # Join transaction + identity
    df = txn.join(id_df, on="TransactionID", how="left")

    if sample:
        logger.info(f"Sampling {sample} rows")
        fraction = min(1.0, sample / df.count())
        df = df.sample(withReplacement=False, fraction=fraction).limit(sample)
    return df


def transform_fraud(df: DataFrame) -> DataFrame:
    return (
        df
        .dropDuplicates(["TransactionID"])
        .select(
            col("TransactionID").cast("string").alias("source_customer_id"),
            col("TransactionAmt").cast("decimal(12,2)").alias("transaction_amt"),
            col("ProductCD").alias("product_cd"),
            col("card1").cast("int"),
            col("card2").cast("int"),
            col("card3").cast("int"),
            col("card4").cast("string"),
            col("card5").cast("int"),
            col("card6").cast("string"),
            col("addr1").cast("int"),
            col("addr2").cast("int"),
            col("dist1").cast("decimal(10,2)"),
            col("dist2").cast("decimal(10,2)"),
            col("DeviceType").alias("device_type"),
            col("DeviceInfo").alias("device_info"),
            col("id_01").cast("double"),
            col("id_02").cast("double"),
            col("id_03").cast("double"),
            col("id_04").cast("double"),
            col("id_05").cast("double"),
            col("id_06").cast("string"),
            col("id_07").cast("double"),
            col("id_08").cast("double"),
            col("id_09").cast("string"),
            col("id_10").cast("double"),
            col("id_11").cast("double"),
            col("id_12").cast("double"),
            col("id_13").cast("double"),
            col("id_14").cast("double"),
            col("id_15").cast("double"),
            col("id_16").cast("double"),
            col("id_17").cast("double"),
            col("id_18").cast("double"),
            col("id_19").cast("double"),
            col("id_20").cast("double"),
            col("id_21").cast("double"),
            col("id_22").cast("double"),
            col("id_23").cast("double"),
            col("id_24").cast("double"),
            col("id_25").cast("double"),
            col("id_26").cast("double"),
            col("id_27").cast("double"),
            col("id_28").cast("double"),
            col("id_29").cast("double"),
            col("id_30").cast("double"),
            col("id_31").cast("double"),
            col("id_32").cast("double"),
            col("id_33").cast("double"),
            col("id_34").cast("double"),
            col("id_35").cast("double"),
            col("id_36").cast("double"),
            col("id_37").cast("double"),
            col("id_38").cast("double"),
            col("isFraud").cast("int").alias("is_fraud"),
            when(col("TransactionAmt").cast("decimal") > 0,
                 round(lit(1) + log10(col("TransactionAmt").cast("decimal")), 4))
            .otherwise(lit(1)).alias("transaction_amt_log"),
            lit("fraud").alias("source_system"),
        )
        .withColumn("customer_id", monotonically_increasing_id() + 2000000)
    )


# ── Write ─────────────────────────────────────────────────────

def write_to_postgres(df: DataFrame, table: str, mode: str = "append"):
    count = df.count()
    logger.info(f"Writing {count} rows to PostgreSQL table: {table}")
    (
        df.write
        .mode(mode)
        .format("jdbc")
        .option("url", JDBC_URL)
        .option("dbtable", table)
        .option("user", JDBC_PROPS["user"])
        .option("password", JDBC_PROPS["password"])
        .option("driver", JDBC_PROPS["driver"])
        .option("batchsize", 5000)
        .option("numPartitions", 4)
        .save()
    )
    logger.info(f"Write complete: {table}")
    return count


# ── Main ──────────────────────────────────────────────────────

TRANSFORM_MAP = {
    "churn": (extract_churn, transform_churn, "fact_churn"),
    "lending": (extract_lending, transform_lending, "fact_loan"),
    "fraud": (extract_fraud, transform_fraud, "fact_transaction"),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, choices=["churn", "lending", "fraud"])
    parser.add_argument("--date", default="2026-07-15")
    parser.add_argument("--sample", type=int, help="Max rows to process (for large datasets)")
    args = parser.parse_args()

    extract_fn, transform_fn, target_table = TRANSFORM_MAP[args.source]

    spark = create_spark()
    try:
        kwargs = {}
        if args.source in ("lending", "fraud") and args.sample:
            kwargs["sample"] = args.sample

        raw_df = extract_fn(spark, **kwargs)
        clean_df = transform_fn(raw_df)

        clean_df = clean_df.withColumn("etl_date", lit(args.date))

        # Write to PostgreSQL
        write_to_postgres(clean_df, target_table, mode="append")

        # Log to etl_metadata
        row_count = clean_df.count()
        logger.info(f"Pipeline complete: {row_count} rows written to {target_table}")

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
