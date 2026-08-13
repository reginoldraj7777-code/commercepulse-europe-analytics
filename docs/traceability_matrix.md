# Traceability matrix

| Requirement / decision | Data/model | KPI or analysis | Decision product | Validation |
|---|---|---|---|---|
| Profitable growth | Order items, targets, marketing | Net revenue, contribution, margin rate, target variance | Executive + Growth pages, Summary workbook | Item/month reconciliation |
| Marketing efficiency | Spend + order profitability | ROAS, spend pacing, channel contribution | Growth page, SQL 05/18/19 | Allocation coverage |
| Conversion quality | Sessions | Funnel, conversion, Wilson CI, page-load association | Product page, notebook, SQL 08/09 | Session uniqueness and domains |
| Customer retention | Orders + customers | Cohort retention, repeat rate, value deciles | Customer page, SQL 10/11/23 | Customer/order keys |
| Return economics | Returns + items | Unit return rate, refund/recovery, Pareto | Operations page, SQL 12/13 | Return-item FK |
| Delivery reliability | Fulfillment + orders | On-time rate, transit, carrier/hub exceptions | Operations page, SQL 14/15 | Date-sequence check |
| Inventory opportunity | Inventory + products | Stockout rate, lost units/revenue, reorder queue | Operations page, SQL 16/17 | Nonnegative inventory |
| Finance trust | FX + item economics | EUR reconciliation, contribution identity | Checks sheet, SQL 21/22 | FX and reconciliation gates |
| Action ownership | Diagnostic outputs | Root causes, guardrails, priority | Root Cause page, Action Register, SQL 24 | Status validation and review cadence |
| Planning uncertainty | Monthly revenue | Backtested benchmark and 95% interval | Forecast sheet, notebook | WAPE, bias, interval checks |

## Code-to-output anchors

- Generator: `src/commercepulse/generator.py`
- Quality: `src/commercepulse/quality.py`
- Analysis: `src/commercepulse/analysis.py`
- dbt model tests: `dbt/models/marts/_models.yml`, `dbt/tests/`
- DAX: `powerbi/CommercePulse.SemanticModel/definition/tables/KPI Measures.tmdl`
- Excel formulas: `scripts/build_excel_manager_pack.mjs`
- Release validation: `scripts/validate_project.py`
