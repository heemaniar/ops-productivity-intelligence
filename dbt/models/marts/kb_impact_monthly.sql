-- Monthly handle-time / SLA / FCR split by KB-addressability.
-- Powers the headline "↑24%" before/after chart (reference line at kb_launch).
select
    created_month,
    kb_addressable,
    count(*)                                              as cases,
    round(avg(handle_time_minutes), 1)                    as avg_handle_min,
    round(avg(first_response_minutes), 1)                 as avg_first_response_min,
    round(avg(if(sla_met, 1, 0)), 3)                      as sla_met_rate,
    round(avg(if(is_first_contact_resolution, 1, 0)), 3)  as fcr_rate
from {{ ref('fct_cases') }}
where status = 'Closed'
group by created_month, kb_addressable
