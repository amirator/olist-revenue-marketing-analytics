-- Star schema: 5 dimensions, 3 facts
CREATE OR REPLACE TABLE dim_customer AS
SELECT customer_id, customer_unique_id, city, state FROM stg_customers;

CREATE OR REPLACE TABLE dim_product AS SELECT product_id, category FROM stg_products;

CREATE OR REPLACE TABLE dim_seller AS
SELECT s.seller_id, s.city, s.state, d.mql_id IS NOT NULL AS acquired_via_funnel,
       coalesce(m.origin,'not_in_funnel') AS acquisition_origin
FROM stg_sellers s LEFT JOIN stg_deals d USING (seller_id) LEFT JOIN stg_mql m USING (mql_id);

CREATE OR REPLACE TABLE dim_date AS
SELECT CAST(d AS DATE) AS date_key, year(d) AS year, month(d) AS month,
       strftime(d,'%Y-%m') AS year_month, dayname(d) AS weekday
FROM range(DATE '2016-09-01', DATE '2018-12-31', INTERVAL 1 DAY) t(d);

CREATE OR REPLACE TABLE dim_lead AS
SELECT m.mql_id, m.first_contact_date, m.origin, m.landing_page_id,
       d.seller_id, d.won_at, d.business_segment, d.lead_type, d.business_type,
       d.mql_id IS NOT NULL AS is_won,
       date_diff('day', m.first_contact_date, CAST(d.won_at AS DATE)) AS days_to_close
FROM stg_mql m LEFT JOIN stg_deals d USING (mql_id);

-- Order grain fact
CREATE OR REPLACE TABLE fct_orders AS
WITH items AS (
  SELECT order_id, count(*) AS n_items, sum(price) AS item_revenue, sum(freight) AS freight
  FROM stg_order_items GROUP BY 1),
pay AS (SELECT order_id, sum(payment_value) AS payment_value FROM stg_payments GROUP BY 1)
SELECT o.order_id, o.customer_id, c.customer_unique_id, c.state AS customer_state, o.order_status,
       CAST(o.purchased_at AS DATE) AS date_key, o.purchased_at, o.delivered_at, o.estimated_at,
       coalesce(i.n_items,0) AS n_items, coalesce(i.item_revenue,0) AS item_revenue,
       coalesce(i.freight,0) AS freight, coalesce(p.payment_value,0) AS payment_value,
       CASE WHEN o.delivered_at IS NULL THEN NULL
            ELSE greatest(date_diff('day', CAST(o.estimated_at AS DATE), CAST(o.delivered_at AS DATE)),0) END AS days_late,
       CASE WHEN o.delivered_at IS NULL THEN NULL ELSE CAST(o.delivered_at AS DATE) > CAST(o.estimated_at AS DATE) END AS is_late,
       r.review_score,
       row_number() OVER (PARTITION BY c.customer_unique_id ORDER BY o.purchased_at, o.order_id) AS customer_order_seq
FROM stg_orders o JOIN stg_customers c USING (customer_id)
LEFT JOIN items i USING (order_id) LEFT JOIN pay p USING (order_id) LEFT JOIN stg_reviews r USING (order_id);

-- Item grain fact
CREATE OR REPLACE TABLE fct_order_items AS
SELECT i.order_id, i.order_item_id, i.product_id, i.seller_id, o.customer_id, o.date_key, o.order_status,
       i.price, i.freight
FROM stg_order_items i JOIN fct_orders o USING (order_id);

-- Lead grain fact (funnel)
CREATE OR REPLACE TABLE fct_leads AS
SELECT l.mql_id, l.first_contact_date AS date_key, l.origin, l.is_won::INT AS won, l.days_to_close, l.seller_id,
       coalesce(g.gmv,0) AS seller_gmv, coalesce(g.n_orders,0) AS seller_orders
FROM dim_lead l LEFT JOIN (
  SELECT seller_id, sum(price) AS gmv, count(DISTINCT order_id) AS n_orders
  FROM fct_order_items WHERE order_status NOT IN ('canceled','unavailable') GROUP BY 1) g USING (seller_id);
