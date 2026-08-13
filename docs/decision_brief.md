# Decision brief

## Executive decision

Protect Q2 growth while restoring contribution economics. The recommended sequence is to correct paid-channel/category pricing first, stabilize German delivery operations, remediate mobile performance in Sweden and the United Kingdom, and improve German electronics replenishment.

## Evidence from the CI scenario

| Signal | Result | Interpretation |
|---|---:|---|
| Q2 net revenue | €582,689 | +12.8% QoQ; demand remains healthy |
| Q2 contribution margin | €39,715 | Down €52,168 QoQ |
| Q2 margin rate | 6.8% | Down 11.0 percentage points |
| Paid Search contribution change | -€23,145 | Largest channel loss |
| Electronics contribution change | -€22,731 | Largest category loss |
| Germany contribution change | -€18,406 | Largest market loss |
| Forecast holdout WAPE | 9.9% | Useful benchmark with material uncertainty |

The root-cause findings are additive diagnostic cuts, not a causal decomposition. A market, channel, and category can describe the same underlying orders; their changes must not be summed together.

## Action queue

| Priority | Owner | Action | Expected impact | Guardrail |
|---|---|---|---|---|
| P0 | Commercial Director | Reprice and cap discounts for Electronics in Paid Search | Recover 1–2 margin-rate points in affected mix | Orders and 30-day return rate not worse by >5% |
| P0 | Operations Director | Delivery-SLA recovery for Germany and North hub | Move on-time rate toward 94%; reduce late-delivery returns | Shipping cost/order increase ≤€0.50 |
| P1 | Head of E-commerce | Mobile performance remediation in Sweden and UK | Improve checkout completion without more media | Use Wilson CIs; require experiment for causality |
| P1 | Inventory Planning Lead | Raise reorder coverage for Electronics in Germany | Recover estimated lost demand | Monitor days of supply and aged inventory |

## Measurement plan

1. Establish pre-action baselines by market, channel, category, and device.
2. Review P0 actions weekly for six weeks.
3. Track contribution margin rate as the primary outcome.
4. Track orders, return rate, shipping cost/order, and aged inventory as guardrails.
5. For mobile changes, run a controlled experiment where feasible; otherwise report association only.
6. Update the action register status and evidence link after every review.

## Caveats

All operating data and findings are synthetic. Attribution is last touch. Forecast intervals are residual-based and do not capture every business shock. See [limitations.md](limitations.md).
