"""RFM scoring and K-Means customer segmentation."""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

FEATURES = ["recency_days", "frequency", "monetary"]
K_RANGE = range(2, 11)
SEED = 42

# Second name used when two clusters land on the same rule-based label (the higher-value one keeps the first).
FALLBACK_NAMES = {"Champions": "Loyal Customers", "Loyal Customers": "Potential Loyalists",
                  "New / Promising": "Potential Loyalists", "At Risk": "Cooling Down",
                  "Hibernating": "Lost", "Cooling Down": "Lost"}

ACTIONS = {
    "Champions": "Reward and retain: VIP/loyalty perks, early access to new ranges, referral incentives. Do not over-discount.",
    "Loyal Customers": "Upsell and cross-sell bundles; invite into the loyalty tier to move them up to Champions.",
    "Potential Loyalists": "Nurture with personalised recommendations and a second/third-order incentive.",
    "New / Promising": "Onboarding journey: welcome series and a time-limited offer on the next order to build the buying habit.",
    "At Risk": "Win-back now: personalised 'we miss you' campaign with a meaningful offer; high past value justifies spend.",
    "Cooling Down": "Re-engagement emails with best-sellers; test small incentives before they lapse completely.",
    "Hibernating": "Low-cost automated reactivation only; suppress from expensive channels.",
    "Lost": "Low-cost automated reactivation only; suppress from expensive channels.",
}


def rfm_scores(rfm: pd.DataFrame) -> pd.DataFrame:
    """Classic 1-5 quintile scores. Lower recency is better, so its labels are reversed.
    rank(method='first') breaks ties so qcut always gets 5 distinct bins (frequency has many 1s)."""
    out = rfm.copy()
    out["R"] = pd.qcut(out["recency_days"].rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
    out["F"] = pd.qcut(out["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    out["M"] = pd.qcut(out["monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    out["RFM_score"] = out["R"].astype(str) + out["F"].astype(str) + out["M"].astype(str)
    return out


def scale(rfm: pd.DataFrame) -> np.ndarray:
    """log1p tames the heavy right skew of frequency/monetary; StandardScaler puts all three on one scale."""
    return StandardScaler().fit_transform(np.log1p(rfm[FEATURES]))


def evaluate_k(X: np.ndarray) -> pd.DataFrame:
    rows = []
    for k in K_RANGE:
        km = KMeans(n_clusters=k, n_init=10, random_state=SEED).fit(X)
        rows.append({"k": k, "inertia": km.inertia_, "silhouette": silhouette_score(X, km.labels_)})
    return pd.DataFrame(rows)


def choose_k(scores: pd.DataFrame, min_k: int = 3) -> int:
    """Best silhouette among k >= 3: two segments ('good' vs 'bad') are too coarse to act on."""
    return int(scores[scores["k"] >= min_k].sort_values("silhouette", ascending=False).iloc[0]["k"])


def name_clusters(rfm: pd.DataFrame) -> dict[int, str]:
    """Label each cluster by comparing its medians with the overall customer medians."""
    overall = rfm[FEATURES].median()
    prof = rfm.groupby("cluster")[FEATURES].median()
    # value rank: higher frequency/monetary and lower recency is better
    value = (-np.log1p(prof["recency_days"]) + np.log1p(prof["frequency"]) + np.log1p(prof["monetary"]))
    names = {}
    for c in value.sort_values(ascending=False).index:
        recent = prof.loc[c, "recency_days"] <= overall["recency_days"]
        frequent = prof.loc[c, "frequency"] > overall["frequency"]
        high_value = prof.loc[c, "monetary"] > overall["monetary"]
        if recent and frequent and high_value:
            name = "Champions"
        elif recent and (frequent or high_value):
            name = "Loyal Customers"
        elif recent:
            name = "New / Promising"
        elif frequent or high_value:
            name = "At Risk"
        else:
            name = "Hibernating"
        while name in names.values():
            name = FALLBACK_NAMES[name]
        names[c] = name
    return names


def segment(rfm: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    X = scale(rfm)
    scores = evaluate_k(X)
    k = choose_k(scores)
    out = rfm_scores(rfm)
    out["cluster"] = KMeans(n_clusters=k, n_init=10, random_state=SEED).fit_predict(X)
    out["segment"] = out["cluster"].map(name_clusters(out))
    return out, scores, k


def profile(seg: pd.DataFrame) -> pd.DataFrame:
    p = seg.groupby("segment").agg(
        customers=("customer_id", "count"),
        median_recency_days=("recency_days", "median"),
        median_frequency=("frequency", "median"),
        median_monetary=("monetary", "median"),
        total_revenue=("monetary", "sum"),
    )
    p["customer_share_pct"] = (100 * p["customers"] / p["customers"].sum()).round(1)
    p["revenue_share_pct"] = (100 * p["total_revenue"] / p["total_revenue"].sum()).round(1)
    p["action"] = p.index.map(ACTIONS)
    return p.sort_values("revenue_share_pct", ascending=False).round(1)
