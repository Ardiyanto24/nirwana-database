select
    row_number() over (order by venue_type) as venue_type_id,
    venue_type as venue_type_name
from (
    select distinct venue_type
    from {{ ref('mart_cleaned__venues') }}
    where venue_type is not null
)
