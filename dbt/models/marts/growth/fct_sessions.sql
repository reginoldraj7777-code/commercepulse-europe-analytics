select
    s.*,
    d.month_start,
    d.week_start,
    m.market_code,
    m.market_name,
    c.channel_name,
    c.channel_group,
    case when s.converted_order_id is not null then 1 else 0 end as converted_session
from {{ ref('stg_sessions') }} as s
left join {{ ref('dim_date') }} as d using (date_key)
left join {{ ref('dim_market') }} as m using (market_key)
left join {{ ref('dim_channel') }} as c using (channel_key)
