"""Streamlit dashboard. Run `python -m src.pipeline` first, then `streamlit run app.py`."""
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st

from src.download import ROOT
from src.pipeline import PALETTE

REPORTS = ROOT / "reports"
SQL = REPORTS / "sql"

st.set_page_config(page_title="Customer Segmentation", page_icon="🛍️", layout="wide")

if not (REPORTS / "segment_profile.csv").exists():
    st.error("No results yet. Run `python -m src.pipeline` first.")
    st.stop()

monthly = pd.read_csv(SQL / "03_monthly_revenue.csv", parse_dates=["month"])
cohorts = pd.read_csv(SQL / "06_cohort_retention.csv", parse_dates=["cohort_month"])
countries = pd.read_csv(SQL / "05_top_countries.csv")
products = pd.read_csv(SQL / "04_top_products.csv")
segments = pd.read_csv(REPORTS / "customer_segments.csv")
profile = pd.read_csv(REPORTS / "segment_profile.csv", index_col="segment")

st.title("🛍️ Customer Segmentation & Sales Analytics")
st.caption("UCI Online Retail II · Dec 2009 – Dec 2011 · SQL in DuckDB, RFM + K-Means segmentation")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Revenue", f"£{monthly['revenue'].sum() / 1e6:.2f}M")
c2.metric("Orders", f"{monthly['orders'].sum():,}")
c3.metric("Customers", f"{len(segments):,}")
c4.metric("Avg order value", f"£{monthly['revenue'].sum() / monthly['orders'].sum():,.0f}")
c5.metric("One-time buyers", f"{100 * (segments['frequency'] == 1).mean():.1f}%")

st.subheader("Customer segments")
selected = st.multiselect("Segments", list(profile.index), default=list(profile.index))
left, right = st.columns([3, 2])
with left:
    view = profile.loc[selected, ["customers", "customer_share_pct", "revenue_share_pct",
                                  "median_recency_days", "median_frequency", "median_monetary", "action"]]
    st.dataframe(view, width="stretch")
with right:
    fig, ax = plt.subplots(figsize=(5, 3.2))
    p = profile.loc[selected].sort_values("revenue_share_pct")
    ax.barh(p.index, p["revenue_share_pct"], color=[PALETTE[s] for s in p.index])
    ax.set_xlabel("% of revenue")
    ax.set_title("Revenue share by segment")
    st.pyplot(fig, width="stretch")

left, right = st.columns(2)
with left:
    st.subheader("Monthly revenue")
    st.line_chart(monthly[~monthly["is_partial_month"]].set_index("month")["revenue"])
with right:
    st.subheader("Top countries")
    st.bar_chart(countries, x="country", y="revenue", sort="-revenue", horizontal=True)

st.subheader("Cohort retention (% of cohort buying again N months later)")
grid = cohorts[cohorts["month_number"] <= 12].assign(cohort=lambda d: d["cohort_month"].dt.strftime("%Y-%m")) \
    .pivot(index="cohort", columns="month_number", values="retention_pct")
fig, ax = plt.subplots(figsize=(12, 6))
sns.heatmap(grid, annot=True, fmt=".0f", cmap="Blues", vmax=50, cbar=False, ax=ax)
ax.set_xlabel("months since first purchase")
ax.set_ylabel("")
st.pyplot(fig, width="stretch")

st.subheader("Top products by revenue")
st.dataframe(products[["revenue_rank", "description", "units_sold", "revenue", "revenue_share_pct"]],
             hide_index=True, width="stretch")
