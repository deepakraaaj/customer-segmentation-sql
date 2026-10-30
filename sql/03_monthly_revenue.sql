-- 03_monthly_revenue.sql
-- Monthly KPIs with month-over-month growth (LAG window function).
-- December 2011 only has data up to the 9th, so it is flagged as a partial month.
WITH monthly AS (
    SELECT
        date_trunc('month', invoice_date)      AS month,
        SUM(revenue)                           AS revenue,
        COUNT(DISTINCT invoice)                AS orders,
        COUNT(DISTINCT customer_id)            AS active_customers
    FROM sales
    GROUP BY 1
)
SELECT
    month,
    ROUND(revenue, 2)                                                    AS revenue,
    orders,
    active_customers,
    ROUND(revenue / orders, 2)                                           AS avg_order_value,
    ROUND(100.0 * (revenue / LAG(revenue) OVER (ORDER BY month) - 1), 1) AS revenue_mom_pct,
    month = (SELECT date_trunc('month', MAX(invoice_date)) FROM sales)   AS is_partial_month
FROM monthly
ORDER BY month;
