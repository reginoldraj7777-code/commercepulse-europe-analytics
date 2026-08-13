# CommercePulse Europe v1.0.0

Release date: 2026-08-13

## Delivered

- Deterministic ten-market European commerce scenario with CI and 2M+ row profiles.
- Raw, quarantine, and clean Parquet layers with manifests and quality evidence.
- PostgreSQL 16 loader, dbt project, governed marts, tests, and 24 SQL analyses.
- Executed decision notebook, analytical charts, forecast diagnostics, and action register.
- Source-controlled Power BI Project with 16 tables, 52 DAX measures, 23 relationships, six pages, and 36 visuals.
- Formula-backed eight-sheet Excel manager pack with native charts, controlled edits, provenance, and 32-check gate.
- CI workflow, architecture, business/data contracts, KPI catalog, decision brief, traceability, and recruiter walkthrough.

## Verified release gates

| Gate | Result |
|---|---|
| Python tests | 16 passed |
| Ruff | Passed |
| SQLFluff | dbt models and 24 analyses passed |
| dbt parse | Passed with dbt 1.9 / PostgreSQL adapter 1.9 |
| Sample quality | PASS |
| Analytical reconciliation | PASS |
| Full-scale generation | 2,530,582 rows |
| Full-scale quality | PASS; 0 failed critical checks |
| Power BI schema validation | Succeeded; 0 errors, 0 warnings |
| Excel formula scan | 0 matched errors |
| Excel visual review | Eight sheets reviewed; PASS |
| Project contract validator | PASS |

## Environment boundary

Power BI Desktop is not available in the Linux build environment. The project source is rebuilt and validated against current Microsoft JSON schemas, but live PostgreSQL refresh, credential handling, interaction testing, and pixel-level report review remain a Windows Power BI Desktop handoff. This is the only open acceptance item in the portfolio scope.

## Disclosure

All business records and findings are deterministic synthetic data. Cached European Central Bank exchange-rate observations are the only real data source.
