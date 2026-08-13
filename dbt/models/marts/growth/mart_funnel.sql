select
    1 as stage_order,
    'Sessions'::text as stage,
    count(distinct session_id) as sessions
from {{ ref('fct_sessions') }}
union all
select
    2 as stage_order,
    'Product view'::text as stage,
    count(distinct case when product_views > 0 then session_id end) as sessions
from {{ ref('fct_sessions') }}
union all
select
    3 as stage_order,
    'Added to cart'::text as stage,
    count(distinct case when added_to_cart then session_id end) as sessions
from {{ ref('fct_sessions') }}
union all
select
    4 as stage_order,
    'Checkout started'::text as stage,
    count(distinct case when checkout_started then session_id end) as sessions
from {{ ref('fct_sessions') }}
union all
select
    5 as stage_order,
    'Purchased'::text as stage,
    count(distinct case when converted_order_id is not null then session_id end) as sessions
from {{ ref('fct_sessions') }}
