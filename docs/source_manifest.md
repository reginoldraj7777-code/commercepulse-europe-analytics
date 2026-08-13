# Source manifest

| Source | Classification | Repository asset | Usage |
|---|---|---|---|
| CommercePulse dimensions and facts | Deterministic synthetic | `src/commercepulse/generator.py`, `data/sample/` | Portfolio business scenario |
| Scenario configuration | Authored configuration | `config/profiles.yaml` | Date range, scale, markets, currencies, seed |
| Quality rules | Authored controls | `config/data_quality_rules.yaml` | Critical validation thresholds |
| ECB euro reference rates | Real public reference data | `data/reference/ecb/eurofxref-hist.csv` | Convert generated GBP, PLN, SEK amounts to EUR |
| dbt transformations | Authored analytics logic | `dbt/models/` | Governed warehouse marts |
| SQL analyses | Authored analytics logic | `sql/analysis/` | Decision questions and exception queries |

Primary external source: [European Central Bank euro foreign-exchange reference rates](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html).

The exact sample table sizes and SHA-256 hashes are recorded in `data/sample/generation_manifest.json`. The manifest also records injected defects, known process shifts, profile settings, source URL, and disclosure.

## Classification rule

No generated business value should be described as an observed company fact. Only ECB exchange-rate observations are real. Derived findings are synthetic scenario findings.
