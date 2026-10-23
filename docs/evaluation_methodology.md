# Evaluation methodology

## Three separate data scopes

1. Existing ten-market warehouse demo: original Pandera quarantine, PostgreSQL/dbt marts, Power BI and Excel.
2. New six-market scale profile: 8M event rows referencing 650K journeys. Stable IDs, evenly cycled markets/channels, synthetic engagement and synthetic order economics. This validates processing scale, not realistic customer behavior.
3. Independent 365-day daily demand fixture per market, with trend, weekday seasonality and Poisson noise. It does not consume the event stream.

## Provenance and quality

Seed 20261018; manifest includes UTC date, base commit, exact implementation SHA256, dependency/platform versions and partition hashes. Event key SHA256 hashes row-major little-endian int64 IDs, journey IDs, market codes and channel codes and is invariant to chunk size. Event IDs are contiguous and unique by construction. Tests independently read persisted Parquet and verify uniqueness and foreign keys. Row-pass denominator is 8M; validation groups cover FK bounds, market/channel domains and finite engagement in [0,1). No historical 99.5% SLA follows from this fixture.

## Forward evaluation

Train on days 0–336; hold out days 337–364 for all six markets. Fit ordinary least squares on an intercept, normalized time and six weekday indicators. No holdout targets enter fitting. Compare with the last training week repeated four times. WAPE = sum(abs(actual − prediction)) / sum(abs(actual)), pooled over 168 holdout points. No target-driven seed search or rounding to a résumé number. These results do not establish real-world demand accuracy.

## Decision scenarios

Retarget consenting journeys with 2–5 orders. Incremental contribution = historical modeled contribution/order × assumed incremental purchase probability − €0.35 per eligible contact. Report 2, 4 and 6 percentage-point sensitivity. This is not an estimated treatment effect or an annual forecast.

Inventory supply initially covers floor(94% of each market's demand). Allocate an integer budget equal to 40% of unmet units, prioritizing contribution/order minus €2 recovery cost. With equal unit costs and a linear objective, greedy allocation is optimal. Constraints prevent exceeding unmet demand or the budget; nonpositive margins receive no units. Report both total modeled recovery and the much smaller difference from equal allocation. Neither number is observed revenue.

The top value quintile comparison sorts by contribution then compares contribution / marketing spend against the full population. Selection by the outcome induces a large difference; it cannot support a claim of causal marketing optimization.
