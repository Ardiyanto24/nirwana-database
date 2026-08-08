select
    employee_id,
    review_period,
    score,
    notes
from {{ ref('mart_cleaned__employee_performance') }}
