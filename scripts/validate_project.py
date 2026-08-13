from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    failures: list[str] = []
    quality_path = ROOT / "artifacts" / "validation" / "data_quality_report.json"
    analysis_path = ROOT / "artifacts" / "analysis" / "executive_summary.json"
    for path in (quality_path, analysis_path):
        if not path.exists():
            failures.append(f"missing {path.relative_to(ROOT)}")
    if quality_path.exists():
        quality = json.loads(quality_path.read_text(encoding="utf-8"))
        if quality.get("status") != "PASS":
            failures.append("data quality status is not PASS")
    if analysis_path.exists():
        analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
        if analysis.get("reconciliation_status") != "PASS":
            failures.append("analysis reconciliation is not PASS")
    full_run_path = ROOT / "artifacts" / "validation" / "full_run_manifest.json"
    if not full_run_path.exists():
        failures.append("full portfolio run manifest is missing")
    else:
        full_run = json.loads(full_run_path.read_text(encoding="utf-8"))
        if full_run.get("generated_rows", 0) < 2_000_000:
            failures.append("full portfolio run is below 2,000,000 rows")
        if full_run.get("quality_status") != "PASS":
            failures.append("full portfolio quality status is not PASS")
    query_count = len(list((ROOT / "sql" / "analysis").glob("[0-9][0-9]_*.sql")))
    if query_count != 24:
        failures.append(f"expected 24 SQL portfolio queries, found {query_count}")
    power_bi_files = [
        ROOT / "powerbi" / "CommercePulse.pbip",
        ROOT / "powerbi" / "CommercePulse.Report" / "definition.pbir",
        ROOT / "powerbi" / "CommercePulse.SemanticModel" / "definition.pbism",
    ]
    for path in power_bi_files:
        if not path.exists():
            failures.append(f"missing {path.relative_to(ROOT)}")
        elif path.suffix in {".pbip", ".pbir", ".pbism"}:
            json.loads(path.read_text(encoding="utf-8"))
    power_bi_validation = ROOT / "artifacts" / "validation" / "powerbi_validation.json"
    if not power_bi_validation.exists():
        failures.append("Power BI schema validation evidence is missing")
    else:
        result = json.loads(power_bi_validation.read_text(encoding="utf-8"))["data"]
        if result.get("result") != "succeeded" or result.get("errorCount") != 0:
            failures.append("Power BI schema validation did not succeed cleanly")
    workbook = ROOT / "excel" / "CommercePulse_Manager_Pack.xlsx"
    if not workbook.exists() or workbook.stat().st_size < 10000:
        failures.append("Excel manager pack is missing or implausibly small")
    excel_validation = ROOT / "artifacts" / "validation" / "excel_validation.json"
    if not excel_validation.exists():
        failures.append("Excel validation evidence is missing")
    else:
        result = json.loads(excel_validation.read_text(encoding="utf-8"))
        if result.get("status") != "PASS" or result.get("formula_error_matches") != 0:
            failures.append("Excel validation did not succeed cleanly")
    notebook = ROOT / "notebooks" / "commercepulse_decision_analysis.ipynb"
    if not notebook.exists():
        failures.append("executed decision notebook is missing")
    else:
        payload = json.loads(notebook.read_text(encoding="utf-8"))
        if any(cell.get("cell_type") == "code" and cell.get("execution_count") is None for cell in payload["cells"]):
            failures.append("decision notebook contains unexecuted code cells")
    reconciliation = ROOT / "artifacts" / "analysis" / "reconciliations.csv"
    if reconciliation.exists() and not pd.read_csv(reconciliation)["status"].eq("PASS").all():
        failures.append("one or more analytical reconciliations failed")
    if failures:
        print("PROJECT VALIDATION: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PROJECT VALIDATION: PASS")
    print(
        "- deterministic sample and 2M+ portfolio run, quality checks, analysis, notebook, "
        "Power BI, Excel, and SQL assets present"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
