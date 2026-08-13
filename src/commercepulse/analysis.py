from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import norm

from commercepulse.io import read_table, write_json

BLUE = "#2563EB"
GOLD = "#D99A16"
ORANGE = "#EA7A1F"
OLIVE = "#6E7F2B"
PINK = "#C84B83"
INK = "#172033"
GRID = "#D9DEE8"


def _wilson_interval(successes: int, total: int, confidence: float = 0.95) -> tuple[float, float]:
    if total <= 0:
        return np.nan, np.nan
    z = norm.ppf(1 - (1 - confidence) / 2)
    observed = successes / total
    denominator = 1 + z**2 / total
    center = (observed + z**2 / (2 * total)) / denominator
    margin = (
        z
        * np.sqrt(observed * (1 - observed) / total + z**2 / (4 * total**2))
        / denominator
    )
    return float(center - margin), float(center + margin)


def _latest_two_complete_quarters(max_date: pd.Timestamp) -> tuple[pd.Period, pd.Period]:
    current_quarter = max_date.to_period("Q")
    if max_date < current_quarter.end_time.normalize():
        current_quarter -= 1
    return current_quarter - 1, current_quarter


def _build_finance_detail(clean_folder: Path) -> tuple[pd.DataFrame, dict[str, float]]:
    orders = read_table(clean_folder, "fact_orders")
    items = read_table(clean_folder, "fact_order_items")
    returns = read_table(clean_folder, "fact_returns")
    fulfillment = read_table(clean_folder, "fact_fulfillment")
    spend = read_table(clean_folder, "fact_marketing_spend")
    products = read_table(clean_folder, "dim_product")
    geography = read_table(clean_folder, "dim_geography")
    channels = read_table(clean_folder, "dim_channel")

    completed = orders.query("order_status == 'Completed'").copy()
    completed["order_date"] = completed["order_ts"].dt.normalize()
    completed["month_start"] = completed["order_date"].dt.to_period("M").dt.to_timestamp()
    completed["quarter"] = completed["order_date"].dt.to_period("Q").astype(str)
    detail = items.merge(
        completed[
            [
                "order_id",
                "order_date",
                "month_start",
                "quarter",
                "customer_key",
                "market_key",
                "channel_key",
                "campaign_key",
            ]
        ],
        on="order_id",
        how="inner",
        validate="many_to_one",
    )
    detail = detail.merge(
        products[["product_key", "category", "subcategory", "brand"]],
        on="product_key",
        how="left",
        validate="many_to_one",
    )
    detail = detail.merge(
        geography[["market_key", "market_code", "market_name", "region_cluster"]],
        on="market_key",
        how="left",
        validate="many_to_one",
    )
    detail = detail.merge(
        channels[["channel_key", "channel_name", "channel_group"]],
        on="channel_key",
        how="left",
        validate="many_to_one",
    )
    if returns.empty:
        return_summary = pd.DataFrame(
            columns=[
                "order_item_id",
                "units_returned",
                "refund_local",
                "handling_cost_local",
                "recovered_cogs_local",
            ]
        )
    else:
        return_summary = returns.groupby("order_item_id", as_index=False).agg(
            units_returned=("units_returned", "sum"),
            refund_local=("refund_local", "sum"),
            handling_cost_local=("handling_cost_local", "sum"),
            recovered_cogs_local=("recovered_cogs_local", "sum"),
        )
    detail = detail.merge(return_summary, on="order_item_id", how="left", validate="one_to_one")
    for column in (
        "units_returned",
        "refund_local",
        "handling_cost_local",
        "recovered_cogs_local",
    ):
        detail[column] = detail[column].fillna(0)
    detail["gross_revenue_eur"] = detail["gross_revenue_local"] / detail["fx_local_per_eur"]
    detail["discount_eur"] = detail["discount_local"] / detail["fx_local_per_eur"]
    detail["refund_eur"] = detail["refund_local"] / detail["fx_local_per_eur"]
    detail["cogs_eur"] = detail["cogs_local"] / detail["fx_local_per_eur"]
    detail["handling_cost_eur"] = detail["handling_cost_local"] / detail["fx_local_per_eur"]
    detail["recovered_cogs_eur"] = detail["recovered_cogs_local"] / detail["fx_local_per_eur"]
    detail["net_revenue_eur"] = (
        detail["gross_revenue_eur"] - detail["discount_eur"] - detail["refund_eur"]
    )

    shipment = fulfillment[["order_id", "shipping_cost_local", "fx_local_per_eur"]].copy()
    shipment["shipping_cost_eur"] = shipment["shipping_cost_local"] / shipment["fx_local_per_eur"]
    item_count = detail.groupby("order_id")["order_item_id"].transform("count")
    detail = detail.merge(
        shipment[["order_id", "shipping_cost_eur"]], on="order_id", how="left", validate="many_to_one"
    )
    detail["shipping_cost_eur"] = detail["shipping_cost_eur"].fillna(0) / item_count
    detail["contribution_before_marketing_eur"] = (
        detail["net_revenue_eur"]
        - detail["cogs_eur"]
        + detail["recovered_cogs_eur"]
        - detail["handling_cost_eur"]
        - detail["shipping_cost_eur"]
    )

    spend["spend_date"] = spend["spend_date"].dt.normalize()
    spend["month_start"] = spend["spend_date"].dt.to_period("M").dt.to_timestamp()
    spend["spend_eur"] = spend["spend_local"] / spend["fx_local_per_eur"]
    allocation_keys = ["month_start", "market_key", "channel_key"]
    market_month_keys = ["month_start", "market_key"]
    spend_period = spend.groupby(allocation_keys, as_index=False)["spend_eur"].sum()
    cell_revenue = detail.groupby(allocation_keys, as_index=False).agg(
        cell_net_revenue_eur=("net_revenue_eur", "sum")
    )
    spend_cells = spend_period.merge(cell_revenue, on=allocation_keys, how="left")
    spend_cells["cell_net_revenue_eur"] = spend_cells["cell_net_revenue_eur"].fillna(0)
    spend_cells["direct_spend_eur"] = np.where(
        spend_cells["cell_net_revenue_eur"] > 0,
        spend_cells["spend_eur"],
        0.0,
    )
    spend_cells["residual_spend_eur"] = (
        spend_cells["spend_eur"] - spend_cells["direct_spend_eur"]
    )
    residual_by_market_month = spend_cells.groupby(market_month_keys, as_index=False).agg(
        residual_spend_eur=("residual_spend_eur", "sum")
    )
    market_month_revenue = detail.groupby(market_month_keys, as_index=False).agg(
        market_month_net_revenue_eur=("net_revenue_eur", "sum")
    )
    detail = detail.merge(
        spend_cells[allocation_keys + ["direct_spend_eur", "cell_net_revenue_eur"]],
        on=allocation_keys,
        how="left",
        validate="many_to_one",
    )
    detail = detail.merge(
        residual_by_market_month,
        on=market_month_keys,
        how="left",
        validate="many_to_one",
    ).merge(
        market_month_revenue,
        on=market_month_keys,
        how="left",
        validate="many_to_one",
    )
    detail[["direct_spend_eur", "residual_spend_eur"]] = detail[
        ["direct_spend_eur", "residual_spend_eur"]
    ].fillna(0)
    detail["direct_marketing_allocation_eur"] = np.where(
        detail["cell_net_revenue_eur"] > 0,
        detail["direct_spend_eur"]
        * detail["net_revenue_eur"]
        / detail["cell_net_revenue_eur"],
        0.0,
    )
    detail["residual_marketing_allocation_eur"] = np.where(
        detail["market_month_net_revenue_eur"] > 0,
        detail["residual_spend_eur"]
        * detail["net_revenue_eur"]
        / detail["market_month_net_revenue_eur"],
        0.0,
    )
    detail["allocated_marketing_eur"] = (
        detail["direct_marketing_allocation_eur"]
        + detail["residual_marketing_allocation_eur"]
    )
    detail["contribution_margin_eur"] = (
        detail["contribution_before_marketing_eur"] - detail["allocated_marketing_eur"]
    )
    detail["contribution_margin_rate"] = np.where(
        detail["net_revenue_eur"] != 0,
        detail["contribution_margin_eur"] / detail["net_revenue_eur"],
        np.nan,
    )
    allocation_diagnostics = {
        "total_marketing_spend_eur": float(spend["spend_eur"].sum()),
        "allocated_marketing_spend_eur": float(detail["allocated_marketing_eur"].sum()),
        "direct_marketing_spend_eur": float(detail["direct_marketing_allocation_eur"].sum()),
        "residual_marketing_spend_eur": float(
            detail["residual_marketing_allocation_eur"].sum()
        ),
        "completed_order_net_revenue_eur": float(detail["net_revenue_eur"].sum()),
        "completed_order_count": float(completed["order_id"].nunique()),
        "fulfilled_completed_order_count": float(
            completed["order_id"].isin(fulfillment["order_id"]).sum()
        ),
    }
    return detail, allocation_diagnostics


def _monthly_kpis(
    clean_folder: Path, detail: pd.DataFrame, diagnostics: dict[str, float]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    sessions = read_table(clean_folder, "fact_sessions")
    orders = read_table(clean_folder, "fact_orders")
    fulfillment = read_table(clean_folder, "fact_fulfillment")
    inventory = read_table(clean_folder, "fact_inventory_snapshot")
    targets = read_table(clean_folder, "fact_targets")

    sessions["month_start"] = sessions["session_ts"].dt.to_period("M").dt.to_timestamp()
    sessions_month = sessions.groupby("month_start", as_index=False).agg(
        sessions=("session_id", "nunique"),
        converted_sessions=("converted_order_id", "count"),
        avg_page_load_ms=("page_load_ms", "mean"),
    )
    sessions_month["conversion_rate"] = (
        sessions_month["converted_sessions"] / sessions_month["sessions"]
    )
    completed = orders.query("order_status == 'Completed'").copy()
    completed["month_start"] = completed["order_ts"].dt.to_period("M").dt.to_timestamp()
    order_month = completed.groupby("month_start", as_index=False).agg(
        orders=("order_id", "nunique"), purchasing_customers=("customer_key", "nunique")
    )
    finance_month = detail.groupby("month_start", as_index=False).agg(
        gross_revenue_eur=("gross_revenue_eur", "sum"),
        discounts_eur=("discount_eur", "sum"),
        refunds_eur=("refund_eur", "sum"),
        net_revenue_eur=("net_revenue_eur", "sum"),
        cogs_eur=("cogs_eur", "sum"),
        recovered_cogs_eur=("recovered_cogs_eur", "sum"),
        return_handling_cost_eur=("handling_cost_eur", "sum"),
        fulfillment_cost_eur=("shipping_cost_eur", "sum"),
        marketing_spend_eur=("allocated_marketing_eur", "sum"),
        contribution_margin_eur=("contribution_margin_eur", "sum"),
        units_sold=("quantity", "sum"),
        units_returned=("units_returned", "sum"),
    )
    fulfillment = fulfillment.merge(
        completed[["order_id", "month_start"]], on="order_id", how="inner", validate="one_to_one"
    )
    fulfillment_month = fulfillment.groupby("month_start", as_index=False).agg(
        fulfilled_orders=("order_id", "nunique"), on_time_orders=("is_on_time", "sum")
    )
    fulfillment_month["on_time_delivery_rate"] = (
        fulfillment_month["on_time_orders"] / fulfillment_month["fulfilled_orders"]
    )
    inventory["month_start"] = inventory["snapshot_date"].dt.to_period("M").dt.to_timestamp()
    inventory_month = inventory.groupby("month_start", as_index=False).agg(
        inventory_snapshots=("inventory_snapshot_id", "count"),
        stockout_snapshots=("stockout_flag", "sum"),
        estimated_lost_units=("estimated_lost_units", "sum"),
    )
    inventory_month["stockout_rate"] = (
        inventory_month["stockout_snapshots"] / inventory_month["inventory_snapshots"]
    )
    target_month = targets.groupby("month_start", as_index=False).agg(
        net_revenue_target_eur=("net_revenue_target_eur", "sum"),
        contribution_margin_target_eur=("contribution_margin_target_eur", "sum"),
        orders_target=("orders_target", "sum"),
    )
    monthly = finance_month.merge(sessions_month, on="month_start", how="outer")
    for other in (order_month, fulfillment_month, inventory_month, target_month):
        monthly = monthly.merge(other, on="month_start", how="left")
    monthly = monthly.sort_values("month_start").reset_index(drop=True)
    monthly["average_order_value_eur"] = monthly["net_revenue_eur"] / monthly["orders"]
    monthly["contribution_margin_rate"] = (
        monthly["contribution_margin_eur"] / monthly["net_revenue_eur"]
    )
    monthly["return_rate"] = monthly["units_returned"] / monthly["units_sold"]
    monthly["net_revenue_vs_target_eur"] = (
        monthly["net_revenue_eur"] - monthly["net_revenue_target_eur"]
    )
    monthly["net_revenue_target_attainment"] = (
        monthly["net_revenue_eur"] / monthly["net_revenue_target_eur"]
    )
    monthly["contribution_vs_target_eur"] = (
        monthly["contribution_margin_eur"] - monthly["contribution_margin_target_eur"]
    )
    monthly["marketing_roas"] = np.where(
        monthly["marketing_spend_eur"] > 0,
        monthly["net_revenue_eur"] / monthly["marketing_spend_eur"],
        np.nan,
    )

    total_sessions = int(sessions["session_id"].nunique())
    total_converted = int(sessions["converted_order_id"].notna().sum())
    conversion_low, conversion_high = _wilson_interval(total_converted, total_sessions)
    total_units = int(detail["quantity"].sum())
    returned_units = int(detail["units_returned"].sum())
    return_low, return_high = _wilson_interval(returned_units, total_units)
    customer_orders = completed.groupby("customer_key")["order_id"].nunique()
    repeat_rate = float((customer_orders.ge(2).sum() / len(customer_orders)) if len(customer_orders) else np.nan)
    overall = pd.DataFrame(
        [
            {"metric": "Net Revenue", "value": detail["net_revenue_eur"].sum(), "unit": "EUR"},
            {
                "metric": "Contribution Margin",
                "value": detail["contribution_margin_eur"].sum(),
                "unit": "EUR",
            },
            {
                "metric": "Contribution Margin Rate",
                "value": detail["contribution_margin_eur"].sum() / detail["net_revenue_eur"].sum(),
                "unit": "rate",
            },
            {"metric": "Conversion Rate", "value": total_converted / total_sessions, "unit": "rate"},
            {"metric": "Conversion Rate CI Low", "value": conversion_low, "unit": "rate"},
            {"metric": "Conversion Rate CI High", "value": conversion_high, "unit": "rate"},
            {"metric": "Return Rate", "value": returned_units / total_units, "unit": "rate"},
            {"metric": "Return Rate CI Low", "value": return_low, "unit": "rate"},
            {"metric": "Return Rate CI High", "value": return_high, "unit": "rate"},
            {"metric": "Repeat Purchase Rate", "value": repeat_rate, "unit": "rate"},
            {
                "metric": "Marketing Allocation Coverage",
                "value": diagnostics["allocated_marketing_spend_eur"]
                / diagnostics["total_marketing_spend_eur"],
                "unit": "rate",
            },
            {
                "metric": "Fulfillment Coverage",
                "value": diagnostics["fulfilled_completed_order_count"]
                / diagnostics["completed_order_count"],
                "unit": "rate",
            },
        ]
    )
    return monthly, overall


def _funnel(clean_folder: Path) -> pd.DataFrame:
    sessions = read_table(clean_folder, "fact_sessions")
    rows = [
        (1, "Sessions", int(sessions["session_id"].nunique())),
        (2, "Product view", int(sessions.loc[sessions["product_views"] > 0, "session_id"].nunique())),
        (3, "Added to cart", int(sessions.loc[sessions["added_to_cart"], "session_id"].nunique())),
        (4, "Checkout started", int(sessions.loc[sessions["checkout_started"], "session_id"].nunique())),
        (5, "Purchased", int(sessions.loc[sessions["converted_order_id"].notna(), "session_id"].nunique())),
    ]
    funnel = pd.DataFrame(rows, columns=["stage_order", "stage", "sessions"])
    funnel["stage_conversion"] = funnel["sessions"] / funnel["sessions"].shift(1)
    funnel.loc[0, "stage_conversion"] = 1.0
    funnel["overall_conversion"] = funnel["sessions"] / funnel.loc[0, "sessions"]
    return funnel


def _cohort_retention(clean_folder: Path) -> pd.DataFrame:
    orders = read_table(clean_folder, "fact_orders").query("order_status == 'Completed'").copy()
    orders["order_month"] = orders["order_ts"].dt.to_period("M")
    first_month = orders.groupby("customer_key")["order_month"].min().rename("cohort_month")
    cohort = orders[["customer_key", "order_month"]].drop_duplicates().merge(
        first_month, on="customer_key", how="left", validate="many_to_one"
    )
    cohort["month_index"] = (
        (cohort["order_month"].dt.year - cohort["cohort_month"].dt.year) * 12
        + cohort["order_month"].dt.month
        - cohort["cohort_month"].dt.month
    )
    cohort = cohort.loc[cohort["month_index"].between(0, 12)]
    counts = cohort.groupby(["cohort_month", "month_index"], as_index=False)["customer_key"].nunique()
    counts = counts.rename(columns={"customer_key": "active_customers"})
    sizes = counts.query("month_index == 0")[["cohort_month", "active_customers"]].rename(
        columns={"active_customers": "cohort_size"}
    )
    counts = counts.merge(sizes, on="cohort_month", how="left", validate="many_to_one")
    counts["retention_rate"] = counts["active_customers"] / counts["cohort_size"]
    counts["cohort_month"] = counts["cohort_month"].astype(str)
    return counts


def _root_causes(detail: pd.DataFrame) -> tuple[pd.DataFrame, str, str]:
    prior_period, current_period = _latest_two_complete_quarters(detail["order_date"].max())
    prior_label, current_label = str(prior_period), str(current_period)
    scoped = detail.loc[detail["quarter"].isin([prior_label, current_label])].copy()
    rows: list[pd.DataFrame] = []
    for dimension, column in (
        ("Market", "market_code"),
        ("Channel", "channel_name"),
        ("Category", "category"),
    ):
        grouped = scoped.groupby([column, "quarter"], as_index=False).agg(
            net_revenue_eur=("net_revenue_eur", "sum"),
            contribution_margin_eur=("contribution_margin_eur", "sum"),
            orders=("order_id", "nunique"),
            units_sold=("quantity", "sum"),
            units_returned=("units_returned", "sum"),
        )
        pivot = grouped.pivot(index=column, columns="quarter")
        output = pd.DataFrame({"dimension_value": pivot.index})
        output["dimension"] = dimension
        for metric in (
            "net_revenue_eur",
            "contribution_margin_eur",
            "orders",
            "units_sold",
            "units_returned",
        ):
            prior_values = pivot.get((metric, prior_label), pd.Series(0, index=pivot.index))
            current_values = pivot.get((metric, current_label), pd.Series(0, index=pivot.index))
            output[f"prior_{metric}"] = np.asarray(prior_values)
            output[f"current_{metric}"] = np.asarray(current_values)
        output["delta_net_revenue_eur"] = (
            output["current_net_revenue_eur"] - output["prior_net_revenue_eur"]
        )
        output["delta_contribution_margin_eur"] = (
            output["current_contribution_margin_eur"]
            - output["prior_contribution_margin_eur"]
        )
        output["prior_contribution_margin_rate"] = (
            output["prior_contribution_margin_eur"] / output["prior_net_revenue_eur"]
        )
        output["current_contribution_margin_rate"] = (
            output["current_contribution_margin_eur"] / output["current_net_revenue_eur"]
        )
        output["delta_contribution_margin_rate_pp"] = 100 * (
            output["current_contribution_margin_rate"]
            - output["prior_contribution_margin_rate"]
        )
        output["current_return_rate"] = (
            output["current_units_returned"] / output["current_units_sold"]
        )
        rows.append(output)
    return pd.concat(rows, ignore_index=True), prior_label, current_label


def _operational_drivers(clean_folder: Path) -> pd.DataFrame:
    sessions = read_table(clean_folder, "fact_sessions")
    geography = read_table(clean_folder, "dim_geography")
    channels = read_table(clean_folder, "dim_channel")
    sessions = sessions.merge(
        geography[["market_key", "market_code"]], on="market_key", how="left", validate="many_to_one"
    ).merge(
        channels[["channel_key", "channel_name"]],
        on="channel_key",
        how="left",
        validate="many_to_one",
    )
    sessions["quarter"] = sessions["session_ts"].dt.to_period("Q").astype(str)
    grouped = sessions.groupby(
        ["quarter", "market_code", "device_type"], as_index=False
    ).agg(
        sessions=("session_id", "count"),
        converted_sessions=("converted_order_id", "count"),
        avg_page_load_ms=("page_load_ms", "mean"),
    )
    grouped["conversion_rate"] = grouped["converted_sessions"] / grouped["sessions"]
    return grouped


def _inventory_opportunity(clean_folder: Path) -> pd.DataFrame:
    inventory = read_table(clean_folder, "fact_inventory_snapshot")
    products = read_table(clean_folder, "dim_product")
    geography = read_table(clean_folder, "dim_geography")
    inventory = inventory.merge(
        products[["product_key", "category", "list_price_eur"]],
        on="product_key",
        how="left",
        validate="many_to_one",
    ).merge(
        geography[["market_key", "market_code"]], on="market_key", how="left", validate="many_to_one"
    )
    inventory["quarter"] = inventory["snapshot_date"].dt.to_period("Q").astype(str)
    inventory["estimated_lost_revenue_eur"] = (
        inventory["estimated_lost_units"] * inventory["list_price_eur"]
    )
    grouped = inventory.groupby(["quarter", "market_code", "category"], as_index=False).agg(
        snapshots=("inventory_snapshot_id", "count"),
        stockout_snapshots=("stockout_flag", "sum"),
        estimated_lost_units=("estimated_lost_units", "sum"),
        estimated_lost_revenue_eur=("estimated_lost_revenue_eur", "sum"),
    )
    grouped["stockout_rate"] = grouped["stockout_snapshots"] / grouped["snapshots"]
    return grouped


def _forecast(monthly: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
    history = monthly[["month_start", "net_revenue_eur"]].dropna().copy()
    values = history["net_revenue_eur"].to_numpy(dtype=float)
    time_index = np.arange(len(values), dtype=float)
    holdout = min(3, max(1, len(values) // 4))
    train_count = len(values) - holdout
    if train_count < 3:
        raise ValueError("At least four monthly observations are required for forecasting")
    train_values = values[:train_count]
    train_index = time_index[:train_count]
    if train_count >= 15:
        backtest_prediction = values[train_count - 12 : len(values) - 12]
        method = "Seasonal naive (12-month lag)"
    else:
        coefficients = np.polyfit(train_index, train_values, deg=1)
        backtest_prediction = np.polyval(coefficients, time_index[train_count:])
        method = "Linear trend benchmark"
    actual_holdout = values[train_count:]
    errors = actual_holdout - backtest_prediction
    wape = float(np.abs(errors).sum() / np.abs(actual_holdout).sum())
    bias = float(errors.sum() / np.abs(actual_holdout).sum())

    annual_sin = np.sin(2 * np.pi * time_index / 12)
    annual_cos = np.cos(2 * np.pi * time_index / 12)
    design = np.column_stack([np.ones(len(values)), time_index, annual_sin, annual_cos])
    coefficients, *_ = np.linalg.lstsq(design, values, rcond=None)
    fitted = design @ coefficients
    residual_std = float(np.std(values - fitted, ddof=min(4, len(values) - 1)))
    future_index = np.arange(len(values), len(values) + 3, dtype=float)
    future_design = np.column_stack(
        [
            np.ones(3),
            future_index,
            np.sin(2 * np.pi * future_index / 12),
            np.cos(2 * np.pi * future_index / 12),
        ]
    )
    future_values = future_design @ coefficients
    next_month = history["month_start"].max() + pd.offsets.MonthBegin(1)
    forecast_dates = pd.date_range(next_month, periods=3, freq="MS")
    point_forecast = np.maximum(future_values, 0)
    forecast = pd.DataFrame(
        {
            "month_start": forecast_dates,
            "forecast_net_revenue_eur": point_forecast,
            "forecast_lower_95_eur": np.minimum(
                np.maximum(future_values - 1.96 * residual_std, 0), point_forecast
            ),
            "forecast_upper_95_eur": np.maximum(
                future_values + 1.96 * residual_std, point_forecast
            ),
            "model": "OLS trend plus annual sine/cosine terms",
        }
    )
    diagnostics = {
        "backtest_method": method,
        "holdout_months": holdout,
        "wape": wape,
        "bias": bias,
        "residual_std_eur": residual_std,
    }
    return forecast, diagnostics


def _conversion_model(clean_folder: Path) -> pd.DataFrame:
    sessions = read_table(clean_folder, "fact_sessions")
    sample = sessions.sample(min(80000, len(sessions)), random_state=20260813).copy()
    sample["converted"] = sample["converted_order_id"].notna().astype(int)
    sample["mobile"] = sample["device_type"].eq("Mobile").astype(int)
    sample["paid_social"] = sample["channel_key"].eq(3).astype(int)
    sample["load_seconds"] = sample["page_load_ms"] / 1000
    sample["views_scaled"] = sample["product_views"] / sample["product_views"].std()
    try:
        import statsmodels.api as sm

        features = sm.add_constant(
            sample[["mobile", "paid_social", "load_seconds", "views_scaled"]],
            has_constant="add",
        )
        fitted = sm.Logit(sample["converted"], features).fit(disp=False, maxiter=100)
        confidence = fitted.conf_int()
        rows = []
        for feature in features.columns:
            rows.append(
                {
                    "feature": feature,
                    "coefficient": float(fitted.params[feature]),
                    "odds_ratio": float(np.exp(fitted.params[feature])),
                    "p_value": float(fitted.pvalues[feature]),
                    "odds_ratio_ci_low": float(np.exp(confidence.loc[feature, 0])),
                    "odds_ratio_ci_high": float(np.exp(confidence.loc[feature, 1])),
                    "sample_rows": len(sample),
                    "method": "statsmodels logistic regression; association, not causation",
                }
            )
        return pd.DataFrame(rows)
    except (ImportError, ValueError, np.linalg.LinAlgError):
        from scipy.stats import pointbiserialr

        correlation, p_value = pointbiserialr(sample["converted"], sample["load_seconds"])
        return pd.DataFrame(
            [
                {
                    "feature": "load_seconds",
                    "coefficient": correlation,
                    "odds_ratio": np.nan,
                    "p_value": p_value,
                    "odds_ratio_ci_low": np.nan,
                    "odds_ratio_ci_high": np.nan,
                    "sample_rows": len(sample),
                    "method": "point-biserial correlation fallback; association, not causation",
                }
            ]
        )


def _action_register(
    roots: pd.DataFrame,
    operational: pd.DataFrame,
    inventory: pd.DataFrame,
    current_quarter: str,
) -> pd.DataFrame:
    market_risk = roots.query("dimension == 'Market'").nsmallest(1, "delta_contribution_margin_eur").iloc[0]
    channel_risk = roots.query("dimension == 'Channel'").nsmallest(1, "delta_contribution_margin_eur").iloc[0]
    category_risk = roots.query("dimension == 'Category'").nsmallest(1, "delta_contribution_margin_eur").iloc[0]
    mobile = operational.query(
        "quarter == @current_quarter and market_code in ['SE', 'GB'] and device_type == 'Mobile'"
    )
    inventory_risk = inventory.query("quarter == @current_quarter").nlargest(
        1, "estimated_lost_revenue_eur"
    ).iloc[0]
    current_mobile_load = float(mobile["avg_page_load_ms"].mean()) if not mobile.empty else np.nan
    current_mobile_conversion = float(mobile["conversion_rate"].mean()) if not mobile.empty else np.nan
    return pd.DataFrame(
        [
            {
                "action_id": "ACT-001",
                "priority": "P0",
                "owner": "Commercial Director",
                "action": f"Reprice and cap discounts for {category_risk['dimension_value']} in {channel_risk['dimension_value']}.",
                "evidence": (
                    f"{category_risk['dimension_value']} contribution changed by "
                    f"EUR {category_risk['delta_contribution_margin_eur']:,.0f} in {current_quarter}."
                ),
                "expected_impact": "Recover 1-2 percentage points of contribution margin in the affected mix.",
                "guardrail": "Orders and 30-day return rate must not worsen by more than 5% relative.",
                "review_cadence": "Weekly for six weeks",
                "status": "Proposed",
            },
            {
                "action_id": "ACT-002",
                "priority": "P0",
                "owner": "Operations Director",
                "action": f"Launch a delivery-SLA recovery plan for {market_risk['dimension_value']} and the North hub.",
                "evidence": (
                    f"{market_risk['dimension_value']} contribution changed by "
                    f"EUR {market_risk['delta_contribution_margin_eur']:,.0f}; late delivery is an explicit return driver."
                ),
                "expected_impact": "Improve on-time rate toward 94% and reduce late-delivery returns.",
                "guardrail": "Shipping cost per fulfilled order may rise by at most EUR 0.50.",
                "review_cadence": "Weekly operations review",
                "status": "Proposed",
            },
            {
                "action_id": "ACT-003",
                "priority": "P1",
                "owner": "Head of E-commerce",
                "action": "Prioritize mobile performance remediation in Sweden and the United Kingdom.",
                "evidence": (
                    f"Current-quarter mobile load averages {current_mobile_load:,.0f} ms with "
                    f"{current_mobile_conversion:.1%} conversion in those markets."
                ),
                "expected_impact": "Improve checkout completion and conversion without increasing media spend.",
                "guardrail": "Track conversion with Wilson confidence intervals; avoid causal claims without an experiment.",
                "review_cadence": "Biweekly product review",
                "status": "Proposed",
            },
            {
                "action_id": "ACT-004",
                "priority": "P1",
                "owner": "Inventory Planning Lead",
                "action": (
                    f"Raise reorder coverage for {inventory_risk['category']} in "
                    f"{inventory_risk['market_code']}."
                ),
                "evidence": (
                    f"Estimated lost revenue is EUR {inventory_risk['estimated_lost_revenue_eur']:,.0f} "
                    f"with a {inventory_risk['stockout_rate']:.1%} snapshot stockout rate."
                ),
                "expected_impact": "Recover lost units while limiting excess inventory.",
                "guardrail": "Monitor days of supply and aged stock alongside stockout rate.",
                "review_cadence": "Monthly S&OP",
                "status": "Proposed",
            },
        ]
    )


def _apply_chart_style(axis: plt.Axes) -> None:
    axis.spines[["top", "right"]].set_visible(False)
    axis.spines[["left", "bottom"]].set_color(GRID)
    axis.grid(axis="y", color=GRID, linewidth=0.7, alpha=0.75)
    axis.tick_params(colors=INK, labelsize=9)
    axis.set_axisbelow(True)


def _save_charts(
    output_root: Path,
    monthly: pd.DataFrame,
    funnel: pd.DataFrame,
    cohort: pd.DataFrame,
    roots: pd.DataFrame,
    forecast: pd.DataFrame,
    prior_quarter: str,
    current_quarter: str,
) -> list[dict[str, str]]:
    chart_root = output_root.parent / "charts"
    chart_root.mkdir(parents=True, exist_ok=True)
    chart_map: list[dict[str, str]] = []

    fig, axis = plt.subplots(figsize=(10, 5.2), constrained_layout=True)
    axis.plot(monthly["month_start"], monthly["net_revenue_eur"], color=BLUE, linewidth=2.4, marker="o", label="Actual")
    axis.plot(monthly["month_start"], monthly["net_revenue_target_eur"], color=GOLD, linewidth=1.8, linestyle="--", label="Target")
    _apply_chart_style(axis)
    axis.set_title("Monthly net revenue and operating target", loc="left", color=INK, fontsize=13, weight="bold")
    axis.set_ylabel("EUR")
    axis.legend(frameon=False)
    path = chart_root / "monthly_net_revenue.png"
    fig.savefig(path, dpi=170, facecolor="white")
    plt.close(fig)
    chart_map.append({"chart": "Monthly net revenue", "path": str(path.relative_to(output_root.parent.parent))})

    fig, axis = plt.subplots(figsize=(8.5, 4.8), constrained_layout=True)
    ordered = funnel.sort_values("stage_order", ascending=False)
    axis.barh(ordered["stage"], ordered["sessions"], color=BLUE)
    for index, value in enumerate(ordered["sessions"]):
        axis.text(value, index, f" {value:,.0f}", va="center", color=INK, fontsize=9)
    _apply_chart_style(axis)
    axis.set_title("Commerce conversion funnel", loc="left", color=INK, fontsize=13, weight="bold")
    axis.set_xlabel("Unique sessions")
    path = chart_root / "conversion_funnel.png"
    fig.savefig(path, dpi=170, facecolor="white")
    plt.close(fig)
    chart_map.append({"chart": "Conversion funnel", "path": str(path.relative_to(output_root.parent.parent))})

    matrix = cohort.pivot(index="cohort_month", columns="month_index", values="retention_rate").sort_index()
    fig, axis = plt.subplots(figsize=(10, 6), constrained_layout=True)
    image = axis.imshow(matrix.to_numpy(), aspect="auto", cmap="Blues", vmin=0, vmax=1)
    axis.set_yticks(np.arange(len(matrix.index)), labels=matrix.index)
    axis.set_xticks(np.arange(len(matrix.columns)), labels=matrix.columns)
    axis.set_xlabel("Months since first purchase")
    axis.set_ylabel("First-purchase cohort")
    axis.set_title("Monthly purchasing-cohort retention", loc="left", color=INK, fontsize=13, weight="bold")
    fig.colorbar(image, ax=axis, format=lambda value, _: f"{value:.0%}")
    path = chart_root / "cohort_retention.png"
    fig.savefig(path, dpi=170, facecolor="white")
    plt.close(fig)
    chart_map.append({"chart": "Cohort retention", "path": str(path.relative_to(output_root.parent.parent))})

    negative_roots = roots.nsmallest(8, "delta_contribution_margin_eur").sort_values(
        "delta_contribution_margin_eur", ascending=True
    )
    labels = negative_roots["dimension"] + ": " + negative_roots["dimension_value"].astype(str)
    fig, axis = plt.subplots(figsize=(9.5, 5.2), constrained_layout=True)
    axis.barh(labels, negative_roots["delta_contribution_margin_eur"], color=ORANGE)
    _apply_chart_style(axis)
    axis.axvline(0, color=INK, linewidth=0.8)
    axis.set_title(
        f"Contribution-margin change by driver ({prior_quarter} to {current_quarter})",
        loc="left",
        color=INK,
        fontsize=13,
        weight="bold",
    )
    axis.set_xlabel("EUR change")
    path = chart_root / "contribution_root_causes.png"
    fig.savefig(path, dpi=170, facecolor="white")
    plt.close(fig)
    chart_map.append({"chart": "Contribution root causes", "path": str(path.relative_to(output_root.parent.parent))})

    fig, axis = plt.subplots(figsize=(10, 5.2), constrained_layout=True)
    axis.plot(monthly["month_start"], monthly["net_revenue_eur"], color=BLUE, linewidth=2.2, label="Actual")
    axis.plot(forecast["month_start"], forecast["forecast_net_revenue_eur"], color=GOLD, linewidth=2.2, marker="o", label="Forecast")
    axis.fill_between(
        forecast["month_start"],
        forecast["forecast_lower_95_eur"],
        forecast["forecast_upper_95_eur"],
        color=GOLD,
        alpha=0.18,
        label="95% interval",
    )
    _apply_chart_style(axis)
    axis.set_title("Three-month net-revenue forecast", loc="left", color=INK, fontsize=13, weight="bold")
    axis.set_ylabel("EUR")
    axis.legend(frameon=False)
    path = chart_root / "net_revenue_forecast.png"
    fig.savefig(path, dpi=170, facecolor="white")
    plt.close(fig)
    chart_map.append({"chart": "Net revenue forecast", "path": str(path.relative_to(output_root.parent.parent))})
    return chart_map


def run_analysis(clean_folder: Path, output_root: Path) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    detail, allocation_diagnostics = _build_finance_detail(clean_folder)
    monthly, overall = _monthly_kpis(clean_folder, detail, allocation_diagnostics)
    funnel = _funnel(clean_folder)
    cohort = _cohort_retention(clean_folder)
    roots, prior_quarter, current_quarter = _root_causes(detail)
    operational = _operational_drivers(clean_folder)
    inventory = _inventory_opportunity(clean_folder)
    forecast, forecast_diagnostics = _forecast(monthly)
    conversion_model = _conversion_model(clean_folder)
    actions = _action_register(roots, operational, inventory, current_quarter)

    outputs = {
        "monthly_kpis": monthly,
        "overall_kpis": overall,
        "funnel": funnel,
        "cohort_retention": cohort,
        "root_causes": roots,
        "operational_drivers": operational,
        "inventory_opportunity": inventory,
        "forecast": forecast,
        "conversion_driver_model": conversion_model,
        "action_register": actions,
    }
    for name, frame in outputs.items():
        frame.to_csv(output_root / f"{name}.csv", index=False)

    total_net_revenue = float(detail["net_revenue_eur"].sum())
    finance_identity = float(
        (
            detail["net_revenue_eur"]
            - detail["cogs_eur"]
            + detail["recovered_cogs_eur"]
            - detail["handling_cost_eur"]
            - detail["shipping_cost_eur"]
            - detail["allocated_marketing_eur"]
            - detail["contribution_margin_eur"]
        )
        .abs()
        .max()
    )
    reconciliation = pd.DataFrame(
        [
            {
                "check": "Item contribution identity",
                "observed_delta": finance_identity,
                "threshold": 0.000001,
                "status": "PASS" if finance_identity <= 0.000001 else "FAIL",
            },
            {
                "check": "Monthly net revenue reconciles to item detail",
                "observed_delta": abs(monthly["net_revenue_eur"].sum() - total_net_revenue),
                "threshold": 0.02,
                "status": "PASS"
                if abs(monthly["net_revenue_eur"].sum() - total_net_revenue) <= 0.02
                else "FAIL",
            },
            {
                "check": "Marketing allocation coverage",
                "observed_delta": abs(
                    allocation_diagnostics["total_marketing_spend_eur"]
                    - allocation_diagnostics["allocated_marketing_spend_eur"]
                ),
                "threshold": max(10.0, allocation_diagnostics["total_marketing_spend_eur"] * 0.01),
                "status": "PASS"
                if abs(
                    allocation_diagnostics["total_marketing_spend_eur"]
                    - allocation_diagnostics["allocated_marketing_spend_eur"]
                )
                <= max(10.0, allocation_diagnostics["total_marketing_spend_eur"] * 0.01)
                else "FAIL",
            },
        ]
    )
    reconciliation.to_csv(output_root / "reconciliations.csv", index=False)
    chart_map = _save_charts(
        output_root, monthly, funnel, cohort, roots, forecast, prior_quarter, current_quarter
    )

    quarter_summary = detail.groupby("quarter", as_index=False).agg(
        net_revenue_eur=("net_revenue_eur", "sum"),
        contribution_margin_eur=("contribution_margin_eur", "sum"),
        orders=("order_id", "nunique"),
        units_sold=("quantity", "sum"),
        units_returned=("units_returned", "sum"),
    )
    quarter_summary["contribution_margin_rate"] = (
        quarter_summary["contribution_margin_eur"] / quarter_summary["net_revenue_eur"]
    )
    quarter_summary["return_rate"] = quarter_summary["units_returned"] / quarter_summary["units_sold"]
    quarter_summary.to_csv(output_root / "quarterly_kpis.csv", index=False)
    prior = quarter_summary.set_index("quarter").loc[prior_quarter]
    current = quarter_summary.set_index("quarter").loc[current_quarter]
    top_negative = roots.nsmallest(5, "delta_contribution_margin_eur")
    summary = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "scenario_disclosure": "The business records and findings are synthetic; ECB FX reference data is real.",
        "analysis_window": {
            "start": str(detail["order_date"].min().date()),
            "end": str(detail["order_date"].max().date()),
            "comparison": f"{prior_quarter} versus {current_quarter}",
        },
        "headline": {
            "current_quarter_net_revenue_eur": float(current["net_revenue_eur"]),
            "net_revenue_change_pct": float(
                current["net_revenue_eur"] / prior["net_revenue_eur"] - 1
            ),
            "current_quarter_contribution_margin_eur": float(
                current["contribution_margin_eur"]
            ),
            "contribution_margin_change_eur": float(
                current["contribution_margin_eur"] - prior["contribution_margin_eur"]
            ),
            "current_quarter_contribution_margin_rate": float(
                current["contribution_margin_rate"]
            ),
            "contribution_margin_rate_change_pp": float(
                100
                * (current["contribution_margin_rate"] - prior["contribution_margin_rate"])
            ),
            "current_quarter_return_rate": float(current["return_rate"]),
        },
        "top_negative_contribution_drivers": top_negative[
            [
                "dimension",
                "dimension_value",
                "delta_contribution_margin_eur",
                "delta_contribution_margin_rate_pp",
            ]
        ].to_dict(orient="records"),
        "forecast_diagnostics": forecast_diagnostics,
        "allocation_diagnostics": allocation_diagnostics,
        "reconciliation_status": (
            "PASS" if reconciliation["status"].eq("PASS").all() else "FAIL"
        ),
        "actions": actions.to_dict(orient="records"),
        "chart_map": chart_map,
        "methodology_caveats": [
            "Scenario findings describe generated commerce operations, not a real company.",
            "Last-touch channel attribution is used for revenue; it is not causal incrementality.",
            "The conversion model is observational and reports association, not causal lift.",
            "Lost revenue from stockouts is an estimate based on generated demand and list price.",
            "Forecast intervals reflect model residuals and do not capture all business uncertainty.",
        ],
    }
    write_json(summary, output_root / "executive_summary.json")
    if not reconciliation["status"].eq("PASS").all():
        raise ValueError("Analysis reconciliation failed; see reconciliations.csv")
    return summary
