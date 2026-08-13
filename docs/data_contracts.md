# Data contracts

## Contract principles

- Keys are stable integers within a generated run.
- Timestamps use the `Europe/Berlin` scenario timezone and are stored without personally identifying attributes.
- Currency values in raw facts are local; clean/dbt finance models expose EUR fields explicitly.
- Raw defects are expected and documented. Only clean Parquet is loaded to PostgreSQL.
- A critical quality failure blocks downstream trust even when files are produced.

## Dimensions and references

| Table | Grain / key | Required semantics |
|---|---|---|
| `dim_date` | Date / `date_key` | Calendar, ISO week, month, quarter, weekend flags |
| `dim_geography` | Market / `market_key` | Ten markets, currency, VAT, region, hub |
| `dim_channel` | Channel / `channel_key` | Channel group and paid flag |
| `dim_campaign` | Campaign / `campaign_key` | Channel ownership, objective, active dates |
| `dim_customer` | Customer / `customer_key` | Synthetic segment, acquisition, home market; no PII |
| `dim_product` | Product / `product_key` | SKU, hierarchy, brand, price, cost, lead time |
| `ref_fx_rates` | Date × currency | Local currency units per EUR and source date |
| `bridge_market_holiday` | Market × holiday date | Generated demand calendar adjustment |

## Facts

| Table | Grain / key | Mandatory controls |
|---|---|---|
| `fact_sessions` | Session / `session_id` | Unique ID, non-null market, valid device, nonnegative activity |
| `fact_orders` | Order / `order_id` | Unique ID, session/customer/market keys, status, FX, local totals |
| `fact_order_items` | Line / `order_item_id` | Unique ID, valid order/product, quantity >0, nonnegative economics |
| `fact_marketing_spend` | Spend record / `spend_id` | Nonnegative spend, valid market/channel/campaign |
| `fact_fulfillment` | Fulfilled order | Shipped ≤ delivered, cost and SLA attributes |
| `fact_returns` | Return event | Valid order-item key, units/refund/reason/recovery |
| `fact_inventory_snapshot` | Month × product × market | On-hand ≥0, reorder and estimated lost demand |
| `fact_targets` | Month × market × channel | Revenue, contribution, and order targets |

## Known injected defects and treatment

| Rule | Treatment |
|---|---|
| Duplicate session ID | Keep canonical row; quarantine duplicate |
| Missing session market | Quarantine |
| Invalid order-item product | Quarantine line |
| Nonpositive order-item quantity | Quarantine line |
| Negative marketing spend | Quarantine row |
| Delivered before shipped | Quarantine fulfillment row |
| Orphan return item | Quarantine return row |
| Negative inventory on hand | Quarantine snapshot |
| Arrival more than 14 days late | Retained as late-arriving operational reality and monitored |

## Marts

| Model | Grain | Primary consumers |
|---|---|---|
| `fct_order_item_profitability` | Completed order item | Finance, category, customer value |
| `fct_sessions` | Session | Funnel, device, conversion |
| `fct_inventory` | Product × market × snapshot | Inventory planning |
| `mart_monthly_executive` | Month | Executive scorecard, Excel |
| `mart_target_variance` | Month × market × channel | Finance and management variance |
| `mart_channel_profitability` | Month × market × channel | Marketing and commercial |
| `mart_customer_cohorts` | Cohort month × month index | CRM retention |
| `mart_operations` | Month × market × hub × carrier | Operations |
| `mart_product_returns` | Month × market × product hierarchy | Product and returns |
| `mart_funnel` | Ordered funnel stage | E-commerce |

## Quality evidence

Machine-readable results live in `artifacts/validation/data_quality_report.json`; the compact table is `data_quality_checks.csv`. Reconciliation evidence lives in `artifacts/analysis/reconciliations.csv`.
