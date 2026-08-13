select
    return_id::bigint as return_id,
    order_id::bigint as order_id,
    order_item_id::bigint as order_item_id,
    return_date::date as return_date,
    return_reason::text as return_reason,
    units_returned::integer as units_returned,
    refund_local::double precision as refund_local,
    handling_cost_local::double precision as handling_cost_local,
    recovered_cogs_local::double precision as recovered_cogs_local,
    restockable::boolean as restockable,
    currency_code::text as currency_code,
    fx_local_per_eur::double precision as fx_local_per_eur,
    refund_local / nullif(fx_local_per_eur, 0) as refund_eur,
    handling_cost_local / nullif(fx_local_per_eur, 0) as handling_cost_eur,
    recovered_cogs_local / nullif(fx_local_per_eur, 0) as recovered_cogs_eur,
    loaded_at::timestamp as loaded_at
from {{ source('raw', 'fact_returns') }}
