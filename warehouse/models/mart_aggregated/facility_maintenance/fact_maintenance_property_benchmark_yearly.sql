with tickets as (
    select
        property_id,
        extract(year from reported_date) as year,
        count(*) as ticket_count
    from {{ ref('mart_cleaned__maintenance_tickets') }}
    group by 1, 2
),

rooms_count as (
    select property_id, count(*) as room_count
    from {{ ref('mart_cleaned__rooms') }}
    group by 1
)

select
    t.property_id,
    t.year,
    safe_divide(t.ticket_count, nullif(r.room_count, 0)) as tickets_per_room,
    date_diff(date(t.year, 12, 31), p.opening_date, day) / 365.25 as building_age_years,
    safe_divide(
        safe_divide(t.ticket_count, nullif(r.room_count, 0)),
        nullif(date_diff(date(t.year, 12, 31), p.opening_date, day) / 365.25, 0)
    ) as tickets_per_room_normalized
from tickets as t
left join rooms_count as r
    on t.property_id = r.property_id
left join {{ ref('dim_property') }} as p
    on t.property_id = p.property_id
