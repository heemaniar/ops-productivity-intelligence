-- Enriched case fact: one row per case, joined to the dimension seeds, with
-- date helpers + KB-period flag. This is the grain the Looker dashboard sits on.
with c as (
    select * from {{ ref('stg_cases') }}
)
select
    c.*,
    date(c.created_date)                                   as created_date_day,
    date_trunc(date(c.created_date), month)                as created_month,
    c.created_date >= timestamp('{{ var("kb_launch") }}')  as is_post_kb,
    cl.client_name,
    cl.segment,
    cl.region,
    cl.client_type,
    a.agent_name,
    a.role            as agent_role,
    a.specialization,
    v.vendor_name,
    v.product_lines
from c
left join {{ ref('dim_client') }} cl using (client_id)
left join {{ ref('dim_agent')  }} a  on a.agent_id = c.owner_agent_id
left join {{ ref('dim_vendor') }} v  using (vendor_id)
