"""Render README.md from reports/kpis.json so every narrative number comes from the data."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def findings(k):
    h, r, f = k["headline"], k["repeat"], k["funnel_overall"]
    fo = {x["origin"]: x for x in k["funnel_origin"]}
    d = {x["bucket"][2:]: x for x in k["delay_review"]}
    sp = k["state"][0]
    late = d["4-7d late"]
    return [
        ("Revenue scale", f"BRL {h['gmv']/1e6:.2f}M item GMV from {h['orders']:,} realised orders; AOV BRL {h['aov_items']:.2f}, {h['basket_items']:.2f} items per basket",
         "Small baskets: bundling/cross-sell is the main AOV lever."),
        ("Retention", f"only {r['repeat_rate']:.1%} of {r['customers']:,} customers ordered more than once",
         "Growth is acquisition-led; a CRM/loyalty programme has clear headroom."),
        ("Delivery vs reviews", f"on-time orders average {d['on time']['avg_review']:.2f} stars vs {late['avg_review']:.2f} when 4-7 days late ({late['share_1_2_star']:.0%} are 1-2 star)",
         "Late delivery is the strongest review-score driver measured here (correlation, not causation)."),
        ("Geography", f"{sp['state']} delivers {sp['gmv']/h['gmv']:.1%} of GMV; RJ late rate {next(s for s in k['state'] if s['state']=='RJ')['late_rate']:.1%} vs SP {sp['late_rate']:.1%}",
         "Logistics fixes outside SP protect ratings."),
        ("Funnel", f"{int(f['won'])} of {f['mqls']:,} MQLs became won deals ({f['mql_to_won']:.1%}); only {int(f['active_sellers'])} won sellers ({f['active_sellers']/f['won']:.1%}) appear with any order",
         "More than half of won sellers never make a sale here, so onboarding (won -> first sale) is a lever alongside lead conversion."),
        ("Channels", f"paid_search converts {fo['paid_search']['mql_to_won']:.1%} and organic_search {fo['organic_search']['mql_to_won']:.1%}, vs social {fo['social']['mql_to_won']:.1%} and email {fo['email']['mql_to_won']:.1%}",
         "Shift effort toward search; audit social/email lead quality before spending more."),
    ]

def origin_table(k):
    rows = ["| Origin | MQLs | Won | MQL->won | Won sellers with orders | Acquired-seller GMV (BRL) | GMV per MQL (BRL) | Median days to close |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for x in k["funnel_origin"]:
        rows.append(f"| {x['origin']} | {x['mqls']:,} | {int(x['won'])} | {x['mql_to_won']:.1%} | {int(x['active_sellers'])} | {x['seller_gmv']:,.0f} | {x['gmv_per_mql']:.0f} | {x['median_days_to_close'] if x['median_days_to_close'] is not None else '-'} |")
    return "\n".join(rows)

def scenario_table(k):
    rows = ["| Assumed CPL (BRL) — ASSUMPTION | Implied spend | Implied CPA per won deal | Acquired-seller GMV per BRL spent |", "|---:|---:|---:|---:|"]
    for s in k["scenario_cpl"]:
        rows.append(f"| {s['assumed_cpl_brl']} | {s['implied_total_spend']:,.0f} | {s['implied_cpa_per_won']:,.0f} | {s['gmv_per_spend']:.2f} |")
    return "\n".join(rows)

def main():
    k = json.loads((ROOT / "reports" / "kpis.json").read_text())
    tpl = (ROOT / "docs" / "README.template.md").read_text()
    ft = "| Theme | Finding (from data) | So what |\n|---|---|---|\n" + "\n".join(f"| {a} | {b} | {c} |" for a, b, c in findings(k))
    rc = "| Table | Rows |\n|---|---:|\n" + "\n".join(f"| {t} | {n:,} |" for t, n in k["row_counts"].items())
    out = tpl.replace("{{FINDINGS}}", ft).replace("{{ORIGIN_TABLE}}", origin_table(k)).replace("{{SCENARIO}}", scenario_table(k)).replace("{{ROWCOUNTS}}", rc)
    (ROOT / "README.md").write_text(out); print("README rendered")

if __name__ == "__main__":
    main()
