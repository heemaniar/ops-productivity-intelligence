-- Cleaned case grain: explicit column list documents the contract; types are
-- already correct from the loader, so this is a light pass-through.
with source as (
    select * from {{ source('raw', 'fact_cases') }}
)
select
    case_id,
    case_number,
    created_date,
    first_response_at,
    closed_date,
    status,
    origin,
    priority,
    client_id,
    contact_name,
    owner_agent_id,
    vendor_id,
    product_line,
    product_type,
    case_type_id,
    category,                       -- true intent
    category_tagged,                -- recorded at intake (carries ~12% noise)
    is_mistagged,
    subcategory,
    subject,
    description,
    reason_code,
    first_response_minutes,
    handle_time_minutes,
    resolution_time_hours,
    reopened_count,
    escalated,
    sla_target_hours,
    sla_met,
    is_first_contact_resolution,
    csat_score,
    csat_comment,
    resolution_summary,
    kb_addressable
from source
