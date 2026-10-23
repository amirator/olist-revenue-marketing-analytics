# Olist Revenue & Marketing-Funnel Analytics (DuckDB SQL + Power BI)

**Turning Olist's public e-commerce orders and marketing funnel data into a tested star schema and a one-page BI scorecard covering revenue, retention, delivery quality and lead-to-seller conversion by channel.**

![Scorecard](reports/scorecard.png)

Outputs: [PNG](reports/scorecard.png) · [PDF](reports/scorecard.pdf) · [HTML](reports/scorecard.html) · [kpis.json](reports/kpis.json) · [Power BI pack](powerbi/)

## Business questions
1. How big is the business, and what drives order value (AOV, basket size)?
2. Do customers come back (repeat rate)?
3. How much does late delivery cost in review score?
4. Which states drive GMV, and where is logistics weakest?
5. Which marketing origins turn leads into won sellers, and how much GMV do those sellers generate?
6. Can we compute CPL/CPA/ROI? (Only partly; see the *Spend* section.)

## Headline findings
All numbers below are rendered from `reports/kpis.json` by `src/readme.py`, and a test fails if they drift.

{{FINDINGS}}

### Funnel by origin (MQL → won deal → seller with orders)
{{ORIGIN_TABLE}}

"Acquired-seller GMV" is the item revenue sold on Olist by sellers whose `seller_id` appears in closed deals (order data ends in Oct 2018, so recent deals have little time to sell).

### Spend, CPL, CPA and ROI: not in the data
Neither dataset contains ad spend or sales cost, so **no real CPL, CPA or ROI is reported**. The only defensible return-side metric is *acquired-seller GMV per MQL* (above). For discussion only, the table below shows what CPA and GMV per BRL spent **would** be under assumed cost-per-lead values. They are scenario parameters (`CPL_SCENARIO_BRL` in `src/build.py` and a What-If parameter in DAX), not findings:

{{SCENARIO}}

## Data and licence
| Dataset | Publisher | Licence | Source used |
|---|---|---|---|
| Brazilian E-Commerce Public Dataset by Olist (9 CSVs) | Olist, [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) | CC BY-NC-SA 4.0 | Olist's own GitHub mirror [olist/work-at-olist-data](https://github.com/olist/work-at-olist-data/tree/master/datasets) |
| Marketing Funnel by Olist (MQLs + closed deals) | Olist, [Kaggle](https://www.kaggle.com/datasets/olistbr/marketing-funnel-olist) | CC BY-NC-SA 4.0 | Public mirror [francoc99/olist](https://github.com/francoc99/olist) (zipped CSVs) |

Kaggle requires a login, so `src/download.py` pulls from the mirrors and writes `data/manifest.json` (URL, bytes, SHA-256, UTC timestamp). Row counts are tested against the official Kaggle figures: 99,441 orders, 112,650 items, 103,886 payments, 32,951 products, 3,095 sellers, 8,000 MQLs and 842 closed deals. Raw files are not committed. Non-commercial portfolio use only.

{{ROWCOUNTS}}

## Data issues found while profiling
- **Reviews:** some orders have several reviews. Staging keeps the latest answer per order (98,673 orders with a review).
- **Funnel has no SQL stage:** the data only has MQL (qualified lead) → won deal. Unqualified leads and lost deals are not published, so lead→qualified and qualified→won cannot be separated. "Conversion" here means MQL→won.
- **Won ≠ selling:** only about 45% of won `seller_id`s appear in the orders data, so seller state can only be observed for active sellers. State is therefore reported as active acquired sellers and their GMV, not as a conversion rate.
- **Funnel vs orders timing:** MQLs run from June 2017 to May 2018, deals close until Nov 2018, and orders end in Oct 2018, so GMV from late-acquired sellers is right-censored.
- **Incomplete months:** 2016-09 to 2016-12 and 2018-09/10 are sparse, so the trend chart shows complete months from 2017-01 to 2018-08.
- **Date anomaly:** 1 deal has a won date before its first-contact date. It is kept and flagged by a test.
- **Origin blanks:** 60 MQLs have a blank origin and are merged with the source's own `unknown` value (1,159 in total). That bucket converts best, which suggests tracking gaps on high-intent leads.
- **Payments vs items:** payments include freight, instalment interest and vouchers, so GMV uses item `price`. Payment totals are reconciled separately.

## Approach
```
raw CSVs ──► sql/01_staging.sql ──► sql/02_star.sql ──────────► sql/03_kpis.sql ──► reports/kpis.json ──► scorecard (PNG/PDF/HTML)
(mirrors,     typed, deduped        dim_customer/product/seller/   KPI views (CTEs,                     └► README (rendered)
 manifest)                          date/lead; fct_orders,         window fns)       powerbi/*.csv + measures.dax
                                    fct_order_items, fct_leads                  pytest data-quality gate
```

## KPI definitions
| KPI | Definition |
|---|---|
| Realised order | `order_status` not canceled/unavailable and has at least one item |
| GMV | Sum of item `price` (BRL, nominal; excludes freight) on realised orders |
| AOV / basket size | GMV ÷ realised orders / mean items per realised order |
| Repeat rate | Share of `customer_unique_id` with 2+ realised orders |
| Late | Delivered date later than estimated date (delivered orders only) |
| MQL→won | Closed deals ÷ marketing-qualified leads, by `origin` |
| Acquired-seller GMV per MQL | GMV of won sellers ÷ MQLs (the return-side input to ROI) |

## Power BI pack (`powerbi/`)
Full tables: `dim_product`, `dim_seller`, `dim_date`, `dim_lead`, `fct_leads`. Order-side tables are a **deterministic 10% sample** (by order_id hash, keys kept consistent): `fct_orders_sample`, `fct_order_items_sample`, `dim_customer_sample`. `measures.dax` mirrors the SQL KPIs and documents the relationships, plus a What-If CPL parameter for the scenario measures.

## Reference repos studied (and what was borrowed)
| Repo | Borrowed |
|---|---|
| [dbt-labs/jaffle_shop_duckdb](https://github.com/dbt-labs/jaffle_shop_duckdb) | Layered staging → marts SQL on DuckDB, one file per layer |
| [cmarquezf/sql-marketing-with-olist](https://github.com/cmarquezf/sql-marketing-with-olist) | Joining the marketing funnel to e-commerce data with SQL, and handling blank dates/values explicitly |
| [vinhsphabmixay/Customer360_Olist_project](https://github.com/vinhsphabmixay/Customer360_Olist_project) | Treating MQL + closed deals as a lead fact linked to sellers (`seller_id`) |
| [francoc99/olist](https://github.com/francoc99/olist) | Public mirror of the funnel CSVs (data source; verified against Kaggle row counts) |
| [drivendataorg/cookiecutter-data-science](https://github.com/drivendataorg/cookiecutter-data-science) | `data/ src/ reports/` layout, Makefile and one-command reproduce |

## Tools
DuckDB SQL, Python (pandas, matplotlib), pytest, Power BI (DAX). Exact versions are pinned in `requirements.txt`.

## Reproduce
```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python run.py      # downloads data, builds DuckDB, exports, renders, runs tests
```

## Tests
`pytest -q` runs data-quality checks on official row counts, unique keys, referential integrity, not-nulls, value ranges, item/payment reconciliation, funnel and state totals summing to headline values, output files, and README-vs-KPI drift.

## Limitations
- Public 2016–2018 Brazilian marketplace data. It is not KSA data and says nothing about any employer.
- No marketing spend, so CPL/CPA/ROI are scenario-only. Findings are descriptive correlations, not causal effects.
- Funnel lacks unqualified leads and lost deals. Acquired-seller GMV is right-censored and only attributable to deals with a matching `seller_id`.
- GMV is nominal BRL with no inflation or FX adjustment.

## Author
Mohammad Amir Khan · [github.com/amirator](https://github.com/amirator). A personal portfolio project, not commissioned by or affiliated with Olist.
