"""Question-driven business dashboards for FinSight (churn, lending, fraud, data health).

Each section is framed as a business question, shows the evidence, and states the
answer in plain language. Data comes from the PostgreSQL warehouse (WAREHOUSE_URL);
when it is unreachable the pages fall back to a clearly labelled synthetic demo set.
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

_ver = tuple(int(x) for x in st.__version__.split(".")[:2] if x.isdigit())
STRETCH = {"width": "stretch"} if _ver >= (1, 50) else {"use_container_width": True}

WAREHOUSE_URL = os.getenv("WAREHOUSE_URL", "")
PRIMARY, BAD, GOOD, WARN, MUTED = "#2563eb", "#dc2626", "#16a34a", "#f59e0b", "#94a3b8"

QUERIES = {
    "churn": """SELECT customer_id, tenure, monthly_charges, total_charges, contract_type, payment_method,
                paperless_billing, internet_service, online_security, tech_support, streaming_tv,
                churn_flag, churn_probability, tenure_group FROM fact_churn""",
    "loan": """SELECT loan_amount, interest_rate, grade, purpose, term, dti, credit_score, loan_status,
               issue_date, default_flag, annual_income, home_ownership FROM fact_loan""",
    "txn": """SELECT transaction_id, transaction_amt, product_cd, transaction_dt, device_type, card4, card6,
              email_domain, is_fraud FROM fact_transaction ORDER BY transaction_dt DESC LIMIT 300000""",
    "etl": """SELECT dag_id, task_id, target_table, records_read, records_written, records_failed, status,
              started_at, completed_at, error_message FROM etl_metadata ORDER BY started_at DESC LIMIT 2000""",
}


# ------------------------------------------------------------------ data
def _demo(seed: int = 11) -> dict[str, pd.DataFrame]:
    rng = np.random.RandomState(seed)
    n = 5000
    contract = rng.choice(["Month-to-month", "One year", "Two year"], n, p=[0.55, 0.21, 0.24])
    tenure = np.where(contract == "Month-to-month", rng.randint(0, 40, n), rng.randint(6, 72, n))
    internet = rng.choice(["DSL", "Fiber optic", "No"], n, p=[0.34, 0.44, 0.22])
    monthly = np.where(internet == "Fiber optic", rng.normal(85, 15, n), np.where(internet == "DSL", rng.normal(55, 12, n), rng.normal(22, 4, n))).clip(18, 120)
    payment = rng.choice(["Electronic check", "Mailed check", "Bank transfer (automatic)", "Credit card (automatic)"], n)
    logit = -1.3 + 1.4 * (contract == "Month-to-month") - 0.03 * tenure + 0.6 * (internet == "Fiber optic") + 0.5 * (payment == "Electronic check")
    p = 1 / (1 + np.exp(-logit))
    churn = pd.DataFrame({
        "customer_id": [f"C{i:05d}" for i in range(n)], "tenure": tenure, "monthly_charges": monthly.round(2),
        "total_charges": (tenure * monthly).round(2), "contract_type": contract, "payment_method": payment,
        "paperless_billing": rng.choice(["Yes", "No"], n), "internet_service": internet,
        "online_security": rng.choice(["Yes", "No"], n), "tech_support": rng.choice(["Yes", "No"], n),
        "streaming_tv": rng.choice(["Yes", "No"], n), "churn_flag": (rng.uniform(size=n) < p).astype(int),
        "churn_probability": p.round(4),
    })
    churn["tenure_group"] = pd.cut(churn.tenure, [-1, 12, 24, 48, 100], labels=["0-12", "13-24", "25-48", "49+"]).astype(str)

    m = 20000
    grade = rng.choice(list("ABCDEFG"), m, p=[0.17, 0.30, 0.29, 0.14, 0.07, 0.025, 0.005])
    gi = pd.Series(grade).map({g: i for i, g in enumerate("ABCDEFG")}).to_numpy()
    rate = (6 + gi * 2.6 + rng.normal(0, 1, m)).clip(5, 31)
    dflt = (rng.uniform(size=m) < (0.04 + gi * 0.045)).astype(int)
    loan = pd.DataFrame({
        "loan_amount": rng.randint(1000, 35000, m), "interest_rate": rate.round(2), "grade": grade,
        "purpose": rng.choice(["debt_consolidation", "credit_card", "home_improvement", "small_business", "other"], m, p=[0.5, 0.2, 0.1, 0.05, 0.15]),
        "term": rng.choice([" 36 months", " 60 months"], m, p=[0.7, 0.3]), "dti": rng.uniform(0, 40, m).round(1),
        "credit_score": (720 - gi * 22 + rng.normal(0, 20, m)).clip(500, 850).astype(int),
        "loan_status": np.where(dflt == 1, "Charged Off", "Fully Paid"),
        "issue_date": pd.to_datetime("2015-01-01") + pd.to_timedelta(rng.randint(0, 365 * 4, m), unit="D"),
        "default_flag": dflt, "annual_income": rng.lognormal(11, 0.5, m).round(0),
        "home_ownership": rng.choice(["RENT", "MORTGAGE", "OWN"], m, p=[0.45, 0.4, 0.15]),
    })

    k = 30000
    dev = rng.choice(["desktop", "mobile", "unknown"], k, p=[0.5, 0.35, 0.15])
    dom = rng.choice(["gmail.com", "yahoo.com", "hotmail.com", "anonymous.com", "outlook.com", "protonmail.com"], k, p=[0.4, 0.2, 0.15, 0.1, 0.1, 0.05])
    amt = rng.lognormal(4.2, 1.1, k).round(2)
    ts = pd.Timestamp("2026-06-01") + pd.to_timedelta(rng.randint(0, 90 * 86400, k), unit="s")
    hour = ts.hour
    pf = 0.015 + 0.03 * (dev == "mobile") + 0.05 * (dom == "anonymous.com") + 0.04 * ((hour < 5)) + 0.02 * (amt > 400)
    txn = pd.DataFrame({
        "transaction_id": np.arange(k), "transaction_amt": amt, "product_cd": rng.choice(list("WCRHS"), k),
        "transaction_dt": ts, "device_type": dev, "card4": rng.choice(["visa", "mastercard", "discover", "american express"], k),
        "card6": rng.choice(["debit", "credit"], k), "email_domain": dom, "is_fraud": (rng.uniform(size=k) < pf).astype(int),
    })
    start = pd.Timestamp("2026-09-01") - pd.to_timedelta(np.arange(60)[::-1], unit="D")
    etl = pd.DataFrame({
        "dag_id": "finsight_pipeline", "task_id": rng.choice(["load_churn", "load_lending", "load_fraud", "feature_store"], 60),
        "target_table": rng.choice(["fact_churn", "fact_loan", "fact_transaction"], 60),
        "records_read": rng.randint(1e4, 5e5, 60), "status": rng.choice(["success", "failed"], 60, p=[0.93, 0.07]),
        "started_at": start, "completed_at": start + pd.to_timedelta(rng.randint(60, 900, 60), unit="s"),
        "error_message": None,
    })
    etl["records_written"] = (etl.records_read * np.where(etl.status == "success", 1, 0.2)).astype(int)
    etl["records_failed"] = etl.records_read - etl.records_written
    return {"churn": churn, "loan": loan, "txn": txn, "etl": etl}


@st.cache_data(ttl=300, show_spinner="Loading warehouse data...")
def load_data() -> tuple[dict[str, pd.DataFrame], str]:
    """Return (frames, source) where source is 'warehouse' or 'demo'."""
    if WAREHOUSE_URL:
        try:
            from sqlalchemy import create_engine

            engine = create_engine(WAREHOUSE_URL, connect_args={"connect_timeout": 5})
            frames = {k: pd.read_sql(q, engine) for k, q in QUERIES.items()}
            if len(frames["churn"]) or len(frames["loan"]) or len(frames["txn"]):
                return frames, "warehouse"
        except Exception as exc:  # fall through to demo data
            return _demo(), f"demo (warehouse error: {str(exc)[:80]})"
    return _demo(), "demo"


# ------------------------------------------------------------------ helpers
def _pct(x: float) -> str:
    return f"{x:.1%}"


def _money(x: float) -> str:
    return f"${x/1e6:,.2f}M" if abs(x) >= 1e6 else f"${x:,.0f}"


def _answer(text: str) -> None:
    st.success(f"**Answer:** {text}")


def _rate_chart(df: pd.DataFrame, cat: str, rate_col: str, count_col: str, overall: float, title: str, order=None) -> go.Figure:
    d = df.copy()
    if order:
        d[cat] = pd.Categorical(d[cat], order, ordered=True)
        d = d.sort_values(cat)
    else:
        d = d.sort_values(rate_col, ascending=False)
    colors = [BAD if r > overall * 1.15 else (GOOD if r < overall * 0.85 else PRIMARY) for r in d[rate_col]]
    fig = go.Figure(go.Bar(x=d[cat].astype(str), y=d[rate_col], marker_color=colors,
                           text=[f"{r:.1%}" for r in d[rate_col]], textposition="outside",
                           customdata=d[count_col], hovertemplate="%{x}<br>rate %{y:.1%}<br>n=%{customdata:,}<extra></extra>"))
    fig.add_hline(y=overall, line_dash="dash", line_color=MUTED, annotation_text=f"overall {overall:.1%}")
    fig.update_layout(title=title, height=330, yaxis_tickformat=".0%", margin=dict(l=10, r=10, t=40, b=10))
    return fig


def _segment(df: pd.DataFrame, col: str, flag: str, value: str | None = None) -> pd.DataFrame:
    g = df.groupby(col, observed=True).agg(rate=(flag, "mean"), n=(flag, "size"), events=(flag, "sum"))
    if value:
        g["value_lost"] = df[df[flag] == 1].groupby(col, observed=True)[value].sum().reindex(g.index).fillna(0)
    return g.reset_index()


# ------------------------------------------------------------------ pages
def page_executive(frames: dict) -> None:
    st.header("Executive summary")
    st.caption("The questions a leadership team asks first, answered across churn, lending, fraud and data health.")
    ch, ln, tx, etl = frames["churn"], frames["loan"], frames["txn"], frames["etl"]
    churn_rate = ch.churn_flag.mean() if len(ch) else float("nan")
    rev_risk = (ch[ch.churn_flag == 1].monthly_charges.sum() * 12) if len(ch) else 0
    dflt = ln.default_flag.mean() if len(ln) else float("nan")
    loss = (ln[ln.default_flag == 1].loan_amount.sum()) if len(ln) else 0
    fr = tx.is_fraud.mean() if len(tx) else float("nan")
    fr_loss = tx[tx.is_fraud == 1].transaction_amt.sum() if len(tx) else 0
    etl_ok = (etl.status.str.lower().isin(["success", "completed"])).mean() if len(etl) else float("nan")

    c = st.columns(4)
    c[0].metric("Customer churn rate", _pct(churn_rate), help="Share of customers who left")
    c[1].metric("Annual revenue at risk", _money(rev_risk), help="12 x monthly charges of churned customers")
    c[2].metric("Loan default rate", _pct(dflt))
    c[3].metric("Principal in default", _money(loss))
    c = st.columns(4)
    c[0].metric("Fraud rate", _pct(fr))
    c[1].metric("Fraud exposure", _money(fr_loss))
    c[2].metric("ETL success rate", _pct(etl_ok))
    c[3].metric("Customers / Loans / Txns", f"{len(ch):,} / {len(ln):,} / {len(tx):,}")

    st.subheader("Where should we act first?")
    items = []
    if len(ch):
        seg = _segment(ch, "contract_type", "churn_flag", "monthly_charges").sort_values("value_lost", ascending=False).iloc[0]
        items.append(f"**Churn:** `{seg.contract_type}` customers churn at {_pct(seg.rate)} and account for {_money(seg.value_lost * 12)} of annual revenue lost.")
    if len(ln):
        seg = _segment(ln, "grade", "default_flag", "loan_amount").sort_values("value_lost", ascending=False).iloc[0]
        items.append(f"**Lending:** grade `{seg.grade}` loans carry the largest defaulted principal ({_money(seg.value_lost)}, default rate {_pct(seg.rate)}).")
    if len(tx):
        seg = _segment(tx, "email_domain", "is_fraud")
        seg = seg[seg.n >= 200].sort_values("rate", ascending=False).iloc[0]
        items.append(f"**Fraud:** email domain `{seg.email_domain}` has a {_pct(seg.rate)} fraud rate across {seg.n:,} transactions.")
    if len(etl):
        failed = etl[~etl.status.str.lower().isin(["success", "completed"])]
        items.append(f"**Data health:** {len(failed)} failed pipeline runs in the latest {len(etl)} runs." if len(failed) else "**Data health:** all recent pipeline runs succeeded.")
    for it in items:
        st.markdown(f"- {it}")


def page_churn(frames: dict) -> None:
    st.header("Customer churn: who leaves, why it matters, who to call")
    ch = frames["churn"]
    if ch.empty:
        st.info("No churn data available.")
        return
    overall = ch.churn_flag.mean()
    annual_rev = ch.monthly_charges.sum() * 12
    lost = ch[ch.churn_flag == 1].monthly_charges.sum() * 12

    st.subheader("1. How big is the problem?")
    c = st.columns(4)
    c[0].metric("Churn rate", _pct(overall))
    c[1].metric("Customers lost", f"{int(ch.churn_flag.sum()):,}")
    c[2].metric("Annual revenue lost", _money(lost))
    c[3].metric("Share of revenue lost", _pct(lost / annual_rev if annual_rev else 0))
    ch_ = ch[ch.churn_flag == 1]
    st.caption(f"Churned customers pay ${ch_.monthly_charges.mean():,.0f}/month on average vs "
               f"${ch[ch.churn_flag == 0].monthly_charges.mean():,.0f} for retained ones, "
               f"and left after {ch_.tenure.median():.0f} months (median).")

    st.subheader("2. Which segments churn the most?")
    dims = {"contract_type": "Contract", "tenure_group": "Tenure (months)", "internet_service": "Internet service",
            "payment_method": "Payment method", "paperless_billing": "Paperless billing", "tech_support": "Tech support",
            "online_security": "Online security"}
    dim = st.selectbox("Break down by", list(dims), format_func=dims.get)
    seg = _segment(ch, dim, "churn_flag", "monthly_charges")
    order = ["0-12", "13-24", "25-48", "49+"] if dim == "tenure_group" else None
    st.plotly_chart(_rate_chart(seg, dim, "rate", "n", overall, f"Churn rate by {dims[dim].lower()}", order), **STRETCH)

    st.subheader("3. Where is the revenue loss concentrated?")
    rows = []
    for d in dims:
        s = _segment(ch, d, "churn_flag", "monthly_charges")
        s = s[s.n >= 50]
        for _, r in s.iterrows():
            rows.append({"segment": f"{dims[d]}: {r[d]}", "customers": r.n, "churn_rate": r.rate,
                         "annual_revenue_lost": r.value_lost * 12, "excess_vs_overall": (r.rate - overall) * r.n})
    top = pd.DataFrame(rows).sort_values("annual_revenue_lost", ascending=False).head(10)
    fig = px.bar(top.iloc[::-1], x="annual_revenue_lost", y="segment", orientation="h", color="churn_rate",
                 color_continuous_scale="Reds", labels={"annual_revenue_lost": "Annual revenue lost ($)", "segment": ""})
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, **STRETCH)
    worst = top.iloc[0]
    _answer(f"{worst.segment} is the single largest source of lost revenue ({_money(worst.annual_revenue_lost)} a year at a "
            f"{_pct(worst.churn_rate)} churn rate vs {_pct(overall)} overall).")

    st.subheader("4. What could a retention offer recover?")
    mtm = ch[ch.contract_type == "Month-to-month"]
    longc = ch[ch.contract_type != "Month-to-month"]
    if len(mtm) and len(longc):
        c1, c2 = st.columns([1, 2])
        conv = c1.slider("Share of month-to-month customers moved to a longer contract", 0, 50, 10, format="%d%%") / 100
        gap = mtm.churn_flag.mean() - longc.churn_flag.mean()
        saved = len(mtm) * conv * max(gap, 0)
        recovered = saved * mtm.monthly_charges.mean() * 12
        c2.metric("Estimated customers retained", f"{saved:,.0f}")
        c2.metric("Estimated annual revenue recovered", _money(recovered),
                  help=f"Month-to-month churn exceeds longer-contract churn by {gap:.1%}. Observed association, not a causal estimate.")

    st.subheader("5. Which active customers should we contact now?")
    active = ch[ch.churn_flag == 0].copy()
    if "churn_probability" in active and active.churn_probability.notna().any():
        active["annual_value"] = active.monthly_charges * 12
        active["expected_loss"] = active.churn_probability * active.annual_value
        n = st.slider("List size", 10, 200, 25)
        cols = ["customer_id", "contract_type", "tenure", "monthly_charges", "churn_probability", "expected_loss"]
        out = active.sort_values("expected_loss", ascending=False).head(n)[cols]
        st.dataframe(out.style.format({"monthly_charges": "${:,.0f}", "churn_probability": "{:.0%}", "expected_loss": "${:,.0f}"}),
                     **STRETCH, hide_index=True)
        st.download_button("Download call list", out.to_csv(index=False).encode(), "retention_call_list.csv", "text/csv")
        _answer(f"The top {n} active customers represent {_money(out.expected_loss.sum())} of expected annual revenue loss; "
                "prioritised by churn probability x annual value.")
    else:
        st.info("churn_probability is empty in the warehouse; score customers via the API to enable the call list.")


def page_lending(frames: dict) -> None:
    st.header("Lending: where do we lose money and are we priced for it?")
    ln = frames["loan"].copy()
    if ln.empty:
        st.info("No lending data available.")
        return
    overall = ln.default_flag.mean()
    ln["issue_date"] = pd.to_datetime(ln.issue_date, errors="coerce")
    ln["term"] = ln.term.astype(str).str.strip()
    ln["dti_bucket"] = pd.cut(ln.dti, [-1, 10, 20, 30, 1000], labels=["<10", "10-20", "20-30", "30+"]).astype(str)
    ln["fico_band"] = pd.cut(ln.credit_score, [0, 600, 660, 700, 740, 900], labels=["<600", "600-659", "660-699", "700-739", "740+"]).astype(str)

    st.subheader("1. How much of the book is in default?")
    c = st.columns(4)
    c[0].metric("Loans", f"{len(ln):,}")
    c[1].metric("Default rate", _pct(overall))
    c[2].metric("Defaulted principal", _money(ln[ln.default_flag == 1].loan_amount.sum()))
    c[3].metric("Principal-weighted default rate", _pct(ln[ln.default_flag == 1].loan_amount.sum() / ln.loan_amount.sum()))

    st.subheader("2. Which borrower segments default most?")
    dims = {"grade": "Grade", "purpose": "Purpose", "term": "Term", "dti_bucket": "Debt-to-income", "fico_band": "FICO band",
            "home_ownership": "Home ownership"}
    dim = st.selectbox("Break down by", list(dims), format_func=dims.get)
    seg = _segment(ln, dim, "default_flag", "loan_amount")
    order = {"grade": list("ABCDEFG"), "dti_bucket": ["<10", "10-20", "20-30", "30+"],
             "fico_band": ["<600", "600-659", "660-699", "700-739", "740+"]}.get(dim)
    st.plotly_chart(_rate_chart(seg, dim, "rate", "n", overall, f"Default rate by {dims[dim].lower()}", order), **STRETCH)

    st.subheader("3. Is the interest rate covering the risk?")
    g = ln.groupby("grade").agg(avg_rate=("interest_rate", "mean"), default_rate=("default_flag", "mean"), n=("grade", "size")).reset_index()
    lgd = st.slider("Assumed loss given default (share of principal lost)", 0.3, 1.0, 0.6, 0.05)
    g["expected_loss"] = g.default_rate * lgd * 100
    g["margin_pts"] = g.avg_rate - g.expected_loss
    fig = go.Figure()
    fig.add_bar(x=g.grade, y=g.avg_rate, name="Avg interest rate (%)", marker_color=PRIMARY)
    fig.add_bar(x=g.grade, y=g.expected_loss, name="Expected credit loss (%)", marker_color=BAD)
    fig.add_scatter(x=g.grade, y=g.margin_pts, name="Margin after losses (pts)", mode="lines+markers", line=dict(color=GOOD, width=3))
    fig.update_layout(barmode="group", height=360, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="% of principal")
    st.plotly_chart(fig, **STRETCH)
    neg = g[g.margin_pts < 0]
    if len(neg):
        _answer(f"Grades {', '.join(neg.grade)} are priced below expected losses at {lgd:.0%} loss-given-default; "
                "interest income there does not cover credit losses before funding and servicing costs.")
    else:
        best = g.sort_values("margin_pts").iloc[-1]
        _answer(f"All grades earn more than expected losses at {lgd:.0%} loss-given-default; grade {best.grade} has the widest margin "
                f"({best.margin_pts:.1f} pts). Funding and servicing costs are not included.")

    st.subheader("4. Are newer cohorts performing better or worse?")
    if ln.issue_date.notna().any():
        ln["vintage"] = ln.issue_date.dt.to_period("Q").dt.to_timestamp()
        v = ln.groupby("vintage").agg(rate=("default_flag", "mean"), n=("default_flag", "size")).reset_index()
        v = v[v.n >= 100]
        fig = px.line(v, x="vintage", y="rate", markers=True, labels={"rate": "Default rate", "vintage": "Issue quarter"})
        fig.update_layout(height=300, yaxis_tickformat=".0%", margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, **STRETCH)
        st.caption("Recent vintages look better partly because they have had less time to default (right-censoring).")

    st.subheader("5. Portfolio concentration")
    p = ln.groupby("grade").loan_amount.sum().reset_index()
    fig = px.pie(p, names="grade", values="loan_amount", hole=0.5, category_orders={"grade": list("ABCDEFG")})
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, **STRETCH)


def page_fraud(frames: dict) -> None:
    st.header("Fraud: where, when and how much?")
    tx = frames["txn"].copy()
    if tx.empty:
        st.info("No transaction data available.")
        return
    tx["transaction_dt"] = pd.to_datetime(tx.transaction_dt, errors="coerce")
    overall = tx.is_fraud.mean()

    st.subheader("1. How much fraud are we seeing?")
    fr = tx[tx.is_fraud == 1]
    c = st.columns(4)
    c[0].metric("Transactions", f"{len(tx):,}")
    c[1].metric("Fraud rate", _pct(overall))
    c[2].metric("Fraud exposure", _money(fr.transaction_amt.sum()))
    c[3].metric("Avg fraud vs legit amount", f"${fr.transaction_amt.mean():,.0f} / ${tx[tx.is_fraud == 0].transaction_amt.mean():,.0f}")

    st.subheader("2. Which channels carry the most risk?")
    dims = {"device_type": "Device", "product_cd": "Product", "card4": "Card network", "card6": "Card type", "email_domain": "Email domain"}
    dim = st.selectbox("Break down by", list(dims), format_func=dims.get)
    seg = _segment(tx.fillna({dim: "unknown"}), dim, "is_fraud", "transaction_amt")
    min_n = st.slider("Minimum transactions per segment", 1, 1000, 100)
    st.plotly_chart(_rate_chart(seg[seg.n >= min_n], dim, "rate", "n", overall, f"Fraud rate by {dims[dim].lower()}"), **STRETCH)

    st.subheader("3. When does fraud happen?")
    if tx.transaction_dt.notna().any():
        tx["hour"] = tx.transaction_dt.dt.hour
        tx["dow"] = tx.transaction_dt.dt.day_name()
        heat = tx.pivot_table(index="dow", columns="hour", values="is_fraud", aggfunc="mean").reindex(
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
        fig = px.imshow(heat, aspect="auto", color_continuous_scale="Reds", labels=dict(color="Fraud rate", x="Hour", y=""))
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, **STRETCH)
        by_hour = tx.groupby("hour").is_fraud.mean()
        night = tx[tx.hour < 6].is_fraud.mean()
        _answer(f"Fraud peaks at {int(by_hour.idxmax()):02d}:00 ({_pct(by_hour.max())}); overnight (00-06h) fraud runs at {_pct(night)} "
                f"vs {_pct(tx[tx.hour >= 6].is_fraud.mean())} in the day.")

    st.subheader("4. Does transaction size matter?")
    tx["amt_band"] = pd.cut(tx.transaction_amt, [0, 25, 100, 250, 500, 1000, 1e9], labels=["<25", "25-100", "100-250", "250-500", "500-1k", "1k+"]).astype(str)
    seg = _segment(tx, "amt_band", "is_fraud", "transaction_amt")
    st.plotly_chart(_rate_chart(seg, "amt_band", "rate", "n", overall, "Fraud rate by amount band", ["<25", "25-100", "100-250", "250-500", "500-1k", "1k+"]), **STRETCH)

    st.subheader("5. What does a review policy cost and save?")
    c1, c2 = st.columns(2)
    review_cost = c1.number_input("Cost of one manual review ($)", 1.0, 500.0, 15.0)
    capture = c2.slider("Share of fraud caught by reviewing the top 10% riskiest segments", 10, 90, 55, format="%d%%") / 100
    reviews = len(tx) * 0.10
    saved = fr.transaction_amt.sum() * capture
    st.metric("Net benefit of reviewing top 10%", _money(saved - reviews * review_cost),
              help=f"{reviews:,.0f} reviews x ${review_cost:,.0f} vs ${saved:,.0f} fraud prevented. Capture rate is an assumption; use the model's lift for a real estimate.")


def page_data_health(frames: dict) -> None:
    st.header("Data health: can we trust the numbers?")
    etl = frames["etl"].copy()
    if etl.empty:
        st.info("No ETL run history available.")
        return
    etl["ok"] = etl.status.str.lower().isin(["success", "completed"])
    etl["started_at"] = pd.to_datetime(etl.started_at, errors="coerce")
    etl["completed_at"] = pd.to_datetime(etl.completed_at, errors="coerce")
    etl["minutes"] = (etl.completed_at - etl.started_at).dt.total_seconds() / 60
    c = st.columns(4)
    c[0].metric("Runs", f"{len(etl):,}")
    c[1].metric("Success rate", _pct(etl.ok.mean()))
    c[2].metric("Records processed", f"{int(etl.records_written.fillna(0).sum()):,}")
    c[3].metric("Records failed", f"{int(etl.records_failed.fillna(0).sum()):,}")

    st.subheader("Is the pipeline getting slower or less reliable?")
    daily = etl.set_index("started_at").resample("D").agg(runs=("ok", "size"), success=("ok", "mean"), minutes=("minutes", "mean")).dropna().reset_index()
    fig = go.Figure()
    fig.add_bar(x=daily.started_at, y=daily.minutes, name="Avg duration (min)", marker_color=MUTED)
    fig.add_scatter(x=daily.started_at, y=daily.success, name="Success rate", yaxis="y2", line=dict(color=PRIMARY))
    fig.update_layout(height=320, yaxis2=dict(overlaying="y", side="right", tickformat=".0%", range=[0, 1.05]),
                      margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, **STRETCH)

    st.subheader("Which tables fail most?")
    t = etl.groupby("target_table").agg(runs=("ok", "size"), failure_rate=("ok", lambda s: 1 - s.mean())).reset_index()
    st.dataframe(t.style.format({"failure_rate": "{:.1%}"}), **STRETCH, hide_index=True)
    failed = etl[~etl.ok]
    if len(failed):
        st.subheader("Recent failures")
        st.dataframe(failed[["started_at", "task_id", "target_table", "records_failed", "error_message"]].head(15), **STRETCH, hide_index=True)


BUSINESS_PAGES = {
    "Executive summary": page_executive,
    "Churn & retention": page_churn,
    "Lending risk": page_lending,
    "Fraud analysis": page_fraud,
    "Data health": page_data_health,
}


def render(page: str) -> None:
    frames, source = load_data()
    if source.startswith("demo"):
        st.warning(f"Showing synthetic demo data ({source}). Set WAREHOUSE_URL to point at the FinSight PostgreSQL warehouse.")
    BUSINESS_PAGES[page](frames)
