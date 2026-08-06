"""Streamlit front end for FinSight ML predictions."""

from __future__ import annotations

import os

import pandas as pd
import requests
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_KEY = os.environ["FINSIGHT_API_KEY"]
API_HEADERS = {"X-API-Key": API_KEY}

st.set_page_config(page_title="FinSight ML Workbench", layout="wide")
st.title("FinSight ML Workbench")


def post_prediction(endpoint: str, payload: dict) -> dict:
    response = requests.post(f"{API_BASE_URL}{endpoint}", json=payload, headers=API_HEADERS, timeout=30)
    response.raise_for_status()
    return response.json()


def render_result(result: dict) -> None:
    c1, c2, c3 = st.columns(3)
    c1.metric("Prediction", result["prediction"])
    c2.metric("Confidence", f"{result['probability']:.2%}")
    c3.metric("Inference", f"{result['inference_ms']} ms")
    st.caption(f"Model: {result['model']} v{result['model_version']}")
    st.write("Top drivers")
    st.write(result["top_drivers"])
    if result.get("fallback"):
        st.warning("Using heuristic fallback because a trained model artifact is not available yet.")


tab_churn, tab_default, tab_fraud, tab_batch = st.tabs(
    ["Churn Predictor", "Loan Default Predictor", "Fraud Predictor", "CSV Upload"]
)

with tab_churn:
    st.subheader("Customer Churn Prediction")
    with st.form("churn_form"):
        tenure = st.number_input("Tenure", min_value=0, value=12)
        monthly_charges = st.number_input("Monthly charges", min_value=0.0, value=100.0)
        contract_type = st.selectbox("Contract type", ["Month-to-month", "One year", "Two year"])
        payment_method = st.selectbox(
            "Payment method",
            ["Electronic check", "Mailed check", "Bank transfer (automatic)", "Credit card (automatic)"],
        )
        internet_service = st.selectbox("Internet service", ["DSL", "Fiber optic", "No"])
        c1, c2 = st.columns(2)
        with c1:
            online_security = st.selectbox("Online security", ["No", "Yes"])
            tech_support = st.selectbox("Tech support", ["No", "Yes"])
        with c2:
            paperless_billing = st.selectbox("Paperless billing", ["Yes", "No"])
            streaming_tv = st.selectbox("Streaming TV", ["No", "Yes"])
        submitted = st.form_submit_button("Predict churn")
    if submitted:
        result = post_prediction(
            "/predict/churn",
            {
                "tenure": tenure,
                "monthly_charges": monthly_charges,
                "total_charges": tenure * monthly_charges,
                "contract_type": contract_type,
                "payment_method": payment_method,
                "internet_service": internet_service,
                "online_security": online_security,
                "tech_support": tech_support,
                "paperless_billing": paperless_billing,
                "streaming_tv": streaming_tv,
            },
        )
        render_result(result)

with tab_default:
    st.subheader("Loan Default Prediction")
    with st.form("default_form"):
        fico_score = st.slider("FICO score", min_value=300, max_value=900, value=660)
        debt_ratio = st.number_input("Debt ratio", min_value=0.0, value=22.0)
        loan_amount = st.number_input("Loan amount", min_value=1.0, value=12000.0)
        grade = st.selectbox("Grade", list("ABCDEFG"), index=2)
        purpose = st.selectbox("Purpose", ["debt_consolidation", "credit_card", "home_improvement", "small_business", "other"])
        c1, c2 = st.columns(2)
        with c1:
            annual_inc = st.number_input("Annual income", min_value=0.0, value=75000.0)
            emp_length = st.number_input("Employment length (years)", min_value=0.0, value=8.0)
            home_ownership = st.selectbox("Home ownership", ["RENT", "MORTGAGE", "OWN", "OTHER"])
            revol_util = st.number_input("Revolving utilization %", min_value=0.0, value=35.0)
        with c2:
            revol_bal = st.number_input("Revolving balance", min_value=0.0, value=12000.0)
            delinq_2yrs = st.number_input("Delinquencies (2yrs)", min_value=0, value=0)
            pub_rec = st.number_input("Public records", min_value=0, value=0)
            open_acc = st.number_input("Open credit lines", min_value=0, value=12)
        verification_status = st.selectbox("Verification status", ["Not Verified", "Source Verified", "Verified"])
        submitted = st.form_submit_button("Predict default")
    if submitted:
        result = post_prediction(
            "/predict/default",
            {
                "fico_score": fico_score,
                "debt_ratio": debt_ratio,
                "loan_amount": loan_amount,
                "grade": grade,
                "purpose": purpose,
                "annual_inc": annual_inc,
                "emp_length": emp_length,
                "revol_bal": revol_bal,
                "revol_util": revol_util,
                "delinq_2yrs": delinq_2yrs,
                "pub_rec": pub_rec,
                "open_acc": open_acc,
                "home_ownership": home_ownership,
                "verification_status": verification_status,
            },
        )
        render_result(result)

with tab_fraud:
    st.subheader("Fraud Detection")
    with st.form("fraud_form"):
        transaction_amt = st.number_input("Transaction amount", min_value=1.0, value=250.0)
        device_type = st.selectbox("Device type", ["desktop", "mobile", "unknown"])
        card_type = st.selectbox("Card type", ["visa", "mastercard", "american express", "discover", "unknown"])
        browser = st.selectbox("Browser", ["chrome", "safari", "firefox", "edge", "unknown"])
        email_domain = st.text_input("Email domain", value="gmail.com")
        provide_context = st.checkbox("Provide velocity & distance context (advanced)", value=False)
        dist1 = dist2 = txn_cnt_1h = txn_cnt_24h = txn_amt_sum_24h = txn_amt_std_24h = None
        if provide_context:
            st.caption("When left off, these features are median-imputed from the training data.")
            c1, c2 = st.columns(2)
            with c1:
                dist1 = st.number_input("Dist 1 (km)", min_value=0.0, value=0.0)
                txn_cnt_1h = st.number_input("Tx count (1h)", min_value=0, value=0)
                txn_amt_sum_24h = st.number_input("Tx amount sum (24h)", min_value=0.0, value=0.0)
            with c2:
                dist2 = st.number_input("Dist 2 (km)", min_value=0.0, value=0.0)
                txn_cnt_24h = st.number_input("Tx count (24h)", min_value=0, value=0)
                txn_amt_std_24h = st.number_input("Tx amount std (24h)", min_value=0.0, value=0.0)
        submitted = st.form_submit_button("Predict fraud")
    if submitted:
        payload = {
            "transaction_amt": transaction_amt,
            "device_type": device_type,
            "card_type": card_type,
            "browser": browser,
            "email_domain": email_domain,
        }
        if provide_context:
            payload.update(
                {
                    "dist1": dist1,
                    "dist2": dist2,
                    "txn_cnt_1h": txn_cnt_1h,
                    "txn_cnt_24h": txn_cnt_24h,
                    "txn_amt_sum_24h": txn_amt_sum_24h,
                    "txn_amt_std_24h": txn_amt_std_24h,
                }
            )
        result = post_prediction("/predict/fraud", payload)
        render_result(result)

with tab_batch:
    st.subheader("Batch CSV Scoring Template")
    st.write("Upload a CSV with columns matching one of the prediction schemas, then use the API endpoints for scoring.")
    uploaded = st.file_uploader("Upload CSV", type=["csv"])
    if uploaded:
        frame = pd.read_csv(uploaded)
        st.dataframe(frame.head(20), use_container_width=True)
        st.info("For portfolio demos, batch scoring can be implemented by iterating rows through the selected API endpoint.")
