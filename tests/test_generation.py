from __future__ import annotations

from dataclasses import replace

import pandas as pd

from commercepulse.config import load_profile
from commercepulse.generator import generate_scenario


def test_scenario_contains_required_domains(built_project: dict) -> None:
    tables = {row["table"] for row in built_project["generation"]["files"]}
    assert {
        "fact_sessions",
        "fact_orders",
        "fact_order_items",
        "fact_marketing_spend",
        "fact_fulfillment",
        "fact_returns",
        "fact_inventory_snapshot",
        "fact_targets",
        "ref_fx_rates",
    }.issubset(tables)


def test_generation_is_deterministic(tmp_path) -> None:
    profile = replace(load_profile("ci"), customers=300, products=40, sessions=4000)
    first = generate_scenario(profile, tmp_path / "one")
    second = generate_scenario(profile, tmp_path / "two")
    first_hashes = {row["table"]: row["sha256"] for row in first["files"]}
    second_hashes = {row["table"]: row["sha256"] for row in second["files"]}
    assert first_hashes == second_hashes


def test_ecb_rates_are_real_reference_data(built_project: dict) -> None:
    path = built_project["data"] / "raw" / "ref_fx_rates.parquet"
    rates = pd.read_parquet(path)
    assert set(rates["currency_code"]) == {"EUR", "GBP", "PLN", "SEK"}
    assert rates["source_name"].str.contains("European Central Bank").all()
    assert rates["local_per_eur"].gt(0).all()


def test_portfolio_profile_is_realistic_scale() -> None:
    profile = load_profile("portfolio")
    assert profile.sessions >= 1_500_000
    assert profile.customers >= 50_000
    assert profile.products >= 500
