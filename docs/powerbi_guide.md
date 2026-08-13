# Power BI guide

## Open and refresh

1. Start PostgreSQL and build dbt marts:

   ```bash
   docker compose up -d postgres
   python -m commercepulse.cli load-postgres --input data/sample/clean
   dbt build --project-dir dbt --profiles-dir dbt
   ```

2. On Windows, open `powerbi/CommercePulse.pbip` in a current Power BI Desktop release.
3. Confirm parameters `Server = localhost` and `Database = commercepulse`.
4. Authenticate with the local PostgreSQL credentials from `.env.example`.
5. Refresh, inspect all six pages, and save locally. Do not commit local `.pbi` cache/settings or a generated `.pbix`.

## Source-controlled structure

| Path | Purpose |
|---|---|
| `CommercePulse.pbip` | Project entry point |
| `CommercePulse.SemanticModel/definition/` | TMDL database, model, expressions, relationships, 16 tables, 52 DAX measures |
| `CommercePulse.Report/definition/` | PBIR report, six pages, 36 visuals |
| `CommercePulse.Report/StaticResources/` | Custom theme |
| `scripts/build_powerbi_model.mjs` | Deterministic semantic-model builder |
| `scripts/build_powerbi_report.mjs` | Deterministic report-definition builder |

## Rebuild and validate

```bash
cd powerbi
npm ci
cd ..
node scripts/build_powerbi_model.mjs
node scripts/build_powerbi_report.mjs
powerbi/node_modules/.bin/powerbi-report-author --pretty validate powerbi/CommercePulse.pbip
```

Expected schema result: `succeeded`, zero errors, zero warnings.

## Governance notes

- The semantic model queries `portfolio` dbt marts through PostgreSQL import partitions.
- All leadership KPIs are explicit DAX measures with format strings and descriptions.
- The report avoids a product-filtered session conversion breakdown because session facts do not carry a product key.
- The report does not make causal claims for marketing attribution or page-load associations.
