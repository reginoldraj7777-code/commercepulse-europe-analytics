from __future__ import annotations

from commercepulse.config import PROJECT_ROOT


def test_sql_portfolio_has_twenty_four_queries() -> None:
    queries = sorted((PROJECT_ROOT / "sql" / "analysis").glob("[0-9][0-9]_*.sql"))
    assert len(queries) == 24
    combined = "\n".join(path.read_text(encoding="utf-8").lower() for path in queries)
    assert " over (" in combined
    assert "percentile_cont" in combined
    assert "nullif" in combined
    assert "dense_rank" in combined or "row_number" in combined


def test_power_bi_and_excel_contracts_exist() -> None:
    assert (PROJECT_ROOT / "powerbi" / "CommercePulse.pbip").exists()
    assert (PROJECT_ROOT / "excel" / "CommercePulse_Manager_Pack.xlsx").exists()


def test_no_legacy_domain_language_in_primary_code() -> None:
    forbidden = ("red hat", "snowflake readiness", "stock market", "telemetry platform")
    paths = list((PROJECT_ROOT / "src").rglob("*.py")) + [PROJECT_ROOT / "README.md"]
    content = "\n".join(
        path.read_text(encoding="utf-8").lower() for path in paths if path.exists()
    )
    for phrase in forbidden:
        assert phrase not in content


def test_core_documentation_exists() -> None:
    required = [
        "business_requirements.md",
        "architecture.md",
        "data_contracts.md",
        "kpi_catalog.md",
        "decision_brief.md",
        "dashboard_blueprint.md",
        "recruiter_walkthrough.md",
        "limitations.md",
    ]
    docs = PROJECT_ROOT / "docs"
    assert all((docs / name).exists() for name in required)
