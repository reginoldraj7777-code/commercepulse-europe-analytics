select
    target_id::bigint as target_id,
    month_start::date as month_start,
    month_key::integer as month_key,
    market_key::smallint as market_key,
    channel_key::smallint as channel_key,
    net_revenue_target_eur::double precision as net_revenue_target_eur,
    contribution_margin_target_eur::double precision as contribution_margin_target_eur,
    orders_target::integer as orders_target,
    conversion_rate_target::double precision as conversion_rate_target,
    on_time_delivery_target::double precision as on_time_delivery_target,
    return_rate_guardrail::double precision as return_rate_guardrail,
    target_method::text as target_method
from {{ source('raw', 'fact_targets') }}
