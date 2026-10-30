"""End-to-end run: SQL layer -> RFM segmentation -> charts and reports.

Usage: python -m src.pipeline
"""
import json
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.patches import Patch

from src.download import ROOT
from src.segment import profile, segment
from src.sql_runner import run_all

REPORTS = ROOT / "reports"
PALETTE = {"Champions": "#7c3aed", "Loyal Customers": "#2563eb", "Potential Loyalists": "#0891b2",
           "New / Promising": "#16a34a", "At Risk": "#f59e0b", "Cooling Down": "#fb923c",
           "Hibernating": "#94a3b8", "Lost": "#64748b"}
sns.set_theme(style="whitegrid")


def save(name):
    plt.tight_layout()
    plt.savefig(REPORTS / name, dpi=130)
    plt.close()


def plot_revenue(monthly: pd.DataFrame):
    m = monthly[~monthly["is_partial_month"]].copy()
    m["month"] = pd.to_datetime(m["month"])
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(m["month"], m["revenue"] / 1e3, marker="o", color="#2563eb", lw=2.5)
    ax.fill_between(m["month"], m["revenue"] / 1e3, alpha=0.12, color="#2563eb")
    ax.set_title("Monthly revenue (complete months)", fontsize=14, weight="bold")
    ax.set_ylabel("revenue (£ thousands)")
    save("revenue_trend.png")


def plot_cohorts(cohorts: pd.DataFrame, max_months: int = 12):
    c = cohorts[cohorts["month_number"] <= max_months].copy()
    c["cohort"] = pd.to_datetime(c["cohort_month"]).dt.strftime("%Y-%m")
    grid = c.pivot(index="cohort", columns="month_number", values="retention_pct")
    fig, ax = plt.subplots(figsize=(13, 9))
    sns.heatmap(grid, annot=True, fmt=".0f", cmap="Blues", vmax=50, cbar_kws={"label": "% of cohort active"}, ax=ax)
    ax.grid(False)
    ax.set_title("Monthly cohort retention (%)", fontsize=14, weight="bold")
    ax.set_xlabel("months since first purchase")
    ax.set_ylabel("acquisition cohort")
    save("cohort_retention.png")


def plot_k_selection(scores: pd.DataFrame, k: int):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.2))
    a1.plot(scores["k"], scores["inertia"], marker="o", color="#2563eb")
    a1.set_title("Elbow method (inertia)", weight="bold")
    a2.plot(scores["k"], scores["silhouette"], marker="o", color="#7c3aed")
    a2.set_title("Silhouette score", weight="bold")
    for a in (a1, a2):
        a.axvline(k, ls="--", color="#ef4444")
        a.set_xlabel("number of clusters k")
    a2.annotate(f"chosen k = {k}", (k, scores.set_index("k").loc[k, "silhouette"]),
                xytext=(10, 10), textcoords="offset points", color="#ef4444", weight="bold")
    save("k_selection.png")


def plot_segments(prof: pd.DataFrame):
    p = prof.sort_values("revenue_share_pct")
    y = np.arange(len(p))
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.barh(y + 0.2, p["customer_share_pct"], height=0.4, color="#cbd5e1", label="% of customers")
    ax.barh(y - 0.2, p["revenue_share_pct"], height=0.4, color=[PALETTE[s] for s in p.index], label="% of revenue")
    for i, (cs, rs) in enumerate(zip(p["customer_share_pct"], p["revenue_share_pct"])):
        ax.text(cs + 0.5, i + 0.2, f"{cs:.0f}%", va="center", fontsize=9, color="#475569")
        ax.text(rs + 0.5, i - 0.2, f"{rs:.0f}%", va="center", fontsize=9, weight="bold")
    ax.set_yticks(y, p.index)
    ax.set_title("Customer share vs revenue share by segment", fontsize=14, weight="bold")
    ax.legend(handles=[Patch(color="#cbd5e1", label="% of customers"),
                       Patch(color="#475569", label="% of revenue (segment colour)")], loc="lower right")
    save("segment_share.png")


def plot_scatter(seg: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(10, 6))
    for name, g in seg.groupby("segment"):
        ax.scatter(g["recency_days"], g["monetary"], s=10 + 2 * np.sqrt(g["frequency"]) * 4, alpha=0.5,
                   color=PALETTE[name], label=name, edgecolors="none")
    ax.set_yscale("log")
    ax.set_xlabel("recency (days since last purchase)")
    ax.set_ylabel("monetary value (£, log scale)")
    ax.set_title("Customer segments (bubble size = frequency)", fontsize=14, weight="bold")
    ax.legend(markerscale=2)
    save("segment_scatter.png")


def main():
    REPORTS.mkdir(exist_ok=True)
    sql = run_all()
    seg, scores, k = segment(sql["07_rfm"])
    prof = profile(seg)
    seg.to_csv(REPORTS / "customer_segments.csv", index=False)
    scores.round(4).to_csv(REPORTS / "k_selection.csv", index=False)
    prof.to_csv(REPORTS / "segment_profile.csv")

    plot_revenue(sql["03_monthly_revenue"])
    plot_cohorts(sql["06_cohort_retention"])
    plot_k_selection(scores, k)
    plot_segments(prof)
    plot_scatter(seg)

    with open(REPORTS / "run_log.jsonl", "a") as log:
        log.write(json.dumps({"timestamp": datetime.now().isoformat(timespec="seconds"), "k": k,
                              "silhouette": round(float(scores.set_index("k").loc[k, "silhouette"]), 4),
                              "customers": len(seg)}) + "\n")
    print(f"\nChosen k = {k}\n")
    print(prof.drop(columns="action").to_string())


if __name__ == "__main__":
    main()
