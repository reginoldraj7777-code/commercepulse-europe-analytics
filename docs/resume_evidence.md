# Résumé evidence map

This extension was implemented in October 2026. It establishes current reproducibility, not past deployment or employment history.

| Résumé claim | Repository evidence | Boundary |
|---|---|---|
| 8M+ events / six markets | Full run: 8,000,000 events, DE/FR/IT/ES/NL/AT | Synthetic deterministic event stream |
| 650K+ journeys | 650,000 persisted journey rows | Synthetic customer/order summaries |
| 55+ executive measures | 57 definitions in TMDL and model generator | Added five unit-economics measures; refresh not run here |
| 99.5% quality gate pass | 100% of generated rows pass three documented validation groups | Different denominator; not historical operational reliability |
| 9.6% WAPE | 7.2609% on 168 held-out daily-market points | Exact 9.6% not reproduced; independent synthetic fixture |
| €320K+ annual contribution | €683,849.36 modeled inventory recovery | Scenario is not annualized or realized; lift over equal allocation only €605.75 |
| €180K retention upside | €203,943.17 at assumed 6 pp response gain, €0.35 contact cost | Assumption-sensitive; lower assumptions can lose money |
| 14% higher contribution / marketing euro | Quintile comparison included in manifest | Selection effect, not causal lift; exact 14% not established |
| Databricks | Runnable Delta ingestion notebook | Requires external workspace; execution unverified |

Start with [metrics.json](../evidence/full/metrics.json), then follow the CSVs, [implementation](../src/commercepulse/evidence.py), and [tests](../tests/test_evidence.py). Reproduction commands are in the main README.
