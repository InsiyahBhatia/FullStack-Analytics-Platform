"""
Feature Store — pandas-based feature generation.

Generates aggregated customer-level features from fact_churn, fact_loan,
and fact_transaction tables. Writes results to the feature_store table.

Used as an Airflow task after ETL completes.
"""

import logging
from datetime import date, datetime, timezone
from sqlalchemy import text

logger = logging.getLogger("finsight.feature_store")


def generate_features(engine) -> int:
    """Build aggregated features from all fact tables and write to feature_store."""
    asof_date = date.today()

    with engine.begin() as conn:
        # ── Churn features ──────────────────────────────────────
        churn = conn.execute(text("""
            SELECT
                COUNT(*)::int AS total_customers,
                ROUND(AVG(tenure)::numeric, 1) AS avg_tenure,
                ROUND(AVG(monthly_charges)::numeric, 2) AS avg_monthly_charges,
                ROUND(AVG(total_charges)::numeric, 2) AS avg_total_charges,
                ROUND(AVG(churn_flag)::numeric, 4) AS churn_rate,
                ROUND(
                    COUNT(*) FILTER (WHERE contract_type = 'Month-to-month')::numeric
                    / NULLIF(COUNT(*), 0), 4
                ) AS month_to_month_pct
            FROM fact_churn
        """)).mappings().one()

        # ── Lending features ────────────────────────────────────
        loan = conn.execute(text("""
            SELECT
                COUNT(*)::int AS total_loans,
                ROUND(AVG(loan_amount)::numeric, 2) AS avg_loan_amount,
                ROUND(AVG(interest_rate)::numeric, 2) AS avg_interest_rate,
                ROUND(AVG(default_flag)::numeric, 4) AS default_rate,
                ROUND(AVG(debt_ratio)::numeric, 2) AS avg_debt_ratio,
                ROUND(
                    COUNT(*) FILTER (WHERE high_risk = 1)::numeric
                    / NULLIF(COUNT(*), 0), 4
                ) AS high_risk_pct
            FROM fact_loan
        """)).mappings().one()

        # ── Fraud features ──────────────────────────────────────
        fraud = conn.execute(text("""
            SELECT
                COUNT(*)::int AS total_transactions,
                COUNT(*) FILTER (WHERE is_fraud = 1)::int AS fraud_count,
                ROUND(AVG(is_fraud)::numeric, 4) AS fraud_rate,
                ROUND(AVG(transaction_amt)::numeric, 2) AS avg_transaction_amt
            FROM fact_transaction
        """)).mappings().one()

        # ── Composite risk score ────────────────────────────────
        # Weighted blend: 0.40 * fraud_rate + 0.30 * default_rate + 0.30 * churn_rate
        risk_score = round(
            0.40 * float(fraud["fraud_rate"] or 0)
            + 0.30 * float(loan["default_rate"] or 0)
            + 0.30 * float(churn["churn_rate"] or 0),
            4,
        )

        # ── Write to feature_store ──────────────────────────────
        conn.execute(text("""
            INSERT INTO feature_store (
                feature_asof_date, total_customers, avg_tenure, avg_monthly_charges,
                avg_total_charges, churn_rate, month_to_month_pct,
                total_loans, avg_loan_amount, avg_interest_rate, default_rate,
                avg_debt_ratio, high_risk_pct,
                total_transactions, fraud_count, fraud_rate, avg_transaction_amt,
                customer_risk_score
            ) VALUES (
                :asof_date, :total_customers, :avg_tenure, :avg_monthly_charges,
                :avg_total_charges, :churn_rate, :month_to_month_pct,
                :total_loans, :avg_loan_amount, :avg_interest_rate, :default_rate,
                :avg_debt_ratio, :high_risk_pct,
                :total_transactions, :fraud_count, :fraud_rate, :avg_transaction_amt,
                :customer_risk_score
            )
        """), {
            "asof_date": asof_date,
            "total_customers": churn["total_customers"],
            "avg_tenure": churn["avg_tenure"],
            "avg_monthly_charges": churn["avg_monthly_charges"],
            "avg_total_charges": churn["avg_total_charges"],
            "churn_rate": churn["churn_rate"],
            "month_to_month_pct": churn["month_to_month_pct"],
            "total_loans": loan["total_loans"],
            "avg_loan_amount": loan["avg_loan_amount"],
            "avg_interest_rate": loan["avg_interest_rate"],
            "default_rate": loan["default_rate"],
            "avg_debt_ratio": loan["avg_debt_ratio"],
            "high_risk_pct": loan["high_risk_pct"],
            "total_transactions": fraud["total_transactions"],
            "fraud_count": fraud["fraud_count"],
            "fraud_rate": fraud["fraud_rate"],
            "avg_transaction_amt": fraud["avg_transaction_amt"],
            "customer_risk_score": risk_score,
        })

        logger.info(
            f"Feature store written: {churn['total_customers']} customers, "
            f"{loan['total_loans']} loans, {fraud['total_transactions']} transactions, "
            f"risk_score={risk_score}"
        )
        return 1
