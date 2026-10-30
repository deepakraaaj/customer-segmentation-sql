-- 01_clean.sql
-- Builds the analysis-ready `sales` table from the `raw` view (one row per invoice line).
-- Cleaning rules:
--   1. Cancelled invoices start with 'C'                       -> excluded
--   2. Quantity <= 0 (returns / adjustments) or price <= 0     -> excluded
--   3. Missing customer_id (guest checkouts)                   -> excluded (cannot segment them)
--   4. Non-product stock codes (POST, M, BANK CHARGES, ...)    -> excluded; real products start with 5 digits
--   5. Exact duplicate rows (the two source sheets overlap)    -> removed with DISTINCT
CREATE OR REPLACE TABLE sales AS
SELECT DISTINCT
    invoice,
    stock_code,
    trim(description)               AS description,
    quantity,
    invoice_date,
    price,
    CAST(customer_id AS INTEGER)    AS customer_id,
    country,
    quantity * price                AS revenue
FROM raw
WHERE invoice NOT LIKE 'C%'
  AND quantity > 0
  AND price > 0
  AND customer_id IS NOT NULL
  AND regexp_matches(stock_code, '^[0-9]{5}');
