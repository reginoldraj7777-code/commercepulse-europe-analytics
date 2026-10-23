# KPI catalog

| KPI | Governed formula | Grain | Direction | Owner | Guardrail / target |
|---|---|---|---|---|---|
| Gross Revenue | Sum of item gross revenue EUR | Item → period | Higher | Commercial | Context only |
| Net Revenue | Gross revenue − discounts − refunds | Item → period | Higher | Finance | Meet revenue target |
| Contribution Margin | Net revenue − COGS + recovered COGS − return handling − fulfillment − allocated marketing | Item → period | Higher | Finance | Meet contribution target |
| Contribution Margin Rate | Contribution margin / net revenue | Period | Higher | Finance | Recover toward ≥15% |
| Revenue Target Attainment | Net revenue / revenue target | Month × market × channel | Higher | Finance | ≥100% |
| Conversion Rate | Converted sessions / valid sessions | Session → period | Higher | E-commerce | Evaluate with Wilson CI |
| Average Page Load | Mean page load milliseconds | Session segment | Lower | E-commerce | Investigate ≥1,500 ms |
| Orders | Distinct completed orders | Period | Higher | Commercial | Compare with target |
| AOV | Net revenue / completed orders | Period | Context | Commercial | Interpret with mix |
| Units Sold | Completed-order item quantity | Product → period | Higher | Commercial | Interpret with margin |
| Return Rate | Returned units / units sold | Product → period | Lower | Operations | ≤10% directional target |
| On-Time Delivery Rate | On-time delivered orders / fulfilled orders | Period / carrier / hub | Higher | Operations | ≥94% |
| Shipping Cost per Order | Shipping cost / fulfilled orders | Period | Lower | Operations | Action guardrail ≤+€0.50 |
| Marketing ROAS | Last-touch net revenue / allocated media spend | Month × market × channel | Higher | Marketing | ≥5.0x directional |
| Marketing Allocation Coverage | Allocated media spend / direct spend | Portfolio | Higher | Finance | 100% target |
| Stockout Rate | Stockout snapshots / inventory snapshots | Product × market | Lower | Supply Chain | ≤5% directional |
| Estimated Lost Revenue | Estimated lost units × list price | Product × market | Lower | Supply Chain | Opportunity estimate |
| Repeat Purchase Rate | Customers with ≥2 completed orders / purchasing customers | Customer | Higher | CRM | Trend |
| Cohort Retention | Active cohort customers / cohort size | Cohort × month index | Higher | CRM | Compare curves |

## Interpretation rules

- Zero denominators return blank or zero according to the consumer’s display convention; they never produce an infinite rate.
- Contribution margin is after marketing allocation and is not gross margin.
- ROAS uses last-touch attribution and must not be presented as causal incrementality.
- Return rate is unit-based; refund rate is not interchangeable.
- Stockout lost revenue is an opportunity estimate, not booked revenue.
- Rate comparisons should include uncertainty when sample size can affect the conclusion.

## Cross-tool governance

The source formulas are implemented in `src/commercepulse/analysis.py`, dbt marts, `powerbi/CommercePulse.SemanticModel/definition/tables/KPI Measures.tmdl`, and formula cells in `excel/CommercePulse_Manager_Pack.xlsx`. The workbook `Definitions` sheet provides the manager-facing version.

## Unit economics extension (October 2026)

| Measure | Definition | Interpretation |
|---|---|---|
| Contribution per Order | Contribution Margin / Orders | Contribution after modeled costs per order |
| Contribution per Customer | Contribution Margin / Purchasing Customers | Contribution per distinct purchasing customer |
| Contribution per Marketing Euro | Contribution Margin / Marketing Spend | Descriptive ratio; not causal marketing ROI |
| Discount Rate | Discounts / Gross Revenue | Discount burden on gross revenue |
| Refund Rate | Refunds / Gross Revenue | Refund burden on gross revenue |

All five use DAX DIVIDE to return blank when the denominator is zero. Definitions are maintained in both the TMDL source and model generator, bringing the semantic model to 57 measures.
