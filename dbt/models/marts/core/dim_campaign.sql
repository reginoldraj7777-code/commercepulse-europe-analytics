select
    campaign_key::integer as campaign_key,
    campaign_name::text as campaign_name,
    market_key::smallint as market_key,
    channel_key::smallint as channel_key,
    campaign_type::text as campaign_type,
    is_promotion::boolean as is_promotion,
    start_date::date as start_date,
    end_date::date as end_date
from {{ source('raw', 'dim_campaign') }}
