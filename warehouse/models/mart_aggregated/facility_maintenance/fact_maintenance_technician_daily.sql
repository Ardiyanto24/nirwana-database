select
    assigned_staff_id,
    reported_date as period_date,
    count(*) as ticket_count,
    sum(labor_hours) as labor_hours
from {{ ref('mart_cleaned__maintenance_tickets') }}
where assigned_staff_id is not null
group by 1, 2
