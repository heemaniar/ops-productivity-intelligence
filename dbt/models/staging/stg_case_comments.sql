select
    case_number,
    seq,
    author_type,
    author,
    created_at,
    body
from {{ source('raw', 'fact_case_comments') }}
