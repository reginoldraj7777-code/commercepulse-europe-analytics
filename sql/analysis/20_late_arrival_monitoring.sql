-- Monitor retained late arrivals without treating them as invalid business events.
select
    date_trunc('week', session_ts)::date as week_start,
    count(*) as sessions,
    count(*) filter (where is_late_arrival) as late_arrivals,
    avg(is_late_arrival::integer) as late_arrival_rate,
    max(loaded_at - session_ts) as maximum_load_lag
from growth.fct_sessions
group by date_trunc('week', session_ts)
order by week_start;
