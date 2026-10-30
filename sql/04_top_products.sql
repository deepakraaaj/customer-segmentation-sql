-- 04_top_products.sql
-- Top 15 products by revenue, with their share of total revenue (window SUM over all rows).
SELECT
    stock_code,
    ANY_VALUE(description)                                        AS description,
    SUM(quantity)                                                 AS units_sold,
    ROUND(SUM(revenue), 2)                                        AS revenue,
    ROUND(100.0 * SUM(revenue) / SUM(SUM(revenue)) OVER (), 2)    AS revenue_share_pct,
    RANK() OVER (ORDER BY SUM(revenue) DESC)                      AS revenue_rank
FROM sales
GROUP BY stock_code
QUALIFY revenue_rank <= 15
ORDER BY revenue_rank;
