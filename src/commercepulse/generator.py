from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from commercepulse.config import PROJECT_ROOT, ScenarioProfile
from commercepulse.fx import ECB_SOURCE_URL, load_ecb_rates
from commercepulse.io import build_file_manifest, ensure_directories, write_json, write_table

CHANNEL_ROWS = [
    (1, "Organic Search", "Owned/Earned", False),
    (2, "Paid Search", "Paid", True),
    (3, "Paid Social", "Paid", True),
    (4, "Email / CRM", "Owned/Earned", False),
    (5, "Direct", "Owned/Earned", False),
    (6, "Marketplace", "Paid", True),
]

MARKET_ROWS = [
    (1, "DE", "Germany", "DACH", "EUR", 0.19, 0.31, "Central"),
    (2, "AT", "Austria", "DACH", "EUR", 0.20, 0.07, "Central"),
    (3, "NL", "Netherlands", "Benelux", "EUR", 0.21, 0.08, "West"),
    (4, "FR", "France", "West", "EUR", 0.20, 0.12, "West"),
    (5, "ES", "Spain", "South", "EUR", 0.21, 0.08, "South"),
    (6, "IT", "Italy", "South", "EUR", 0.22, 0.10, "South"),
    (7, "BE", "Belgium", "Benelux", "EUR", 0.21, 0.05, "West"),
    (8, "PL", "Poland", "Central/East", "PLN", 0.23, 0.07, "Central"),
    (9, "SE", "Sweden", "Nordics", "SEK", 0.25, 0.06, "North"),
    (10, "GB", "United Kingdom", "UKI", "GBP", 0.20, 0.06, "North"),
]

CATEGORY_CONFIG = {
    "Electronics": {
        "subcategories": ("Audio", "Smart Home", "Accessories"),
        "price": 115.0,
        "margin": 0.34,
        "return": 0.08,
    },
    "Home": {
        "subcategories": ("Kitchen", "Decor", "Storage"),
        "price": 72.0,
        "margin": 0.42,
        "return": 0.07,
    },
    "Apparel": {
        "subcategories": ("Tops", "Outerwear", "Footwear"),
        "price": 64.0,
        "margin": 0.47,
        "return": 0.18,
    },
    "Beauty": {
        "subcategories": ("Skincare", "Haircare", "Fragrance"),
        "price": 39.0,
        "margin": 0.54,
        "return": 0.05,
    },
    "Sports": {
        "subcategories": ("Fitness", "Outdoor", "Team Sports"),
        "price": 82.0,
        "margin": 0.40,
        "return": 0.11,
    },
}


def _date_key(values: pd.Series | pd.DatetimeIndex) -> np.ndarray:
    dates = pd.DatetimeIndex(values)
    return dates.strftime("%Y%m%d").astype("int32")


def _sigmoid(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-values))


def _build_date_dimension(profile: ScenarioProfile) -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = pd.date_range(profile.start_date, profile.end_date, freq="D")
    frame = pd.DataFrame({"date": dates})
    frame["date_key"] = _date_key(dates)
    frame["year"] = frame["date"].dt.year.astype("int16")
    frame["quarter"] = "Q" + frame["date"].dt.quarter.astype(str)
    frame["month"] = frame["date"].dt.month.astype("int8")
    frame["month_name"] = frame["date"].dt.strftime("%b")
    frame["month_start"] = frame["date"].dt.to_period("M").dt.to_timestamp()
    frame["week_start"] = frame["date"] - pd.to_timedelta(frame["date"].dt.weekday, unit="D")
    frame["iso_week"] = frame["date"].dt.isocalendar().week.astype("int16")
    frame["day_name"] = frame["date"].dt.day_name()
    frame["is_weekend"] = frame["date"].dt.weekday.ge(5)
    frame["is_month_end"] = frame["date"].dt.is_month_end

    holiday_rows: list[dict[str, Any]] = []
    for year in sorted(frame["year"].unique()):
        common = [
            (f"{year}-01-01", "New Year's Day"),
            (f"{year}-05-01", "Labour Day"),
            (f"{year}-12-25", "Christmas Day"),
            (f"{year}-12-26", "Second Christmas Day"),
        ]
        market_specific = {
            "DE": [(f"{year}-10-03", "German Unity Day")],
            "AT": [(f"{year}-10-26", "Austrian National Day")],
            "FR": [(f"{year}-07-14", "Bastille Day")],
            "ES": [(f"{year}-10-12", "National Day of Spain")],
            "IT": [(f"{year}-06-02", "Republic Day")],
            "PL": [(f"{year}-11-11", "Independence Day")],
            "SE": [(f"{year}-06-06", "National Day of Sweden")],
            "GB": [(f"{year}-12-26", "Boxing Day")],
        }
        for market_key, market_code, *_ in MARKET_ROWS:
            for holiday_date, holiday_name in common + market_specific.get(market_code, []):
                timestamp = pd.Timestamp(holiday_date)
                if dates.min() <= timestamp <= dates.max():
                    holiday_rows.append(
                        {
                            "date_key": int(timestamp.strftime("%Y%m%d")),
                            "market_key": market_key,
                            "market_code": market_code,
                            "holiday_name": holiday_name,
                            "source_type": "documented scenario calendar",
                        }
                    )
    holidays = pd.DataFrame(holiday_rows)
    holiday_dates = set(holidays["date_key"].tolist()) if not holidays.empty else set()
    frame["is_european_holiday"] = frame["date_key"].isin(holiday_dates)
    return frame[
        [
            "date_key",
            "date",
            "year",
            "quarter",
            "month",
            "month_name",
            "month_start",
            "week_start",
            "iso_week",
            "day_name",
            "is_weekend",
            "is_month_end",
            "is_european_holiday",
        ]
    ], holidays


def _build_geography_dimension() -> pd.DataFrame:
    return pd.DataFrame(
        MARKET_ROWS,
        columns=[
            "market_key",
            "market_code",
            "market_name",
            "region_cluster",
            "currency_code",
            "vat_rate",
            "demand_weight",
            "fulfillment_hub",
        ],
    )


def _build_channel_dimension() -> pd.DataFrame:
    return pd.DataFrame(
        CHANNEL_ROWS,
        columns=["channel_key", "channel_name", "channel_group", "is_paid"],
    )


def _build_campaign_dimension(profile: ScenarioProfile) -> pd.DataFrame:
    rows: list[dict[str, Any]] = [
        {
            "campaign_key": 0,
            "campaign_name": "No paid campaign",
            "market_key": 0,
            "channel_key": 0,
            "campaign_type": "None",
            "is_promotion": False,
            "start_date": pd.Timestamp(profile.start_date),
            "end_date": pd.Timestamp(profile.end_date),
        }
    ]
    campaign_key = 1
    paid_channels = [row for row in CHANNEL_ROWS if row[3]]
    for market_key, market_code, *_ in MARKET_ROWS:
        for channel_key, channel_name, *_ in paid_channels:
            for campaign_type, is_promotion in (("Always-on", False), ("Promotion", True)):
                rows.append(
                    {
                        "campaign_key": campaign_key,
                        "campaign_name": f"{market_code} {channel_name} {campaign_type}",
                        "market_key": market_key,
                        "channel_key": channel_key,
                        "campaign_type": campaign_type,
                        "is_promotion": is_promotion,
                        "start_date": pd.Timestamp(profile.start_date),
                        "end_date": pd.Timestamp(profile.end_date),
                    }
                )
                campaign_key += 1
    return pd.DataFrame(rows)


def _build_customer_dimension(profile: ScenarioProfile, rng: np.random.Generator) -> pd.DataFrame:
    acquisition_dates = pd.date_range(profile.start_date, profile.end_date, freq="D")
    market_probabilities = np.array([row[6] for row in MARKET_ROWS], dtype=float)
    market_probabilities /= market_probabilities.sum()
    frame = pd.DataFrame(
        {
            "customer_key": np.arange(1, profile.customers + 1, dtype="int64"),
            "customer_id": [f"CUS-{value:07d}" for value in range(1, profile.customers + 1)],
            "acquisition_date": rng.choice(acquisition_dates, size=profile.customers),
            "home_market_key": rng.choice(
                np.arange(1, 11), size=profile.customers, p=market_probabilities
            ),
            "acquisition_channel_key": rng.choice(
                np.arange(1, 7), size=profile.customers, p=[0.24, 0.23, 0.13, 0.18, 0.15, 0.07]
            ),
            "customer_segment": rng.choice(
                ["Value", "Core", "Premium"],
                size=profile.customers,
                p=[0.42, 0.46, 0.12],
            ),
            "loyalty_tier": rng.choice(
                ["None", "Bronze", "Silver", "Gold"],
                size=profile.customers,
                p=[0.45, 0.31, 0.18, 0.06],
            ),
            "marketing_consent": rng.choice(
                [True, False], size=profile.customers, p=[0.72, 0.28]
            ),
        }
    )
    frame["acquisition_date_key"] = _date_key(frame["acquisition_date"])
    return frame


def _build_product_dimension(profile: ScenarioProfile, rng: np.random.Generator) -> pd.DataFrame:
    categories = np.array(list(CATEGORY_CONFIG))
    chosen_categories = rng.choice(
        categories, size=profile.products, p=[0.20, 0.22, 0.24, 0.16, 0.18]
    )
    rows: list[dict[str, Any]] = []
    for product_key, category in enumerate(chosen_categories, start=1):
        settings = CATEGORY_CONFIG[str(category)]
        list_price = max(8.0, rng.lognormal(np.log(settings["price"]), 0.34))
        gross_margin = float(np.clip(rng.normal(settings["margin"], 0.045), 0.20, 0.70))
        rows.append(
            {
                "product_key": product_key,
                "sku": f"SKU-{product_key:05d}",
                "product_name": f"{category} Product {product_key:04d}",
                "category": str(category),
                "subcategory": rng.choice(settings["subcategories"]),
                "brand": f"Brand {1 + product_key % 12:02d}",
                "list_price_eur": round(list_price, 2),
                "standard_cost_eur": round(list_price * (1.0 - gross_margin), 2),
                "base_return_probability": settings["return"],
                "supplier_lead_time_days": int(rng.integers(7, 36)),
                "weight_kg": round(float(rng.lognormal(-0.05, 0.75)), 3),
                "popularity_weight": float(1.0 / ((product_key + 8) ** 0.67)),
            }
        )
    frame = pd.DataFrame(rows)
    frame["popularity_weight"] /= frame["popularity_weight"].sum()
    return frame


def _build_marketing_spend(
    profile: ScenarioProfile,
    dim_date: pd.DataFrame,
    dim_geography: pd.DataFrame,
    dim_campaign: pd.DataFrame,
    fx_rates: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    active_campaigns = dim_campaign.query("campaign_key > 0").copy()
    grid = (
        dim_date[["date_key", "date", "month"]]
        .assign(_join=1)
        .merge(active_campaigns.assign(_join=1), on="_join")
        .drop(columns="_join")
    )
    grid = grid.merge(
        dim_geography[["market_key", "currency_code", "demand_weight"]],
        on="market_key",
        how="left",
    )
    grid = grid.merge(
        fx_rates[["rate_date_key", "currency_code", "local_per_eur"]],
        left_on=["date_key", "currency_code"],
        right_on=["rate_date_key", "currency_code"],
        how="left",
        validate="many_to_one",
    )
    channel_base = grid["channel_key"].map({2: 510.0, 3: 390.0, 6: 270.0}).to_numpy()
    promo_month = grid["month"].isin([4, 5, 6, 11, 12]).to_numpy()
    promo_multiplier = np.where(
        grid["is_promotion"].to_numpy(), np.where(promo_month, 1.20, 0.12), 1.0
    )
    stress = np.where(
        (grid["date"] >= pd.Timestamp("2026-04-01"))
        & grid["market_key"].isin([9, 10])
        & grid["channel_key"].eq(3),
        1.65,
        1.0,
    )
    seasonality = 1.0 + 0.18 * np.sin((grid["date"].dt.dayofyear.to_numpy() - 40) / 365 * 2 * np.pi)
    # Keep media economics comparable across the lightweight CI and portfolio
    # profiles. The unscaled campaign grid represents roughly 7,500 sessions
    # per day; lower-volume profiles receive proportionally lower spend.
    session_density_factor = profile.sessions / len(dim_date) / 7_500
    spend_eur = (
        channel_base
        * grid["demand_weight"].to_numpy()
        * 10
        * session_density_factor
        * promo_multiplier
        * stress
        * seasonality
        * rng.lognormal(0.0, 0.13, size=len(grid))
    )
    cpm = grid["channel_key"].map({2: 24.0, 3: 9.5, 6: 31.0}).to_numpy()
    ctr = grid["channel_key"].map({2: 0.035, 3: 0.012, 6: 0.026}).to_numpy()
    impressions = np.maximum(1, np.round(spend_eur / cpm * 1000)).astype("int64")
    clicks = rng.binomial(impressions, np.clip(ctr, 0.001, 0.20)).astype("int64")
    result = pd.DataFrame(
        {
            "spend_id": np.arange(1, len(grid) + 1, dtype="int64"),
            "date_key": grid["date_key"].astype("int32"),
            "spend_date": grid["date"],
            "market_key": grid["market_key"].astype("int16"),
            "channel_key": grid["channel_key"].astype("int8"),
            "campaign_key": grid["campaign_key"].astype("int16"),
            "currency_code": grid["currency_code"],
            "fx_local_per_eur": grid["local_per_eur"].astype(float),
            "impressions": impressions,
            "clicks": clicks,
            "spend_local": np.round(spend_eur * grid["local_per_eur"].to_numpy(), 2),
            "loaded_at": pd.Timestamp(profile.end_date) + pd.Timedelta(days=1),
        }
    )
    return result


def _build_sessions(
    profile: ScenarioProfile,
    dim_date: pd.DataFrame,
    dim_customer: pd.DataFrame,
    dim_campaign: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    dates = dim_date["date"].to_numpy()
    day_of_year = dim_date["date"].dt.dayofyear.to_numpy()
    date_weights = 1.0 + 0.17 * np.sin((day_of_year - 35) / 365 * 2 * np.pi)
    date_weights *= np.where(dim_date["is_weekend"].to_numpy(), 1.09, 1.0)
    date_weights *= np.where(dim_date["month"].isin([11, 12]).to_numpy(), 1.22, 1.0)
    date_weights /= date_weights.sum()
    chosen_dates = pd.DatetimeIndex(rng.choice(dates, size=profile.sessions, p=date_weights))
    market_probabilities = np.array([row[6] for row in MARKET_ROWS], dtype=float)
    market_probabilities /= market_probabilities.sum()
    market_keys = rng.choice(np.arange(1, 11), size=profile.sessions, p=market_probabilities)
    channel_keys = rng.choice(
        np.arange(1, 7),
        size=profile.sessions,
        p=[0.23, 0.24, 0.13, 0.17, 0.15, 0.08],
    )
    customer_keys = rng.integers(1, profile.customers + 1, size=profile.sessions)
    devices = rng.choice(
        np.array(["Mobile", "Desktop", "Tablet"]),
        size=profile.sessions,
        p=[0.56, 0.38, 0.06],
    )
    promo_flags = np.isin(chosen_dates.month, [4, 5, 6, 11, 12]) & (
        rng.random(profile.sessions) < 0.40
    )
    campaign_lookup = np.zeros((11, 7, 2), dtype="int16")
    for row in dim_campaign.query("campaign_key > 0").itertuples(index=False):
        campaign_lookup[int(row.market_key), int(row.channel_key), int(bool(row.is_promotion))] = int(
            row.campaign_key
        )
    is_paid = np.isin(channel_keys, [2, 3, 6])
    campaign_keys = np.zeros(profile.sessions, dtype="int16")
    campaign_keys[is_paid] = campaign_lookup[
        market_keys[is_paid], channel_keys[is_paid], promo_flags[is_paid].astype(int)
    ]

    load_ms = rng.lognormal(np.log(1150), 0.34, size=profile.sessions)
    load_ms *= np.where(devices == "Mobile", 1.22, 0.88)
    performance_stress = (
        (chosen_dates >= pd.Timestamp("2026-04-01"))
        & np.isin(market_keys, [9, 10])
        & (devices == "Mobile")
    )
    load_ms += np.where(performance_stress, 650.0, 0.0)
    load_ms = np.round(load_ms).astype("int32")
    product_views = np.clip(rng.poisson(2.9, size=profile.sessions) + 1, 1, 20).astype("int16")
    channel_add_effect = np.take(
        np.array([0.0, 0.02, 0.06, -0.01, 0.04, 0.01, 0.05]), channel_keys
    )
    add_probability = np.clip(
        0.07 + 0.055 * product_views + channel_add_effect - 0.000045 * np.maximum(load_ms - 1000, 0),
        0.04,
        0.72,
    )
    added_to_cart = rng.random(profile.sessions) < add_probability
    checkout_started = added_to_cart & (rng.random(profile.sessions) < 0.66)
    loyalty_lookup = (
        dim_customer.set_index("customer_key")["loyalty_tier"]
        .map({"None": 0.0, "Bronze": 0.12, "Silver": 0.25, "Gold": 0.42})
        .reindex(np.arange(1, profile.customers + 1))
        .to_numpy()
    )
    loyalty_effect = loyalty_lookup[customer_keys - 1]
    channel_conversion_effect = np.take(
        np.array([0.0, 0.15, 0.08, -0.10, 0.30, 0.22, 0.02]), channel_keys
    )
    conversion_score = (
        0.92
        + loyalty_effect
        + channel_conversion_effect
        + 0.32 * promo_flags.astype(float)
        - 0.00035 * np.maximum(load_ms - 1100, 0)
        - 0.18 * (devices == "Mobile")
    )
    conversion_probability = _sigmoid(conversion_score)
    converted = checkout_started & (rng.random(profile.sessions) < conversion_probability)
    session_seconds = rng.integers(0, 24 * 60 * 60, size=profile.sessions)
    session_ts = chosen_dates + pd.to_timedelta(session_seconds, unit="s")
    base_load_lag_minutes = rng.integers(5, 3 * 24 * 60, size=profile.sessions)
    late_arrival = rng.random(profile.sessions) < 0.007
    load_lag_minutes = base_load_lag_minutes + np.where(late_arrival, 20 * 24 * 60, 0)
    loaded_at = session_ts + pd.to_timedelta(load_lag_minutes, unit="m")

    order_ids = np.full(profile.sessions, np.nan)
    order_ids[converted] = np.arange(1, int(converted.sum()) + 1)
    return pd.DataFrame(
        {
            "session_id": np.arange(1, profile.sessions + 1, dtype="int64"),
            "session_ts": session_ts,
            "date_key": _date_key(chosen_dates),
            "customer_key": customer_keys.astype("int64"),
            "market_key": market_keys.astype("int16"),
            "channel_key": channel_keys.astype("int8"),
            "campaign_key": campaign_keys,
            "device_type": devices,
            "page_load_ms": load_ms,
            "product_views": product_views,
            "added_to_cart": added_to_cart,
            "checkout_started": checkout_started,
            "converted_order_id": pd.array(order_ids, dtype="Int64"),
            "loaded_at": loaded_at,
            "is_late_arrival": late_arrival,
        }
    )


def _build_orders_and_items(
    profile: ScenarioProfile,
    fact_sessions: pd.DataFrame,
    dim_geography: pd.DataFrame,
    dim_product: pd.DataFrame,
    fx_rates: pd.DataFrame,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    converted = fact_sessions.loc[fact_sessions["converted_order_id"].notna()].copy()
    converted["order_id"] = converted["converted_order_id"].astype("int64")
    order_count = len(converted)
    order_item_counts = rng.choice([1, 2, 3, 4], size=order_count, p=[0.58, 0.28, 0.10, 0.04])
    item_order_ids = np.repeat(converted["order_id"].to_numpy(), order_item_counts)
    item_count = len(item_order_ids)
    product_keys = rng.choice(
        dim_product["product_key"].to_numpy(),
        size=item_count,
        p=dim_product["popularity_weight"].to_numpy(),
    )
    order_lookup = converted.set_index("order_id")
    item_market = order_lookup.loc[item_order_ids, "market_key"].to_numpy()
    item_channel = order_lookup.loc[item_order_ids, "channel_key"].to_numpy()
    item_campaign = order_lookup.loc[item_order_ids, "campaign_key"].to_numpy()
    item_order_date = pd.DatetimeIndex(order_lookup.loc[item_order_ids, "session_ts"].dt.normalize())
    currency_lookup = dim_geography.set_index("market_key")["currency_code"]
    item_currency = currency_lookup.loc[item_market].to_numpy()
    fx_lookup = fx_rates.set_index(["rate_date_key", "currency_code"])["local_per_eur"]
    item_date_keys = _date_key(item_order_date)
    item_fx = fx_lookup.reindex(pd.MultiIndex.from_arrays([item_date_keys, item_currency])).to_numpy()
    product_lookup = dim_product.set_index("product_key")
    list_price = product_lookup.loc[product_keys, "list_price_eur"].to_numpy()
    standard_cost = product_lookup.loc[product_keys, "standard_cost_eur"].to_numpy()
    categories = product_lookup.loc[product_keys, "category"].to_numpy()
    quantities = rng.choice([1, 2, 3], size=item_count, p=[0.88, 0.10, 0.02]).astype("int16")
    unit_price_eur = np.maximum(4.0, list_price * rng.normal(1.0, 0.035, size=item_count))
    promotion = item_campaign > 0
    base_discount_rate = rng.beta(1.4, 12.0, size=item_count) * 0.22
    promo_discount = np.where(promotion, 0.035, 0.0)
    margin_stress = (
        (item_order_date >= pd.Timestamp("2026-04-01"))
        & (categories == "Apparel")
        & (item_channel == 3)
        & np.isin(item_market, [9, 10])
    )
    discount_rate = np.clip(base_discount_rate + promo_discount + 0.13 * margin_stress, 0, 0.38)
    gross_local = unit_price_eur * quantities * item_fx
    discount_local = gross_local * discount_rate
    cogs_local = standard_cost * quantities * item_fx
    items = pd.DataFrame(
        {
            "order_item_id": np.arange(1, item_count + 1, dtype="int64"),
            "order_id": item_order_ids.astype("int64"),
            "product_key": product_keys.astype("int32"),
            "quantity": quantities,
            "currency_code": item_currency,
            "fx_local_per_eur": item_fx.astype(float),
            "unit_price_local": np.round(unit_price_eur * item_fx, 2),
            "gross_revenue_local": np.round(gross_local, 2),
            "discount_local": np.round(discount_local, 2),
            "cogs_local": np.round(cogs_local, 2),
            "loaded_at": item_order_date + pd.to_timedelta(rng.integers(1, 4, size=item_count), unit="D"),
        }
    )
    item_totals = items.groupby("order_id", as_index=False).agg(
        gross_revenue_local=("gross_revenue_local", "sum"),
        discount_local=("discount_local", "sum"),
        item_quantity=("quantity", "sum"),
    )
    order_dates = pd.DatetimeIndex(converted["session_ts"].dt.normalize())
    order_currency = currency_lookup.loc[converted["market_key"]].to_numpy()
    order_date_keys = _date_key(order_dates)
    order_fx = fx_lookup.reindex(pd.MultiIndex.from_arrays([order_date_keys, order_currency])).to_numpy()
    order_status = rng.choice(["Completed", "Cancelled"], size=order_count, p=[0.982, 0.018])
    orders = converted[
        [
            "order_id",
            "session_id",
            "customer_key",
            "market_key",
            "channel_key",
            "campaign_key",
        ]
    ].copy()
    orders["order_ts"] = converted["session_ts"].to_numpy() + pd.to_timedelta(
        rng.integers(4, 121, size=order_count), unit="m"
    )
    profile_end_ts = pd.Timestamp(profile.end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    orders["order_ts"] = orders["order_ts"].clip(upper=profile_end_ts)
    orders["date_key"] = order_date_keys
    orders["currency_code"] = order_currency
    orders["fx_local_per_eur"] = order_fx
    orders = orders.merge(item_totals, on="order_id", how="left", validate="one_to_one")
    orders["net_revenue_local"] = orders["gross_revenue_local"] - orders["discount_local"]
    orders["shipping_revenue_local"] = np.where(
        orders["net_revenue_local"] >= 75 * orders["fx_local_per_eur"],
        0.0,
        4.9 * orders["fx_local_per_eur"],
    )
    vat_lookup = dim_geography.set_index("market_key")["vat_rate"]
    orders["tax_local"] = (
        orders["net_revenue_local"]
        * vat_lookup.loc[orders["market_key"]].to_numpy()
        / (1 + vat_lookup.loc[orders["market_key"]].to_numpy())
    )
    orders["order_status"] = order_status
    orders["loaded_at"] = orders["order_ts"] + pd.to_timedelta(
        rng.integers(1, 3 * 24 * 60, size=order_count), unit="m"
    )
    late_orders = rng.random(order_count) < 0.006
    orders.loc[late_orders, "loaded_at"] += pd.Timedelta(days=20)
    orders["is_late_arrival"] = late_orders
    monetary = [
        "gross_revenue_local",
        "discount_local",
        "net_revenue_local",
        "shipping_revenue_local",
        "tax_local",
    ]
    orders[monetary] = orders[monetary].round(2)
    return orders, items


def _build_fulfillment(
    profile: ScenarioProfile,
    orders: pd.DataFrame,
    dim_geography: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    eligible = orders.query("order_status == 'Completed'").copy()
    order_dates = pd.DatetimeIndex(eligible["order_ts"].dt.normalize())
    hubs = dim_geography.set_index("market_key").loc[eligible["market_key"], "fulfillment_hub"].to_numpy()
    ship_days = rng.choice([0, 1, 2, 3], size=len(eligible), p=[0.05, 0.48, 0.38, 0.09])
    promised_days = rng.choice([3, 4, 5, 6], size=len(eligible), p=[0.13, 0.44, 0.34, 0.09])
    transit_days = rng.choice([1, 2, 3, 4, 5], size=len(eligible), p=[0.06, 0.31, 0.39, 0.19, 0.05])
    north_stress = (order_dates >= pd.Timestamp("2026-04-01")) & (hubs == "North")
    transit_days = transit_days + np.where(north_stress, rng.choice([1, 2, 3], size=len(eligible)), 0)
    shipped = order_dates + pd.to_timedelta(ship_days, unit="D")
    delivered = shipped + pd.to_timedelta(transit_days, unit="D")
    promised = order_dates + pd.to_timedelta(promised_days, unit="D")
    carrier = np.select(
        [hubs == "Central", hubs == "West", hubs == "South", hubs == "North"],
        ["DHL", "DPD", "GLS", "PostNord / Royal Mail"],
        default="DHL",
    )
    shipping_cost_eur = (
        4.2
        + 0.85 * eligible["item_quantity"].to_numpy()
        + np.where(hubs == "North", 1.2, 0.0)
        + np.where(delivered > promised, 1.8, 0.0)
    )
    result = pd.DataFrame(
        {
            "fulfillment_id": np.arange(1, len(eligible) + 1, dtype="int64"),
            "order_id": eligible["order_id"].to_numpy(),
            "market_key": eligible["market_key"].to_numpy(),
            "fulfillment_hub": hubs,
            "carrier": carrier,
            "promised_delivery_date": promised,
            "shipped_date": shipped,
            "delivered_date": delivered,
            "is_on_time": delivered <= promised,
            "currency_code": eligible["currency_code"].to_numpy(),
            "fx_local_per_eur": eligible["fx_local_per_eur"].to_numpy(),
            "shipping_cost_local": np.round(
                shipping_cost_eur * eligible["fx_local_per_eur"].to_numpy(), 2
            ),
            "loaded_at": delivered + pd.to_timedelta(rng.integers(1, 72, size=len(eligible)), unit="h"),
        }
    )
    return result


def _build_returns(
    order_items: pd.DataFrame,
    orders: pd.DataFrame,
    fulfillment: pd.DataFrame,
    dim_product: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    eligible_orders = orders.query("order_status == 'Completed'")[
        ["order_id", "order_ts", "market_key", "channel_key"]
    ]
    candidates = order_items.merge(eligible_orders, on="order_id", how="inner", validate="many_to_one")
    candidates = candidates.merge(
        fulfillment[["order_id", "delivered_date", "is_on_time"]],
        on="order_id",
        how="inner",
        validate="many_to_one",
    )
    candidates = candidates.merge(
        dim_product[["product_key", "category", "base_return_probability"]],
        on="product_key",
        how="left",
        validate="many_to_one",
    )
    late_effect = np.where(candidates["is_on_time"].to_numpy(), 0.0, 0.075)
    discount_rate = candidates["discount_local"] / candidates["gross_revenue_local"].replace(0, np.nan)
    discount_effect = np.nan_to_num(discount_rate.to_numpy()) * 0.24
    probability = np.clip(
        candidates["base_return_probability"].to_numpy() + late_effect + discount_effect,
        0.01,
        0.48,
    )
    returned = rng.random(len(candidates)) < probability
    selected = candidates.loc[returned].copy()
    if selected.empty:
        return pd.DataFrame(
            columns=[
                "return_id",
                "order_id",
                "order_item_id",
                "return_date",
                "return_reason",
                "units_returned",
                "refund_local",
                "handling_cost_local",
                "recovered_cogs_local",
                "restockable",
                "currency_code",
                "fx_local_per_eur",
                "loaded_at",
            ]
        )
    units_returned = np.array(
        [int(rng.integers(1, int(quantity) + 1)) for quantity in selected["quantity"]],
        dtype="int16",
    )
    return_days = rng.integers(3, 31, size=len(selected))
    return_date = pd.DatetimeIndex(selected["delivered_date"]) + pd.to_timedelta(return_days, unit="D")
    return_reason = rng.choice(
        ["Size / fit", "Damaged", "Not as expected", "Late delivery", "Changed mind"],
        size=len(selected),
        p=[0.28, 0.12, 0.28, 0.12, 0.20],
    )
    return_reason = np.where(~selected["is_on_time"].to_numpy(), "Late delivery", return_reason)
    restockable = (~np.isin(return_reason, ["Damaged"])) & (rng.random(len(selected)) < 0.86)
    net_unit_local = (
        (selected["gross_revenue_local"] - selected["discount_local"])
        / selected["quantity"]
    ).to_numpy()
    cogs_unit_local = (selected["cogs_local"] / selected["quantity"]).to_numpy()
    fx_values = selected["fx_local_per_eur"].to_numpy()
    return pd.DataFrame(
        {
            "return_id": np.arange(1, len(selected) + 1, dtype="int64"),
            "order_id": selected["order_id"].to_numpy(),
            "order_item_id": selected["order_item_id"].to_numpy(),
            "return_date": return_date,
            "return_reason": return_reason,
            "units_returned": units_returned,
            "refund_local": np.round(net_unit_local * units_returned, 2),
            "handling_cost_local": np.round((4.0 + np.where(restockable, 0.8, 5.0)) * fx_values, 2),
            "recovered_cogs_local": np.round(
                cogs_unit_local * units_returned * np.where(restockable, 0.72, 0.0), 2
            ),
            "restockable": restockable,
            "currency_code": selected["currency_code"].to_numpy(),
            "fx_local_per_eur": fx_values,
            "loaded_at": return_date + pd.to_timedelta(rng.integers(1, 96, size=len(selected)), unit="h"),
        }
    )


def _build_inventory(
    profile: ScenarioProfile,
    dim_geography: pd.DataFrame,
    dim_product: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    snapshots = pd.date_range(profile.start_date, profile.end_date, freq=profile.inventory_frequency)
    grid = pd.MultiIndex.from_product(
        [snapshots, dim_geography["market_key"], dim_product["product_key"]],
        names=["snapshot_date", "market_key", "product_key"],
    ).to_frame(index=False)
    grid = grid.merge(
        dim_product[
            ["product_key", "category", "popularity_weight", "supplier_lead_time_days"]
        ],
        on="product_key",
        how="left",
        validate="many_to_one",
    )
    market_weight = dim_geography.set_index("market_key")["demand_weight"]
    demand_signal = (
        grid["popularity_weight"].to_numpy()
        * market_weight.loc[grid["market_key"]].to_numpy()
        * profile.products
        * 35
    )
    stockout_probability = np.clip(
        0.025
        + 0.0022 * (grid["supplier_lead_time_days"].to_numpy() - 7)
        + 0.05 * (grid["category"].to_numpy() == "Electronics"),
        0.01,
        0.30,
    )
    replenishment_stress = (
        (grid["snapshot_date"] >= pd.Timestamp("2026-04-01"))
        & grid["market_key"].eq(1)
        & grid["category"].eq("Electronics")
    )
    stockout_probability = np.clip(stockout_probability + 0.22 * replenishment_stress, 0, 0.65)
    stockout = rng.random(len(grid)) < stockout_probability
    on_hand = rng.poisson(np.maximum(2.0, demand_signal * 6.5)).astype("int32")
    on_hand[stockout] = 0
    in_transit = rng.poisson(np.maximum(1.0, demand_signal * 2.2)).astype("int32")
    lost_units = np.where(stockout, rng.poisson(np.maximum(1.0, demand_signal * 0.8)), 0).astype(
        "int32"
    )
    return pd.DataFrame(
        {
            "inventory_snapshot_id": np.arange(1, len(grid) + 1, dtype="int64"),
            "snapshot_date": grid["snapshot_date"],
            "date_key": _date_key(grid["snapshot_date"]),
            "market_key": grid["market_key"].astype("int16"),
            "product_key": grid["product_key"].astype("int32"),
            "on_hand_units": on_hand,
            "in_transit_units": in_transit,
            "reorder_point_units": np.ceil(demand_signal * 3.1).astype("int32"),
            "stockout_flag": stockout,
            "estimated_lost_units": lost_units,
            "loaded_at": grid["snapshot_date"] + pd.Timedelta(days=1),
        }
    )


def _build_targets(
    profile: ScenarioProfile,
    dim_geography: pd.DataFrame,
    dim_channel: pd.DataFrame,
) -> pd.DataFrame:
    months = pd.date_range(profile.start_date, profile.end_date, freq="MS")
    grid = pd.MultiIndex.from_product(
        [months, dim_geography["market_key"], dim_channel["channel_key"]],
        names=["month_start", "market_key", "channel_key"],
    ).to_frame(index=False)
    market_weight = dim_geography.set_index("market_key")["demand_weight"]
    channel_weights = {1: 0.21, 2: 0.25, 3: 0.14, 4: 0.17, 5: 0.15, 6: 0.08}
    monthly_sessions = profile.sessions / len(months)
    base_revenue = monthly_sessions * 0.125 * 1.65 * 73.0
    growth_index = 1.0 + 0.012 * np.arange(len(months))
    month_growth = pd.Series(growth_index, index=months)
    target_revenue = (
        base_revenue
        * market_weight.loc[grid["market_key"]].to_numpy()
        * grid["channel_key"].map(channel_weights).to_numpy()
        * month_growth.loc[grid["month_start"]].to_numpy()
        * 1.06
    )
    return pd.DataFrame(
        {
            "target_id": np.arange(1, len(grid) + 1, dtype="int64"),
            "month_start": grid["month_start"],
            "month_key": grid["month_start"].dt.strftime("%Y%m").astype("int32"),
            "market_key": grid["market_key"].astype("int16"),
            "channel_key": grid["channel_key"].astype("int8"),
            "net_revenue_target_eur": np.round(target_revenue, 2),
            "contribution_margin_target_eur": np.round(target_revenue * 0.285, 2),
            "orders_target": np.round(target_revenue / 88.0).astype("int32"),
            "conversion_rate_target": 0.132,
            "on_time_delivery_target": 0.94,
            "return_rate_guardrail": 0.115,
            "target_method": "independent operating plan using market and channel capacity",
        }
    )


def _inject_defects(
    tables: dict[str, pd.DataFrame],
    profile: ScenarioProfile,
    rng: np.random.Generator,
) -> tuple[dict[str, pd.DataFrame], list[dict[str, Any]]]:
    raw = {name: frame.copy() for name, frame in tables.items()}
    manifest: list[dict[str, Any]] = []

    sessions = raw["fact_sessions"]
    duplicate_count = max(1, int(len(sessions) * 0.0006))
    duplicate_rows = sessions.sample(duplicate_count, random_state=profile.seed).copy()
    duplicate_rows["loaded_at"] += pd.Timedelta(hours=2)
    raw["fact_sessions"] = pd.concat([sessions, duplicate_rows], ignore_index=True)
    manifest.append(
        {"rule": "duplicate_session_id", "table": "fact_sessions", "injected_rows": duplicate_count}
    )
    missing_market_count = max(1, int(len(sessions) * 0.0004))
    missing_indices = rng.choice(len(raw["fact_sessions"]), size=missing_market_count, replace=False)
    raw["fact_sessions"].loc[missing_indices, "market_key"] = np.nan
    manifest.append(
        {"rule": "missing_session_market", "table": "fact_sessions", "injected_rows": missing_market_count}
    )

    items = raw["fact_order_items"]
    invalid_item_total = max(2, int(len(items) * 0.0007))
    invalid_indices = rng.choice(len(items), size=invalid_item_total, replace=False)
    split = invalid_item_total // 2
    items.loc[invalid_indices[:split], "product_key"] = int(tables["dim_product"]["product_key"].max()) + 999
    items.loc[invalid_indices[split:], "quantity"] = 0
    manifest.extend(
        [
            {
                "rule": "invalid_order_item_product",
                "table": "fact_order_items",
                "injected_rows": split,
            },
            {
                "rule": "nonpositive_order_item_quantity",
                "table": "fact_order_items",
                "injected_rows": invalid_item_total - split,
            },
        ]
    )

    spend = raw["fact_marketing_spend"]
    negative_spend_count = max(1, int(len(spend) * 0.001))
    spend_indices = rng.choice(len(spend), size=negative_spend_count, replace=False)
    spend.loc[spend_indices, "spend_local"] *= -1
    manifest.append(
        {
            "rule": "negative_marketing_spend",
            "table": "fact_marketing_spend",
            "injected_rows": negative_spend_count,
        }
    )

    fulfillment = raw["fact_fulfillment"]
    invalid_fulfillment_count = max(1, int(len(fulfillment) * 0.0008))
    fulfillment_indices = rng.choice(len(fulfillment), size=invalid_fulfillment_count, replace=False)
    fulfillment.loc[fulfillment_indices, "delivered_date"] = (
        fulfillment.loc[fulfillment_indices, "shipped_date"] - pd.Timedelta(days=1)
    )
    manifest.append(
        {
            "rule": "invalid_fulfillment_sequence",
            "table": "fact_fulfillment",
            "injected_rows": invalid_fulfillment_count,
        }
    )

    returns = raw["fact_returns"]
    if not returns.empty:
        orphan_return_count = max(1, int(len(returns) * 0.001))
        return_indices = rng.choice(len(returns), size=orphan_return_count, replace=False)
        returns.loc[return_indices, "order_item_id"] = int(items["order_item_id"].max()) + 999
        manifest.append(
            {
                "rule": "orphan_return_item",
                "table": "fact_returns",
                "injected_rows": orphan_return_count,
            }
        )

    inventory = raw["fact_inventory_snapshot"]
    negative_inventory_count = max(1, int(len(inventory) * 0.0008))
    inventory_indices = rng.choice(len(inventory), size=negative_inventory_count, replace=False)
    inventory.loc[inventory_indices, "on_hand_units"] = (
        -rng.integers(1, 8, size=negative_inventory_count)
    ).astype("int32")
    manifest.append(
        {
            "rule": "negative_inventory_on_hand",
            "table": "fact_inventory_snapshot",
            "injected_rows": negative_inventory_count,
        }
    )
    manifest.append(
        {
            "rule": "late_arrival_over_14_days",
            "table": "fact_sessions",
            "injected_rows": int(tables["fact_sessions"]["is_late_arrival"].sum()),
        }
    )
    return raw, manifest


def generate_scenario(profile: ScenarioProfile, output_root: Path) -> dict[str, Any]:
    ensure_directories(output_root)
    raw_folder = output_root / "raw"
    rng = np.random.default_rng(profile.seed)
    dim_date, bridge_market_holiday = _build_date_dimension(profile)
    dim_geography = _build_geography_dimension()
    dim_channel = _build_channel_dimension()
    dim_campaign = _build_campaign_dimension(profile)
    dim_customer = _build_customer_dimension(profile, rng)
    dim_product = _build_product_dimension(profile, rng)
    fx_rates = load_ecb_rates(
        PROJECT_ROOT / "data" / "reference" / "ecb" / "eurofxref-hist.csv",
        profile.start_date,
        profile.end_date,
        currencies=tuple(sorted(set(profile.currencies.values()))),
    )
    fact_marketing_spend = _build_marketing_spend(
        profile, dim_date, dim_geography, dim_campaign, fx_rates, rng
    )
    fact_sessions = _build_sessions(profile, dim_date, dim_customer, dim_campaign, rng)
    fact_orders, fact_order_items = _build_orders_and_items(
        profile, fact_sessions, dim_geography, dim_product, fx_rates, rng
    )
    fact_fulfillment = _build_fulfillment(profile, fact_orders, dim_geography, rng)
    fact_returns = _build_returns(
        fact_order_items, fact_orders, fact_fulfillment, dim_product, rng
    )
    fact_inventory_snapshot = _build_inventory(profile, dim_geography, dim_product, rng)
    fact_targets = _build_targets(profile, dim_geography, dim_channel)

    tables = {
        "dim_date": dim_date,
        "dim_geography": dim_geography,
        "dim_channel": dim_channel,
        "dim_campaign": dim_campaign,
        "dim_customer": dim_customer,
        "dim_product": dim_product,
        "bridge_market_holiday": bridge_market_holiday,
        "ref_fx_rates": fx_rates,
        "fact_sessions": fact_sessions,
        "fact_orders": fact_orders,
        "fact_order_items": fact_order_items,
        "fact_marketing_spend": fact_marketing_spend,
        "fact_fulfillment": fact_fulfillment,
        "fact_returns": fact_returns,
        "fact_inventory_snapshot": fact_inventory_snapshot,
        "fact_targets": fact_targets,
    }
    raw_tables, defect_manifest = _inject_defects(tables, profile, rng)
    for table_name, frame in raw_tables.items():
        write_table(frame, raw_folder, table_name)

    file_manifest = build_file_manifest(raw_folder)
    total_rows = sum(row["rows"] for row in file_manifest)
    manifest = {
        "project": "CommercePulse Europe",
        "profile": asdict(profile),
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "data_classification": "deterministic synthetic operational data plus real ECB reference rates",
        "scenario_disclosure": (
            "All customers, sessions, orders, products, marketing, fulfillment, returns, inventory, "
            "targets, and findings are synthetic. ECB exchange-rate observations are real reference data."
        ),
        "seed": profile.seed,
        "total_rows": total_rows,
        "files": file_manifest,
        "injected_defects": defect_manifest,
        "external_sources": [
            {
                "name": "European Central Bank euro foreign exchange reference rates",
                "url": ECB_SOURCE_URL,
                "cached_file": "data/reference/ecb/eurofxref-hist.csv",
                "usage": "local-currency-to-EUR conversion; rates are local currency units per EUR",
            }
        ],
        "known_process_shifts": [
            "Mobile page latency rises in Sweden and the United Kingdom from 2026-04-01.",
            "North-hub transit time rises from 2026-04-01.",
            "Apparel paid-social promotions in Sweden and the United Kingdom use deeper discounts from 2026-04-01.",
            "German electronics replenishment pressure rises from 2026-04-01.",
        ],
    }
    write_json(manifest, output_root / "generation_manifest.json")
    return manifest
