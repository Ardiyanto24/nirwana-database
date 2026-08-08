select
    row_number() over (order by reason) as reason_id,
    reason as reason_name
from (
    select distinct reason
    from {{ ref('mart_cleaned__pricing_history') }}
    where reason is not null
)
