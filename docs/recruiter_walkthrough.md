# Recruiter walkthrough

## Five-minute path

1. Start with the README headline: revenue grew, contribution weakened, and the project answers why.
2. Open the Excel `Summary` sheet to see the decision framing, formula-backed cards, charts, and action queue.
3. Open the executed notebook and inspect the stored outputs for confidence intervals, diagnostics, forecast backtest, and actions.
4. Browse `sql/analysis/` to see 24 decision queries rather than tutorial fragments.
5. Inspect the Power BI folder: report definition, TMDL semantic model, 52 measures, relationships, theme, and six pages are all source-controlled.
6. Finish with `artifacts/validation` and the `Checks` workbook sheet to demonstrate trust controls.

## Fifteen-minute technical path

| Minute | Open | Demonstrate |
|---:|---|---|
| 0–2 | `config/profiles.yaml`, generator manifest | Deterministic scale, markets, currencies, seed, process shifts |
| 2–4 | `src/commercepulse/quality.py`, quarantine | Defects are deliberately injected, isolated, and measured |
| 4–7 | dbt finance marts | Atomic economics, residual spend allocation, reconciliations |
| 7–9 | SQL queries 03, 10, 13, 22, 24 | Windowing, cohorts, ordered-set aggregate, finance control, action queue |
| 9–12 | Notebook and decision brief | Statistical restraint, uncertainty, forecast backtest, recommendations |
| 12–14 | Power BI project | Governed semantic model and decision-oriented page flow |
| 14–15 | Excel checks/action sheets | Manager usability and operational follow-through |

## Questions this project answers

- How would you reconcile finance and marketing allocation?
- How do you distinguish a real operational defect from bad source data?
- What is the grain of every core fact and mart?
- Why can’t product category filter a session conversion measure in this model?
- How do you communicate uncertainty without blocking a decision?
- How does a finding become an owned action with a guardrail?

## Suggested live demo

```bash
python -m commercepulse.cli all --profile ci --data-root data/demo --artifact-root artifacts/demo
pytest
python scripts/validate_project.py
```

Then compare the new manifest and hashes to demonstrate deterministic generation. Use the committed `data/sample` path for the standard expected values.

## Honest boundary

The committed Power BI source is schema-validated, but a Linux-only build environment cannot perform a Power BI Desktop refresh or visual pixel comparison. The workbook and analytical charts are rendered and visually checked in the build environment. This distinction is deliberate and documented.
