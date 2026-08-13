# Limitations

1. **Synthetic operations.** All business records and findings are generated. They demonstrate methods and decision design, not performance of a real company.
2. **Attribution is not incrementality.** Revenue and contribution by channel use last-touch assignment. A controlled test or causal design is required for incremental media claims.
3. **Root-cause cuts overlap.** Market, channel, and category diagnostics describe intersecting populations and cannot be summed as an additive bridge.
4. **Observational conversion model.** Load time, device, and market coefficients describe association after modeled controls; they do not prove causal lift.
5. **Forecast is a benchmark.** The trend/seasonal regression has limited history in the CI sample. Residual-based intervals omit structural shocks and parameter uncertainty.
6. **Stockout opportunity is estimated.** Lost units and revenue depend on generated demand assumptions and list prices; they are not booked sales.
7. **Returns can mature after the reporting date.** Recent cohorts/orders may have incomplete return observation windows in real deployments; the synthetic scenario simplifies this.
8. **FX is reference data.** ECB reference rates are suitable for analytical translation, not statutory accounting or trade execution.
9. **Local deployment.** Docker defaults and credentials are for development only. Production requires secret management, access control, encryption, backup, and monitoring.
10. **Power BI build boundary.** PBIP/PBIR/TMDL source and schemas are validated in Linux. Refresh, credential prompts, and final visual interaction require Power BI Desktop on Windows.
11. **Excel compatibility.** The workbook uses standard formulas, tables, comments, validation, conditional formatting, and charts; minor rendering differences may occur across Excel versions.

## What would change for production

- Replace generated facts with contracted source feeds and incremental ingestion.
- Add orchestration, observability, lineage catalog integration, and freshness SLAs.
- Implement row-level security and privacy review.
- Use finance-approved FX and close-period controls.
- Add experiment assignment and causal measurement for product/marketing actions.
- Expand forecast history and compare multiple time-series benchmarks.
