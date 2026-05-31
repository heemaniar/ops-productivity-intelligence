-- Per agent: volume, handle time, SLA, FCR, CSAT.
select
    agent_name,
    agent_role,
    specialization,
    count(*)                                              as cases,
    round(avg(handle_time_minutes), 1)                    as avg_handle_min,
    round(avg(if(sla_met, 1, 0)), 3)                      as sla_met_rate,
    round(avg(if(is_first_contact_resolution, 1, 0)), 3)  as fcr_rate,
    round(avg(csat_score), 2)                             as avg_csat
from {{ ref('fct_cases') }}
where status = 'Closed'
group by agent_name, agent_role, specialization
