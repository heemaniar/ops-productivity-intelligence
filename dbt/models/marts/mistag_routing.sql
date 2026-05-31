-- True vs recorded category — intake mis-routing heatmap. Off-diagonal cells are
-- tickets routed to the wrong queue at intake (~12% of volume); this is what the
-- LLM re-classification in ml_classify.py is designed to catch.
select
    category          as true_category,
    category_tagged   as recorded_category,
    count(*)          as volume,
    countif(is_mistagged) as mistagged_volume
from {{ ref('stg_cases') }}
group by true_category, recorded_category
