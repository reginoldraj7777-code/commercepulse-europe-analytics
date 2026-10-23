# Warehouse walkthrough

The ten-market warehouse scenario connects synthetic orders, sessions, marketing, returns and inventory to PostgreSQL/dbt marts, a Power BI report and an Excel manager pack. It is separate from the six-market 8M-event benchmark in `evidence/full/`.

## Generate and inspect the sample

Run from the repository root with Python 3.12:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m commercepulse.cli all --profile ci --data-root data/sample --artifact-root artifacts
python scripts/build_notebook.py
python scripts/execute_notebook.py notebooks/commercepulse_decision_analysis.ipynb
pytest
python scripts/validate_project.py
```

The sample produces 115,397 raw rows and PASS quality/reconciliation checks. Inspect the [executive summary](../artifacts/analysis/executive_summary.json), [quality report](../artifacts/validation/data_quality_report.json) and [decision brief](decision_brief.md) for its findings and assumptions.

## Build the warehouse

Docker and PostgreSQL port 5432 are required:

```bash
docker compose up -d postgres
python -m commercepulse.cli load-postgres --input data/sample/clean
dbt build --project-dir dbt --profiles-dir dbt
```

Connection defaults match [docker-compose.yml](../docker-compose.yml). Override them through the `POSTGRES_*` variables in [.env.example](../.env.example). dbt writes marts to the `portfolio` schema.

## Open the decision products

| Product | Purpose | Setup |
|---|---|---|
| [Power BI project](../powerbi/CommercePulse.pbip) | Six pages, 57 measure definitions and 23 relationships | Follow the [Power BI guide](powerbi_guide.md); Desktop refresh requires Windows and the marts |
| [Excel manager pack](../excel/CommercePulse_Manager_Pack.xlsx) | Formulas, charts, reconciliation and management actions | See the [Excel guide](excel_guide.md) |
| [Executed notebook](../notebooks/commercepulse_decision_analysis.ipynb) | Diagnostics, uncertainty, forecast and actions | Regenerate with the commands above |
| [SQL analyses](../sql/analysis/README.md) | 24 commercial and operational questions | Run against the PostgreSQL marts |

## Larger warehouse profile

```bash
python -m commercepulse.cli generate --profile portfolio --output data/full
python -m commercepulse.cli quality --input data/full --output artifacts/full_validation
```

The committed [full-run manifest](../artifacts/validation/full_run_manifest.json) records 2,530,582 generated rows, 2,527,989 clean rows and 2,593 quarantined rows. This profile has its own grain and denominator; its counts must not be combined with the independent event benchmark.

All operating records are synthetic. Cached ECB exchange rates are public reference observations. See the [source manifest](source_manifest.md), [data contracts](data_contracts.md) and [limitations](limitations.md).
