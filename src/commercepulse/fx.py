from __future__ import annotations

from pathlib import Path

import pandas as pd

ECB_SOURCE_URL = (
    "https://www.ecb.europa.eu/stats/policy_and_exchange_rates/"
    "euro_reference_exchange_rates/html/index.en.html"
)


def load_ecb_rates(
    csv_path: Path,
    start_date: str,
    end_date: str,
    currencies: tuple[str, ...] = ("EUR", "GBP", "PLN", "SEK"),
) -> pd.DataFrame:
    """Return one row per calendar date and currency.

    ECB reference rates are quoted as local currency units per EUR. Weekends and
    TARGET closing days are forward-filled from the latest published business day.
    EUR is added at a constant rate of one.
    """

    raw = pd.read_csv(csv_path, na_values=["N/A"], parse_dates=["Date"])
    raw = raw.loc[:, ~raw.columns.str.startswith("Unnamed")]
    raw = raw.sort_values("Date").set_index("Date")
    calendar = pd.date_range(start_date, end_date, freq="D")
    selected = [currency for currency in currencies if currency != "EUR"]
    missing = sorted(set(selected) - set(raw.columns))
    if missing:
        raise ValueError(f"ECB cache is missing currencies: {missing}")
    daily = raw[selected].reindex(calendar).ffill().bfill()
    daily["EUR"] = 1.0
    daily.index.name = "rate_date"
    long = daily.reset_index().melt(
        id_vars="rate_date", var_name="currency_code", value_name="local_per_eur"
    )
    long["rate_date_key"] = long["rate_date"].dt.strftime("%Y%m%d").astype("int32")
    long["local_per_eur"] = long["local_per_eur"].astype("float64")
    long["source_name"] = "European Central Bank euro reference exchange rates"
    long["source_url"] = ECB_SOURCE_URL
    return long[
        [
            "rate_date_key",
            "rate_date",
            "currency_code",
            "local_per_eur",
            "source_name",
            "source_url",
        ]
    ]
