select
    channel_key::smallint as channel_key,
    channel_name::text as channel_name,
    channel_group::text as channel_group,
    is_paid::boolean as is_paid
from {{ source('raw', 'dim_channel') }}
