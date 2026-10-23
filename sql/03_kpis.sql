-- KPI views. "Realised" = order_status NOT IN ('canceled','unavailable')
CREATE OR REPLACE VIEW v_realised AS
SELECT * FROM fct_orders WHERE order_status NOT IN ('canceled','unavailable') AND n_items > 0;

CREATE OR REPLACE VIEW kpi_headline AS
SELECT count(*) AS orders, sum(item_revenue) AS gmv, sum(payment_value) AS payments,
       sum(item_revenue)/count(*) AS aov_items, sum(payment_value)/count(*) AS aov_paid,
       avg(n_items) AS basket_items, count(DISTINCT customer_unique_id) AS customers
FROM v_realised;

CREATE OR REPLACE VIEW kpi_monthly AS
SELECT strftime(date_key,'%Y-%m') AS ym, count(*) AS orders, sum(item_revenue) AS gmv
FROM v_realised GROUP BY 1 ORDER BY 1;

CREATE OR REPLACE VIEW kpi_repeat AS
WITH c AS (SELECT customer_unique_id, count(*) n FROM v_realised GROUP BY 1)
SELECT count(*) AS customers, sum((n>1)::INT) AS repeaters, avg((n>1)::INT) AS repeat_rate FROM c;

CREATE OR REPLACE VIEW kpi_state AS
SELECT customer_state AS state, count(*) AS orders, sum(item_revenue) AS gmv,
       sum(item_revenue)/count(*) AS aov, avg(is_late::INT) FILTER (WHERE is_late IS NOT NULL) AS late_rate,
       avg(review_score) AS avg_review
FROM v_realised GROUP BY 1 ORDER BY gmv DESC;

CREATE OR REPLACE VIEW kpi_delay_review AS
SELECT CASE WHEN days_late = 0 THEN '0 on time'
            WHEN days_late <= 3 THEN '1 1-3d late'
            WHEN days_late <= 7 THEN '2 4-7d late'
            WHEN days_late <= 14 THEN '3 8-14d late' ELSE '4 15d+ late' END AS bucket,
       count(*) AS orders, avg(review_score) AS avg_review,
       avg((review_score<=2)::INT) AS share_1_2_star
FROM fct_orders WHERE order_status='delivered' AND delivered_at IS NOT NULL AND review_score IS NOT NULL
GROUP BY 1 ORDER BY 1;

CREATE OR REPLACE VIEW kpi_funnel_origin AS
SELECT origin, count(*) AS mqls, sum(won) AS won, avg(won) AS mql_to_won,
       sum((seller_orders>0)::INT) AS active_sellers,
       sum(seller_gmv) AS seller_gmv,
       sum(seller_gmv)/count(*) AS gmv_per_mql,
       median(days_to_close) AS median_days_to_close
FROM fct_leads GROUP BY 1 ORDER BY mqls DESC;

CREATE OR REPLACE VIEW kpi_funnel_overall AS
SELECT count(*) AS mqls, sum(won) AS won, avg(won) AS mql_to_won,
       sum((seller_orders>0)::INT) AS active_sellers, sum(seller_gmv) AS seller_gmv
FROM fct_leads;

-- Seller state is only known for won leads whose seller_id appears in the sellers table (i.e. sold at least once)
CREATE OR REPLACE VIEW kpi_seller_state_conversion AS
SELECT s.state, count(*) AS active_acquired_sellers, sum(l.seller_gmv) AS seller_gmv,
       sum(l.seller_gmv)/count(*) AS gmv_per_seller
FROM fct_leads l JOIN dim_seller s USING (seller_id) WHERE l.won=1 GROUP BY 1 ORDER BY active_acquired_sellers DESC;

CREATE OR REPLACE VIEW kpi_category AS
SELECT p.category, sum(i.price) AS gmv, count(DISTINCT i.order_id) AS orders
FROM fct_order_items i JOIN dim_product p USING (product_id)
WHERE i.order_status NOT IN ('canceled','unavailable') GROUP BY 1 ORDER BY gmv DESC;
