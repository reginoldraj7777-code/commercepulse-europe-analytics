select
    date_trunc('month', spend_date)::date as month_start,
    market_key,
    channel_key,
    sum(spend_eur) as marketing_spend_eur,
    sum(impressions) as impressions,
    sum(clicks) as clicks
from {{ ref('stg_marketing_spend') }}
group by 1, 2, 3
