-- Compare mobile speed and conversion by market and month.
select
    month_start,
    market_code,
    count(*) as sessions,
    avg(page_load_ms) as average_page_load_ms,
    percentile_cont(0.9) within group (order by page_load_ms) as p90_page_load_ms,
    avg(converted_session) as conversion_rate
from growth.fct_sessions
where device_type = 'Mobile'
group by month_start, market_code
having count(*) >= 100
order by month_start asc, average_page_load_ms desc;
