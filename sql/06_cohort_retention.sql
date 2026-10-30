-- 06_cohort_retention.sql
-- Monthly acquisition cohorts: a customer's cohort is the month of their first purchase.
-- retention_pct = share of the cohort that purchased again N months later.
-- The last month (December 2011, data ends on the 9th) is excluded so it doesn't look like a retention drop.
WITH customer_months AS (
    SELECT DISTINCT
        customer_id,
        date_trunc('month', invoice_date) AS order_month
    FROM sales
    WHERE invoice_date < (SELECT date_trunc('month', MAX(invoice_date)) FROM sales)
),
with_cohort AS (
    SELECT
        customer_id,
        order_month,
        MIN(order_month) OVER (PARTITION BY customer_id) AS cohort_month
    FROM customer_months
),
cohort_counts AS (
    SELECT
        cohort_month,
        datediff('month', cohort_month, order_month) AS month_number,
        COUNT(*)                                     AS active_customers
    FROM with_cohort
    GROUP BY 1, 2
)
SELECT
    cohort_month,
    month_number,
    active_customers,
    FIRST_VALUE(active_customers) OVER (PARTITION BY cohort_month ORDER BY month_number) AS cohort_size,
    ROUND(100.0 * active_customers
          / FIRST_VALUE(active_customers) OVER (PARTITION BY cohort_month ORDER BY month_number), 1) AS retention_pct
FROM cohort_counts
ORDER BY cohort_month, month_number;
