from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "Bank Customer Churn Prediction.csv"
RESULTS = ROOT / "results"
st.set_page_config(page_title="ChurnGuard AI", page_icon="◈", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
:root{--ink:#f3f5f2;--muted:#8c9995;--lime:#c1f36c;--coral:#ff8275;--line:#283432}
html,body,[class*="css"]{font-family:'Manrope',sans-serif}
.stApp{background:radial-gradient(ellipse at 72% 0%,#18302a 0%,#101716 48%,#0d1212 100%);color:var(--ink)}
.stAppViewContainer .main .block-container{padding-top:2rem}
[data-testid="stSidebar"]{background:#111918;border-right:1px solid var(--line)}
[data-testid="stSidebar"] *{color:var(--ink)}
[data-baseweb="tag"]{background:#c1f36c!important;color:#101716!important}
[data-baseweb="tag"] *{color:#101716!important;fill:#101716!important}
[data-testid="stSlider"] [role="slider"]{background:#c1f36c!important;border-color:#c1f36c!important}
[data-testid="stSlider"] [data-baseweb="slider"] div[role="presentation"]{background:#c1f36c}
.hero{padding:28px 4px 24px;border-bottom:1px solid var(--line);margin-bottom:22px}
.eyebrow{font:500 11px 'DM Mono';letter-spacing:2px;color:var(--lime);text-transform:uppercase}
.hero h1{font-size:clamp(32px,4vw,52px);letter-spacing:-2.8px;line-height:1;margin:12px 0;color:var(--ink)}
.hero p{color:var(--muted);max-width:630px;font-size:14px;line-height:1.7}
.metric{background:linear-gradient(145deg,#162120,#111818);border:1px solid var(--line);border-radius:16px;padding:18px 20px;min-height:116px}
.metric-label{font:11px 'DM Mono';letter-spacing:1px;text-transform:uppercase;color:var(--muted)}
.metric-value{font-size:32px;font-weight:800;letter-spacing:-1px;margin-top:8px}
.metric-note{font-size:11px;color:var(--muted);margin-top:2px}
.section{font-size:20px;letter-spacing:-.6px;font-weight:700;margin:26px 0 12px}
.tag{display:inline-block;border:1px solid #405342;border-radius:20px;color:var(--lime);padding:5px 10px;font:10px 'DM Mono';letter-spacing:.5px}
div[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:12px;overflow:hidden}
.stButton>button{background:var(--lime);color:#111918;border:0;border-radius:9px;font-weight:800}
.stButton>button:hover{background:#d2ff89;color:#111918}
.stDownloadButton>button{border-color:#45554e;color:var(--ink);border-radius:9px}
footer{visibility:hidden}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH)


try:
    data = load_data()
except Exception as exc:
    st.error(f"Could not read the project dataset: {exc}")
    st.stop()

st.sidebar.markdown("<div class='eyebrow'>◈ CHURNGUARD / ANALYTICS</div>", unsafe_allow_html=True)
st.sidebar.markdown("### Workspace")
st.sidebar.caption(f"{len(data):,} customer records · {data.shape[1]} fields")
countries = sorted(data["country"].dropna().unique().tolist())
selected = st.sidebar.multiselect("Markets", countries, default=countries)
min_age, max_age = int(data.age.min()), int(data.age.max())
age_range = st.sidebar.slider("Customer age", min_age, max_age, (min_age, max_age))
active_only = st.sidebar.toggle("Active members only", value=False)
filtered = data[data.country.isin(selected) & data.age.between(*age_range)]
if active_only:
    filtered = filtered[filtered.active_member == 1]

st.markdown("<div class='hero'><div class='eyebrow'>CUSTOMER INTELLIGENCE · LIVE VIEW</div><h1>See risk before<br>customers leave.</h1><p>Explore the signals behind historical churn, focus on the segments that need attention, and score customer records with your trained model.</p><span class='tag'>HISTORICAL CHURN · NO FORECAST WINDOW</span></div>", unsafe_allow_html=True)
rate = float(filtered.churn.mean()) if len(filtered) else 0.0
retained = int((filtered.churn == 0).sum())
churned = int(filtered.churn.sum())
col1, col2, col3, col4 = st.columns(4)
for col, label, value, note in [
    (col1, "CUSTOMERS IN VIEW", f"{len(filtered):,}", "Filtered records"),
    (col2, "HISTORICAL CHURN", f"{rate:.1%}", f"{churned:,} churned · {retained:,} retained"),
    (col3, "AVG. CUSTOMER AGE", f"{filtered.age.mean():.0f}" if len(filtered) else "—", "Years"),
    (col4, "ACTIVE MEMBERS", f"{filtered.active_member.mean():.1%}" if len(filtered) else "—", "Share of current view"),
]:
    col.markdown(f"<div class='metric'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div><div class='metric-note'>{note}</div></div>", unsafe_allow_html=True)

st.markdown("<div class='section'>The patterns in your portfolio <span class='tag'>SEGMENT VIEW</span></div>", unsafe_allow_html=True)
a, b = st.columns([1.15, 1])
with a:
    by_country = filtered.groupby("country", as_index=False).agg(churn_rate=("churn", "mean"), customers=("churn", "size"))
    fig = px.bar(by_country, x="country", y="churn_rate", color="churn_rate", text=by_country.churn_rate.map(lambda x: f"{x:.0%}"),
                 color_continuous_scale=["#9ddc61", "#f3c96b", "#ff8275"], labels={"country": "Market", "churn_rate": "Churn rate"})
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", coloraxis_showscale=False, margin=dict(l=8, r=8, t=14, b=8), yaxis_tickformat=".0%", height=310)
    fig.update_traces(textposition="outside", marker_line_width=0)
    st.plotly_chart(fig, width="stretch")
with b:
    age_data = filtered.assign(age_band=pd.cut(filtered.age, [0, 30, 40, 50, 60, 120], labels=["<30", "30–39", "40–49", "50–59", "60+"])).groupby(["age_band", "churn"], observed=True).size().reset_index(name="customers")
    age_data["outcome"] = age_data.churn.map({0: "Stayed", 1: "Churned"})
    fig2 = px.bar(age_data, x="age_band", y="customers", color="outcome", barmode="group", color_discrete_map={"Stayed": "#b9ed76", "Churned": "#ff8275"}, labels={"age_band": "Age band", "customers": "Customers", "outcome": "Outcome"})
    fig2.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=8, r=8, t=14, b=8), height=310, legend=dict(orientation="h", y=1.15))
    st.plotly_chart(fig2, width="stretch")

stream_summary_path = RESULTS / "stream_summary.json"
if stream_summary_path.exists():
    stream = json.loads(stream_summary_path.read_text(encoding="utf-8"))
    st.markdown("<div class='section'>Kafka stream snapshot <span class='tag'>INGESTED EVENTS</span></div>", unsafe_allow_html=True)
    st.caption(f"Topic: `{stream['topic']}` · Consumer group: `{stream['consumer_group']}`")
    s1, s2, s3, s4 = st.columns(4)
    for col, label, value, note in [
        (s1, "EVENTS CONSUMED", f"{stream['records_consumed']:,}", "Kafka customer records"),
        (s2, "CHURNED EVENTS", f"{stream['churned_records']:,}", "Historical label = 1"),
        (s3, "STREAM CHURN RATE", f"{stream['churn_rate']:.1%}", "From consumed records"),
        (s4, "COUNTRIES", f"{len(stream['records_by_country'])}", "Markets in this stream"),
    ]:
        col.markdown(f"<div class='metric'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div><div class='metric-note'>{note}</div></div>", unsafe_allow_html=True)
    country_counts = pd.DataFrame(stream["records_by_country"].items(), columns=["country", "records"]).sort_values("records", ascending=False)
    stream_fig = px.bar(country_counts, x="country", y="records", text="records", color_discrete_sequence=["#b9ed76"], labels={"country": "Market", "records": "Events consumed"})
    stream_fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=8, r=8, t=10, b=8), height=250, showlegend=False)
    stream_fig.update_traces(textposition="outside", marker_line_width=0)
    st.plotly_chart(stream_fig, width="stretch")

mapreduce_path = RESULTS / "hdfs_mapreduce_country_summary.csv"
if mapreduce_path.exists():
    mapreduce = pd.read_csv(mapreduce_path)
    country_results = mapreduce[mapreduce.country != "ALL"].copy()
    overall = mapreduce[mapreduce.country == "ALL"]
    st.markdown("<div class='section'>Hadoop MapReduce results <span class='tag'>HDFS PROCESSING</span></div>", unsafe_allow_html=True)
    st.caption("Country churn counts aggregated by a Hadoop Streaming job from the partitioned files stored in HDFS.")
    if not overall.empty:
        total = overall.iloc[0]
        h1, h2, h3, h4 = st.columns(4)
        for col, label, value, note in [
            (h1, "HDFS RECORDS", f"{int(total.customers):,}", "Read by MapReduce"),
            (h2, "CHURNED", f"{int(total.churned):,}", "Historical label = 1"),
            (h3, "RETAINED", f"{int(total.stayed):,}", "Historical label = 0"),
            (h4, "OVERALL CHURN", f"{float(total.churn_rate_percent):.2f}%", "MapReduce output"),
        ]:
            col.markdown(f"<div class='metric'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div><div class='metric-note'>{note}</div></div>", unsafe_allow_html=True)
    if not country_results.empty:
        mapreduce_fig = px.bar(
            country_results, x="country", y="churn_rate_percent",
            text=country_results.churn_rate_percent.map(lambda value: f"{value:.2f}%"),
            color="churn_rate_percent", color_continuous_scale=["#9ddc61", "#f3c96b", "#ff8275"],
            labels={"country": "Market", "churn_rate_percent": "Historical churn rate (%)"},
        )
        mapreduce_fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", coloraxis_showscale=False, margin=dict(l=8, r=8, t=14, b=8), height=280)
        mapreduce_fig.update_traces(textposition="outside", marker_line_width=0)
        st.plotly_chart(mapreduce_fig, width="stretch")
        st.dataframe(country_results, width="stretch", hide_index=True)

st.markdown("<div class='section'>Customer explorer <span class='tag'>FILTERED RECORDS</span></div>", unsafe_allow_html=True)
show = filtered.copy()
show["outcome"] = show.churn.map({0: "Stayed", 1: "Churned"})
st.dataframe(show[["customer_id", "country", "gender", "age", "tenure", "balance", "products_number", "active_member", "outcome"]], width="stretch", hide_index=True, height=300)
st.download_button("Download filtered records", show.to_csv(index=False).encode("utf-8"), "churnguard_customers.csv", "text/csv")

st.markdown("<div class='section'>Score a customer file <span class='tag'>MODEL ASSIST</span></div>", unsafe_allow_html=True)
st.caption("Upload records with the same customer attributes. The model returns a historical churn-risk probability; use it to prioritize review, not as a guaranteed prediction.")
model_path = RESULTS / "churn_model.joblib"
upload = st.file_uploader("Customer CSV", type=["csv"], help="Expected features: credit_score, country, gender, age, tenure, balance, products_number, credit_card, active_member, estimated_salary")
if upload:
    scoring = pd.read_csv(upload)
    if model_path.exists():
        artifact = joblib.load(model_path)
        missing = sorted(set(artifact["feature_columns"]) - set(scoring.columns))
        if missing:
            st.error("Missing model input columns: " + ", ".join(missing))
        else:
            scores = artifact["model"].predict_proba(scoring[artifact["feature_columns"]])[:, 1]
            scoring["churn_risk_probability"] = scores
            scoring["risk_band"] = pd.cut(scores, [-0.001, 0.35, 0.65, 1.0], labels=["Lower", "Elevated", "Higher"])
            st.dataframe(scoring.sort_values("churn_risk_probability", ascending=False), width="stretch", hide_index=True)
            st.download_button("Download scored file", scoring.to_csv(index=False).encode("utf-8"), "churnguard_scored.csv", "text/csv")
    else:
        st.info("Train the model first: run `python src\\train_model.py` from the project folder.")

metrics_path = RESULTS / "model_metrics.json"
if metrics_path.exists():
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    st.markdown("<div class='section'>Model quality <span class='tag'>HELD-OUT DATA</span></div>", unsafe_allow_html=True)
    st.caption("Performance on a stratified test split; results may differ on new customers.")
    m1, m2, m3, m4 = st.columns(4)
    for col, label, key in [(m1, "ROC AUC", "roc_auc"), (m2, "CHURN RECALL", "recall_churn"), (m3, "PRECISION", "precision_churn"), (m4, "TEST RECORDS", "test_rows")]:
        value = f"{metrics[key]:.1%}" if key != "test_rows" else f"{metrics[key]:,}"
        col.markdown(f"<div class='metric'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div></div>", unsafe_allow_html=True)
else:
    st.info("Model metrics appear here after running `python src\\train_model.py`.")

st.markdown("<div style='margin:36px 0 12px;padding-top:14px;border-top:1px solid #283432;color:#71807b;font:11px DM Mono'>CHURNGUARD AI · DECISION SUPPORT · HISTORICAL DATA ONLY</div>", unsafe_allow_html=True)
