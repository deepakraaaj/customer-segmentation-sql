-- 05_top_countries.sql
-- Revenue, customers and running revenue share by country (cumulative window SUM).
SELECT
    country,
    COUNT(DISTINCT customer_id)                                                         AS customers,
    ROUND(SUM(revenue), 2)                                                              AS revenue,
    ROUND(100.0 * SUM(revenue) / SUM(SUM(revenue)) OVER (), 2)                          AS revenue_share_pct,
    ROUND(100.0 * SUM(SUM(revenue)) OVER (ORDER BY SUM(revenue) DESC)
                / SUM(SUM(revenue)) OVER (), 2)                                         AS cumulative_share_pct
FROM sales
GROUP BY country
ORDER BY revenue DESC
LIMIT 10;
