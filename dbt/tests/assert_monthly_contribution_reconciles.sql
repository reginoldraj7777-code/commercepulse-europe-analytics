select *
from {{ ref('mart_monthly_executive') }}
where abs(
    contribution_margin_eur
    - (
        net_revenue_eur
        - cogs_eur
        + recovered_cogs_eur
        - return_handling_cost_eur
        - fulfillment_cost_eur
        - marketing_spend_eur
    )
) >= 0.02
