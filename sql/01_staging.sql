-- Staging: typed, lightly cleaned copies of raw CSVs (raw files untouched)
CREATE OR REPLACE TABLE stg_orders AS
SELECT order_id, customer_id, order_status,
       CAST(order_purchase_timestamp AS TIMESTAMP) AS purchased_at,
       CAST(order_approved_at AS TIMESTAMP) AS approved_at,
       CAST(order_delivered_customer_date AS TIMESTAMP) AS delivered_at,
       CAST(order_estimated_delivery_date AS TIMESTAMP) AS estimated_at
FROM read_csv_auto('{raw}/olist_orders_dataset.csv', header=true, all_varchar=true);

CREATE OR REPLACE TABLE stg_customers AS
SELECT customer_id, customer_unique_id, customer_zip_code_prefix AS zip_prefix,
       lower(customer_city) AS city, upper(customer_state) AS state
FROM read_csv_auto('{raw}/olist_customers_dataset.csv', header=true, all_varchar=true);

CREATE OR REPLACE TABLE stg_order_items AS
SELECT order_id, CAST(order_item_id AS INT) AS order_item_id, product_id, seller_id,
       CAST(price AS DECIMAL(12,2)) AS price, CAST(freight_value AS DECIMAL(12,2)) AS freight
FROM read_csv_auto('{raw}/olist_order_items_dataset.csv', header=true, all_varchar=true);

CREATE OR REPLACE TABLE stg_payments AS
SELECT order_id, CAST(payment_sequential AS INT) AS payment_seq, payment_type,
       CAST(payment_installments AS INT) AS installments, CAST(payment_value AS DECIMAL(12,2)) AS payment_value
FROM read_csv_auto('{raw}/olist_order_payments_dataset.csv', header=true, all_varchar=true);

-- Reviews: dedupe to one review per order (latest answer wins)
CREATE OR REPLACE TABLE stg_reviews AS
SELECT order_id, review_id, CAST(review_score AS INT) AS review_score,
       CAST(review_creation_date AS TIMESTAMP) AS review_created_at
FROM read_csv_auto('{raw}/olist_order_reviews_dataset.csv', header=true, all_varchar=true)
QUALIFY row_number() OVER (PARTITION BY order_id ORDER BY review_answer_timestamp DESC, review_id) = 1;

CREATE OR REPLACE TABLE stg_products AS
SELECT p.product_id, coalesce(t.product_category_name_english, p.product_category_name, 'unknown') AS category
FROM read_csv_auto('{raw}/olist_products_dataset.csv', header=true, all_varchar=true) p
LEFT JOIN read_csv_auto('{raw}/product_category_name_translation.csv', header=true, all_varchar=true) t
  USING (product_category_name);

CREATE OR REPLACE TABLE stg_sellers AS
SELECT seller_id, seller_zip_code_prefix AS zip_prefix, lower(seller_city) AS city, upper(seller_state) AS state
FROM read_csv_auto('{raw}/olist_sellers_dataset.csv', header=true, all_varchar=true);

CREATE OR REPLACE TABLE stg_mql AS
SELECT mql_id, CAST(first_contact_date AS DATE) AS first_contact_date, landing_page_id,
       coalesce(nullif(origin,''), 'unknown') AS origin
FROM read_csv_auto('{raw}/olist_marketing_qualified_leads_dataset.csv', header=true, all_varchar=true);

CREATE OR REPLACE TABLE stg_deals AS
SELECT mql_id, seller_id, sdr_id, sr_id, CAST(won_date AS TIMESTAMP) AS won_at,
       coalesce(nullif(business_segment,''),'unknown') AS business_segment,
       coalesce(nullif(lead_type,''),'unknown') AS lead_type,
       coalesce(nullif(business_type,''),'unknown') AS business_type,
       TRY_CAST(declared_monthly_revenue AS DOUBLE) AS declared_monthly_revenue
FROM read_csv_auto('{raw}/olist_closed_deals_dataset.csv', header=true, all_varchar=true);
