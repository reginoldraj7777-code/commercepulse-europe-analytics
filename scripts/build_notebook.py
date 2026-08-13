from __future__ import annotations

import json
from pathlib import Path

import nbformat as nbf

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_ROOT = PROJECT_ROOT / "artifacts" / "analysis"
OUTPUT_PATH = PROJECT_ROOT / "notebooks" / "commercepulse_decision_analysis.ipynb"


def build_notebook() -> Path:
    summary = json.loads((ANALYSIS_ROOT / "executive_summary.json").read_text(encoding="utf-8"))
    headline = summary["headline"]
    comparison = summary["analysis_window"]["comparison"]
    top_driver = summary["top_negative_contribution_drivers"][0]
    notebook = nbf.v4.new_notebook()
    notebook["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12"},
    }
    notebook["cells"] = [
        nbf.v4.new_markdown_cell(
            f"""# CommercePulse Europe — Decision Analysis

## tl;dr

This reproducible notebook analyzes a **deterministic synthetic European commerce scenario**. ECB FX observations are real reference data; no result describes a real company.

- Comparison: **{comparison}**.
- Current-quarter net revenue: **EUR {headline['current_quarter_net_revenue_eur']:,.0f}** ({headline['net_revenue_change_pct']:+.1%} versus the prior quarter).
- Current-quarter contribution margin: **EUR {headline['current_quarter_contribution_margin_eur']:,.0f}**; margin rate moved **{headline['contribution_margin_rate_change_pp']:+.1f} pp**.
- Largest negative contribution driver: **{top_driver['dimension']}: {top_driver['dimension_value']}** (EUR {top_driver['delta_contribution_margin_eur']:,.0f}).
- Recommendation: protect profitable growth by addressing discount depth, North-hub delivery reliability, mobile latency, and replenishment exceptions with explicit guardrails.
"""
        ),
        nbf.v4.new_markdown_cell(
            """## Context & Methods

**Decision.** Where should commercial, product, operations, finance, and inventory leaders intervene to improve growth quality rather than revenue alone?

**Unit of analysis.** Atomic order items for profitability; sessions for conversion; order-item returns for refund economics; order fulfillment for SLA; product-market-month snapshots for inventory.

### Key Assumptions

- Last-touch channel attribution is descriptive, not causal incrementality.
- Contribution margin equals net revenue after discounts and refunds, less COGS, marketing, outbound fulfillment, and return handling, plus recoverable COGS.
- Rates use summed numerators and denominators; group rates are never averaged without weights.
- Logistic regression estimates associations and cannot establish causal lift.
- The forecast is a planning benchmark with out-of-sample backtesting, not a promise.
"""
        ),
        nbf.v4.new_code_cell(
            """from pathlib import Path
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

ROOT = Path.cwd()
if not (ROOT / 'artifacts' / 'analysis').exists():
    ROOT = ROOT.parent
ANALYSIS = ROOT / 'artifacts' / 'analysis'
VALIDATION = ROOT / 'artifacts' / 'validation'

monthly = pd.read_csv(ANALYSIS / 'monthly_kpis.csv', parse_dates=['month_start'])
overall = pd.read_csv(ANALYSIS / 'overall_kpis.csv')
funnel = pd.read_csv(ANALYSIS / 'funnel.csv')
cohort = pd.read_csv(ANALYSIS / 'cohort_retention.csv')
roots = pd.read_csv(ANALYSIS / 'root_causes.csv')
forecast = pd.read_csv(ANALYSIS / 'forecast.csv', parse_dates=['month_start'])
actions = pd.read_csv(ANALYSIS / 'action_register.csv')
reconciliation = pd.read_csv(ANALYSIS / 'reconciliations.csv')
summary = json.loads((ANALYSIS / 'executive_summary.json').read_text())

assert reconciliation['status'].eq('PASS').all()
print(f"Loaded {len(monthly)} monthly observations; all analytical reconciliations pass.")"""
        ),
        nbf.v4.new_markdown_cell("## Data"),
        nbf.v4.new_code_cell(
            """quality = json.loads((VALIDATION / 'data_quality_report.json').read_text())
quality_table = pd.DataFrame(quality['checks'])
display(quality_table[['table', 'check', 'status', 'observed', 'expected']])
assert quality['status'] == 'PASS'"""
        ),
        nbf.v4.new_markdown_cell("## Results"),
        nbf.v4.new_code_cell(
            """display(overall)
display(monthly.tail(6)[[
    'month_start', 'net_revenue_eur', 'net_revenue_target_attainment',
    'contribution_margin_eur', 'contribution_margin_rate', 'conversion_rate',
    'return_rate', 'on_time_delivery_rate', 'stockout_rate'
]])"""
        ),
        nbf.v4.new_code_cell(
            """fig, ax = plt.subplots(figsize=(10, 4.8))
ax.plot(monthly['month_start'], monthly['net_revenue_eur'], color='#2563EB', marker='o', label='Actual')
ax.plot(monthly['month_start'], monthly['net_revenue_target_eur'], color='#D99A16', linestyle='--', label='Target')
ax.set_title('Monthly net revenue and operating target')
ax.set_ylabel('EUR')
ax.spines[['top', 'right']].set_visible(False)
ax.grid(axis='y', color='#D9DEE8', linewidth=0.7)
ax.legend(frameon=False)
plt.show()"""
        ),
        nbf.v4.new_code_cell(
            """display(funnel[['stage_order', 'stage', 'sessions', 'stage_conversion', 'overall_conversion']])
fig, ax = plt.subplots(figsize=(8, 4.2))
view = funnel.sort_values('stage_order', ascending=False)
ax.barh(view['stage'], view['sessions'], color='#2563EB')
ax.set_title('Commerce conversion funnel')
ax.set_xlabel('Unique sessions')
ax.spines[['top', 'right']].set_visible(False)
plt.show()"""
        ),
        nbf.v4.new_code_cell(
            """matrix = cohort.pivot(index='cohort_month', columns='month_index', values='retention_rate').sort_index()
fig, ax = plt.subplots(figsize=(10, 5.5))
image = ax.imshow(matrix.to_numpy(), aspect='auto', cmap='Blues', vmin=0, vmax=1)
ax.set_yticks(np.arange(len(matrix.index)), labels=matrix.index)
ax.set_xticks(np.arange(len(matrix.columns)), labels=matrix.columns)
ax.set_title('Monthly purchasing-cohort retention')
ax.set_xlabel('Months since first purchase')
ax.set_ylabel('First-purchase cohort')
fig.colorbar(image, ax=ax)
plt.show()"""
        ),
        nbf.v4.new_code_cell(
            """negative = roots.nsmallest(10, 'delta_contribution_margin_eur').copy()
display(negative[[
    'dimension', 'dimension_value', 'delta_net_revenue_eur',
    'delta_contribution_margin_eur', 'delta_contribution_margin_rate_pp',
    'current_return_rate'
]])"""
        ),
        nbf.v4.new_code_cell(
            """display(forecast)
print('Backtest diagnostics:', summary['forecast_diagnostics'])
fig, ax = plt.subplots(figsize=(10, 4.8))
ax.plot(monthly['month_start'], monthly['net_revenue_eur'], color='#2563EB', label='Actual')
ax.plot(forecast['month_start'], forecast['forecast_net_revenue_eur'], color='#D99A16', marker='o', label='Forecast')
ax.fill_between(
    forecast['month_start'], forecast['forecast_lower_95_eur'],
    forecast['forecast_upper_95_eur'], color='#D99A16', alpha=0.18
)
ax.set_title('Three-month net-revenue forecast')
ax.set_ylabel('EUR')
ax.spines[['top', 'right']].set_visible(False)
ax.legend(frameon=False)
plt.show()"""
        ),
        nbf.v4.new_markdown_cell("## Takeaways"),
        nbf.v4.new_code_cell(
            """display(actions[['priority', 'owner', 'action', 'evidence', 'guardrail', 'review_cadence']])
assert actions['owner'].notna().all()
assert actions['guardrail'].notna().all()"""
        ),
        nbf.v4.new_markdown_cell(
            """The management response should sequence four actions: (1) margin discipline in the weakest category-channel mix, (2) North-hub SLA recovery, (3) mobile performance remediation in Sweden and the United Kingdom, and (4) targeted replenishment for the largest estimated stockout opportunity. Each action has an owner, review cadence, and guardrail in the action register.

The scenario supports prioritization, not causal claims. The next real-world step would be an owned pilot or experiment with pre-registered success metrics and guardrails."""
        ),
    ]
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(notebook, OUTPUT_PATH)
    return OUTPUT_PATH


if __name__ == "__main__":
    print(build_notebook())
