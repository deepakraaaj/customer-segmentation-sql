-- 02_data_quality.sql
-- How many raw rows each cleaning rule affects (a row can break more than one rule).
SELECT 'raw rows'                       AS check_name, COUNT(*) AS n_rows FROM raw
UNION ALL SELECT 'cancelled invoices',      COUNT(*) FROM raw WHERE invoice LIKE 'C%'
UNION ALL SELECT 'quantity <= 0',           COUNT(*) FROM raw WHERE quantity <= 0
UNION ALL SELECT 'price <= 0',              COUNT(*) FROM raw WHERE price <= 0
UNION ALL SELECT 'missing customer_id',     COUNT(*) FROM raw WHERE customer_id IS NULL
UNION ALL SELECT 'non-product stock code',  COUNT(*) FROM raw WHERE NOT regexp_matches(stock_code, '^[0-9]{5}')
UNION ALL SELECT 'exact duplicate rows',    COUNT(*) - (SELECT COUNT(*) FROM (SELECT DISTINCT * FROM raw)) FROM raw
UNION ALL SELECT 'clean rows',              COUNT(*) FROM sales;
