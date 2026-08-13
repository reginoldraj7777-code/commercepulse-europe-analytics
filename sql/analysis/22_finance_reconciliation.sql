-- Prove the contribution formula from its atomic components.
select
    month_start,
    contribution_margin_eur,
    net_revenue_eur - cogs_eur + recovered_cogs_eur
    - return_handling_cost_eur - fulfillment_cost_eur - marketing_spend_eur
        as recomputed_contribution_margin_eur,
    contribution_margin_eur
    - (
        net_revenue_eur - cogs_eur + recovered_cogs_eur
        - return_handling_cost_eur - fulfillment_cost_eur - marketing_spend_eur
    ) as reconciliation_delta_eur
from finance.mart_monthly_executive
order by month_start;
