-- Grain: property_id x room_type_id x period_date. occupancy_rate/adr/revpar dari
-- daily_occupancy (grain aslinya sudah persis ini, tanpa channel -- lihat catatan
-- koreksi grain di desain-skema-mart-aggregated.md). Revenue & room_type_revenue_share_pct
-- dari bookings, di-GROUP BY room_type (bukan per channel).
with occupancy as (
    select
        property_id,
        room_type,
        date as period_date,
        rooms_sold,
        total_rooms_available,
        occupancy_rate,
        adr,
        revpar
    from {{ ref('mart_cleaned__daily_occupancy') }}
),

room_revenue as (
    select
        property_id,
        room_type,
        check_in_date as period_date,
        sum(total_amount) as revenue
    from {{ ref('mart_cleaned__bookings') }}
    where status in ('completed', 'confirmed')
    group by 1, 2, 3
),

room_revenue_with_share as (
    select
        *,
        safe_divide(revenue, sum(revenue) over (partition by property_id, period_date)) as room_type_revenue_share_pct
    from room_revenue
)

select
    o.property_id,
    rt.room_type_id,
    o.period_date,
    o.rooms_sold,
    o.total_rooms_available,
    o.occupancy_rate,
    o.adr,
    o.revpar,
    r.revenue,
    r.room_type_revenue_share_pct
from occupancy as o
left join room_revenue_with_share as r
    on o.property_id = r.property_id
    and o.room_type = r.room_type
    and o.period_date = r.period_date
left join {{ ref('dim_room_type') }} as rt
    on o.room_type = rt.room_type_name
