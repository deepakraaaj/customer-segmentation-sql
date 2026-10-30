-- 07_rfm.sql
-- Recency, Frequency, Monetary value per customer.
-- Snapshot date = one day after the last transaction, so the most recent buyers have recency = 1.
WITH snapshot AS (
    SELECT MAX(invoice_date)::DATE + INTERVAL 1 DAY AS snapshot_date FROM sales
)
SELECT
    customer_id,
    datediff('day', MAX(invoice_date)::DATE, ANY_VALUE(snapshot_date))  AS recency_days,
    COUNT(DISTINCT invoice)                                            AS frequency,
    ROUND(SUM(revenue), 2)                                             AS monetary,
    MIN(invoice_date)::DATE                                            AS first_purchase,
    MAX(invoice_date)::DATE                                            AS last_purchase,
    mode(country)                                                      AS country
FROM sales, snapshot
GROUP BY customer_id
ORDER BY customer_id;
