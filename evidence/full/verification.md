# Verification record — 2026-10-20

Executed locally on Python 3.12:

- `python -m commercepulse.evidence --profile full --persist --output evidence/full`: completed; 8,000,000 events, 650,000 journeys, 32 Parquet event partitions.
- `python -m pytest -q`: 20 passed.
- `python -m ruff check src tests scripts`: all checks passed.
- `python scripts/validate_project.py`: PROJECT VALIDATION: PASS. This checks existing release artifacts; it does not re-execute PostgreSQL, dbt, Excel or Power BI Desktop.
- `node --check scripts/build_powerbi_model.mjs`: passed syntax check.
- `python scripts/render_evidence.py`: chart generated from committed metrics and CSVs and visually inspected.

Databricks and Power BI Desktop were not executed. Existing historical validation files retain their original scope. The GitHub workflow reruns the warehouse and report-source gates separately.
