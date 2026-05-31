-- Per case type: volume, handle time, FCR, reopen — the ticket-pattern
-- Pareto / bubble chart and the KB backlog table.
select
    category,
    subcategory,
    subject,
    count(*)                                              as volume,
    round(avg(handle_time_minutes), 1)                    as avg_handle_min,
    round(avg(if(is_first_contact_resolution, 1, 0)), 3)  as fcr_rate,
    round(avg(if(reopened_count > 0, 1, 0)), 3)           as reopen_rate,
    round(avg(if(sla_met, 1, 0)), 3)                      as sla_met_rate,
    any_value(kb_addressable)                             as kb_addressable
from {{ ref('fct_cases') }}
where status = 'Closed'
group by category, subcategory, subject
