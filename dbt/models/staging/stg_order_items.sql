select
    order_item_id::bigint as order_item_id,
    order_id::bigint as order_id,
    product_key::integer as product_key,
    quantity::integer as quantity,
    currency_code::text as currency_code,
    fx_local_per_eur::double precision as fx_local_per_eur,
    unit_price_local::double precision as unit_price_local,
    gross_revenue_local::double precision as gross_revenue_local,
    discount_local::double precision as discount_local,
    cogs_local::double precision as cogs_local,
    gross_revenue_local / nullif(fx_local_per_eur, 0) as gross_revenue_eur,
    discount_local / nullif(fx_local_per_eur, 0) as discount_eur,
    cogs_local / nullif(fx_local_per_eur, 0) as cogs_eur,
    loaded_at::timestamp as loaded_at
from {{ source('raw', 'fact_order_items') }}
