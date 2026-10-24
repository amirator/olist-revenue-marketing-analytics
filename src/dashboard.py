"""Power BI-style scorecard: KPI cards, wide trend, 4 breakdowns, source line. PNG + PDF + self-contained HTML."""
import base64, json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parents[1]
NAVY, TEAL, GREY, RED = "#1F3A5F", "#2A9D8F", "#8D99AE", "#E76F51"

def main():
    k = json.loads((ROOT / "reports" / "kpis.json").read_text())
    h, r, f = k["headline"], k["repeat"], k["funnel_overall"]
    fig = plt.figure(figsize=(16, 10), facecolor="#F4F6F9")
    gs = fig.add_gridspec(3, 4, height_ratios=[0.55, 1.3, 1.5], hspace=0.55, wspace=0.32, left=0.05, right=0.97, top=0.9, bottom=0.08)
    fig.suptitle("Olist Brazil | Revenue & Seller-Acquisition Funnel Scorecard (2016-09 to 2018-10)", fontsize=17, weight="bold", color=NAVY, x=0.05, ha="left")
    cards = [("GMV (item revenue, BRL)", f"{h['gmv']/1e6:.2f}M"), ("Orders (realised)", f"{h['orders']:,}"),
             ("AOV (items, BRL)", f"{h['aov_items']:.0f}"), ("Customer repeat rate", f"{r['repeat_rate']:.1%}"),
             ("MQL -> won deal", f"{f['mql_to_won']:.1%}"), ("Late deliveries", f"{k['late_overall']['late_rate']:.1%}")]
    cg = gs[0, :].subgridspec(1, 6, wspace=0.12)
    for i, (lab, val) in enumerate(cards):
        ax = fig.add_subplot(cg[0, i]); ax.set_facecolor("white"); ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values(): s.set_color("#DDE2E8")
        ax.text(0.5, 0.58, val, ha="center", va="center", fontsize=22, weight="bold", color=NAVY)
        ax.text(0.5, 0.18, lab, ha="center", va="center", fontsize=10, color="#555")
    m = [x for x in k["monthly"] if "2017-01" <= x["ym"] <= "2018-08"]
    ax = fig.add_subplot(gs[1, :])
    ax.bar([x["ym"] for x in m], [x["gmv"] / 1e3 for x in m], color=TEAL)
    ax.set_title("Monthly GMV, BRL thousands (complete months 2017-01 to 2018-08)", loc="left", color=NAVY, weight="bold")
    ax.tick_params(axis="x", rotation=45, labelsize=8); ax.spines[["top", "right"]].set_visible(False)
    fo = [x for x in k["funnel_origin"] if x["mqls"] >= 100]
    ax = fig.add_subplot(gs[2, 0]); fo_s = sorted(fo, key=lambda x: x["mql_to_won"])
    ax.barh([x["origin"] for x in fo_s], [x["mql_to_won"] * 100 for x in fo_s], color=NAVY)
    ax.set_title("MQL -> won % by origin (n>=100)", loc="left", color=NAVY, weight="bold", fontsize=10)
    for i, x in enumerate(fo_s): ax.text(x["mql_to_won"] * 100 + 0.2, i, f"{x['mql_to_won']:.1%} ({int(x['won'])}/{x['mqls']})", va="center", fontsize=7)
    ax.set_xlim(0, 25); ax.tick_params(labelsize=8)
    ax = fig.add_subplot(gs[2, 1]); fg = sorted(fo, key=lambda x: x["gmv_per_mql"])
    ax.barh([x["origin"] for x in fg], [x["gmv_per_mql"] for x in fg], color=TEAL)
    ax.set_title("Acquired-seller GMV per MQL, BRL", loc="left", color=NAVY, weight="bold", fontsize=10); ax.tick_params(labelsize=8)
    dr = k["delay_review"]; ax = fig.add_subplot(gs[2, 2])
    ax.bar([d["bucket"][2:] for d in dr], [d["avg_review"] for d in dr], color=[TEAL] + [RED] * 4)
    for i, d in enumerate(dr): ax.text(i, d["avg_review"] + 0.05, f"{d['avg_review']:.2f}", ha="center", fontsize=8)
    ax.set_ylim(0, 5); ax.set_title("Avg review score by delivery delay", loc="left", color=NAVY, weight="bold", fontsize=10); ax.tick_params(axis="x", labelsize=7, rotation=20)
    st = k["state"][:8]; ax = fig.add_subplot(gs[2, 3])
    ax.bar([s["state"] for s in st], [s["gmv"] / 1e6 for s in st], color=GREY)
    ax2 = ax.twinx(); ax2.plot([s["state"] for s in st], [s["late_rate"] * 100 for s in st], color=RED, marker="o")
    ax2.set_ylabel("late %", color=RED, fontsize=8)
    ax.set_title("GMV (BRL M) and late-delivery % by state", loc="left", color=NAVY, weight="bold", fontsize=10); ax.tick_params(labelsize=8)
    fig.text(0.05, 0.015, "Source: Brazilian E-Commerce Public Dataset by Olist + Marketing Funnel by Olist (CC BY-NC-SA 4.0). Realised = not canceled/unavailable. "
             "No ad-spend data: CPL/CPA are scenario-only (see README). Built by Amir Khan with DuckDB SQL + Python.", fontsize=8, color="#555")
    out = ROOT / "reports"
    fig.savefig(out / "scorecard.png", dpi=110); fig.savefig(out / "scorecard.pdf"); plt.close(fig)
    b64 = base64.b64encode((out / "scorecard.png").read_bytes()).decode()
    rows = "".join(f"<tr><td>{x['origin']}</td><td>{x['mqls']}</td><td>{int(x['won'])}</td><td>{x['mql_to_won']:.1%}</td><td>{x['seller_gmv']:,.0f}</td></tr>" for x in k["funnel_origin"])
    (out / "scorecard.html").write_text(f"""<!doctype html><html><head><meta charset="utf-8"><title>Olist scorecard</title>
<style>body{{font-family:Segoe UI,Arial;background:#F4F6F9;margin:24px}}table{{border-collapse:collapse;background:#fff}}td,th{{border:1px solid #ddd;padding:4px 10px;text-align:right}}</style></head>
<body><img src="data:image/png;base64,{b64}" style="max-width:100%"><h3>Funnel by origin</h3>
<table><tr><th>origin</th><th>MQLs</th><th>won</th><th>MQL&rarr;won</th><th>acquired-seller GMV (BRL)</th></tr>{rows}</table></body></html>""")
    print("scorecard written")

if __name__ == "__main__":
    main()
