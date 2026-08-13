select
    spend_id::bigint as spend_id,
    date_key::integer as date_key,
    spend_date::date as spend_date,
    market_key::smallint as market_key,
    channel_key::smallint as channel_key,
    campaign_key::integer as campaign_key,
    currency_code::text as currency_code,
    fx_local_per_eur::double precision as fx_local_per_eur,
    impressions::bigint as impressions,
    clicks::bigint as clicks,
    spend_local::double precision as spend_local,
    spend_local / nullif(fx_local_per_eur, 0) as spend_eur,
    loaded_at::timestamp as loaded_at
from {{ source('raw', 'fact_marketing_spend') }}
