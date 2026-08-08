-- Grain: property_id x period_date. Menggantikan fact_revenue_property_summary draf M5.2
-- (digabung ke sini, grain identik). MoM/YoY dihitung via self-join tanggal persis
-- (bukan LAG(n) baris, supaya tidak salah kalau ada gap tanggal).
with property_daily as (
    select
        property_id,
        period_date,
        safe_divide(sum(rooms_sold), nullif(sum(total_rooms_available), 0)) as occupancy_rate,
        safe_divide(sum(revenue), nullif(sum(rooms_sold), 0)) as adr,
        safe_divide(sum(revenue), nullif(sum(total_rooms_available), 0)) as revpar
    from {{ ref('fact_revenue_room_type_daily') }}
    group by 1, 2
),

with_growth as (
    select
        cur.property_id,
        cur.period_date,
        cur.occupancy_rate,
        cur.adr,
        cur.revpar,
        cur.occupancy_rate - mom.occupancy_rate as mom_occupancy_growth,
        cur.occupancy_rate - yoy.occupancy_rate as yoy_occupancy_growth,
        cur.adr - mom.adr as mom_adr_growth,
        cur.adr - yoy.adr as yoy_adr_growth,
        cur.revpar - mom.revpar as mom_revpar_growth,
        cur.revpar - yoy.revpar as yoy_revpar_growth
    from property_daily as cur
    left join property_daily as mom
        on cur.property_id = mom.property_id
        and mom.period_date = date_sub(cur.period_date, interval 1 month)
    left join property_daily as yoy
        on cur.property_id = yoy.property_id
        and yoy.period_date = date_sub(cur.period_date, interval 1 year)
),

guest_booking_rank as (
    select
        property_id,
        check_in_date as period_date,
        guest_id,
        row_number() over (partition by guest_id order by booking_date) as guest_booking_seq
    from {{ ref('mart_cleaned__bookings') }}
    where status in ('completed', 'confirmed') and guest_id is not null
),

repeat_guest as (
    select
        property_id,
        period_date,
        safe_divide(countif(guest_booking_seq > 1), count(*)) as repeat_guest_rate
    from guest_booking_rank
    group by 1, 2
),

lead_time as (
    select
        property_id,
        check_in_date as period_date,
        avg(date_diff(check_in_date, booking_date, day)) as avg_lead_time_days,
        approx_quantiles(date_diff(check_in_date, booking_date, day), 2)[offset(1)] as median_lead_time_days
    from {{ ref('mart_cleaned__bookings') }}
    where status in ('completed', 'confirmed')
    group by 1, 2
),

ranked as (
    select
        *,
        rank() over (partition by period_date order by revpar desc) as revpar_rank_group,
        rank() over (partition by period_date order by adr desc) as adr_rank_group,
        rank() over (partition by period_date order by occupancy_rate desc) as occupancy_rank_group
    from with_growth
)

select
    r.property_id,
    r.period_date,
    lt.avg_lead_time_days,
    lt.median_lead_time_days,
    r.mom_occupancy_growth,
    r.yoy_occupancy_growth,
    r.mom_adr_growth,
    r.yoy_adr_growth,
    r.mom_revpar_growth,
    r.yoy_revpar_growth,
    rg.repeat_guest_rate,
    r.revpar_rank_group,
    r.adr_rank_group,
    r.occupancy_rank_group
from ranked as r
left join repeat_guest as rg
    on r.property_id = rg.property_id and r.period_date = rg.period_date
left join lead_time as lt
    on r.property_id = lt.property_id and r.period_date = lt.period_date
