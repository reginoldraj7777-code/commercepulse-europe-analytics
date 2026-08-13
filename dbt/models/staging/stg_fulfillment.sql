select
    fulfillment_id::bigint as fulfillment_id,
    order_id::bigint as order_id,
    market_key::smallint as market_key,
    fulfillment_hub::text as fulfillment_hub,
    carrier::text as carrier,
    promised_delivery_date::date as promised_delivery_date,
    shipped_date::date as shipped_date,
    delivered_date::date as delivered_date,
    is_on_time::boolean as is_on_time,
    currency_code::text as currency_code,
    fx_local_per_eur::double precision as fx_local_per_eur,
    shipping_cost_local::double precision as shipping_cost_local,
    shipping_cost_local / nullif(fx_local_per_eur, 0) as shipping_cost_eur,
    loaded_at::timestamp as loaded_at
from {{ source('raw', 'fact_fulfillment') }}
