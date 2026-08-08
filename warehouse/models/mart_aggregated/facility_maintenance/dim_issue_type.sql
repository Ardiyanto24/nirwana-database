select
    row_number() over (order by issue_type) as issue_type_id,
    issue_type as issue_type_name
from (
    select distinct issue_type
    from {{ ref('mart_cleaned__maintenance_tickets') }}
    where issue_type is not null
)
