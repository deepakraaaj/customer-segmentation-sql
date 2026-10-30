# Interview Prep: Customer Segmentation & SQL Analytics

Questions an interviewer is likely to ask about this project, with answers based on the actual code and results. Read them with the code open; be ready to point to the file.

---

## Project overview

**1. Explain the project in 60 seconds.**
I took 1,067,371 real transactions from a UK online gift retailer (UCI Online Retail II, Dec 2009–Dec 2011). In SQL (DuckDB) I cleaned the data down to 776,577 valid sales lines, analysed revenue trends, products, countries and cohort retention, and built RFM features (Recency, Frequency, Monetary) for 5,852 customers. I log-transformed and standardised the features, clustered them with K-Means (k = 4, chosen by elbow + silhouette) and named the segments from their median RFM values. The main finding: the **Champions** segment is 20.4% of customers but generates 73.5% of revenue, while 24.7% of customers are **At Risk** high-value buyers who haven't purchased in a median of 185 days, so they're the best win-back target. Results are in a Streamlit dashboard.

**2. Why this problem? What's the business value?**
Marketing budgets are limited. Segmentation tells the business *who* to spend on and *how*: protect Champions without discounting, win back At Risk customers before they churn, nurture new customers into repeat buyers, and stop spending expensive channels on Hibernating customers (33.4% of customers but only 3.6% of revenue).

**3. Why DuckDB instead of pandas for the SQL part?**
DuckDB runs SQL directly on a Parquet file, in-process, with no server to set up. It's columnar, so cleaning plus all six analysis queries over a million rows run in about 0.6 seconds on a laptop. It also keeps the logic in SQL, which is how this work is usually done against a real warehouse (Snowflake, BigQuery, Postgres); the same queries port with minor dialect changes.

## Data cleaning

**4. What cleaning did you do, and why?** (`sql/01_clean.sql`)

| Rule | Rows affected | Reason |
|------|-------------:|--------|
| Invoice starts with `C` (cancellation) | 19,494 | Not real sales |
| Quantity ≤ 0 | 22,950 | Returns/adjustments |
| Price ≤ 0 | 6,207 | Free samples, write-offs |
| Missing customer_id | 243,007 | Guest checkouts can't be segmented |
| Non-product stock code (POST, M, BANK CHARGES…) | 6,093 | Postage, fees, manual adjustments, not products |
| Exact duplicate rows | 34,335 | The two source sheets overlap |

Rows can break several rules, so the counts don't add up to the removed total. Result: 1,067,371 → 776,577 rows.

**5. You dropped 243k rows with no customer ID. Isn't that a lot of data to lose?**
Yes, about 23% of raw rows. For *customer* segmentation those rows are unusable because they can't be tied to a person. They're still valid revenue, so for company-level revenue reporting I'd keep them in a separate table. That's a deliberate scoping decision, and I'd mention it to stakeholders.

**6. How did you handle cancellations? Why not net them against the original order?**
I excluded them. Netting is more accurate for monetary value, but matching each cancellation to its original line isn't straightforward (partial quantities, different invoice numbers), so I kept the first version simple and documented the choice. With more time I'd match cancellations to their original line (same customer, stock code, quantity) and subtract them.

## SQL

**7. Walk me through the cohort retention query.** (`sql/06_cohort_retention.sql`)
1. `customer_months`: one row per customer per month they ordered (`DISTINCT` + `date_trunc('month', ...)`).
2. `with_cohort`: `MIN(order_month) OVER (PARTITION BY customer_id)` gives each customer's first purchase month, which is their cohort.
3. `cohort_counts`: `datediff('month', cohort_month, order_month)` gives the month number; count customers per cohort per month number.
4. Final: divide by `FIRST_VALUE(active_customers) OVER (PARTITION BY cohort_month ORDER BY month_number)`, the cohort size at month 0.

I excluded December 2011 because the data ends on the 9th; otherwise every cohort's last cell would show a fake retention drop.

**8. Difference between `RANK`, `DENSE_RANK` and `ROW_NUMBER`?**
For tied values, `ROW_NUMBER` gives unique numbers (1, 2, 3), `RANK` gives ties the same number and skips the next ones (1, 1, 3), and `DENSE_RANK` gives ties the same number without gaps (1, 1, 2). I used `RANK` for top products with `QUALIFY revenue_rank <= 15`, so tied products are both included.

**9. What does `QUALIFY` do?**
It filters on a window function's result, like `HAVING` does for aggregates. Without it you'd wrap the query in a subquery and filter with `WHERE` in the outer query.

**10. Write a query for month-over-month revenue growth.**
```sql
WITH monthly AS (
    SELECT date_trunc('month', invoice_date) AS month, SUM(revenue) AS revenue
    FROM sales GROUP BY 1
)
SELECT month, revenue,
       ROUND(100.0 * (revenue / LAG(revenue) OVER (ORDER BY month) - 1), 1) AS mom_pct
FROM monthly ORDER BY month;
```

**11. Write a query for each country's share of revenue and its running total.**
```sql
SELECT country,
       SUM(revenue) AS revenue,
       100.0 * SUM(revenue) / SUM(SUM(revenue)) OVER () AS share_pct,
       100.0 * SUM(SUM(revenue)) OVER (ORDER BY SUM(revenue) DESC)
             / SUM(SUM(revenue)) OVER () AS cumulative_pct
FROM sales GROUP BY country ORDER BY revenue DESC;
```
`SUM(SUM(revenue)) OVER ()` is a window over the *aggregated* rows: the inner `SUM` is the `GROUP BY` aggregate, the outer one is the window. Result: the UK is 83.71% of revenue, and the top 3 countries reach 90.37%.

**12. How did you compute RFM in SQL?** (`sql/07_rfm.sql`)
Snapshot date = last transaction date + 1 day. Then per customer: recency = days between their last purchase and the snapshot, frequency = `COUNT(DISTINCT invoice)` (orders, not lines), monetary = `SUM(quantity * price)`.

## Feature engineering & modelling

**13. Why log-transform before K-Means?**
K-Means minimises Euclidean distance, so it's dominated by features with large, skewed values. Frequency and monetary had skewness of 12.0 and 25.3 because a few wholesalers spend hundreds of thousands. After `log1p` the skewness dropped to 1.0 and 0.3. I used `log1p` rather than `log` so values of 0 are safe.

**14. And why standardise after that?**
Recency is in days (1–739), frequency in orders (1–373) and monetary in pounds (up to ~£581k). Without scaling, the feature with the largest range would dominate the distance. `StandardScaler` gives each feature mean 0 and standard deviation 1, so they contribute equally.

**15. How did you choose k = 4?**
I ran K-Means for k = 2–10 and looked at:
- **Inertia (elbow method):** the decrease flattens after k = 4.
- **Silhouette score:** k = 2 was highest (0.438), but two segments ("good" vs "bad") aren't actionable. Among k ≥ 3, k = 4 was best (0.366, vs 0.348 for k = 3 and 0.346 for k = 5).

So k = 4 balances statistical quality with business usefulness. That rule is coded in `choose_k()`.

**16. What does a silhouette score of 0.37 mean?**
It ranges from −1 to 1 and compares how close each point is to its own cluster versus the nearest other cluster. 0.37 means reasonable but overlapping structure, which is normal for customer data: customer behaviour is a continuum, not well-separated blobs. You can see it in the scatter plot, where segments touch at their borders.

**17. How did you name the clusters? Did you just eyeball them?**
No, the naming is rule-based (`name_clusters()` in `src/segment.py`). Each cluster's median recency, frequency and monetary is compared with the overall customer medians:
- recent + frequent + high value → Champions
- recent but low frequency → New / Promising
- not recent but frequent or high value → At Risk
- none of the three → Hibernating

This makes the labels reproducible if the data changes. I sanity-checked "New / Promising": 46.6% of those customers made their first purchase in the last 180 days. The rest are recent but infrequent buyers, so "Promising" fits better than a strict "New".

**18. Why K-Means and not something else?**
It's simple, fast, scales to millions of customers and gives centroids that are easy to explain. Alternatives I'd consider:
- **Gaussian Mixture Models:** soft assignment; handles elliptical clusters.
- **DBSCAN / HDBSCAN:** finds outliers such as wholesalers; no k needed. But it's harder to explain and can label many points as noise.
- **Plain RFM quintile scores** (also computed here as `RFM_score`, e.g. "555"): no ML at all, very interpretable, but gives up to 125 combinations that need manual grouping.

**19. K-Means is sensitive to outliers. How did you deal with them?**
The log transform shrinks extreme spenders a lot (skewness 25.3 → 0.3), so they no longer pull centroids far away. I kept them rather than deleting them: they're real, valuable customers and they belong in Champions. Another option would be to cap values at the 99th percentile.

## Results & business

**20. What are the key insights?**
- Revenue is concentrated: the top 20% of customers by spend generate 77.2% of revenue (close to the Pareto 80/20 rule), and the Champions segment is 20.4% of customers with 73.5% of revenue.
- Retention is the weak point: on average only 20.7% of a new cohort buys again the next month, and 27.6% of customers ordered only once.
- Strong seasonality: revenue peaks every November (£1.16M in 2010, £1.14M in 2011).
- The UK is 83.7% of revenue, so international growth is an opportunity.

**21. Why does the Dec 2009 cohort retain so much better than the others?**
Left-censoring. The data starts in December 2009, so that "cohort" includes long-standing customers whose real first purchase happened before the data begins. Their 35% month-1 retention isn't comparable with genuinely new cohorts, so I excluded it when computing the 20.7% average.

**22. How would the business use these segments?**
Push the segment labels into the CRM / email tool and run a different journey per segment (see the actions table in the README). Measure each campaign with an A/B test: for example, half of At Risk customers get the win-back offer and half don't, then compare reactivation rate and revenue per customer.

**23. How would you put this into production?**
Schedule the pipeline (Airflow or cron) to re-run monthly against the warehouse and write `customer_segments` back to a table. Then monitor segment sizes over time (a sudden shift means data or behaviour changed) and keep the cluster model fixed between retrains so labels stay stable.

**24. What are the limitations?**
- RFM ignores *what* customers buy, so it can't see product preferences.
- Many customers are wholesalers, which skews monetary value; B2B and B2C would ideally be segmented separately.
- Cancellations are excluded rather than netted.
- Guest checkouts (23% of raw rows) can't be segmented.
- K-Means assumes roughly spherical clusters, and the segments overlap (silhouette 0.37).

**25. What would you do next?**
Customer lifetime value prediction (BG/NBD + Gamma-Gamma) to forecast future rather than past value, market basket analysis for cross-sell, and an A/B test of the At Risk win-back campaign to prove the impact.

---

### Numbers to remember

| | |
|---|---|
| Raw → clean rows | 1,067,371 → 776,577 |
| Customers / orders / revenue | 5,852 / 36,594 / £17.07M |
| Average order value | £466 |
| One-time buyers | 27.6% |
| Avg month-1 retention (excl. Dec 2009 cohort) | 20.7% |
| Chosen k / silhouette | 4 / 0.366 |
| Champions | 20.4% of customers → 73.5% of revenue |
| At Risk | 24.7% of customers, 16.7% of revenue, median 185 days since last order |
