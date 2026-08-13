# Business requirements

## Decision context

CommercePulse Europe is a synthetic ten-market omnichannel retailer. Leadership sees revenue growth alongside weakening contribution economics and needs one governed view across commercial, product, marketing, operations, finance, CRM, and supply chain.

## Primary decision

Identify where growth is destroying or protecting contribution margin, quantify the operational and customer drivers, and turn the evidence into owned actions with measurable guardrails.

## Stakeholders and decisions

| Stakeholder | Decision supported | Required evidence |
|---|---|---|
| General Manager | Balance growth and margin recovery | Revenue, contribution, target variance, root-cause bridge |
| Finance Director | Govern profitable growth | Reconciled EUR economics, targets, allocation coverage |
| Commercial Director | Reprice and control discounting | Category/channel contribution and discount pressure |
| Marketing Lead | Reallocate spend | Attributed ROAS, contribution after media, spend pacing |
| Head of E-commerce | Improve conversion | Funnel, device performance, load time, confidence intervals |
| Operations Director | Recover delivery reliability | On-time rate, carrier/hub exceptions, return reasons, cost |
| Inventory Planning Lead | Reduce lost demand safely | Stockout rate, lost units/revenue, reorder exceptions |
| CRM Lead | Improve customer value | Cohort retention, repeat rate, customer value deciles |

## Functional requirements

1. Generate the same scenario from the same seed across CI and portfolio profiles.
2. Preserve raw records, isolate known defects, and expose clean records only after critical checks pass.
3. Convert local-currency generated economics to EUR using traceable ECB reference rates.
4. Reconcile item economics to monthly finance outputs within €0.02.
5. Allocate marketing spend completely, including residual market-month spend when a channel has no completed-order revenue.
6. Publish governed marts at grains appropriate for management, customer, product, channel, and operations analysis.
7. Expose consistent KPI definitions in Python, SQL/dbt, Power BI/DAX, and Excel.
8. Quantify uncertainty for rates and forecasts; label observational associations as non-causal.
9. Provide a six-page Power BI decision flow and an editable Excel action workflow.
10. Make the entire CI scenario reproducible without proprietary services.

## Non-functional requirements

- Python 3.12, PostgreSQL 16, deterministic seed `20260813`.
- CI execution finishes on a standard hosted runner.
- The full profile produces at least 2,000,000 rows across all generated tables.
- No names, email addresses, street addresses, or other direct identifiers.
- Every material output has a source, definition, test, or reconciliation path.
- Power BI source passes current schema validation with no errors or warnings.
- Excel contains live formulas, native charts, controlled inputs, and a visible validation gate.

## Acceptance measures

| Measure | Acceptance condition |
|---|---|
| Data quality | All critical clean-layer checks PASS |
| Finance reconciliation | Item-to-month maximum delta ≤ €0.02 |
| Marketing allocation | Difference within max(€10, 1% of spend); target 100% |
| SQL portfolio | Exactly 24 documented analyses |
| Power BI | Six pages, 36 visuals, valid PBIP/PBIR/TMDL source |
| Excel | Eight sheets, file >10 KB, no formula errors in final scan |
| Notebook | Every code cell executed and stored |
| Full scale | Aggregate generated rows ≥2M |
