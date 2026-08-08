select
    row_number() over (order by category) as category_id,
    category as category_name
from (
    select distinct category
    from {{ ref('mart_cleaned__fnb_transactions') }}
    where category is not null
)
