from __future__ import annotations

import pandas as pd


def test_analysis_reconciliation_passes(built_project: dict) -> None:
    assert built_project["analysis"]["reconciliation_status"] == "PASS"
    checks = pd.read_csv(built_project["artifacts"] / "analysis" / "reconciliations.csv")
    assert checks["status"].eq("PASS").all()


def test_kpis_use_weighted_numerators_and_denominators(built_project: dict) -> None:
    monthly = pd.read_csv(built_project["artifacts"] / "analysis" / "monthly_kpis.csv")
    recomputed = monthly["units_returned"] / monthly["units_sold"]
    assert (recomputed - monthly["return_rate"]).abs().max() < 1e-12
    recomputed_margin = monthly["contribution_margin_eur"] / monthly["net_revenue_eur"]
    assert (recomputed_margin - monthly["contribution_margin_rate"]).abs().max() < 1e-12


def test_decision_outputs_are_complete(built_project: dict) -> None:
    analysis_root = built_project["artifacts"] / "analysis"
    required = {
        "monthly_kpis.csv",
        "cohort_retention.csv",
        "funnel.csv",
        "root_causes.csv",
        "forecast.csv",
        "conversion_driver_model.csv",
        "action_register.csv",
        "executive_summary.json",
    }
    assert required.issubset({path.name for path in analysis_root.iterdir()})
    actions = pd.read_csv(analysis_root / "action_register.csv")
    assert len(actions) >= 4
    assert actions["owner"].notna().all()
    assert actions["guardrail"].notna().all()


def test_forecast_has_backtest_and_intervals(built_project: dict) -> None:
    forecast = pd.read_csv(built_project["artifacts"] / "analysis" / "forecast.csv")
    assert len(forecast) == 3
    assert (forecast["forecast_upper_95_eur"] >= forecast["forecast_net_revenue_eur"]).all()
    assert (forecast["forecast_lower_95_eur"] <= forecast["forecast_net_revenue_eur"]).all()
    assert built_project["analysis"]["forecast_diagnostics"]["wape"] >= 0
