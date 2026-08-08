with counts as (
    select
        room_id,
        extract(year from reported_date) as year,
        count(*) as ticket_count
    from {{ ref('mart_cleaned__maintenance_tickets') }}
    where room_id is not null
    group by 1, 2
),

yearly_median as (
    select
        year,
        approx_quantiles(ticket_count, 2)[offset(1)] as median_ticket_count
    from counts
    group by 1
)

select
    c.room_id,
    c.year,
    c.ticket_count,
    safe_divide(c.ticket_count, nullif(m.median_ticket_count, 0)) as vs_median_ratio
from counts as c
left join yearly_median as m
    on c.year = m.year
