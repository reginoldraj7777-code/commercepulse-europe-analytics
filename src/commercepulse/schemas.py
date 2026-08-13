from __future__ import annotations

from typing import Any

import pandas as pd

try:
    import pandera.pandas as pa
    Check = pa.Check
    Column = pa.Column
    DataFrameSchema = pa.DataFrameSchema
except ImportError:  # pragma: no cover - used only in deliberately minimal environments
    pa = None
    Check = Column = DataFrameSchema = None


REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    "fact_sessions": (
        "session_id",
        "session_ts",
        "date_key",
        "customer_key",
        "market_key",
        "channel_key",
        "device_type",
        "converted_order_id",
    ),
    "fact_orders": (
        "order_id",
        "session_id",
        "order_ts",
        "customer_key",
        "market_key",
        "currency_code",
        "fx_local_per_eur",
        "net_revenue_local",
    ),
    "fact_order_items": (
        "order_item_id",
        "order_id",
        "product_key",
        "quantity",
        "gross_revenue_local",
        "discount_local",
        "cogs_local",
    ),
    "fact_marketing_spend": (
        "spend_id",
        "date_key",
        "market_key",
        "channel_key",
        "campaign_key",
        "spend_local",
        "fx_local_per_eur",
    ),
}


def validate_required_columns(table_name: str, frame: pd.DataFrame) -> list[str]:
    missing = sorted(set(REQUIRED_COLUMNS.get(table_name, ())) - set(frame.columns))
    return [f"{table_name}: missing required column {column}" for column in missing]


def pandera_schemas() -> dict[str, Any]:
    if pa is None:
        return {}
    return {
        "fact_sessions": DataFrameSchema(
            {
                "session_id": Column(int, nullable=False),
                "customer_key": Column(int, Check.ge(1), nullable=False),
                "channel_key": Column(int, Check.ge(1), nullable=False),
                "product_views": Column(int, Check.ge(0), nullable=False),
            },
            strict=False,
            coerce=True,
        ),
        "fact_order_items": DataFrameSchema(
            {
                "order_item_id": Column(int, nullable=False),
                "order_id": Column(int, nullable=False),
                "quantity": Column(int, Check.gt(0), nullable=False),
                "gross_revenue_local": Column(float, Check.ge(0), nullable=False),
                "discount_local": Column(float, Check.ge(0), nullable=False),
                "cogs_local": Column(float, Check.ge(0), nullable=False),
            },
            strict=False,
            coerce=True,
        ),
    }


def validate_with_pandera(table_name: str, frame: pd.DataFrame) -> list[str]:
    schema = pandera_schemas().get(table_name)
    if schema is None:
        return []
    try:
        schema.validate(frame, lazy=True)
    except pa.errors.SchemaErrors as exc:
        return [f"{table_name}: {len(exc.failure_cases)} Pandera schema violations"]
    return []
