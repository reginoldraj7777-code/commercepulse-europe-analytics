from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from commercepulse.io import build_file_manifest, read_table, write_json, write_table
from commercepulse.schemas import validate_required_columns, validate_with_pandera

DIMENSION_TABLES = (
    "dim_date",
    "dim_geography",
    "dim_channel",
    "dim_campaign",
    "dim_customer",
    "dim_product",
    "bridge_market_holiday",
    "ref_fx_rates",
)

FACT_TABLES = (
    "fact_sessions",
    "fact_orders",
    "fact_order_items",
    "fact_marketing_spend",
    "fact_fulfillment",
    "fact_returns",
    "fact_inventory_snapshot",
    "fact_targets",
)


def _quarantine(frame: pd.DataFrame, mask: pd.Series, rule: str) -> pd.DataFrame:
    selected = frame.loc[mask].copy()
    selected["dq_rule"] = rule
    selected["dq_quarantined_at"] = datetime.now(UTC).isoformat()
    return selected


def _empty_quarantine(frame: pd.DataFrame) -> pd.DataFrame:
    empty = frame.iloc[0:0].copy()
    empty["dq_rule"] = pd.Series(dtype="object")
    empty["dq_quarantined_at"] = pd.Series(dtype="object")
    return empty


def _join_quarantines(parts: list[pd.DataFrame], source: pd.DataFrame) -> pd.DataFrame:
    nonempty = [part for part in parts if not part.empty]
    if not nonempty:
        return _empty_quarantine(source)
    return pd.concat(nonempty, ignore_index=True)


def _clean_sessions(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    ordered = frame.sort_values(["session_id", "loaded_at"], ascending=[True, False]).copy()
    duplicate_mask = ordered.duplicated("session_id", keep="first")
    duplicates = _quarantine(ordered, duplicate_mask, "duplicate_session_id")
    deduplicated = ordered.loc[~duplicate_mask].copy()
    missing_market = deduplicated["market_key"].isna()
    missing = _quarantine(deduplicated, missing_market, "missing_session_market")
    clean = deduplicated.loc[~missing_market].copy()
    clean["market_key"] = clean["market_key"].astype("int16")
    clean = clean.sort_values("session_id").reset_index(drop=True)
    return clean, _join_quarantines([duplicates, missing], frame)


def _clean_orders(
    frame: pd.DataFrame, valid_session_ids: set[int]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    duplicate = frame.duplicated("order_id", keep=False)
    invalid_session = ~frame["session_id"].isin(valid_session_ids)
    invalid_status = ~frame["order_status"].isin(["Completed", "Cancelled"])
    invalid_fx = frame["fx_local_per_eur"].isna() | frame["fx_local_per_eur"].le(0)
    reason = np.select(
        [duplicate, invalid_session, invalid_status, invalid_fx],
        [
            "duplicate_order_id",
            "orphan_order_session",
            "invalid_order_status",
            "invalid_order_fx_rate",
        ],
        default="",
    )
    bad = pd.Series(reason != "", index=frame.index)
    quarantined = frame.loc[bad].copy()
    quarantined["dq_rule"] = reason[bad]
    quarantined["dq_quarantined_at"] = datetime.now(UTC).isoformat()
    return frame.loc[~bad].copy().reset_index(drop=True), quarantined.reset_index(drop=True)


def _clean_order_items(
    frame: pd.DataFrame, valid_order_ids: set[int], valid_product_ids: set[int]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    duplicate = frame.duplicated("order_item_id", keep=False)
    orphan_order = ~frame["order_id"].isin(valid_order_ids)
    orphan_product = ~frame["product_key"].isin(valid_product_ids)
    invalid_quantity = frame["quantity"].le(0) | frame["quantity"].isna()
    invalid_money = (
        frame[["gross_revenue_local", "discount_local", "cogs_local"]]
        .lt(0)
        .any(axis=1)
        | frame["discount_local"].gt(frame["gross_revenue_local"])
    )
    reason = np.select(
        [duplicate, orphan_order, orphan_product, invalid_quantity, invalid_money],
        [
            "duplicate_order_item_id",
            "orphan_order_item_order",
            "invalid_order_item_product",
            "nonpositive_order_item_quantity",
            "invalid_order_item_amount",
        ],
        default="",
    )
    bad = pd.Series(reason != "", index=frame.index)
    quarantined = frame.loc[bad].copy()
    quarantined["dq_rule"] = reason[bad]
    quarantined["dq_quarantined_at"] = datetime.now(UTC).isoformat()
    return frame.loc[~bad].copy().reset_index(drop=True), quarantined.reset_index(drop=True)


def _reconcile_orders_to_items(
    orders: pd.DataFrame, items: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    totals = items.groupby("order_id", as_index=False).agg(
        gross_revenue_local=("gross_revenue_local", "sum"),
        discount_local=("discount_local", "sum"),
        item_quantity=("quantity", "sum"),
    )
    no_valid_item = ~orders["order_id"].isin(totals["order_id"])
    quarantined = _quarantine(orders, no_valid_item, "order_without_valid_items")
    clean = orders.loc[~no_valid_item].drop(
        columns=["gross_revenue_local", "discount_local", "net_revenue_local", "item_quantity"]
    )
    clean = clean.merge(totals, on="order_id", how="inner", validate="one_to_one")
    clean["net_revenue_local"] = clean["gross_revenue_local"] - clean["discount_local"]
    money_columns = [
        "gross_revenue_local",
        "discount_local",
        "net_revenue_local",
        "shipping_revenue_local",
        "tax_local",
    ]
    clean[money_columns] = clean[money_columns].round(2)
    return clean.sort_values("order_id").reset_index(drop=True), quarantined


def _clean_marketing(
    frame: pd.DataFrame,
    valid_markets: set[int],
    valid_channels: set[int],
    valid_campaigns: set[int],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    duplicate = frame.duplicated("spend_id", keep=False)
    invalid_spend = frame["spend_local"].lt(0) | frame["spend_local"].isna()
    invalid_fk = (
        ~frame["market_key"].isin(valid_markets)
        | ~frame["channel_key"].isin(valid_channels)
        | ~frame["campaign_key"].isin(valid_campaigns)
    )
    invalid_fx = frame["fx_local_per_eur"].le(0) | frame["fx_local_per_eur"].isna()
    reason = np.select(
        [duplicate, invalid_spend, invalid_fk, invalid_fx],
        [
            "duplicate_marketing_spend_id",
            "negative_marketing_spend",
            "invalid_marketing_dimension_key",
            "invalid_marketing_fx_rate",
        ],
        default="",
    )
    bad = pd.Series(reason != "", index=frame.index)
    quarantined = frame.loc[bad].copy()
    quarantined["dq_rule"] = reason[bad]
    quarantined["dq_quarantined_at"] = datetime.now(UTC).isoformat()
    return frame.loc[~bad].copy().reset_index(drop=True), quarantined.reset_index(drop=True)


def _clean_fulfillment(
    frame: pd.DataFrame, valid_order_ids: set[int]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    duplicate = frame.duplicated("fulfillment_id", keep=False) | frame.duplicated(
        "order_id", keep=False
    )
    orphan_order = ~frame["order_id"].isin(valid_order_ids)
    invalid_sequence = (
        frame["shipped_date"].gt(frame["delivered_date"])
        | frame["delivered_date"].isna()
        | frame["shipped_date"].isna()
    )
    reason = np.select(
        [duplicate, orphan_order, invalid_sequence],
        ["duplicate_fulfillment_grain", "orphan_fulfillment_order", "invalid_fulfillment_sequence"],
        default="",
    )
    bad = pd.Series(reason != "", index=frame.index)
    quarantined = frame.loc[bad].copy()
    quarantined["dq_rule"] = reason[bad]
    quarantined["dq_quarantined_at"] = datetime.now(UTC).isoformat()
    clean = frame.loc[~bad].copy()
    clean["is_on_time"] = clean["delivered_date"].le(clean["promised_delivery_date"])
    return clean.reset_index(drop=True), quarantined.reset_index(drop=True)


def _clean_returns(
    frame: pd.DataFrame,
    valid_order_ids: set[int],
    clean_items: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if frame.empty:
        return frame.copy(), _empty_quarantine(frame)
    item_quantity = clean_items.set_index("order_item_id")["quantity"]
    duplicate = frame.duplicated("return_id", keep=False)
    orphan_order = ~frame["order_id"].isin(valid_order_ids)
    orphan_item = ~frame["order_item_id"].isin(item_quantity.index)
    allowed_quantity = frame["order_item_id"].map(item_quantity)
    invalid_units = frame["units_returned"].le(0) | frame["units_returned"].gt(allowed_quantity)
    invalid_money = frame[["refund_local", "handling_cost_local", "recovered_cogs_local"]].lt(0).any(axis=1)
    reason = np.select(
        [duplicate, orphan_order, orphan_item, invalid_units, invalid_money],
        [
            "duplicate_return_id",
            "orphan_return_order",
            "orphan_return_item",
            "invalid_return_units",
            "invalid_return_amount",
        ],
        default="",
    )
    bad = pd.Series(reason != "", index=frame.index)
    quarantined = frame.loc[bad].copy()
    quarantined["dq_rule"] = reason[bad]
    quarantined["dq_quarantined_at"] = datetime.now(UTC).isoformat()
    return frame.loc[~bad].copy().reset_index(drop=True), quarantined.reset_index(drop=True)


def _clean_inventory(
    frame: pd.DataFrame, valid_markets: set[int], valid_products: set[int]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    duplicate = frame.duplicated(["snapshot_date", "market_key", "product_key"], keep=False)
    invalid_fk = ~frame["market_key"].isin(valid_markets) | ~frame["product_key"].isin(valid_products)
    invalid_units = (
        frame[["on_hand_units", "in_transit_units", "reorder_point_units", "estimated_lost_units"]]
        .lt(0)
        .any(axis=1)
    )
    reason = np.select(
        [duplicate, invalid_fk, invalid_units],
        ["duplicate_inventory_grain", "invalid_inventory_dimension_key", "negative_inventory_on_hand"],
        default="",
    )
    bad = pd.Series(reason != "", index=frame.index)
    quarantined = frame.loc[bad].copy()
    quarantined["dq_rule"] = reason[bad]
    quarantined["dq_quarantined_at"] = datetime.now(UTC).isoformat()
    return frame.loc[~bad].copy().reset_index(drop=True), quarantined.reset_index(drop=True)


def _clean_targets(
    frame: pd.DataFrame, valid_markets: set[int], valid_channels: set[int]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    duplicate = frame.duplicated(["month_key", "market_key", "channel_key"], keep=False)
    invalid_fk = ~frame["market_key"].isin(valid_markets) | ~frame["channel_key"].isin(valid_channels)
    invalid_target = frame[
        ["net_revenue_target_eur", "contribution_margin_target_eur", "orders_target"]
    ].lt(0).any(axis=1)
    reason = np.select(
        [duplicate, invalid_fk, invalid_target],
        ["duplicate_target_grain", "invalid_target_dimension_key", "negative_target"],
        default="",
    )
    bad = pd.Series(reason != "", index=frame.index)
    quarantined = frame.loc[bad].copy()
    quarantined["dq_rule"] = reason[bad]
    quarantined["dq_quarantined_at"] = datetime.now(UTC).isoformat()
    return frame.loc[~bad].copy().reset_index(drop=True), quarantined.reset_index(drop=True)


def _check_record(
    checks: list[dict[str, Any]],
    check: str,
    table: str,
    passed: bool,
    observed: Any,
    expected: str,
    severity: str = "critical",
) -> None:
    checks.append(
        {
            "check": check,
            "table": table,
            "status": "PASS" if passed else "FAIL",
            "observed": observed,
            "expected": expected,
            "severity": severity,
        }
    )


def validate_clean_tables(tables: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for name, frame in tables.items():
        required_errors = validate_required_columns(name, frame)
        _check_record(
            checks,
            "required_columns",
            name,
            not required_errors,
            "; ".join(required_errors) if required_errors else "all present",
            "all required columns present",
        )
    _check_record(
        checks,
        "unique_session_id",
        "fact_sessions",
        tables["fact_sessions"]["session_id"].is_unique,
        int(tables["fact_sessions"]["session_id"].duplicated().sum()),
        "0 duplicate IDs",
    )
    _check_record(
        checks,
        "session_market_not_null",
        "fact_sessions",
        tables["fact_sessions"]["market_key"].notna().all(),
        int(tables["fact_sessions"]["market_key"].isna().sum()),
        "0 null market keys",
    )
    _check_record(
        checks,
        "unique_order_id",
        "fact_orders",
        tables["fact_orders"]["order_id"].is_unique,
        int(tables["fact_orders"]["order_id"].duplicated().sum()),
        "0 duplicate IDs",
    )
    _check_record(
        checks,
        "unique_order_item_id",
        "fact_order_items",
        tables["fact_order_items"]["order_item_id"].is_unique,
        int(tables["fact_order_items"]["order_item_id"].duplicated().sum()),
        "0 duplicate IDs",
    )
    product_ids = set(tables["dim_product"]["product_key"])
    orphan_items = int((~tables["fact_order_items"]["product_key"].isin(product_ids)).sum())
    _check_record(
        checks,
        "order_item_product_fk",
        "fact_order_items",
        orphan_items == 0,
        orphan_items,
        "0 orphan product keys",
    )
    invalid_quantities = int(tables["fact_order_items"]["quantity"].le(0).sum())
    _check_record(
        checks,
        "positive_item_quantity",
        "fact_order_items",
        invalid_quantities == 0,
        invalid_quantities,
        "0 nonpositive quantities",
    )
    negative_spend = int(tables["fact_marketing_spend"]["spend_local"].lt(0).sum())
    _check_record(
        checks,
        "nonnegative_marketing_spend",
        "fact_marketing_spend",
        negative_spend == 0,
        negative_spend,
        "0 negative spend rows",
    )
    invalid_fulfillment = int(
        tables["fact_fulfillment"]["delivered_date"]
        .lt(tables["fact_fulfillment"]["shipped_date"])
        .sum()
    )
    _check_record(
        checks,
        "fulfillment_date_sequence",
        "fact_fulfillment",
        invalid_fulfillment == 0,
        invalid_fulfillment,
        "0 delivered-before-shipped rows",
    )
    valid_item_ids = set(tables["fact_order_items"]["order_item_id"])
    orphan_returns = int((~tables["fact_returns"]["order_item_id"].isin(valid_item_ids)).sum())
    _check_record(
        checks,
        "return_item_fk",
        "fact_returns",
        orphan_returns == 0,
        orphan_returns,
        "0 orphan order-item keys",
    )
    negative_inventory = int(tables["fact_inventory_snapshot"]["on_hand_units"].lt(0).sum())
    _check_record(
        checks,
        "nonnegative_inventory",
        "fact_inventory_snapshot",
        negative_inventory == 0,
        negative_inventory,
        "0 negative on-hand rows",
    )
    order_totals = tables["fact_order_items"].groupby("order_id", as_index=False).agg(
        gross=("gross_revenue_local", "sum"), discounts=("discount_local", "sum")
    )
    order_totals["net"] = order_totals["gross"] - order_totals["discounts"]
    reconciliation = tables["fact_orders"][["order_id", "net_revenue_local"]].merge(
        order_totals[["order_id", "net"]], on="order_id", how="left", validate="one_to_one"
    )
    max_delta = float((reconciliation["net_revenue_local"] - reconciliation["net"]).abs().max())
    _check_record(
        checks,
        "order_item_reconciliation",
        "fact_orders",
        max_delta <= 0.02,
        round(max_delta, 6),
        "maximum order-level delta <= EUR-equivalent local 0.02",
    )
    for name in ("fact_sessions", "fact_order_items"):
        errors = validate_with_pandera(name, tables[name])
        _check_record(
            checks,
            "pandera_schema",
            name,
            not errors,
            "; ".join(errors) if errors else "schema valid",
            "no Pandera violations",
        )
    return checks


def run_quality_pipeline(input_root: Path, output_root: Path) -> dict[str, Any]:
    raw_folder = input_root / "raw"
    clean_folder = input_root / "clean"
    quarantine_folder = input_root / "quarantine"
    clean_folder.mkdir(parents=True, exist_ok=True)
    quarantine_folder.mkdir(parents=True, exist_ok=True)
    output_root.mkdir(parents=True, exist_ok=True)

    raw = {name: read_table(raw_folder, name) for name in DIMENSION_TABLES + FACT_TABLES}
    clean: dict[str, pd.DataFrame] = {name: raw[name].copy() for name in DIMENSION_TABLES}
    quarantines: dict[str, pd.DataFrame] = {}

    clean["fact_sessions"], quarantines["fact_sessions"] = _clean_sessions(raw["fact_sessions"])
    valid_sessions = set(clean["fact_sessions"]["session_id"])
    clean["fact_orders"], quarantines["fact_orders"] = _clean_orders(
        raw["fact_orders"], valid_sessions
    )
    valid_orders = set(clean["fact_orders"]["order_id"])
    valid_products = set(clean["dim_product"]["product_key"])
    clean["fact_order_items"], quarantines["fact_order_items"] = _clean_order_items(
        raw["fact_order_items"], valid_orders, valid_products
    )
    reconciled_orders, no_item_orders = _reconcile_orders_to_items(
        clean["fact_orders"], clean["fact_order_items"]
    )
    if not no_item_orders.empty:
        quarantines["fact_orders"] = _join_quarantines(
            [quarantines["fact_orders"], no_item_orders], raw["fact_orders"]
        )
    clean["fact_orders"] = reconciled_orders
    valid_orders = set(clean["fact_orders"]["order_id"])
    clean["fact_order_items"] = clean["fact_order_items"].loc[
        clean["fact_order_items"]["order_id"].isin(valid_orders)
    ].reset_index(drop=True)
    valid_markets = set(clean["dim_geography"]["market_key"])
    valid_channels = set(clean["dim_channel"]["channel_key"])
    valid_campaigns = set(clean["dim_campaign"]["campaign_key"])
    clean["fact_marketing_spend"], quarantines["fact_marketing_spend"] = _clean_marketing(
        raw["fact_marketing_spend"], valid_markets, valid_channels, valid_campaigns
    )
    clean["fact_fulfillment"], quarantines["fact_fulfillment"] = _clean_fulfillment(
        raw["fact_fulfillment"], valid_orders
    )
    clean["fact_returns"], quarantines["fact_returns"] = _clean_returns(
        raw["fact_returns"], valid_orders, clean["fact_order_items"]
    )
    clean["fact_inventory_snapshot"], quarantines["fact_inventory_snapshot"] = _clean_inventory(
        raw["fact_inventory_snapshot"], valid_markets, valid_products
    )
    clean["fact_targets"], quarantines["fact_targets"] = _clean_targets(
        raw["fact_targets"], valid_markets, valid_channels
    )

    valid_order_ids = set(clean["fact_orders"]["order_id"])
    invalid_converted = clean["fact_sessions"]["converted_order_id"].notna() & ~clean[
        "fact_sessions"
    ]["converted_order_id"].isin(valid_order_ids)
    clean["fact_sessions"].loc[invalid_converted, "converted_order_id"] = pd.NA

    for table_name, frame in clean.items():
        write_table(frame, clean_folder, table_name)
    for table_name in FACT_TABLES:
        quarantine = quarantines.get(table_name, _empty_quarantine(raw[table_name]))
        write_table(quarantine, quarantine_folder, table_name)

    checks = validate_clean_tables(clean)
    checks_frame = pd.DataFrame(checks)
    checks_frame.to_csv(output_root / "data_quality_checks.csv", index=False)
    quarantine_summary = []
    for table_name, frame in quarantines.items():
        if frame.empty:
            continue
        for rule, count in frame.groupby("dq_rule").size().items():
            quarantine_summary.append(
                {"table": table_name, "rule": rule, "quarantined_rows": int(count)}
            )
    generation_manifest_path = input_root / "generation_manifest.json"
    expected_defects = []
    if generation_manifest_path.exists():
        expected_defects = json.loads(generation_manifest_path.read_text(encoding="utf-8")).get(
            "injected_defects", []
        )
    result = {
        "validated_at_utc": datetime.now(UTC).isoformat(),
        "status": "PASS" if (checks_frame["status"] == "PASS").all() else "FAIL",
        "checks": checks,
        "quarantine_summary": quarantine_summary,
        "expected_injected_defects": expected_defects,
        "raw_files": build_file_manifest(raw_folder),
        "clean_files": build_file_manifest(clean_folder),
        "quarantine_files": build_file_manifest(quarantine_folder),
        "late_arrivals_retained": int(clean["fact_sessions"]["is_late_arrival"].sum()),
        "policy": (
            "Critical/high invalid records are quarantined; stable late-arrival records are retained "
            "with an explicit flag. Order totals are recomputed from surviving atomic items."
        ),
    }
    write_json(result, output_root / "data_quality_report.json")
    if result["status"] != "PASS":
        failed = checks_frame.loc[checks_frame["status"] == "FAIL", "check"].tolist()
        raise ValueError(f"Clean data failed quality checks: {failed}")
    return result
