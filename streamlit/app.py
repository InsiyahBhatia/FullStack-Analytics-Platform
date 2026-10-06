"""Streamlit front end for FinSight: model performance dashboard, predictors, batch scoring."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("FINSIGHT_API_KEY", "")
API_HEADERS = {"X-API-Key": API_KEY}
ARTIFACT_ROOT = Path(os.getenv("MODEL_ARTIFACT_DIR", "models/artifacts"))

TASKS = {
    "churn": {"title": "Customer Churn", "positive": "Will Churn", "endpoint": "/predict/churn"},
    "default": {"title": "Loan Default", "positive": "Will Default", "endpoint": "/predict/default"},
    "fraud": {"title": "Fraud Detection", "positive": "Fraud", "endpoint": "/predict/fraud"},
}
PALETTE = {"primary": "#2563eb", "good": "#16a34a", "warn": "#f59e0b", "bad": "#dc2626", "muted": "#94a3b8"}

# Streamlit >= 1.50 deprecates use_container_width in favour of width="stretch".
_ver = tuple(int(x) for x in st.__version__.split(".")[:2] if x.isdigit())
STRETCH = {"width": "stretch"} if _ver >= (1, 50) else {"use_container_width": True}

st.set_page_config(page_title="FinSight ML Workbench", page_icon=":bar_chart:", layout="wide")
st.markdown(
    """
    <style>
      [data-testid="stMetric"] {background: rgba(148,163,184,.10); border-radius: 10px; padding: 10px 14px;}
      .risk-pill {display:inline-block; padding:4px 12px; border-radius:999px; font-weight:600; color:#fff;}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------- data access
@st.cache_data(ttl=60)
def load_artifacts(task: str) -> dict:
    """Read metadata, benchmark table, curves and feature importance for one task."""
    root = ARTIFACT_ROOT / task
    out: dict = {"metadata": None, "benchmarks": None, "curves": None, "importance": None}
    meta = root / "metadata.json"
    if meta.exists():
        out["metadata"] = json.loads(meta.read_text(encoding="utf-8"))
    bench = ARTIFACT_ROOT / f"{task}_benchmarks.csv"
    if bench.exists():
        out["benchmarks"] = pd.read_csv(bench)
    curves = root / "curves.json"
    if curves.exists():
        out["curves"] = json.loads(curves.read_text(encoding="utf-8"))
    imp = root / "feature_importance.csv"
    if imp.exists():
        out["importance"] = pd.read_csv(imp)
    return out


def api_health() -> bool:
    try:
        return requests.get(f"{API_BASE_URL}/health", timeout=3).ok
    except requests.RequestException:
        return False


def post_prediction(endpoint: str, payload: dict) -> dict:
    response = requests.post(f"{API_BASE_URL}{endpoint}", json=payload, headers=API_HEADERS, timeout=30)
    response.raise_for_status()
    return response.json()


def safe_predict(endpoint: str, payload: dict) -> dict | None:
    try:
        return post_prediction(endpoint, payload)
    except requests.HTTPError as exc:
        detail = exc.response.text[:300] if exc.response is not None else str(exc)
        st.error(f"API rejected the request: {detail}")
    except requests.RequestException as exc:
        st.error(f"Could not reach the prediction API at {API_BASE_URL}: {exc}")
    return None


# ---------------------------------------------------------------- charts
def fmt(value, pct: bool = False) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "n/a"
    return f"{value:.1%}" if pct else f"{value:.3f}"


def risk_band(probability: float, threshold: float) -> tuple[str, str]:
    if probability >= max(threshold, 0.5) * 1.5 or probability >= 0.8:
        return "High", PALETTE["bad"]
    if probability >= threshold:
        return "Elevated", PALETTE["warn"]
    return "Low", PALETTE["good"]


def probability_gauge(probability: float, threshold: float) -> go.Figure:
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=probability * 100,
            number={"suffix": "%", "valueformat": ".1f"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": PALETTE["primary"]},
                "steps": [
                    {"range": [0, threshold * 100], "color": "rgba(22,163,74,.18)"},
                    {"range": [threshold * 100, 100], "color": "rgba(220,38,38,.18)"},
                ],
                "threshold": {"line": {"color": PALETTE["bad"], "width": 4}, "value": threshold * 100},
            },
        )
    )
    fig.update_layout(height=240, margin=dict(l=20, r=20, t=30, b=10))
    return fig


def roc_pr_figure(curves: dict, metrics: dict) -> go.Figure:
    from plotly.subplots import make_subplots

    fig = make_subplots(rows=1, cols=2, subplot_titles=(f"ROC (AUC {fmt(metrics.get('roc_auc'))})",
                                                         f"Precision-Recall (AP {fmt(metrics.get('pr_auc'))})"))
    roc, pr = curves["roc"], curves["pr"]
    fig.add_trace(go.Scatter(x=roc["fpr"], y=roc["tpr"], mode="lines", name="ROC", line=dict(color=PALETTE["primary"])), 1, 1)
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(dash="dash", color=PALETTE["muted"]),
                             showlegend=False), 1, 1)
    fig.add_trace(go.Scatter(x=pr["recall"], y=pr["precision"], mode="lines", name="PR", line=dict(color=PALETTE["good"])), 1, 2)
    base = metrics.get("base_rate")
    if base:
        fig.add_hline(y=base, line_dash="dash", line_color=PALETTE["muted"], row=1, col=2,
                      annotation_text="base rate")
    fig.update_xaxes(title_text="False positive rate", row=1, col=1)
    fig.update_yaxes(title_text="True positive rate", row=1, col=1)
    fig.update_xaxes(title_text="Recall", row=1, col=2)
    fig.update_yaxes(title_text="Precision", row=1, col=2)
    fig.update_layout(height=360, showlegend=False, margin=dict(l=10, r=10, t=40, b=10))
    return fig


def calibration_figure(cal: dict) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Perfect", line=dict(dash="dash", color=PALETTE["muted"])))
    fig.add_trace(go.Scatter(x=cal["mean_predicted"], y=cal["fraction_positive"], mode="lines+markers",
                             name="Model", line=dict(color=PALETTE["primary"])))
    fig.update_layout(height=340, xaxis_title="Mean predicted probability", yaxis_title="Observed rate",
                      margin=dict(l=10, r=10, t=30, b=10), title="Calibration")
    return fig


def confusion_figure(m: dict) -> go.Figure:
    z = [[m["tn"], m["fp"]], [m["fn"], m["tp"]]]
    fig = go.Figure(go.Heatmap(z=z, x=["Pred negative", "Pred positive"], y=["Actual negative", "Actual positive"],
                               text=z, texttemplate="%{text:,}", colorscale="Blues", showscale=False))
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=30, b=10), title="Confusion matrix (test set)")
    return fig


def importance_figure(frame: pd.DataFrame, top: int = 15) -> go.Figure:
    top_df = frame.sort_values("importance", ascending=False).head(top).iloc[::-1]
    fig = go.Figure(go.Bar(x=top_df["importance"], y=top_df["feature"], orientation="h", marker_color=PALETTE["primary"]))
    fig.update_layout(height=max(320, 24 * len(top_df) + 80), margin=dict(l=10, r=10, t=30, b=10),
                      title=f"Top {len(top_df)} features")
    return fig


def leaderboard_figure(bench: pd.DataFrame, selected: str) -> go.Figure:
    bench = bench.sort_values("roc_auc")
    colors = [PALETTE["primary"] if a == selected else PALETTE["muted"] for a in bench["algorithm"]]
    fig = go.Figure(go.Bar(x=bench["roc_auc"], y=bench["algorithm"], orientation="h", marker_color=colors,
                           text=bench["roc_auc"].round(3), textposition="outside"))
    lo = max(0.0, float(bench["roc_auc"].min()) - 0.05)
    fig.update_layout(height=max(220, 60 * len(bench)), xaxis=dict(range=[lo, 1.0], title="Test ROC-AUC"),
                      margin=dict(l=10, r=40, t=30, b=10), title="Candidate leaderboard")
    return fig


# ---------------------------------------------------------------- pages
def page_overview() -> None:
    st.header("Model performance")
    st.caption("Metrics are computed on a held-out test split. Threshold and calibration are fit on a separate "
               "validation slice, so these numbers are not tuned on the test data.")
    cols = st.columns(len(TASKS))
    for col, (task, cfg) in zip(cols, TASKS.items()):
        art = load_artifacts(task)
        meta = art["metadata"]
        with col:
            st.subheader(cfg["title"])
            if not meta:
                st.info("No trained model found. Run `python -m models.train_all`.")
                continue
            m = meta["metrics"]
            st.metric("ROC-AUC", fmt(m.get("roc_auc")), help="Test-set ROC-AUC")
            c1, c2 = st.columns(2)
            c1.metric("PR-AUC", fmt(m.get("pr_auc")))
            c2.metric("Recall", fmt(m.get("recall"), pct=True))
            st.caption(f"{meta['algorithm']} v{meta['version']} | threshold {meta['threshold']:.2f}")

    st.divider()
    task = st.radio("Inspect model", list(TASKS), format_func=lambda t: TASKS[t]["title"], horizontal=True)
    art = load_artifacts(task)
    meta = art["metadata"]
    if not meta:
        st.warning(f"No artifacts found under {ARTIFACT_ROOT / task}.")
        return
    m, pipe = meta["metrics"], meta.get("pipeline", {})

    k = st.columns(6)
    k[0].metric("ROC-AUC", fmt(m.get("roc_auc")))
    k[1].metric("CV ROC-AUC", fmt(m.get("cv_roc_auc")))
    k[2].metric("Precision", fmt(m.get("precision"), pct=True))
    k[3].metric("Recall", fmt(m.get("recall"), pct=True))
    k[4].metric("KS", fmt(m.get("ks")))
    k[5].metric("Lift @ top 10%", f"{m['lift_top10']:.1f}x" if "lift_top10" in m else "n/a")

    if "expected_cost" in m:
        saved = m["baseline_cost"] - m["expected_cost"]
        c = st.columns(3)
        c[0].metric("Expected cost (test)", f"${m['expected_cost']:,.0f}")
        c[1].metric("Cost if nothing flagged", f"${m['baseline_cost']:,.0f}")
        c[2].metric("Savings from model", f"${saved:,.0f}")

    tab_curves, tab_conf, tab_feat, tab_bench, tab_meta = st.tabs(
        ["Curves", "Confusion & calibration", "Feature importance", "Candidates", "Model card"]
    )
    with tab_curves:
        if art["curves"]:
            st.plotly_chart(roc_pr_figure(art["curves"], m), **STRETCH)
        else:
            st.info("Curves not available. Re-run training to generate curves.json.")
    with tab_conf:
        c1, c2 = st.columns(2)
        if "tp" in m:
            c1.plotly_chart(confusion_figure(m), **STRETCH)
        else:
            c1.info("Re-run training to get the confusion matrix.")
        if art["curves"] and "calibration" in art["curves"]:
            c2.plotly_chart(calibration_figure(art["curves"]["calibration"]), **STRETCH)
        else:
            c2.info("Calibration curve not available for this model.")
    with tab_feat:
        if art["importance"] is not None:
            st.plotly_chart(importance_figure(art["importance"]), **STRETCH)
        else:
            st.info("feature_importance.csv not found.")
    with tab_bench:
        if art["benchmarks"] is not None:
            st.plotly_chart(leaderboard_figure(art["benchmarks"], meta["algorithm"]), **STRETCH)
            st.dataframe(art["benchmarks"], **STRETCH, hide_index=True)
        else:
            st.info("Benchmark table not found.")
    with tab_meta:
        c1, c2 = st.columns(2)
        c1.json({k: v for k, v in pipe.items()})
        c2.json({"features": meta["features"], "target": meta["target"], "threshold": meta["threshold"]})


def render_result(result: dict, task: str) -> None:
    meta = load_artifacts(task)["metadata"] or {}
    threshold = float(meta.get("threshold", 0.5))
    probability = float(result["probability"])
    band, color = risk_band(probability, threshold)
    left, right = st.columns([1, 1])
    with left:
        st.plotly_chart(probability_gauge(probability, threshold), **STRETCH)
    with right:
        st.markdown(f"### {result['prediction']}")
        st.markdown(f'<span class="risk-pill" style="background:{color}">{band} risk</span>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        c1.metric("Probability", f"{probability:.1%}")
        c2.metric("Decision threshold", f"{threshold:.0%}")
        st.caption(f"Model {result['model']} v{result['model_version']} | {result['inference_ms']} ms")
        st.write("Key drivers: " + ", ".join(f"`{d}`" for d in result["top_drivers"]))
    if result.get("fallback"):
        st.warning("Using heuristic fallback because a trained model artifact is not available yet.")


def page_churn() -> None:
    st.header("Customer churn")
    with st.form("churn_form"):
        c1, c2 = st.columns(2)
        with c1:
            tenure = st.number_input("Tenure (months)", min_value=0, value=12)
            monthly_charges = st.number_input("Monthly charges", min_value=0.0, value=100.0)
            contract_type = st.selectbox("Contract type", ["Month-to-month", "One year", "Two year"])
            payment_method = st.selectbox(
                "Payment method",
                ["Electronic check", "Mailed check", "Bank transfer (automatic)", "Credit card (automatic)"],
            )
            internet_service = st.selectbox("Internet service", ["DSL", "Fiber optic", "No"])
        with c2:
            online_security = st.selectbox("Online security", ["No", "Yes"])
            tech_support = st.selectbox("Tech support", ["No", "Yes"])
            paperless_billing = st.selectbox("Paperless billing", ["Yes", "No"])
            streaming_tv = st.selectbox("Streaming TV", ["No", "Yes"])
        submitted = st.form_submit_button("Predict churn", type="primary")
    if submitted:
        payload = {
            "tenure": tenure, "monthly_charges": monthly_charges, "total_charges": tenure * monthly_charges,
            "contract_type": contract_type, "payment_method": payment_method, "internet_service": internet_service,
            "online_security": online_security, "tech_support": tech_support,
            "paperless_billing": paperless_billing, "streaming_tv": streaming_tv,
        }
        result = safe_predict(TASKS["churn"]["endpoint"], payload)
        if result:
            render_result(result, "churn")
            if contract_type == "Month-to-month":
                with st.spinner("Scoring a two-year contract for comparison..."):
                    alt = safe_predict(TASKS["churn"]["endpoint"], {**payload, "contract_type": "Two year"})
                if alt:
                    delta = result["probability"] - alt["probability"]
                    st.info(f"What-if: moving this customer to a two-year contract changes churn probability "
                            f"from {result['probability']:.1%} to {alt['probability']:.1%} ({-delta:+.1%}).")


def page_default() -> None:
    st.header("Loan default")
    with st.form("default_form"):
        c1, c2 = st.columns(2)
        with c1:
            fico_score = st.slider("FICO score", 300, 900, 660)
            debt_ratio = st.number_input("Debt ratio", min_value=0.0, value=22.0)
            loan_amount = st.number_input("Loan amount", min_value=1.0, value=12000.0)
            grade = st.selectbox("Grade", list("ABCDEFG"), index=2)
            purpose = st.selectbox(
                "Purpose", ["debt_consolidation", "credit_card", "home_improvement", "small_business", "other"]
            )
            verification_status = st.selectbox("Verification status", ["Not Verified", "Source Verified", "Verified"])
        with c2:
            annual_inc = st.number_input("Annual income", min_value=0.0, value=75000.0)
            emp_length = st.number_input("Employment length (years)", min_value=0.0, value=8.0)
            home_ownership = st.selectbox("Home ownership", ["RENT", "MORTGAGE", "OWN", "OTHER"])
            revol_util = st.number_input("Revolving utilization %", min_value=0.0, value=35.0)
            revol_bal = st.number_input("Revolving balance", min_value=0.0, value=12000.0)
            delinq_2yrs = st.number_input("Delinquencies (2yrs)", min_value=0, value=0)
            pub_rec = st.number_input("Public records", min_value=0, value=0)
            open_acc = st.number_input("Open credit lines", min_value=0, value=12)
        submitted = st.form_submit_button("Predict default", type="primary")
    if submitted:
        result = safe_predict(
            TASKS["default"]["endpoint"],
            {
                "fico_score": fico_score, "debt_ratio": debt_ratio, "loan_amount": loan_amount, "grade": grade,
                "purpose": purpose, "annual_inc": annual_inc, "emp_length": emp_length, "revol_bal": revol_bal,
                "revol_util": revol_util, "delinq_2yrs": delinq_2yrs, "pub_rec": pub_rec, "open_acc": open_acc,
                "home_ownership": home_ownership, "verification_status": verification_status,
            },
        )
        if result:
            render_result(result, "default")


def page_fraud() -> None:
    st.header("Fraud detection")
    with st.form("fraud_form"):
        transaction_amt = st.number_input("Transaction amount", min_value=1.0, value=250.0)
        c1, c2 = st.columns(2)
        with c1:
            device_type = st.selectbox("Device type", ["desktop", "mobile", "unknown"])
            browser = st.selectbox("Browser", ["chrome", "safari", "firefox", "edge", "unknown"])
        with c2:
            card_type = st.selectbox("Card type", ["visa", "mastercard", "american express", "discover", "unknown"])
            email_domain = st.text_input("Email domain", value="gmail.com")
        provide_context = st.checkbox("Provide velocity & distance context (advanced)", value=False)
        context: dict = {}
        if provide_context:
            st.caption("When left off, these features are median-imputed from the training data.")
            c1, c2 = st.columns(2)
            with c1:
                context["dist1"] = st.number_input("Dist 1 (km)", min_value=0.0, value=0.0)
                context["txn_cnt_1h"] = st.number_input("Tx count (1h)", min_value=0, value=0)
                context["txn_amt_sum_24h"] = st.number_input("Tx amount sum (24h)", min_value=0.0, value=0.0)
            with c2:
                context["dist2"] = st.number_input("Dist 2 (km)", min_value=0.0, value=0.0)
                context["txn_cnt_24h"] = st.number_input("Tx count (24h)", min_value=0, value=0)
                context["txn_amt_std_24h"] = st.number_input("Tx amount std (24h)", min_value=0.0, value=0.0)
        submitted = st.form_submit_button("Predict fraud", type="primary")
    if submitted:
        payload = {"transaction_amt": transaction_amt, "device_type": device_type, "card_type": card_type,
                   "browser": browser, "email_domain": email_domain, **context}
        result = safe_predict(TASKS["fraud"]["endpoint"], payload)
        if result:
            render_result(result, "fraud")


def page_batch() -> None:
    st.header("Batch scoring")
    st.write("Upload a CSV whose columns match the chosen model's request fields. Each row is scored through the API.")
    task = st.selectbox("Model", list(TASKS), format_func=lambda t: TASKS[t]["title"])
    meta = load_artifacts(task)["metadata"]
    if meta:
        st.caption("Model features: " + ", ".join(f"`{f}`" for f in meta["features"]))
    uploaded = st.file_uploader("Upload CSV", type=["csv"])
    max_rows = st.number_input("Max rows to score", min_value=1, max_value=5000, value=500)
    if not uploaded:
        return
    frame = pd.read_csv(uploaded).head(int(max_rows))
    st.dataframe(frame.head(20), **STRETCH)
    if not st.button("Score file", type="primary"):
        return

    results, errors = [], []
    progress = st.progress(0.0)
    for i, record in enumerate(frame.to_dict(orient="records")):
        clean = {k: v for k, v in record.items() if pd.notna(v)}
        try:
            r = post_prediction(TASKS[task]["endpoint"], clean)
            results.append({"row": i, "prediction": r["prediction"], "probability": r["probability"]})
        except requests.RequestException as exc:
            detail = exc.response.text[:120] if getattr(exc, "response", None) is not None else str(exc)
            errors.append({"row": i, "error": detail})
            results.append({"row": i, "prediction": None, "probability": None})
        progress.progress((i + 1) / len(frame))

    scored = frame.reset_index(drop=True).join(pd.DataFrame(results).set_index("row"))
    ok = scored.dropna(subset=["probability"])
    c = st.columns(3)
    c[0].metric("Rows scored", f"{len(ok):,}")
    c[1].metric("Rows failed", f"{len(errors):,}")
    if len(ok):
        c[2].metric("Mean probability", f"{ok['probability'].mean():.1%}")
        fig = go.Figure(go.Histogram(x=ok["probability"], nbinsx=20, marker_color=PALETTE["primary"]))
        fig.update_layout(height=280, xaxis_title="Predicted probability", yaxis_title="Rows",
                          margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, **STRETCH)
    st.dataframe(scored, **STRETCH)
    st.download_button("Download scored CSV", scored.to_csv(index=False).encode("utf-8"), "scored.csv", "text/csv")
    if errors:
        with st.expander(f"{len(errors)} row errors"):
            st.dataframe(pd.DataFrame(errors), **STRETCH)


import business  # noqa: E402  (sibling module; streamlit puts this dir on sys.path)

PAGES = {
    **{name: (lambda n=name: business.render(n)) for name in business.BUSINESS_PAGES},
    "Model performance": page_overview,
    "Churn predictor": page_churn,
    "Loan default predictor": page_default,
    "Fraud predictor": page_fraud,
    "Batch scoring": page_batch,
}

with st.sidebar:
    st.title("FinSight")
    page = st.radio("Navigate", list(PAGES), label_visibility="collapsed")
    st.divider()
    if api_health():
        st.success("API online")
    else:
        st.error("API unreachable")
    if not API_KEY:
        st.warning("FINSIGHT_API_KEY is not set; prediction calls will be rejected.")

PAGES[page]()
