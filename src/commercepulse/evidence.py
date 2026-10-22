"""Reproducible scale, forecast, and scenario evidence. All inputs are synthetic."""

import argparse
import hashlib
import json
import platform
import re
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

MARKETS = ["DE", "FR", "IT", "ES", "NL", "AT"]
CHANNELS = ["web", "store", "marketplace"]
ROOT = Path(__file__).resolve().parents[2]


def wape(actual, predicted):
    actual, predicted = np.asarray(actual), np.asarray(predicted)
    if (
        actual.shape != predicted.shape
        or not np.isfinite(actual).all()
        or not np.isfinite(predicted).all()
        or np.abs(actual).sum() == 0
    ):
        raise ValueError("WAPE requires matching finite arrays and a nonzero denominator")
    return float(np.abs(actual - predicted).sum() / np.abs(actual).sum())


def allocate(unmet, unit_margin, budget):
    """Optimal integer allocation for a linear objective with equal unit costs."""
    unmet, unit_margin = np.asarray(unmet, dtype=int), np.asarray(unit_margin, dtype=float)
    if (
        unmet.shape != unit_margin.shape
        or budget < 0
        or (unmet < 0).any()
        or not np.isfinite(unit_margin).all()
    ):
        raise ValueError("Invalid allocation inputs")
    result = np.zeros_like(unmet)
    for index in np.argsort(-unit_margin, kind="stable"):
        if unit_margin[index] <= 0:
            continue
        result[index] = min(int(budget), unmet[index])
        budget -= result[index]
    return result


def forecast_evaluation(seed, output):
    rng = np.random.default_rng(seed)
    rows = []
    days = np.arange(365)
    design = np.column_stack(
        [np.ones(365), days / 365, *[(days % 7 == i).astype(float) for i in range(1, 7)]]
    )
    for index, market in enumerate(MARKETS):
        intensity = (
            (75 + index * 15)
            * (1 + 0.2 * days / 365)
            * np.array([0.9, 0.95, 1, 1, 1.15, 1.3, 0.8])[days % 7]
        )
        actual = rng.poisson(intensity)
        weights = np.linalg.lstsq(design[:337], actual[:337], rcond=None)[0]
        predicted = np.maximum(design[337:] @ weights, 0)
        baseline = np.tile(actual[330:337], 4)
        rows.extend(
            {
                "market": market,
                "day": int(day),
                "actual": int(a),
                "forecast": float(p),
                "seasonal_naive": int(b),
            }
            for day, a, p, b in zip(days[337:], actual[337:], predicted, baseline, strict=True)
        )
    frame = pd.DataFrame(rows)
    frame.to_csv(output / "forecast_holdout.csv", index=False)
    return {
        "train_days": 337,
        "holdout_days": 28,
        "holdout_rows": len(frame),
        "wape": wape(frame.actual, frame.forecast),
        "seasonal_naive_wape": wape(frame.actual, frame.seasonal_naive),
        "scope": "Independent synthetic daily demand fixture; not fitted to the event stream.",
    }


def scenarios(journeys, output):
    eligible = journeys.consent & journeys.orders.between(2, 5)
    per_order = journeys.loc[eligible, "contribution"] / journeys.loc[eligible, "orders"]
    retention = [
        {
            "assumed_incremental_purchase_probability": uplift,
            "eligible_journeys": int(eligible.sum()),
            "contact_cost_eur": 0.35,
            "modeled_net_contribution_eur": float((per_order * uplift - 0.35).sum()),
        }
        for uplift in [0.02, 0.04, 0.06]
    ]
    pd.DataFrame(retention).to_csv(output / "retention_sensitivity.csv", index=False)
    inventory = (
        journeys.groupby("market", sort=True)
        .agg(demand=("orders", "sum"), contribution=("contribution", "sum"))
        .reset_index()
    )
    inventory["unmet"] = inventory.demand - np.floor(inventory.demand * 0.94).astype(int)
    inventory["recovered_unit_margin"] = inventory.contribution / inventory.demand - 2
    budget = int(inventory.unmet.sum() * 0.4)
    inventory["allocated"] = allocate(inventory.unmet, inventory.recovered_unit_margin, budget)
    equal = np.full(len(inventory), budget // len(inventory))
    equal[: budget % len(inventory)] += 1
    inventory["equal_allocated"] = np.minimum(equal, inventory.unmet)
    inventory["modeled_recovery_eur"] = inventory.allocated * inventory.recovered_unit_margin
    inventory.to_csv(output / "inventory_allocation.csv", index=False)
    recovered = float(inventory.modeled_recovery_eur.sum())
    equal_recovered = float((inventory.equal_allocated * inventory.recovered_unit_margin).sum())
    quintiles = pd.qcut(journeys.contribution.rank(method="first"), 5, labels=False)
    top = journeys[quintiles == 4]
    ratio = float(
        top.contribution.sum()
        / top.marketing.sum()
        / (journeys.contribution.sum() / journeys.marketing.sum())
        - 1
    )
    return {
        "retention": retention,
        "inventory": {
            "budget_units": budget,
            "modeled_total_recovery_eur": recovered,
            "equal_allocation_recovery_eur": equal_recovered,
            "optimization_lift_eur": recovered - equal_recovered,
        },
        "top_value_quintile_contribution_per_marketing_euro_relative_difference": ratio,
        "scope": "Assumption-based synthetic scenarios, not realized revenue, causal lift, or validated annual forecasts.",
    }


def run(events, journeys_count, output, seed=20261018, chunk_size=250000, persist=False):
    if not events >= journeys_count >= 6 or chunk_size < 1:
        raise ValueError("Require events >= journeys >= 6 and a positive chunk size")
    started = time.perf_counter()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    # Refuse stale partitions from a previous materialization.
    if persist and (output / "events").exists():
        raise FileExistsError(
            "Choose a new output directory or remove the old events directory explicitly"
        )
    rng = np.random.default_rng(seed)
    ids = np.arange(journeys_count)
    orders = 1 + rng.poisson(2.6, journeys_count)
    revenue = orders * rng.lognormal(3.8, 0.42, journeys_count)
    journeys = pd.DataFrame(
        {
            "journey_id": ids,
            "market": np.array(MARKETS)[ids % 6],
            "orders": orders,
            "net_revenue": revenue,
            "contribution": revenue * rng.uniform(0.18, 0.40, journeys_count),
            "marketing": rng.uniform(8, 28, journeys_count),
            "consent": rng.random(journeys_count) < 0.78,
        }
    )
    digest, counts, failures, partitions = hashlib.sha256(), np.zeros((6, 3), dtype=np.int64), 0, []
    if persist:
        (output / "events").mkdir()
        journeys.to_parquet(output / "journeys.parquet", index=False)
    for start in range(0, events, chunk_size):
        event_id = np.arange(start, min(events, start + chunk_size), dtype=np.int64)
        journey_id = event_id % journeys_count
        market = journey_id % 6
        channel = (event_id // journeys_count) % 3
        engagement = ((event_id * 48271 + seed) % 2147483647) / 2147483647
        valid = (
            (journey_id >= 0)
            & (journey_id < journeys_count)
            & (market >= 0)
            & (market < 6)
            & (channel >= 0)
            & (channel < 3)
            & np.isfinite(engagement)
            & (engagement >= 0)
            & (engagement < 1)
        )
        failures += int((~valid).sum())
        digest.update(
            np.column_stack([event_id, journey_id, market, channel]).astype("<i8").tobytes()
        )
        np.add.at(counts, (market, channel), 1)
        if persist:
            part = output / "events" / f"part-{start:09d}.parquet"
            pd.DataFrame(
                {
                    "event_id": event_id,
                    "journey_id": journey_id,
                    "market": np.array(MARKETS)[market],
                    "channel": np.array(CHANNELS)[channel],
                    "engagement": engagement,
                }
            ).to_parquet(part, index=False)
            partitions.append(
                {
                    "file": str(part.relative_to(output)),
                    "rows": len(event_id),
                    "sha256": hashlib.sha256(part.read_bytes()).hexdigest(),
                }
            )
    pd.DataFrame(counts, index=MARKETS, columns=CHANNELS).rename_axis("market").to_csv(
        output / "event_counts.csv"
    )
    forecast = forecast_evaluation(seed + 1, output)
    business = scenarios(journeys, output)
    measures = ROOT / "powerbi/CommercePulse.SemanticModel/definition/tables/KPI Measures.tmdl"
    metrics = {
        "generated_utc": datetime.now(UTC).isoformat(),
        "seed": seed,
        "base_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "synthetic": True,
        "events": events,
        "journeys": journeys_count,
        "markets": MARKETS,
        "channels": CHANNELS,
        "event_key_sha256": digest.hexdigest(),
        "quality": {
            "evaluated_rows": events,
            "failed_rows": failures,
            "pass_rate": 1 - failures / events,
            "rules": [
                "journey foreign key bounds",
                "market and channel domains",
                "finite engagement in [0,1)",
            ],
            "unique_event_ids": "Contiguous, nonoverlapping ranges by construction; covered by persisted-data regression test.",
        },
        "dax_measures": len(re.findall(r"^\s*measure ", measures.read_text(), re.M)),
        "forecast": forecast,
        "scenarios": business,
        "persisted": persist,
        "partitions": partitions,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "elapsed_seconds": time.perf_counter() - started,
    }
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=["sample", "full"], default="sample")
    parser.add_argument("--output", type=Path, default=Path("evidence/sample"))
    parser.add_argument("--persist", action="store_true")
    args = parser.parse_args()
    scale = (8000000, 650000) if args.profile == "full" else (80000, 6500)
    result = run(*scale, args.output, persist=args.persist)
    print(
        json.dumps(
            {
                key: result[key]
                for key in ["events", "journeys", "dax_measures", "forecast", "elapsed_seconds"]
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
