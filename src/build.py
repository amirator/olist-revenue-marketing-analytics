"""Run SQL layers in DuckDB and export kpis.json + Power BI CSVs."""
import json
from pathlib import Path
import duckdb
ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "olist.duckdb"
CPL_SCENARIO_BRL = [50, 100, 200]  # ASSUMPTION ONLY: no ad spend in the data; illustrative cost-per-lead inputs (BRL)

def connect():
    return duckdb.connect(str(DB))

def build():
    DB.unlink(missing_ok=True)
    con = connect()
    for f in sorted((ROOT / "sql").glob("*.sql")):
        con.execute(f.read_text().replace("{raw}", str(ROOT / "data" / "raw")))
    return con

def rows(con, q):
    df = con.execute(q).df()
    return json.loads(df.to_json(orient="records"))

def export_kpis(con):
    k = {
        "headline": rows(con, "SELECT * FROM kpi_headline")[0],
        "repeat": rows(con, "SELECT * FROM kpi_repeat")[0],
        "funnel_overall": rows(con, "SELECT * FROM kpi_funnel_overall")[0],
        "funnel_origin": rows(con, "SELECT * FROM kpi_funnel_origin"),
        "seller_state": rows(con, "SELECT * FROM kpi_seller_state_conversion LIMIT 8"),
        "state": rows(con, "SELECT * FROM kpi_state"),
        "delay_review": rows(con, "SELECT * FROM kpi_delay_review"),
        "monthly": rows(con, "SELECT * FROM kpi_monthly"),
        "category": rows(con, "SELECT * FROM kpi_category LIMIT 10"),
        "late_overall": rows(con, "SELECT avg(is_late::INT) AS late_rate FROM fct_orders WHERE order_status='delivered' AND is_late IS NOT NULL")[0],
        "row_counts": {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in
                       ["stg_orders", "stg_customers", "stg_order_items", "stg_payments", "stg_reviews", "stg_products",
                        "stg_sellers", "stg_mql", "stg_deals", "fct_orders", "fct_order_items", "fct_leads"]},
    }
    f = k["funnel_overall"]
    # Scenario only: what CPL/CPA/ROAS-on-GMV would be IF each MQL cost X. Not a fact.
    k["scenario_cpl"] = [{"assumed_cpl_brl": c, "implied_total_spend": c * f["mqls"],
                          "implied_cpa_per_won": c * f["mqls"] / f["won"],
                          "gmv_per_spend": f["seller_gmv"] / (c * f["mqls"])} for c in CPL_SCENARIO_BRL]
    (ROOT / "reports" / "kpis.json").write_text(json.dumps(k, indent=2, default=str))
    return k

def export_powerbi(con):
    out = ROOT / "powerbi"
    for t in ["dim_product", "dim_seller", "dim_date", "dim_lead", "fct_leads"]:
        con.execute(f"COPY {t} TO '{out}/{t}.csv' (HEADER)")
    # Order-side tables are large: ship a deterministic 10% sample (by order_id hash) with consistent keys
    con.execute("CREATE OR REPLACE TEMP TABLE s AS SELECT order_id, customer_id FROM fct_orders WHERE hash(order_id) % 10 = 0")
    con.execute(f"COPY (SELECT * EXCLUDE (purchased_at, delivered_at, estimated_at) FROM fct_orders WHERE order_id IN (SELECT order_id FROM s)) TO '{out}/fct_orders_sample.csv' (HEADER)")
    con.execute(f"COPY (SELECT * FROM fct_order_items WHERE order_id IN (SELECT order_id FROM s)) TO '{out}/fct_order_items_sample.csv' (HEADER)")
    con.execute(f"COPY (SELECT * FROM dim_customer WHERE customer_id IN (SELECT customer_id FROM s)) TO '{out}/dim_customer_sample.csv' (HEADER)")

if __name__ == "__main__":
    con = build(); k = export_kpis(con); export_powerbi(con)
    print(json.dumps({x: k[x] for x in ["headline", "repeat", "funnel_overall", "late_overall", "row_counts"]}, indent=1, default=str))
