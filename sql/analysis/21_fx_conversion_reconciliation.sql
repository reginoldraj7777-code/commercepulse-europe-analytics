-- Reconcile local-currency item revenue to the normalized EUR value.
select
    currency_code,
    count(*) as item_rows,
    sum(gross_revenue_local) as gross_revenue_local,
    sum(gross_revenue_eur) as gross_revenue_eur,
    sum(gross_revenue_local / nullif(fx_local_per_eur, 0) - gross_revenue_eur)
        as conversion_delta_eur
from staging.stg_order_items
group by currency_code
order by currency_code;
