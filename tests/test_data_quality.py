import json, re
from pathlib import Path
import duckdb, pytest
ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture(scope="session")
def con():
    c = duckdb.connect(str(ROOT / "data" / "olist.duckdb"), read_only=True); yield c; c.close()

def one(con, q): return con.execute(q).fetchone()[0]

# Official Kaggle row counts
@pytest.mark.parametrize("table,n", [("stg_orders", 99441), ("stg_customers", 99441), ("stg_order_items", 112650),
    ("stg_payments", 103886), ("stg_products", 32951), ("stg_sellers", 3095), ("stg_mql", 8000), ("stg_deals", 842)])
def test_row_counts_match_official(con, table, n): assert one(con, f"SELECT count(*) FROM {table}") == n

@pytest.mark.parametrize("table,key", [("dim_customer", "customer_id"), ("dim_product", "product_id"), ("dim_seller", "seller_id"),
    ("dim_date", "date_key"), ("dim_lead", "mql_id"), ("fct_orders", "order_id"), ("fct_leads", "mql_id"),
    ("fct_order_items", "order_id || '-' || order_item_id"), ("stg_reviews", "order_id"), ("stg_deals", "mql_id")])
def test_unique_keys(con, table, key):
    assert one(con, f"SELECT count(*) - count(DISTINCT {key}) FROM {table}") == 0

@pytest.mark.parametrize("child,col,parent,pcol", [("fct_orders", "customer_id", "dim_customer", "customer_id"),
    ("fct_order_items", "product_id", "dim_product", "product_id"), ("fct_order_items", "seller_id", "dim_seller", "seller_id"),
    ("fct_order_items", "order_id", "fct_orders", "order_id"), ("fct_orders", "date_key", "dim_date", "date_key"),
    ("fct_leads", "date_key", "dim_date", "date_key"), ("stg_deals", "mql_id", "stg_mql", "mql_id")])
def test_referential_integrity(con, child, col, parent, pcol):
    assert one(con, f"SELECT count(*) FROM {child} c LEFT JOIN {parent} p ON c.{col}=p.{pcol} WHERE p.{pcol} IS NULL") == 0

@pytest.mark.parametrize("table,col", [("fct_orders", "order_id"), ("fct_orders", "customer_unique_id"), ("fct_orders", "purchased_at"),
    ("fct_order_items", "price"), ("fct_leads", "origin"), ("dim_lead", "first_contact_date"), ("stg_deals", "won_at")])
def test_not_null(con, table, col): assert one(con, f"SELECT count(*) FROM {table} WHERE {col} IS NULL") == 0

def test_prices_positive(con): assert one(con, "SELECT count(*) FROM stg_order_items WHERE price <= 0") == 0
def test_review_scores_in_range(con): assert one(con, "SELECT count(*) FROM stg_reviews WHERE review_score NOT BETWEEN 1 AND 5") == 0
def test_won_after_first_contact(con):
    # Known source anomaly: exactly 1 deal is won before its first-contact date (documented in README)
    assert one(con, "SELECT count(*) FROM dim_lead WHERE days_to_close < 0") == 1

def test_items_reconcile_to_fact(con):
    assert one(con, "SELECT abs((SELECT sum(price) FROM stg_order_items) - (SELECT sum(item_revenue) FROM fct_orders))") == 0

def test_payments_reconcile_to_fact(con):
    assert one(con, "SELECT abs((SELECT sum(payment_value) FROM stg_payments) - (SELECT sum(payment_value) FROM fct_orders))") == 0

def test_funnel_parts_sum_to_total(con):
    assert one(con, "SELECT sum(mqls) FROM kpi_funnel_origin") == 8000 and one(con, "SELECT sum(won) FROM kpi_funnel_origin") == 842

def test_state_gmv_sums_to_headline(con):
    assert abs(one(con, "SELECT sum(gmv) FROM kpi_state") - one(con, "SELECT gmv FROM kpi_headline")) < 0.01

def test_payments_cover_item_plus_freight(con):
    # payment_value should approximately equal price + freight per order (vouchers/interest cause small gaps)
    share = one(con, """SELECT avg((abs(payment_value - item_revenue - freight) < 1)::INT) FROM fct_orders
                       WHERE order_status='delivered' AND payment_value > 0""")
    assert share > 0.95

def test_outputs_exist():
    for f in ["reports/kpis.json", "reports/scorecard.png", "reports/scorecard.pdf", "reports/scorecard.html", "powerbi/measures.dax", "powerbi/fct_leads.csv"]:
        assert (ROOT / f).stat().st_size > 0, f

def test_readme_numbers_match_kpis():
    from src.readme import findings
    readme = (ROOT / "README.md").read_text()
    for row in findings(json.loads((ROOT / "reports" / "kpis.json").read_text())):
        assert row[1] in readme, f"README drifted from kpis.json: {row[1]}"
