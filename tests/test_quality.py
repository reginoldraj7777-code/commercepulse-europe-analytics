from __future__ import annotations

import pandas as pd


def test_quality_gate_passes(built_project: dict) -> None:
    assert built_project["quality"]["status"] == "PASS"
    checks = pd.DataFrame(built_project["quality"]["checks"])
    assert checks["status"].eq("PASS").all()


def test_expected_defects_are_quarantined(built_project: dict) -> None:
    summary = pd.DataFrame(built_project["quality"]["quarantine_summary"])
    quarantined_rules = set(summary["rule"])
    assert {
        "duplicate_session_id",
        "missing_session_market",
        "invalid_order_item_product",
        "nonpositive_order_item_quantity",
        "negative_marketing_spend",
        "invalid_fulfillment_sequence",
        "orphan_return_item",
        "negative_inventory_on_hand",
    }.issubset(quarantined_rules)


def test_late_arrivals_are_retained_and_flagged(built_project: dict) -> None:
    assert built_project["quality"]["late_arrivals_retained"] > 0


def test_clean_orders_reconcile_to_atomic_items(built_project: dict) -> None:
    clean = built_project["data"] / "clean"
    orders = pd.read_parquet(clean / "fact_orders.parquet")
    items = pd.read_parquet(clean / "fact_order_items.parquet")
    totals = items.groupby("order_id").agg(
        gross=("gross_revenue_local", "sum"), discounts=("discount_local", "sum")
    )
    totals["net"] = totals["gross"] - totals["discounts"]
    merged = orders.set_index("order_id").join(totals)
    assert (merged["net_revenue_local"] - merged["net"]).abs().max() <= 0.02
