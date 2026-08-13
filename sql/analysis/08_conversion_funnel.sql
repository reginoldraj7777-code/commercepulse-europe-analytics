-- Ordered funnel and step conversion.
select
    stage_order,
    stage,
    sessions,
    sessions::double precision
    / nullif(lag(sessions) over (order by stage_order), 0) as step_conversion,
    sessions::double precision
    / nullif(first_value(sessions) over (order by stage_order), 0) as overall_conversion
from growth.mart_funnel
order by stage_order;
