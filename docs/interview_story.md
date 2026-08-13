# Interview story

## Situation

Leadership sees double-digit quarterly revenue growth, yet contribution margin is collapsing. Data is fragmented across demand, orders, marketing, fulfillment, returns, inventory, and targets, with multiple currencies and imperfect operational feeds.

## Task

Build a trustworthy decision system that explains the gap, quantifies uncertainty, and converts findings into owned actions—while remaining reproducible and reviewable without access to a private company environment.

## Actions

1. Designed deterministic synthetic operations across ten European markets and grounded currency conversion in cached ECB reference rates.
2. Injected known defects to demonstrate realistic quarantine and data-quality controls.
3. Modeled atomic order-item contribution, including refunds, recovered COGS, fulfillment, and complete marketing allocation.
4. Built dbt marts and 24 SQL analyses around management decisions rather than generic technical examples.
5. Used confidence intervals, observational diagnostics, and a backtested forecast benchmark to communicate uncertainty honestly.
6. Built a governed Power BI semantic model/report and a formula-backed Excel action workflow.
7. Added CI, tests, manifests, traceability, and documentation so another analyst can challenge every claim.

## Result

The CI scenario isolates a clear growth-quality problem: Q2 revenue +12.8%, contribution -€52.2k, with the largest pressure in Paid Search, Electronics, and Germany. Four actions are assigned to accountable leaders with guardrails. The sample passes data quality, finance reconciliation, allocation, notebook, workbook, Power BI schema, and repository gates.

## Reflection

The key design choice was not a more complex model; it was preserving grain and accountability. Session conversion is not forced into a product hierarchy it cannot support, overlapping root-cause cuts are not summed, and attribution is not labeled causal. That restraint makes the recommendation more credible.
